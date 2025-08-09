#!/bin/bash
set -e

# Build AppImage manually (simplified approach)
# This creates a portable executable without external dependencies

echo "Building AppImage manually..."

APPDIR=AppDir
APP=io.github.fernandomema.minecraft-server-manager-gtk

# Clean previous builds
rm -rf "$APPDIR"
rm -f *.AppImage

# Create AppDir structure
mkdir -p "$APPDIR/usr/bin"
mkdir -p "$APPDIR/usr/share/applications"
mkdir -p "$APPDIR/usr/share/icons/hicolor/scalable/apps"
mkdir -p "$APPDIR/usr/share/icons/hicolor/128x128/apps"
mkdir -p "$APPDIR/usr/share/icons/hicolor/64x64/apps"
mkdir -p "$APPDIR/usr/share/icons/hicolor/48x48/apps"

# Copy application files
echo "Copying application files..."
cp -r main.py controllers models utils views __init__.py "$APPDIR/usr/bin/"
cp minecraft-server-manager.sh "$APPDIR/usr/bin/minecraft-server-manager"
chmod +x "$APPDIR/usr/bin/minecraft-server-manager"

# Copy desktop entry and icons
echo "Copying desktop files and icons..."
cp io.github.fernandomema.minecraft-server-manager-gtk.desktop "$APPDIR/usr/share/applications/"
cp io.github.fernandomema.minecraft-server-manager-gtk.svg "$APPDIR/usr/share/icons/hicolor/scalable/apps/"
cp io.github.fernandomema.minecraft-server-manager-gtk-128.png "$APPDIR/usr/share/icons/hicolor/128x128/apps/$APP.png"
cp io.github.fernandomema.minecraft-server-manager-gtk-64.png "$APPDIR/usr/share/icons/hicolor/64x64/apps/$APP.png"
cp io.github.fernandomema.minecraft-server-manager-gtk-48.png "$APPDIR/usr/share/icons/hicolor/48x48/apps/$APP.png"

# Create AppRun script
echo "Creating AppRun script..."
cat > "$APPDIR/AppRun" << 'EOF'
#!/bin/bash
HERE="$(dirname "$(readlink -f "${0}")")"
export PATH="${HERE}/usr/bin:${PATH}"
export PYTHONPATH="${HERE}/usr/bin:${PYTHONPATH}"

# Isolate from problematic snap environment
unset LD_LIBRARY_PATH
unset LD_PRELOAD

# Check if required dependencies are available
if ! command -v python3 &> /dev/null; then
    echo "Error: Python 3 is required but not found on this system."
    echo "Please install Python 3 and try again."
    exit 1
fi

if ! python3 -c "import gi" 2>/dev/null; then
    echo "Error: PyGObject (GTK bindings for Python) is required but not found."
    echo "Please install python3-gi and try again."
    exit 1
fi

# Run the application
exec "${HERE}/usr/bin/minecraft-server-manager" "$@"
EOF
chmod +x "$APPDIR/AppRun"

# Create desktop file in root (required for AppImage)
cp "$APPDIR/usr/share/applications/io.github.fernandomema.minecraft-server-manager-gtk.desktop" "$APPDIR/"

# Copy icon to root (required for AppImage)
cp io.github.fernandomema.minecraft-server-manager-gtk.svg "$APPDIR/"

# Create a simple portable archive using tar and makeself-like approach
echo "Creating portable AppImage archive..."
APPIMAGE_NAME="minecraft-server-manager-gtk-x86_64.AppImage"

# Create a self-extracting script
cat > "$APPIMAGE_NAME" << 'SELFEXTRACT_EOF'
#!/bin/bash
# Self-extracting AppImage-like portable application

# Check if we're being executed
if [ "${0##*/}" = "minecraft-server-manager-gtk-x86_64.AppImage" ]; then
    # Create temporary directory
    TMPDIR=$(mktemp -d)
    trap "rm -rf $TMPDIR" EXIT
    
    # Extract archive to temp directory
    ARCHIVE_START=$(awk '/^__ARCHIVE_START__/ {print NR + 1; exit 0; }' "$0")
    tail -n+"$ARCHIVE_START" "$0" | tar xzf - -C "$TMPDIR"
    
    # Run the application
    exec "$TMPDIR/AppDir/AppRun" "$@"
fi

__ARCHIVE_START__
SELFEXTRACT_EOF

# Append the tar archive
tar czf - "$APPDIR" >> "$APPIMAGE_NAME"
chmod +x "$APPIMAGE_NAME"

echo "AppImage built successfully: $APPIMAGE_NAME"
echo "Size: $(du -h "$APPIMAGE_NAME" | cut -f1)"
echo ""
echo "To test the AppImage:"
echo "  ./$APPIMAGE_NAME"
echo ""
echo "Dependencies required on target system:"
echo "  - Python 3"
echo "  - PyGObject (python3-gi)"
echo "  - GTK 3"
echo "  - PyYAML (python3-yaml)"
