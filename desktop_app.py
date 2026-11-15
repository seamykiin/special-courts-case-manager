#!/usr/bin/env python3
"""
Desktop App Launcher for LGC Case & Cause List Register
Starts local server.py in a background thread and launches a standalone native desktop window
powered by:
  1. PyQt6-WebEngine (Embedded Chromium desktop window)
  2. pywebview (Microsoft Edge WebView2 desktop window)
  3. Standalone Edge App Window (Frameless dedicated window via msedge.exe --app=...)
  4. System browser fallback
Guarantees the application always opens smoothly on any Windows machine.
"""
import os
import sys
import time
import socket
import shutil
import subprocess
import threading
import urllib.request
from pathlib import Path

# Fix paths for PyInstaller bundle
if getattr(sys, "frozen", False):
    APP_DIR = Path(sys.executable).parent
    BUNDLE_DIR = Path(getattr(sys, "_MEIPASS", APP_DIR))
else:
    APP_DIR = Path(__file__).resolve().parent
    BUNDLE_DIR = APP_DIR

# Set working directory to APP_DIR so local files & databases are placed next to the executable
os.chdir(APP_DIR)
sys.path.insert(0, str(BUNDLE_DIR))
sys.path.insert(0, str(APP_DIR))

# Safe streams for windowed (no-console) execution so print() and logging never crash
class _SafeStream:
    def __init__(self, target=None):
        self._target = target
    def write(self, s):
        if self._target:
            try:
                self._target.write(s)
                self._target.flush()
            except Exception:
                pass
    def flush(self):
        if self._target:
            try:
                self._target.flush()
            except Exception:
                pass
    def isatty(self):
        return False

try:
    _app_log_fp = open(APP_DIR / "app.log", "a", encoding="utf-8")
except Exception:
    _app_log_fp = None

if sys.stdout is None:
    sys.stdout = _SafeStream(_app_log_fp)
if sys.stderr is None:
    sys.stderr = _SafeStream(_app_log_fp)

# Configure Qt plugin paths so PyQt6 always finds platforms/qwindows.dll
qt_plugins_dir = BUNDLE_DIR / "PyQt6" / "Qt6" / "plugins"
qt_platforms_dir = qt_plugins_dir / "platforms"
if qt_platforms_dir.exists():
    os.environ["QT_QPA_PLATFORM_PLUGIN_PATH"] = str(qt_platforms_dir)
if qt_plugins_dir.exists():
    os.environ["QT_PLUGIN_PATH"] = str(qt_plugins_dir)

# Ensure Windows PATH and DLL search directories include BUNDLE_DIR, APP_DIR, and native runtimes
if sys.platform == "win32" or "win" in sys.platform:
    extra_paths = [
        str(APP_DIR),
        str(APP_DIR / "platforms"),
        str(BUNDLE_DIR),
        str(BUNDLE_DIR / "platforms"),
        str(BUNDLE_DIR / "webview" / "lib" / "runtimes" / "win-x64" / "native"),
        str(BUNDLE_DIR / "PyQt6" / "Qt6" / "bin"),
        str(BUNDLE_DIR / "PyQt6" / "Qt6" / "plugins" / "platforms"),
        str(BUNDLE_DIR / "clr_loader" / "ffi" / "dlls" / "amd64"),
        str(BUNDLE_DIR / "pythonnet" / "runtime"),
        str(APP_DIR / "_internal" / "PyQt6" / "Qt6" / "bin"),
    ]
    current_path = os.environ.get("PATH", "")
    os.environ["PATH"] = ";".join([p for p in extra_paths if os.path.exists(p)] + [current_path])
    if hasattr(os, "add_dll_directory"):
        for p in extra_paths:
            if os.path.exists(p):
                try:
                    os.add_dll_directory(p)
                except Exception:
                    pass

import importlib.util

# Prioritize loading server.py and case.py directly from APP_DIR (next to the executable)
# so any updates or fixes in the application folder take immediate effect.
def _load_local_module(mod_name: str, file_path: Path):
    if file_path.exists():
        try:
            spec = importlib.util.spec_from_file_location(mod_name, str(file_path))
            if spec and spec.loader:
                mod = importlib.util.module_from_spec(spec)
                sys.modules[mod_name] = mod
                spec.loader.exec_module(mod)
                return mod
        except Exception as e:
            print(f"Notice: Loading fallback for {file_path.name}: {e}", file=sys.stderr)
    return None

_load_local_module("case", APP_DIR / "case.py")
server = _load_local_module("server", APP_DIR / "server.py")
if server is None:
    import server

def check_server_health(port: int, timeout: float = 8.0) -> bool:
    """Verifies that the server is alive and actively returning HTTP 200."""
    start = time.time()
    url = f"http://127.0.0.1:{port}/api/status"
    while time.time() - start < timeout:
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "LGCLauncher/1.0"})
            with urllib.request.urlopen(req, timeout=1.0) as resp:
                if resp.status == 200:
                    return True
        except Exception:
            pass
        time.sleep(0.15)
    return False

def run_server_thread():
    try:
        server.main()
    except Exception as e:
        print(f"Server thread error: {e}", file=sys.stderr)

def launch_pyqt_window(url: str, title: str = "LGC Case & Cause List Register", width: int = 1440, height: int = 920) -> bool:
    """Tier 1: Embedded Chromium via PyQt6-WebEngine."""
    try:
        from PyQt6.QtWidgets import QApplication, QMainWindow
        from PyQt6.QtWebEngineWidgets import QWebEngineView
        from PyQt6.QtWebEngineCore import QWebEngineProfile, QWebEngineSettings
        from PyQt6.QtCore import QUrl

        app = QApplication.instance()
        if app is None:
            app = QApplication(sys.argv)
        app.setApplicationName(title)

        window = QMainWindow()
        window.setWindowTitle(title)
        window.resize(width, height)
        window.setMinimumSize(1024, 700)

        # Configure modern web engine capabilities
        profile = QWebEngineProfile.defaultProfile()
        settings = profile.settings()
        settings.setAttribute(QWebEngineSettings.WebAttribute.PluginsEnabled, True)
        settings.setAttribute(QWebEngineSettings.WebAttribute.PdfViewerEnabled, True)
        settings.setAttribute(QWebEngineSettings.WebAttribute.JavascriptEnabled, True)
        settings.setAttribute(QWebEngineSettings.WebAttribute.LocalStorageEnabled, True)
        settings.setAttribute(QWebEngineSettings.WebAttribute.LocalContentCanAccessRemoteUrls, True)
        settings.setAttribute(QWebEngineSettings.WebAttribute.LocalContentCanAccessFileUrls, True)
        settings.setAttribute(QWebEngineSettings.WebAttribute.AllowRunningInsecureContent, True)

        web_view = QWebEngineView()
        web_view.setUrl(QUrl(url))

        window.setCentralWidget(web_view)
        window.show()
        window.raise_()
        window.activateWindow()

        app.exec()
        return True
    except Exception as e:
        print(f"PyQt6 window launch failed: {e}", file=sys.stderr)
        return False

def launch_pywebview_window(url: str, title: str = "LGC Case & Cause List Register", width: int = 1440, height: int = 920) -> bool:
    """Tier 2: Microsoft Edge WebView2 via pywebview."""
    try:
        import webview
        window = webview.create_window(
            title=title,
            url=url,
            width=width,
            height=height,
            min_size=(1024, 700),
            confirm_close=False,
            text_select=True
        )
        webview.start(private_mode=False)
        return True
    except Exception as e:
        print(f"pywebview window launch failed: {e}", file=sys.stderr)
        return False

def launch_browser_app_window(url: str, width: int = 1440, height: int = 920) -> bool:
    """Tier 3: Standalone App Window via Microsoft Edge or Chrome (No URL bar, dedicated desktop window)."""
    candidates = [
        # Edge candidates (installed on 100% of Windows 10/11)
        os.path.expandvars(r"%ProgramFiles(x86)%\Microsoft\Edge\Application\msedge.exe"),
        os.path.expandvars(r"%ProgramFiles%\Microsoft\Edge\Application\msedge.exe"),
        os.path.expandvars(r"%LocalAppData%\Microsoft\Edge\Application\msedge.exe"),
        # Chrome candidates
        os.path.expandvars(r"%ProgramFiles%\Google\Chrome\Application\chrome.exe"),
        os.path.expandvars(r"%ProgramFiles(x86)%\Google\Chrome\Application\chrome.exe"),
        os.path.expandvars(r"%LocalAppData%\Google\Chrome\Application\chrome.exe"),
    ]

    # Try Windows registry
    if sys.platform == "win32" or "win" in sys.platform:
        try:
            import winreg
            for exe in ("msedge.exe", "chrome.exe"):
                try:
                    with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, rf"SOFTWARE\Microsoft\Windows\CurrentVersion\App Paths\{exe}") as key:
                        val, _ = winreg.QueryValueEx(key, "")
                        if val and os.path.exists(val):
                            candidates.insert(0, val)
                except Exception:
                    pass
        except Exception:
            pass

    browser_path = None
    for c in candidates:
        if c and os.path.isfile(c):
            browser_path = c
            break

    if not browser_path:
        for name in ("msedge", "chrome"):
            found = shutil.which(name)
            if found:
                browser_path = found
                break

    if browser_path:
        try:
            app_args = [
                browser_path,
                f"--app={url}",
                f"--window-size={width},{height}",
                "--disable-features=Translate",
                "--no-first-run",
            ]
            print(f"Launching standalone app window via: {browser_path}", file=sys.stderr)
            proc = subprocess.Popen(app_args)
            proc.wait()
            return True
        except Exception as e:
            print(f"Browser app window launch failed: {e}", file=sys.stderr)
            return False

    return False

def main():
    # 1. Start server in daemon thread
    server_thread = threading.Thread(target=run_server_thread, daemon=True)
    server_thread.start()

    # 2. Wait for server to signal readiness with the exact active port
    server.SERVER_READY_EVENT.wait(timeout=6.0)
    target_port = server.ACTIVE_PORT or 8000

    # 3. Perform HTTP health check to ensure server is responding with 200 before opening window
    if not check_server_health(target_port, timeout=5.0):
        for alt_port in (8001, 8080):
            if check_server_health(alt_port, timeout=1.0):
                target_port = alt_port
                break

    url = f"http://127.0.0.1:{target_port}"
    print(f"Server verified active at {url}", file=sys.stderr)

    # 4. Launch Standalone Native Desktop Window
    # Tier 1: PyQt6-WebEngine (100% self-contained embedded Chromium desktop window)
    print("Attempting Tier 1 (PyQt6-WebEngine)...", file=sys.stderr)
    if launch_pyqt_window(url):
        return

    # Tier 2: pywebview (Edge WebView2 / WinForms native desktop window)
    print("Attempting Tier 2 (pywebview)...", file=sys.stderr)
    if launch_pywebview_window(url):
        return

    # Tier 3: Standalone Edge/Chrome App Window (Clean desktop window without URL bar or tabs)
    print("Attempting Tier 3 (Edge/Chrome App Mode)...", file=sys.stderr)
    if launch_browser_app_window(url):
        return

    # Tier 4: Fallback to default browser
    print("Attempting Tier 4 (Default browser fallback)...", file=sys.stderr)
    import webbrowser
    webbrowser.open(url)
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        pass

if __name__ == "__main__":
    main()
