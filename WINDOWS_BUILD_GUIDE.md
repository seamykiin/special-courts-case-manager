# Windows Application (.EXE) Build Guide

This project includes a complete build system to cross-compile a standalone Windows desktop application (`LGCCaseRegister.exe`) using Docker on macOS/Linux.

---

## Architecture Overview

```
+-------------------------------------------------------------+
|              LGCCaseRegister.exe (Windows)                  |
|                                                             |
|   +---------------------+        +----------------------+   |
|   |  Native Edge Window | <----> | Python Backend       |   |
|   |  (via pywebview)    |        | (server.py)          |   |
|   +---------------------+        +----------------------+   |
|              |                               |              |
|              v                               v              |
|       Full Modern UI                 pending_cases.db       |
|       (index.html)                   (Local SQLite DB)      |
+-------------------------------------------------------------+
```

- **Native Window Experience**: Runs in a borderless, native desktop window using Windows Edge WebView2. No URL bar, no browser tabs, independent window.
- **Embedded Local Server**: The Python backend runs automatically in a background thread on an internal port.
- **Persistent Data**: The database (`pending_cases.db`) and PDF folder settings are saved locally in the application folder.

---

## Method 1: Build Locally with Docker (Recommended)

### Prerequisites
- [Docker Desktop for Mac](https://www.docker.com/products/docker-desktop) installed and running.

### One-Command Build
In your terminal, navigate to the project directory and run:

```bash
./build_exe.sh
```

### What Happens:
1. `generate_final_index.py` compiles the latest `index.html`.
2. Docker pulls the Wine + Python 3.11 Windows cross-compilation image (`tobix/pywine:3.11`).
3. Installs Windows dependencies (`pyinstaller`, `pillow`, `pywebview`).
4. Compiles the executable using `LGCCaseRegister.spec`.
5. Outputs the complete Windows application and zip archive to:
   ```
   dist/LGCCaseRegister/LGCCaseRegister.exe
   dist/LGCCaseRegister-Windows-x64.zip
   ```

---

## Method 2: Build via GitHub Actions (Zero Local Setup)

If Docker is not running or you prefer a cloud build:
1. Push your code to your GitHub repository.
2. Go to the **Actions** tab in GitHub.
3. Select **"Build Windows Application (.EXE)"** and click **Run workflow**.
4. In ~2 minutes, download the pre-compiled **`LGCCaseRegister-Windows-x64.zip`** directly from the run summary.

---

## Distribution to End Users

To share the application with other Windows users:
1. Zip the `dist/LGCCaseRegister` directory.
2. Send the `.zip` file to the user.
3. The user extracts the `.zip` anywhere on their computer (e.g. Desktop or `C:\Program Files\LGCCaseRegister`).
4. Double-click `LGCCaseRegister.exe` to launch!
   - No Python installation required.
   - No command prompt or terminal needed.
