import json
import sys
import shutil
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Optional


def get_base_dir() -> Path:
    """Get the real app directory whether running frozen (PyInstaller) or as a script."""
    if getattr(sys, 'frozen', False):
        return Path(sys.executable).parent
    else:
        return Path(__file__).parent.parent


APP_DIR = get_base_dir()
VOICES_DIR = APP_DIR / "voices"
PROFILES_PATH = APP_DIR / "profiles.json"


@dataclass
class VoiceProfile:
    name: str
    audio_file: str  # Relative path inside voices/ dir
    transcript: str


class VoiceProfileManager:
    def __init__(self):
        VOICES_DIR.mkdir(exist_ok=True)
        self._profiles: list[VoiceProfile] = []
        self._active_name: Optional[str] = None
        self._load()

    def _load(self):
        if PROFILES_PATH.exists():
            try:
                with open(PROFILES_PATH, "r", encoding="utf-8") as f:
                    data = json.load(f)
                self._profiles = [VoiceProfile(**p) for p in data.get("profiles", [])]
                self._active_name = data.get("active_profile")
            except (json.JSONDecodeError, OSError, TypeError):
                self._profiles = []
                self._active_name = None

    def _save(self):
        data = {
            "profiles": [asdict(p) for p in self._profiles],
            "active_profile": self._active_name,
        }
        with open(PROFILES_PATH, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)

    @property
    def profiles(self) -> list[VoiceProfile]:
        return list(self._profiles)

    @property
    def active_profile(self) -> Optional[VoiceProfile]:
        if self._active_name is None:
            return None
        for p in self._profiles:
            if p.name == self._active_name:
                return p
        return None

    @property
    def active_name(self) -> Optional[str]:
        return self._active_name

    def get_profile(self, name: str) -> Optional[VoiceProfile]:
        for p in self._profiles:
            if p.name == name:
                return p
        return None

    def create_profile(self, name: str, source_audio_path: str, transcript: str) -> VoiceProfile:
        """Create a new voice profile. Copies the audio file into voices/ directory."""
        if not name.strip():
            raise ValueError("Profile name cannot be empty")
        if self.get_profile(name):
            raise ValueError(f"Profile '{name}' already exists")

        source = Path(source_audio_path)
        if not source.exists():
            raise FileNotFoundError(f"Audio file not found: {source_audio_path}")

        # Copy audio to voices/ with a safe filename
        safe_name = "".join(c if c.isalnum() or c in "-_" else "_" for c in name)
        dest_filename = f"{safe_name}{source.suffix}"
        dest = VOICES_DIR / dest_filename

        # Handle collision
        counter = 1
        while dest.exists():
            dest_filename = f"{safe_name}_{counter}{source.suffix}"
            dest = VOICES_DIR / dest_filename
            counter += 1

        shutil.copy2(source, dest)

        profile = VoiceProfile(
            name=name,
            audio_file=dest_filename,
            transcript=transcript.strip(),
        )
        self._profiles.append(profile)
        self._save()
        return profile

    def delete_profile(self, name: str):
        profile = self.get_profile(name)
        if not profile:
            return

        # Delete the copied audio file
        audio_path = VOICES_DIR / profile.audio_file
        if audio_path.exists():
            audio_path.unlink()

        self._profiles = [p for p in self._profiles if p.name != name]
        if self._active_name == name:
            self._active_name = None
        self._save()

    def set_active(self, name: Optional[str]):
        if name is not None and not self.get_profile(name):
            raise ValueError(f"Profile '{name}' not found")
        self._active_name = name
        self._save()

    def get_audio_path(self, profile: VoiceProfile) -> str:
        """Get the absolute path to a profile's audio file."""
        return str(VOICES_DIR / profile.audio_file)