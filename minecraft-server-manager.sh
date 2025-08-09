#!/bin/sh
# Wrapper script for Minecraft Server Manager

# Determine the base directory depending on the runtime environment
if [ -n "$APPDIR" ]; then
    # AppImage environment
    BASEDIR="$APPDIR/usr/bin"
elif [ -d "/app/bin" ]; then
    # Flatpak environment
    BASEDIR="/app/bin"
else
    # System installation or AppImage extraction
    SCRIPT_DIR="$(dirname "$(readlink -f "$0")")"
    if [ -f "$SCRIPT_DIR/main.py" ]; then
        BASEDIR="$SCRIPT_DIR"
    else
        # Try relative to script location
        BASEDIR="$(dirname "$SCRIPT_DIR")/bin"
    fi
fi

# Set the Python path to include our modules
export PYTHONPATH="${BASEDIR}:$PYTHONPATH"

# Change to the application directory
cd "${BASEDIR}" || {
    echo "Error: Cannot change to application directory: $BASEDIR"
    exit 1
}

# Execute the main Python script
exec python3 "${BASEDIR}/main.py" "$@"
