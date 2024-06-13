#!/bin/bash

# Search for the ClockSpeeds directory within the home directory
clockspeeds_path=$(find $HOME -type d -name "ClockSpeeds" 2>/dev/null | head -n 1)

# Exit if ClockSpeeds is not found
if [ -z "$clockspeeds_path" ]; then
    echo "ClockSpeeds directory not found in your home directory."
    exit 1
fi

# Create the applications directory if it doesn't exist
mkdir -p $HOME/.local/share/applications

# Create the .desktop file
cat << EOF > $HOME/.local/share/applications/ClockSpeeds.desktop
[Desktop Entry]
Version=0.1
Type=Application
Name=ClockSpeeds
Comment=Monitor and control your CPU
Exec=python3 $clockspeeds_path/launch.py
Icon=$clockspeeds_path/icon/ClockSpeeds-Icon.png
Terminal=false
Categories=Utility;Application;
EOF

# Make the .desktop file executable
chmod +x $HOME/.local/share/applications/ClockSpeeds.desktop

echo "ClockSpeeds .desktop file has been created and made executable."
