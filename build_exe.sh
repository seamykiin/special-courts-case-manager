#!/usr/bin/env bash
set -e

echo "=========================================================="
echo "  LGC Case Register — Standalone Windows .EXE Builder     "
echo "=========================================================="

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    echo "❌ Error: Docker is not installed or not in PATH."
    echo "Please install Docker Desktop: https://www.docker.com/products/docker-desktop"
    exit 1
fi

# Check if Docker daemon is running
if ! docker info &> /dev/null; then
    echo "⚠️ Docker daemon is not running."
    echo "Please start Docker Desktop on your Mac and re-run this script."
    exit 1
fi

echo "✓ Docker daemon detected."

# Step 1: Ensure latest index.html is generated
if [ -f "generate_final_index.py" ]; then
    echo "▶ Generating fresh index.html..."
    python3 generate_final_index.py
fi

# Step 2: Build the Docker Wine compiler image with PyQt6-WebEngine & pywebview
echo "▶ Building Docker Wine compilation environment (with embedded Chromium engine)..."
docker build --platform=linux/amd64 -t lgc-exe-builder -f Dockerfile.wine .

# Step 3: Run PyInstaller inside the Docker Wine container
echo "▶ Compiling Standalone Windows Desktop App inside container..."
mkdir -p dist build

docker run --platform=linux/amd64 --rm \
    -v "$(pwd)":/src \
    lgc-exe-builder

# Step 4: Post-bundle copy of essential files, Qt plugins, and native runtime DLLs
echo "▶ Bundling all packages, data files, and native runtime DLLs..."
DIST_APP="dist/LGCCaseRegister"

# Copy core files directly into app root for direct access
cp -f index.html "$DIST_APP/"
[ -f server.py ] && cp -f server.py "$DIST_APP/"
[ -f case.py ] && cp -f case.py "$DIST_APP/"
[ -f pending_cases.db ] && cp -f pending_cases.db "$DIST_APP/"
[ -f sample_cause_list.csv ] && cp -f sample_cause_list.csv "$DIST_APP/"
[ -f geo_data.json ] && cp -f geo_data.json "$DIST_APP/"

# Copy WebView2 native loaders if present so Edge Chromium never fails to locate them
if [ -f "$DIST_APP/_internal/webview/lib/runtimes/win-x64/native/WebView2Loader.dll" ]; then
    cp -f "$DIST_APP/_internal/webview/lib/runtimes/win-x64/native/WebView2Loader.dll" "$DIST_APP/"
    cp -f "$DIST_APP/_internal/webview/lib/runtimes/win-x64/native/WebView2Loader.dll" "$DIST_APP/_internal/"
    cp -f "$DIST_APP/_internal/webview/lib/runtimes/win-x64/native/WebView2Loader.dll" "$DIST_APP/_internal/webview/lib/"
fi
if [ -f "$DIST_APP/_internal/webview/lib/Microsoft.Web.WebView2.Core.dll" ]; then
    cp -f "$DIST_APP/_internal/webview/lib/Microsoft.Web.WebView2.Core.dll" "$DIST_APP/"
    cp -f "$DIST_APP/_internal/webview/lib/Microsoft.Web.WebView2.WinForms.dll" "$DIST_APP/"
fi

# Copy Qt platforms plugin and qt.conf so PyQt6 never fails to locate qwindows.dll
if [ -d "$DIST_APP/_internal/PyQt6/Qt6/plugins/platforms" ]; then
    cp -rf "$DIST_APP/_internal/PyQt6/Qt6/plugins/platforms" "$DIST_APP/"
    mkdir -p "$DIST_APP/_internal/platforms"
    cp -rf "$DIST_APP/_internal/PyQt6/Qt6/plugins/platforms"/* "$DIST_APP/_internal/platforms/"
fi

cat << 'EOF' > "$DIST_APP/qt.conf"
[Paths]
Prefix = _internal/PyQt6/Qt6
Plugins = plugins
EOF

# Copy ClrLoader.dll and Python.Runtime.dll for pythonnet fail-safe
if [ -f "$DIST_APP/_internal/clr_loader/ffi/dlls/amd64/ClrLoader.dll" ]; then
    cp -f "$DIST_APP/_internal/clr_loader/ffi/dlls/amd64/ClrLoader.dll" "$DIST_APP/"
fi
if [ -f "$DIST_APP/_internal/pythonnet/runtime/Python.Runtime.dll" ]; then
    cp -f "$DIST_APP/_internal/pythonnet/runtime/Python.Runtime.dll" "$DIST_APP/"
fi

# Step 5: Package into distribution zip
echo "▶ Creating zip package for distribution..."
rm -f dist/LGCCaseRegister-Windows-x64.zip
(cd dist && zip -r -q LGCCaseRegister-Windows-x64.zip LGCCaseRegister)

echo ""
echo "=========================================================="
echo "🎉 SUCCESS: True Standalone Windows App Built Successfully!"
echo "=========================================================="
echo "Your executable is ready at:"
echo "  $(pwd)/dist/LGCCaseRegister/LGCCaseRegister.exe"
echo ""
echo "Distribution Zip Archive:"
echo "  $(pwd)/dist/LGCCaseRegister-Windows-x64.zip"
echo ""
echo "Any Windows user can simply unzip and double-click LGCCaseRegister.exe!"
echo "The app launches in a standalone native desktop window with full embedded Chromium."
echo "=========================================================="
