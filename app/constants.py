from dataclasses import dataclass


@dataclass
class ModelVariant:
    id: str
    hf_repo: str
    display_name: str
    description: str
    variant_type: str  # "custom_voice" | "base" | "voice_design"
    size_label: str
    vram_estimate: str
    vram_min_gb: float
    supports_speakers: bool
    supports_cloning: bool
    supports_voice_design: bool


MODEL_VARIANTS = [
    ModelVariant(
        id="custom-voice-0.6b",
        hf_repo="Qwen/Qwen3-TTS-12Hz-0.6B-CustomVoice",
        display_name="CustomVoice 0.6B  (Lightweight)",
        description=(
            "9 preset speakers with style/tone control via instructions.\n"
            "Best choice for most streamers - fast generation, low VRAM.\n"
            "Requires: 4-6 GB VRAM  |  Download: ~2.5 GB"
        ),
        variant_type="custom_voice",
        size_label="0.6B",
        vram_estimate="4-6 GB",
        vram_min_gb=4.0,
        supports_speakers=True,
        supports_cloning=False,
        supports_voice_design=False,
    ),
    ModelVariant(
        id="custom-voice-1.7b",
        hf_repo="Qwen/Qwen3-TTS-12Hz-1.7B-CustomVoice",
        display_name="CustomVoice 1.7B  (Higher Quality)",
        description=(
            "Same 9 preset speakers, noticeably better voice quality.\n"
            "Better tone control and more natural prosody.\n"
            "Requires: 6-8 GB VRAM  |  Download: ~4.5 GB"
        ),
        variant_type="custom_voice",
        size_label="1.7B",
        vram_estimate="6-8 GB",
        vram_min_gb=6.0,
        supports_speakers=True,
        supports_cloning=False,
        supports_voice_design=False,
    ),
    ModelVariant(
        id="base-0.6b",
        hf_repo="Qwen/Qwen3-TTS-12Hz-0.6B-Base",
        display_name="Base 0.6B  (Voice Cloning)",
        description=(
            "Clone ANY voice from a short audio clip (5-15 seconds).\n"
            "Create voice profiles to reuse cloned voices.\n"
            "Requires: 4-6 GB VRAM  |  Download: ~2.5 GB"
        ),
        variant_type="base",
        size_label="0.6B",
        vram_estimate="4-6 GB",
        vram_min_gb=4.0,
        supports_speakers=False,
        supports_cloning=True,
        supports_voice_design=False,
    ),
    ModelVariant(
        id="base-1.7b",
        hf_repo="Qwen/Qwen3-TTS-12Hz-1.7B-Base",
        display_name="Base 1.7B  (Voice Cloning, Higher Quality)",
        description=(
            "Clone ANY voice with better fidelity and naturalness.\n"
            "Best choice if you want high-quality cloned voices.\n"
            "Requires: 6-8 GB VRAM  |  Download: ~4.5 GB"
        ),
        variant_type="base",
        size_label="1.7B",
        vram_estimate="6-8 GB",
        vram_min_gb=6.0,
        supports_speakers=False,
        supports_cloning=True,
        supports_voice_design=False,
    ),
    ModelVariant(
        id="voice-design-1.7b",
        hf_repo="Qwen/Qwen3-TTS-12Hz-1.7B-VoiceDesign",
        display_name="VoiceDesign 1.7B  (Create Voices from Text)",
        description=(
            "Describe a voice in words and the AI creates it.\n"
            "Example: 'A warm female voice with a slight British accent'\n"
            "No reference audio needed. Requires: 6-8 GB VRAM  |  Download: ~4.5 GB"
        ),
        variant_type="voice_design",
        size_label="1.7B",
        vram_estimate="6-8 GB",
        vram_min_gb=6.0,
        supports_speakers=False,
        supports_cloning=False,
        supports_voice_design=True,
    ),
]

MODEL_VARIANT_MAP = {v.id: v for v in MODEL_VARIANTS}

SPEAKERS = [
    "Ryan", "Aiden", "Vivian", "Serena", "Uncle_Fu",
    "Dylan", "Eric", "Ono_Anna", "Sohee",
]

SPEAKER_INFO = {
    "Ryan": "Dynamic male, strong rhythm (English native) - Great default for English streams",
    "Aiden": "Bright American male, clear midrange (English native)",
    "Vivian": "Bright, slightly sharp young female (Chinese native)",
    "Serena": "Warm, soft young female (Chinese native)",
    "Uncle_Fu": "Seasoned male, low mellow timbre (Chinese native)",
    "Dylan": "Youthful male, clear natural timbre (Chinese native)",
    "Eric": "Lively male, slightly husky brightness (Chinese native)",
    "Ono_Anna": "Lively female (Japanese native)",
    "Sohee": "Warm female, rich emotion (Korean native)",
}

LANGUAGES = [
    "English", "Chinese", "Japanese", "Korean", "German",
    "French", "Russian", "Portuguese", "Spanish", "Italian",
]

DEFAULT_PORT = 7861

APP_VERSION = "0.0.1"

# Supported Python versions as (major, minor) tuples.
# Bootstrap reads this to validate the running Python version.
# Add or remove entries here to change what versions are accepted.
SUPPORTED_PYTHON_VERSIONS = [
    (3, 10),
    (3, 11),
    (3, 12),
]