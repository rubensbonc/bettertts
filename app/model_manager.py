import threading
import traceback
from enum import Enum
from typing import Callable, Optional, Tuple

import numpy as np

from app.constants import MODEL_VARIANTS, MODEL_VARIANT_MAP, ModelVariant


class ModelState(Enum):
    UNLOADED = "unloaded"
    DOWNLOADING = "downloading"
    LOADING = "loading"
    READY = "ready"
    ERROR = "error"


class ModelManager:
    def __init__(self, on_state_change: Optional[Callable] = None):
        self._lock = threading.Lock()
        self._model = None
        self._current_variant: Optional[ModelVariant] = None
        self._state = ModelState.UNLOADED
        self._error_message = ""
        self._on_state_change = on_state_change

    @property
    def state(self) -> ModelState:
        return self._state

    @property
    def current_variant(self) -> Optional[ModelVariant]:
        return self._current_variant

    @property
    def error_message(self) -> str:
        return self._error_message

    def _set_state(self, state: ModelState, error: str = ""):
        self._state = state
        self._error_message = error
        if self._on_state_change:
            try:
                self._on_state_change(state, error)
            except Exception:
                pass

    def _write_error_log(self, context: str = ""):
        """Write full traceback to model_error.log next to the exe."""
        try:
            from app.updater import get_base_dir
            log_path = get_base_dir() / "model_error.log"
            with open(log_path, "w", encoding="utf-8") as f:
                f.write(f"=== Model Error Log ===\n")
                if context:
                    f.write(f"Context: {context}\n")
                f.write("\n")
                traceback.print_exc(file=f)
            print(f"[BetterTTS] Error details written to: {log_path}")
        except Exception as log_err:
            print(f"[BetterTTS] Could not write error log: {log_err}")

    def load_model(self, variant_id: str):
        """Load a model. Call this from a background thread."""
        with self._lock:
            # Unload current model if any
            if self._model is not None:
                self._unload_internal()

            variant = MODEL_VARIANT_MAP.get(variant_id)
            if not variant:
                self._set_state(ModelState.ERROR, f"Unknown model: {variant_id}")
                return

            self._current_variant = variant
            self._set_state(ModelState.DOWNLOADING)

            try:
                import torch
                from qwen_tts import Qwen3TTSModel
                from app.gpu_detect import get_torch_device

                self._set_state(ModelState.LOADING)

                device = get_torch_device()

                # Pick best dtype for the device
                if "cuda" in device:
                    dtype = torch.bfloat16 if torch.cuda.is_bf16_supported() else torch.float16
                else:
                    dtype = torch.float32 if device == "cpu" else torch.float16

                print(f"[BetterTTS] Loading model {variant_id} on {device} with {dtype}")

                try:
                    self._model = Qwen3TTSModel.from_pretrained(
                        variant.hf_repo,
                        device_map=device,
                        dtype=dtype,
                    )
                    # Quick sanity check for CUDA kernel availability
                    if "cuda" in device:
                        test = torch.zeros(1, device=device)
                        del test
                except RuntimeError as cuda_err:
                    err_msg = str(cuda_err).lower()
                    if "no kernel image" in err_msg or "cuda error" in err_msg or "cusolver" in err_msg:
                        print(f"[BetterTTS] CUDA failed on this GPU: {cuda_err}")
                        print(f"[BetterTTS] Falling back to CPU mode...")
                        self._model = None
                        torch.cuda.empty_cache()
                        device = "cpu"
                        dtype = torch.float32
                        self._model = Qwen3TTSModel.from_pretrained(
                            variant.hf_repo,
                            device_map=device,
                            dtype=dtype,
                        )
                        print(f"[BetterTTS] CPU fallback successful.")
                    else:
                        raise

                self._set_state(ModelState.READY)
                print(f"[BetterTTS] Model loaded on {device} with {dtype}")

            except OSError as e:
                # OSError covers Errno 22 (invalid argument), Errno 2 (file not found) etc.
                # Write detailed log so we can see exactly which file/path caused it
                self._write_error_log(f"OSError loading {variant_id}: {e}")
                self._set_state(ModelState.ERROR, f"OS Error: {e}\n\nSee model_error.log next to BetterTTS.exe for details.")
                self._model = None

            except Exception as e:
                self._write_error_log(f"Exception loading {variant_id}: {e}")
                self._set_state(ModelState.ERROR, f"{type(e).__name__}: {e}\n\nSee model_error.log next to BetterTTS.exe for details.")
                self._model = None

    def unload_model(self):
        with self._lock:
            self._unload_internal()

    def _unload_internal(self):
        if self._model is not None:
            del self._model
            self._model = None
            try:
                import torch
                if torch.cuda.is_available():
                    torch.cuda.empty_cache()
            except Exception:
                pass
        self._current_variant = None
        self._set_state(ModelState.UNLOADED)

    def generate(
        self,
        text: str,
        speaker: str = "Ryan",
        language: str = "English",
        instruct: str = "",
        ref_audio: str = "",
        ref_text: str = "",
    ) -> Tuple[np.ndarray, int]:
        """Generate audio. Returns (wav_array, sample_rate). Thread-safe."""
        with self._lock:
            if self._state != ModelState.READY or self._model is None:
                raise RuntimeError(f"Model not ready (state: {self._state.value})")

            vtype = self._current_variant.variant_type

            print(f"[BetterTTS] Generating: text='{text[:80]}', speaker={speaker}, lang={language}, type={vtype}")

            try:
                if vtype == "custom_voice":
                    wavs, sr = self._model.generate_custom_voice(
                        text=text,
                        language=language,
                        speaker=speaker,
                        instruct=instruct or None,
                    )
                elif vtype == "base":
                    if not ref_audio:
                        raise ValueError(
                            "Voice cloning requires a reference audio file. "
                            "Please create a voice profile in the Profiles tab."
                        )
                    wavs, sr = self._model.generate_voice_clone(
                        text=text,
                        language=language,
                        ref_audio=ref_audio,
                        ref_text=ref_text or "",
                    )
                elif vtype == "voice_design":
                    if not instruct:
                        raise ValueError(
                            "VoiceDesign requires a voice description in the instruct field. "
                            "Example: 'A warm female voice with a British accent'"
                        )
                    wavs, sr = self._model.generate_voice_design(
                        text=text,
                        language=language,
                        instruct=instruct,
                    )
                else:
                    raise ValueError(f"Unknown variant type: {vtype}")

            except Exception as e:
                self._write_error_log(f"Exception during generate: {e}")
                raise

            print(f"[BetterTTS] Model returned: {len(wavs)} wav(s), sample_rate={sr}")
            wav = wavs[0]
            print(f"[BetterTTS] wav shape={wav.shape}, dtype={wav.dtype}, min={wav.min():.6f}, max={wav.max():.6f}")

            if np.abs(wav).max() < 1e-6:
                print("[BetterTTS] WARNING: Generated audio is silent (all zeros)!")

            peak = np.abs(wav).max()
            if peak > 0:
                wav = wav / peak * 0.95

            print(f"[BetterTTS] Returning {len(wav)} samples ({len(wav)/sr:.2f}s) at {sr}Hz")
            return wav, sr