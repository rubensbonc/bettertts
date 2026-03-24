import threading
import webbrowser
import customtkinter as ctk

from app.config import load_config, save_config
from app.gpu_detect import get_gpu_info
from app.model_manager import ModelManager, ModelState
from app.voice_profiles import VoiceProfileManager
from app.server import ServerManager
import app.gui.theme as theme
from app.gui.theme import C, F, apply_window_theme, card
from app.gui.server_tab import ServerTab
from app.gui.model_tab import ModelTab
from app.gui.voice_tab import VoiceTab
from app.gui.profiles_tab import ProfilesTab


class AppWindow(ctk.CTk):
    def __init__(self, updater=None):
        super().__init__()
        self.title("BetterTTS")
        self._icon_path = None
        apply_window_theme(self)

        # Set window icon after window is fully initialized
        try:
            from app.updater import get_base_dir
            icon_path = get_base_dir() / "icon.ico"
            if icon_path.exists():
                self._icon_path = str(icon_path)
                self.after(0, self._set_icon)
        except Exception:
            pass

        self.config_data = load_config()
        self.gpu_info = get_gpu_info()

        # Core services
        self.model_manager = ModelManager(on_state_change=self._on_model_state_change)
        self.profile_manager = VoiceProfileManager()
        self.server_manager = ServerManager(
            self.model_manager, self.profile_manager,
            config_data=self.config_data,
            port=self.config_data["port"],
        )

        # Updater passed in from main.py so it's available immediately
        self.updater = updater
        self._update_banner = None
        self._pending_update_version = None

        self._build_header()
        self._build_gpu_bar()

        # Tabs
        self.tabview = ctk.CTkTabview(
            self, anchor="nw",
            fg_color=C.BG_DARK,
            segmented_button_fg_color=C.BG_CARD,
            segmented_button_selected_color=C.ACCENT,
            segmented_button_selected_hover_color=C.ACCENT_HOVER,
            segmented_button_unselected_color=C.BG_CARD,
            segmented_button_unselected_hover_color=C.BG_HOVER,
            corner_radius=10,
        )
        self.tabview.pack(fill="both", expand=True, padx=14, pady=(0, 14))

        for name in ("Server", "Model", "Voice", "Profiles"):
            tab = self.tabview.add(name)
            tab.configure(fg_color=C.BG_DARK)

        self.server_tab = ServerTab(self.tabview.tab("Server"), self)
        self.model_tab = ModelTab(self.tabview.tab("Model"), self)
        self.voice_tab = VoiceTab(self.tabview.tab("Voice"), self)
        self.profiles_tab = ProfilesTab(self.tabview.tab("Profiles"), self)

        self.protocol("WM_DELETE_WINDOW", self._on_close)

        # Show setup guide on first launch
        if self.config_data.get("show_setup_guide", True):
            self.after(300, self._show_setup_wizard)

    def _set_icon(self):
        if not self._icon_path:
            return
        try:
            self.iconbitmap(self._icon_path)
            self.wm_iconbitmap(self._icon_path)
        except Exception:
            pass

        # Force Windows taskbar to use our icon
        try:
            import ctypes
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("BetterTTS.App")
            hwnd = ctypes.windll.user32.GetParent(self.winfo_id())
            if not hwnd:
                hwnd = self.winfo_id()
            icon = ctypes.windll.user32.LoadImageW(
                0, self._icon_path, 1, 0, 0, 0x10 | 0x2
            )
            if icon:
                ctypes.windll.user32.SendMessageW(hwnd, 0x0080, 1, icon)
                ctypes.windll.user32.SendMessageW(hwnd, 0x0080, 0, icon)
        except Exception:
            pass

    # ── Header ────────────────────────────────────────────────────────────────

    def _build_header(self):
        header = ctk.CTkFrame(self, fg_color=C.BG_DARK, height=48)
        header.pack(fill="x", padx=14, pady=(14, 0))
        header.pack_propagate(False)

        title_frame = ctk.CTkFrame(header, fg_color="transparent")
        title_frame.pack(side="left")

        ctk.CTkLabel(
            title_frame, text="Better", font=F.TITLE,
            text_color=C.ACCENT_LIGHT,
        ).pack(side="left")
        ctk.CTkLabel(
            title_frame, text="TTS", font=F.TITLE,
            text_color=C.TEXT,
        ).pack(side="left")

        ctk.CTkLabel(
            header, text="Qwen3-TTS for Streamers",
            font=F.BODY_SM, text_color=C.TEXT_DIM,
        ).pack(side="left", padx=(12, 0))

        links_frame = ctk.CTkFrame(header, fg_color="transparent")
        links_frame.pack(side="right")

        ctk.CTkButton(
            links_frame, text="Consider Donating to help out!", width=210, height=26,
            fg_color=C.SUCCESS_DIM, hover_color=C.SUCCESS,
            text_color="#ffffff", corner_radius=6,
            font=F.CAPTION,
            command=lambda: webbrowser.open("https://streamelements.com/kindredspiritva/tip"),
        ).pack(side="left", padx=(0, 8))

        ctk.CTkButton(
            links_frame, text="by @kindredspiritva", width=130, height=26,
            fg_color="transparent", hover_color=C.BG_HOVER,
            text_color=C.LINK, corner_radius=6,
            font=("Segoe UI", 11),
            command=lambda: webbrowser.open("https://twitter.com/kindredspirityt"),
        ).pack(side="left")

    # ── GPU bar ───────────────────────────────────────────────────────────────

    def _build_gpu_bar(self):
        gpu_card = card(self)
        gpu_card.pack(fill="x", padx=14, pady=(8, 6))

        backend = self.gpu_info.get("backend", "CPU")
        gpu_name = self.gpu_info.get("name", "Unknown")

        if self.gpu_info["available"]:
            vram_str = f"VRAM: {self.gpu_info['vram_gb']} GB  |  " if self.gpu_info["vram_gb"] > 0 else ""
            text = (
                f"GPU: {gpu_name}  |  "
                f"{vram_str}"
                f"Backend: {backend} {self.gpu_info.get('backend_version', '')}"
            )
            ctk.CTkLabel(
                gpu_card, text=text, text_color=C.SUCCESS,
                font=F.BODY_SM,
            ).pack(pady=8, padx=14)
        else:
            is_amd = any(kw in gpu_name.lower() for kw in ["radeon", "amd", "ati"])
            is_intel = "intel" in gpu_name.lower() and "nvidia" not in gpu_name.lower()

            if is_amd:
                line1 = f"GPU: {gpu_name}  |  Running on CPU (no GPU acceleration)"
                line2 = (
                    "AMD GPUs are not supported by Qwen3-TTS — it requires NVIDIA CUDA. "
                    "TTS will still work using your CPU, but generation will be slower."
                )
                color = C.WARNING
            elif is_intel:
                line1 = f"GPU: {gpu_name}  |  Running on CPU (no GPU acceleration)"
                line2 = (
                    "Intel GPUs are not supported by Qwen3-TTS — it requires NVIDIA CUDA. "
                    "TTS will still work using your CPU, but generation will be slower."
                )
                color = C.WARNING
            else:
                line1 = "No GPU detected  |  Running on CPU"
                line2 = (
                    "No dedicated GPU was found. TTS will run on your CPU which is slower. "
                    "For best performance, an NVIDIA GPU (GTX 1060+) is recommended."
                )
                color = C.ERROR

            ctk.CTkLabel(
                gpu_card, text=line1, text_color=color,
                font=("Segoe UI", 12, "bold"),
            ).pack(pady=(8, 0), padx=14)
            ctk.CTkLabel(
                gpu_card, text=line2, text_color=C.TEXT_SEC,
                font=F.CAPTION, wraplength=theme.WRAP_WIDE, justify="center",
            ).pack(pady=(2, 8), padx=14)

    # ── Update banner ─────────────────────────────────────────────────────────

    def notify_update_available(self, version: str):
        """
        Called from main.py when a newer release is found on GitHub.
        Shows a dismissable banner above the tabs with Update / Dismiss buttons.
        """
        if self._update_banner is not None:
            return  # already showing

        self._pending_update_version = version

        banner = ctk.CTkFrame(
            self,
            fg_color=("#1a2e1a", "#1a2e1a"),
            corner_radius=10,
            border_width=1,
            border_color=C.SUCCESS_DIM,
        )
        banner.pack(fill="x", padx=14, pady=(0, 4), before=self.tabview)
        self._update_banner = banner

        inner = ctk.CTkFrame(banner, fg_color="transparent")
        inner.pack(fill="x", padx=12, pady=8)

        # Icon + message
        ctk.CTkLabel(
            inner,
            text="⬆  Update Available",
            font=F.BODY_SM,
            text_color=C.SUCCESS,
        ).pack(side="left")

        ctk.CTkLabel(
            inner,
            text=f"Version {version} is ready to install.",
            font=F.BODY_SM,
            text_color=C.TEXT_SEC,
        ).pack(side="left", padx=(10, 0))

        # Buttons on the right
        btn_frame = ctk.CTkFrame(inner, fg_color="transparent")
        btn_frame.pack(side="right")

        ctk.CTkButton(
            btn_frame,
            text="Dismiss",
            width=80, height=26,
            fg_color="transparent",
            hover_color=C.BG_HOVER,
            text_color=C.TEXT_DIM,
            border_width=1,
            border_color=C.SEPARATOR,
            corner_radius=6,
            font=F.CAPTION,
            command=self._dismiss_update_banner,
        ).pack(side="right", padx=(6, 0))

        ctk.CTkButton(
            btn_frame,
            text="Update Now",
            width=100, height=26,
            fg_color=C.SUCCESS_DIM,
            hover_color=C.SUCCESS,
            text_color="#ffffff",
            corner_radius=6,
            font=F.CAPTION,
            command=self._start_update,
        ).pack(side="right")

    def _dismiss_update_banner(self):
        if self._update_banner is not None:
            self._update_banner.destroy()
            self._update_banner = None

    def _start_update(self):
        """Replace the banner with a progress indicator and kick off the download."""
        print(f"[Updater] _start_update called — banner: {self._update_banner}, updater: {self.updater}")
        if self._update_banner is None:
            print("[Updater] No banner — ignoring")
            return
        if self.updater is None or self.updater._update_info is None:
            print(f"[Updater] Updater not ready — updater={self.updater}")
            return

        # Clear banner contents and show progress UI
        for widget in self._update_banner.winfo_children():
            widget.destroy()

        inner = ctk.CTkFrame(self._update_banner, fg_color="transparent")
        inner.pack(fill="x", padx=12, pady=8)

        self._update_status_label = ctk.CTkLabel(
            inner,
            text="Preparing update…",
            font=F.BODY_SM,
            text_color=C.SUCCESS,
        )
        self._update_status_label.pack(side="left")

        self._update_progress = ctk.CTkProgressBar(
            inner,
            width=200, height=8,
            fg_color=C.BG_INPUT,
            progress_color=C.SUCCESS,
            corner_radius=4,
        )
        self._update_progress.pack(side="left", padx=(12, 0))
        self._update_progress.set(0)

        def _on_progress(done, total):
            if total > 0:
                self.after(0, lambda: self._update_progress.set(done / total))
                mb_done = done / (1024 * 1024)
                mb_total = total / (1024 * 1024)
                self.after(0, lambda: self._update_status_label.configure(
                    text=f"Downloading… {mb_done:.1f} / {mb_total:.1f} MB"
                ))

        def _on_status(msg):
            self.after(0, lambda: self._update_status_label.configure(text=msg))

        def _on_error(err):
            self.after(0, lambda: self._update_status_label.configure(
                text=f"Update failed: {err}", text_color=C.ERROR
            ))
            self.after(0, lambda: self._update_progress.configure(
                progress_color=C.ERROR
            ))

        self.updater._on_download_progress = _on_progress
        self.updater._on_status = _on_status
        self.updater._on_error = _on_error

        threading.Thread(
            target=self.updater.download_and_apply,
            daemon=True
        ).start()

    # ── Rest of app ───────────────────────────────────────────────────────────

    def _show_setup_wizard(self):
        from app.gui.setup_wizard import SetupWizard
        SetupWizard(self, self.config_data, on_close=self.save)

    def _on_model_state_change(self, state: ModelState, error: str):
        self.after(0, lambda: self.model_tab.update_state(state, error))
        self.after(0, lambda: self.server_tab.update_model_state(state))
        self.after(0, lambda: self.voice_tab.update_for_model(self.model_manager.current_variant))
        self.after(0, lambda: self.profiles_tab.update_for_model(self.model_manager.current_variant))

    def save(self):
        save_config(self.config_data)

    def _on_close(self):
        self.server_manager.stop()
        self.model_manager.unload_model()
        self.save()
        self.destroy()