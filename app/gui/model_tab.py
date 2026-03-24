import threading
import customtkinter as ctk

from app.constants import MODEL_VARIANTS, MODEL_VARIANT_MAP
from app.model_manager import ModelState
import app.gui.theme as theme
from app.gui.theme import C, F, BTN_PRIMARY, BTN_SECONDARY, BTN_DANGER, card
from app.gui.widgets import SectionHeader, InfoLabel, CardFrame


class ModelTab:
    def __init__(self, parent: ctk.CTkFrame, app):
        self.app = app
        self.parent = parent
        self._build()
        self._update_description()

    def _build(self):
        scroll = ctk.CTkScrollableFrame(
            self.parent, fg_color="transparent",
            scrollbar_button_color=C.BG_INPUT,
            scrollbar_button_hover_color=C.ACCENT,
        )
        scroll.pack(fill="both", expand=True)
        p = scroll

        # ── Model selection card ────────────────────────────
        sel_card = CardFrame(p)
        sel_card.pack(fill="x", padx=16, pady=(16, 0))

        SectionHeader(sel_card, text="Select Model").pack(
            anchor="w", padx=16, pady=(14, 4))

        InfoLabel(sel_card, text=(
            "Choose which Qwen3-TTS model to load. Larger models produce better quality "
            "but need more VRAM and are slower. CustomVoice has preset speakers; "
            "Base lets you clone any voice; VoiceDesign creates voices from descriptions."
        )).pack(anchor="w", padx=16, pady=(0, 10))

        display_names = [v.display_name for v in MODEL_VARIANTS]
        current_id = self.app.config_data.get("model_id", "custom-voice-0.6b")
        current_variant = MODEL_VARIANT_MAP.get(current_id, MODEL_VARIANTS[0])

        self.model_var = ctk.StringVar(value=current_variant.display_name)
        self.model_menu = ctk.CTkOptionMenu(
            sel_card, variable=self.model_var, values=display_names,
            command=self._on_model_select, width=380, height=34,
            fg_color=C.BG_INPUT, button_color=C.ACCENT,
            button_hover_color=C.ACCENT_HOVER,
            dropdown_fg_color=C.BG_CARD, dropdown_hover_color=C.BG_HOVER,
            corner_radius=8, font=F.BODY,
        )
        self.model_menu.pack(anchor="w", padx=16, pady=(0, 14))

        # ── Description card ────────────────────────────────
        desc_card = CardFrame(p)
        desc_card.pack(fill="x", padx=16, pady=(10, 0))

        self.desc_label = ctk.CTkLabel(
            desc_card, text="", font=F.BODY_SM, text_color=C.TEXT_SEC,
            justify="left", anchor="nw", wraplength=theme.WRAP_CONTENT,
        )
        self.desc_label.pack(padx=16, pady=(12, 4), anchor="w")

        self.vram_warning = ctk.CTkLabel(
            desc_card, text="", font=("Segoe UI", 12, "bold"),
            text_color=C.WARNING, anchor="w",
        )
        self.vram_warning.pack(padx=16, pady=(0, 12), anchor="w")

        # ── Load / Unload buttons ───────────────────────────
        btn_frame = ctk.CTkFrame(p, fg_color="transparent")
        btn_frame.pack(fill="x", padx=16, pady=(12, 0))

        self.load_btn = ctk.CTkButton(
            btn_frame, text="Load Model", command=self._load_clicked,
            width=160, height=38, **BTN_PRIMARY,
            font=("Segoe UI", 13, "bold"),
        )
        self.load_btn.pack(side="left", padx=(0, 10))

        self.unload_btn = ctk.CTkButton(
            btn_frame, text="Unload Model", command=self._unload_clicked,
            width=140, height=38, state="disabled",
            fg_color="#334155", hover_color="#475569",
            text_color=C.TEXT_SEC, corner_radius=8,
        )
        self.unload_btn.pack(side="left")

        # Status
        self.status_label = ctk.CTkLabel(
            p, text="No model loaded", font=F.BODY,
            text_color=C.TEXT_DIM, anchor="w",
        )
        self.status_label.pack(anchor="w", padx=16, pady=(8, 16))

    def _get_selected_variant(self):
        name = self.model_var.get()
        for v in MODEL_VARIANTS:
            if v.display_name == name:
                return v
        return MODEL_VARIANTS[0]

    def _on_model_select(self, _=None):
        self._update_description()
        variant = self._get_selected_variant()
        self.app.config_data["model_id"] = variant.id
        self.app.save()

    def _update_description(self):
        variant = self._get_selected_variant()
        self.desc_label.configure(text=variant.description)

        gpu_vram = self.app.gpu_info.get("vram_gb", 0)
        if not self.app.gpu_info["available"]:
            self.vram_warning.configure(
                text="No GPU detected - model will run on CPU (very slow)",
                text_color=C.ERROR,
            )
        elif gpu_vram < variant.vram_min_gb:
            self.vram_warning.configure(
                text=f"Your GPU has {gpu_vram} GB VRAM but this model needs {variant.vram_estimate}. May run out of memory.",
                text_color=C.WARNING,
            )
        else:
            self.vram_warning.configure(
                text=f"Your GPU ({gpu_vram} GB VRAM) meets the requirement ({variant.vram_estimate}).",
                text_color=C.SUCCESS,
            )

    def _load_clicked(self):
        variant = self._get_selected_variant()
        self.load_btn.configure(state="disabled", text="Loading...")
        self.model_menu.configure(state="disabled")
        thread = threading.Thread(
            target=self.app.model_manager.load_model,
            args=(variant.id,),
            daemon=True,
        )
        thread.start()

    def load_selected_model(self):
        self._load_clicked()

    def _unload_clicked(self):
        self.unload_btn.configure(state="disabled", text="Unloading...")
        self.load_btn.configure(state="disabled")
        threading.Thread(
            target=self.app.model_manager.unload_model,
            daemon=True,
        ).start()

    def update_state(self, state: ModelState, error: str):
        try:
            if state == ModelState.READY:
                variant = self.app.model_manager.current_variant
                self.status_label.configure(
                    text=f"Model loaded: {variant.display_name}" if variant else "Model ready",
                    text_color=C.SUCCESS,
                )
                # Load button goes grey (inactive) — model is already loaded
                self.load_btn.configure(
                    state="disabled", text="Load Model",
                    fg_color=C.BG_INPUT, hover_color=C.BG_INPUT,
                    text_color=C.TEXT_DIM,
                )
                # Unload button goes red (active)
                self.unload_btn.configure(
                    state="normal", text="Unload Model",
                    fg_color=C.ERROR_DIM, hover_color=C.ERROR,
                    text_color="#ffffff",
                )
                self.model_menu.configure(state="disabled")

            elif state == ModelState.DOWNLOADING:
                self.status_label.configure(
                    text="Downloading model (first time only, this may take a few minutes)...",
                    text_color=C.WARNING,
                )
                self.load_btn.configure(state="disabled", text="Downloading...")
                self.unload_btn.configure(state="disabled")
                self.model_menu.configure(state="disabled")

            elif state == ModelState.LOADING:
                self.status_label.configure(
                    text="Loading model onto GPU...", text_color=C.WARNING,
                )
                self.load_btn.configure(state="disabled", text="Loading...")
                self.unload_btn.configure(state="disabled")
                self.model_menu.configure(state="disabled")

            elif state == ModelState.ERROR:
                self.status_label.configure(
                    text=f"Error: {error[:200]}", text_color=C.ERROR,
                )
                self.load_btn.configure(
                    state="normal", text="Retry Load",
                    fg_color=C.ACCENT, hover_color=C.ACCENT_HOVER,
                    text_color="#ffffff",
                )
                self.unload_btn.configure(
                    state="disabled", text="Unload Model",
                    fg_color="#334155", hover_color="#475569",
                    text_color=C.TEXT_SEC,
                )
                self.model_menu.configure(state="normal")

            elif state == ModelState.UNLOADED:
                self.status_label.configure(
                    text="No model loaded", text_color=C.TEXT_DIM,
                )
                # Load button goes back to primary blue (active)
                self.load_btn.configure(
                    state="normal", text="Load Model",
                    fg_color=C.ACCENT, hover_color=C.ACCENT_HOVER,
                    text_color="#ffffff",
                )
                # Unload button goes secondary (grey) — nothing loaded, safe state
                self.unload_btn.configure(
                    state="disabled", text="Unload Model",
                    fg_color="#334155", hover_color="#475569",
                    text_color=C.TEXT_SEC,
                )
                self.model_menu.configure(state="normal")

            # Force tkinter to process the UI update immediately
            self.parent.update_idletasks()

        except Exception as e:
            # Widget may have been destroyed — ignore
            print(f"[ModelTab] update_state error: {e}")