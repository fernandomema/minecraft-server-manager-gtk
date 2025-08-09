#!/bin/sh
# Wrapper script for Minecraft Server Manager Flatpak

# Set the Python path to include our modules
export PYTHONPATH="/app/bin:$PYTHONPATH"

# Change to the application directory 
cd /app/bin

# Execute the main Python script
exec python3 /app/bin/main.py "$@"
