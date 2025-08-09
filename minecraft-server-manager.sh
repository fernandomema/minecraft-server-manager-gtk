#!/bin/sh
# Wrapper script for Minecraft Server Manager

# Determine the base directory depending on the runtime environment
if [ -n "$APPDIR" ]; then
    BASEDIR="$APPDIR/usr/bin"
else
    BASEDIR="/app/bin"
fi

# Set the Python path to include our modules
export PYTHONPATH="${BASEDIR}:$PYTHONPATH"

# Change to the application directory
cd "${BASEDIR}"

# Execute the main Python script
exec python3 "${BASEDIR}/main.py" "$@"
