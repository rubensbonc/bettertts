"""
main.py — Full app entry point. Always runs from the venv via launcher.py.
Has access to torch, qwen-tts, fastapi and all ML dependencies.
"""

import sys
import os
import socket
import atexit
import warnings
from pathlib import Path


def get_base_dir() -> Path:
    if getattr(sys, 'frozen', False):
        return Path(sys.executable).parent
    return Path(__file__).parent.parent


# ── Ensure the base dir is on sys.path so `app.*` imports resolve ────────────
# When run as `python app\main.py` from dist\BetterTTS\, Python's working
# directory is dist\BetterTTS\ but sys.path doesn't include it automatically.
# We insert it here before any app.* imports so everything resolves correctly.
_base = get_base_dir()
if str(_base) not in sys.path:
    sys.path.insert(0, str(_base))


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


# ── CUDA compatibility env vars ───────────────────────────────────────────────
os.environ.setdefault("CUDA_TF32_OVERRIDE", "0")
os.environ.setdefault("CUDA_LAUNCH_BLOCKING", "0")
os.environ.setdefault("CUBLAS_WORKSPACE_CONFIG", ":16:8")


# ── Single instance check ────────────────────────────────────────────────────
_SINGLE_INSTANCE_PORT = 19847
_main_window_ref = None


def _focus_main_window():
    global _main_window_ref
    if _main_window_ref is not None:
        try:
            _main_window_ref.after(0, lambda: (
                _main_window_ref.deiconify(),
                _main_window_ref.lift(),
                _main_window_ref.focus_force(),
            ))
        except Exception:
            pass


def _ensure_single_instance():
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 0)
    try:
        sock.bind(("127.0.0.1", _SINGLE_INSTANCE_PORT))
        sock.listen(1)
        import threading
        def _listen():
            while True:
                try:
                    conn, _ = sock.accept()
                    conn.close()
                    _focus_main_window()
                except Exception:
                    break
        threading.Thread(target=_listen, daemon=True).start()
        return sock
    except OSError:
        try:
            notify = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            notify.settimeout(1.0)
            notify.connect(("127.0.0.1", _SINGLE_INSTANCE_PORT))
            notify.close()
            sys.exit(0)
        except (ConnectionRefusedError, socket.timeout, OSError):
            sock2 = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock2.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            try:
                sock2.bind(("127.0.0.1", _SINGLE_INSTANCE_PORT))
                sock2.listen(1)
                import threading
                def _listen2():
                    while True:
                        try:
                            conn, _ = sock2.accept()
                            conn.close()
                            _focus_main_window()
                        except Exception:
                            break
                threading.Thread(target=_listen2, daemon=True).start()
                return sock2
            except OSError:
                return None


_socket_lock = _ensure_single_instance()

def _cleanup_socket():
    if _socket_lock is not None:
        try:
            _socket_lock.close()
        except Exception:
            pass

atexit.register(_cleanup_socket)


# ── Crash protection ──────────────────────────────────────────────────────────
from app.updater import write_startup_flag, clear_startup_flag, check_and_rollback, cleanup_old_exe

cleanup_old_exe()
check_and_rollback()
write_startup_flag()
atexit.register(clear_startup_flag)


# ── Silence noisy warnings ────────────────────────────────────────────────────
warnings.filterwarnings("ignore", message=".*flash.*attn.*")
warnings.filterwarnings("ignore", message=".*flash-attn.*")
os.environ["TRANSFORMERS_NO_FLASH_ATTN_WARNING"] = "1"

# ── Redirect stdout/stderr to app.log ────────────────────────────────────────
# Always redirect so tqdm never crashes with Errno 22 on windowless process,
# and all print/error output is captured to app.log for debugging.
import io
_log_file = open(get_base_dir() / "app.log", "w", encoding="utf-8", buffering=1)
_unbuffered_log = io.TextIOWrapper(
    _log_file.buffer if hasattr(_log_file, 'buffer') else _log_file,
    encoding="utf-8",
    line_buffering=True,
    write_through=True,
)
sys.stdout = _unbuffered_log
sys.stderr = _unbuffered_log
os.environ["TQDM_DISABLE"] = "1"
print(f"[BetterTTS] Logging started — base dir: {get_base_dir()}")


# ── Set Windows taskbar app identity ─────────────────────────────────────────
# Must be called before any window is created so Windows assigns the right icon
if sys.platform == "win32":
    try:
        import ctypes
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("BetterTTS.App")
    except Exception:
        pass

# All heavy imports happen here — safe because we're in the venv
from app.gui.app_window import AppWindow
from app.updater import Updater


def main():
    global _main_window_ref

    # Create updater first so it can be passed into AppWindow immediately
    def _on_update_available(version: str):
        try:
            if _main_window_ref is not None:
                _main_window_ref.after(0, lambda: _main_window_ref.notify_update_available(version))
        except Exception:
            pass

    updater = Updater(on_update_available=_on_update_available)

    # Pass updater into AppWindow so self.updater is never None
    app = AppWindow(updater=updater)
    _main_window_ref = app

    updater.check_async()

    # Mark startup as successful
    clear_startup_flag()

    app.mainloop()


if __name__ == "__main__":
    main()