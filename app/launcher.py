"""
launcher.py — Lightweight entry point bundled by PyInstaller.

Only imports standard library + customtkinter (for the setup wizard).
Never imports torch, numpy, fastapi, or any ML dependency.

On first launch: runs the setup wizard to create the venv + install deps.
On subsequent launches: immediately hands off to venv\Scripts\python.exe
which runs main.py with the full ML stack available.
"""

import sys
import os
import socket
import atexit
from pathlib import Path

import customtkinter as ctk

# ── Theme constants (mirrors app/gui/theme.py) ────────────────────────────────
_BG_DARK    = "#0f172a"
_BG_CARD    = "#1e293b"
_BG_INPUT   = "#334155"
_ACCENT     = "#7c3aed"
_ACCENT_HOV = "#6d28d9"
_ERROR_DIM  = "#dc2626"
_ERROR      = "#ef4444"
_TEXT       = "#e2e8f0"
_TEXT_SEC   = "#94a3b8"
_TEXT_DIM   = "#64748b"
_WARNING    = "#f59e0b"


def _show_error(title: str, message: str):
    """Show a themed error dialog using customtkinter."""
    ctk.set_appearance_mode("dark")
    ctk.set_default_color_theme("blue")

    win = ctk.CTk()
    win.title(title)
    win.resizable(False, False)
    win.configure(fg_color=_BG_DARK)
    win.attributes("-topmost", True)

    # Set icon if available
    icon_path = get_base_dir() / "icon.ico"
    if icon_path.exists():
        try:
            win.after(0, lambda: win.iconbitmap(str(icon_path)))
        except Exception:
            pass

    # Center on screen
    win.update_idletasks()
    w, h = 480, 220
    x = (win.winfo_screenwidth() - w) // 2
    y = (win.winfo_screenheight() - h) // 2
    win.geometry(f"{w}x{h}+{x}+{y}")

    # Header
    header = ctk.CTkFrame(win, fg_color=_ERROR_DIM, corner_radius=0, height=44)
    header.pack(fill="x")
    header.pack_propagate(False)
    ctk.CTkLabel(
        header, text=f"  ✕  {title}",
        font=ctk.CTkFont(size=13, weight="bold"),
        text_color="#ffffff",
    ).pack(side="left", padx=12, pady=8)

    # Message
    ctk.CTkLabel(
        win, text=message,
        font=ctk.CTkFont(size=12),
        text_color=_TEXT_SEC,
        justify="left",
        wraplength=440,
    ).pack(padx=20, pady=(16, 12), anchor="w")

    # OK button — accent purple to match app primary action style
    ctk.CTkButton(
        win, text="OK", width=100, height=32,
        fg_color=_ACCENT, hover_color=_ACCENT_HOV,
        text_color="#ffffff", corner_radius=6,
        font=ctk.CTkFont(size=12, weight="bold"),
        command=win.destroy,
    ).pack(pady=(0, 16))

    win.mainloop()


def get_base_dir() -> Path:
    if getattr(sys, 'frozen', False):
        return Path(sys.executable).parent
    return Path(__file__).parent.parent


# ── SoX PATH setup ───────────────────────────────────────────────────────────
def _setup_sox():
    base = get_base_dir()
    for path in [
        base / "sox",
        Path("C:/Program Files (x86)/sox-14-4-2"),
        Path("C:/Program Files/sox-14-4-2"),
    ]:
        if path.exists():
            os.environ["PATH"] = str(path) + os.pathsep + os.environ.get("PATH", "")

_setup_sox()


# ── Launcher single instance — separate port from the app ────────────────────
# The app uses port 19847. The launcher uses 19848. Completely independent.
_LAUNCHER_PORT = 19848

def _ensure_single_launcher():
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 0)
    try:
        sock.bind(("127.0.0.1", _LAUNCHER_PORT))
        sock.listen(1)
        return sock
    except OSError:
        sys.exit(0)

_launcher_lock = _ensure_single_launcher()

def _release_launcher_lock():
    try:
        _launcher_lock.close()
    except Exception:
        pass

atexit.register(_release_launcher_lock)


# ── Launch app ────────────────────────────────────────────────────────────────
def _launch_app(venv_python, main_py):
    """
    Launch the full app via venv Python without showing any console window.
    Writes a launch.log next to the exe for debugging startup failures.
    """
    import subprocess
    import time

    base = get_base_dir()
    log_path = base / "launch.log"

    def log(msg):
        try:
            with open(log_path, "a", encoding="utf-8") as f:
                f.write(msg + "\n")
        except Exception:
            pass

    log("=== Launch attempt ===")
    log(f"venv_python: {venv_python}")
    log(f"main_py: {main_py}")
    log(f"main_py exists: {main_py.exists()}")
    log(f"venv_python exists: {Path(venv_python).exists()}")
    log(f"cwd: {main_py.parent.parent}")
    log(f"cwd exists: {main_py.parent.parent.exists()}")

    if not Path(venv_python).exists():
        _show_error(
            "Launch Error",
            f"venv Python not found:\n{venv_python}\n\n"
            f"Delete the venv\\ folder and relaunch to reinstall."
        )
        sys.exit(1)

    if not main_py.exists():
        _show_error(
            "Launch Error",
            f"app\\main.py not found:\n{main_py}\n\n"
            f"Please reinstall BetterTTS."
        )
        sys.exit(1)

    NO_WINDOW = subprocess.CREATE_NO_WINDOW if hasattr(subprocess, "CREATE_NO_WINDOW") else 0
    proc = subprocess.Popen(
        [str(venv_python), str(main_py)],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        creationflags=NO_WINDOW,
        cwd=str(main_py.parent.parent),
    )

    log(f"Process started with PID: {proc.pid}")

    # Release launcher lock so app can bind its own port cleanly
    _release_launcher_lock()

    # Wait up to 10 seconds — if process exits early it crashed
    for _ in range(100):
        time.sleep(0.1)
        if proc.poll() is not None:
            # Code 0 = clean exit (e.g. app closed for update) — exit launcher immediately
            if proc.returncode == 0:
                log("Process exited cleanly with code 0 — launcher exiting")
                sys.exit(0)

            _, stderr = proc.communicate()
            error_msg = stderr.strip() if stderr else b"No error output captured"
            if isinstance(error_msg, bytes):
                error_msg = error_msg.decode("utf-8", errors="replace")
            log(f"Process exited early with code {proc.returncode}")
            log(f"stderr: {error_msg}")
            _show_error(
                "BetterTTS Failed to Start",
                f"BetterTTS exited unexpectedly (code {proc.returncode}).\n\n"
                f"Error:\n{error_msg[-600:]}\n\n"
                f"Check launch.log for details.\n"
                f"Try deleting the venv\\ folder and relaunching."
            )
            sys.exit(1)

    log("Process still running after 10s — launcher exiting cleanly")
    sys.exit(0)


# ── Setup wizard + venv handoff ───────────────────────────────────────────────
def _check_setup():
    base = get_base_dir()
    gpu_file = base / ".gpu_type"
    venv_python = (
        base / "venv" / "Scripts" / "python.exe"
        if sys.platform == "win32"
        else base / "venv" / "bin" / "python"
    )
    main_py = base / "app" / "main.py"

    if not gpu_file.exists() or not venv_python.exists():
        from app.bootstrap import SetupWizard
        wizard = SetupWizard()
        wizard.mainloop()
        if venv_python.exists():
            _launch_app(venv_python, main_py)
        else:
            sys.exit(0)
    else:
        _launch_app(venv_python, main_py)


if __name__ == "__main__":
    _check_setup()