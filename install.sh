#!/bin/bash

# Function to find the correct Python executable
find_python_command() {
    # List of possible Python commands to check
    python_candidates=("python3" "python" "python3.11" "python3.10" "python3.9" "python3.8")
    
    for cmd in "${python_candidates[@]}"; do
        if command -v "$cmd" >/dev/null 2>&1; then
            # Check if it's Python 3
            version_output=$("$cmd" --version 2>&1)
            if echo "$version_output" | grep -q "Python 3"; then
                echo "$cmd"
                return 0
            fi
        fi
    done
    
    echo "python3"  # Fallback to python3
    return 1
}

# Search for the ClockSpeeds directory within the home directory
clockspeeds_path=$(find $HOME -type d -name "ClockSpeeds" 2>/dev/null | head -n 1)

# Exit if ClockSpeeds is not found
if [ -z "$clockspeeds_path" ]; then
    echo "ClockSpeeds directory not found in your home directory."
    exit 1
fi

# Detect the correct Python command
python_cmd=$(find_python_command)
python_full_path=$(which "$python_cmd" 2>/dev/null)

if [ -z "$python_full_path" ]; then
    echo "Warning: Python 3 not found. Using 'python3' as fallback."
    python_full_path="python3"
else
    echo "Found Python at: $python_full_path"
fi

# Create the applications directory if it doesn't exist
mkdir -p $HOME/.local/share/applications

# Create the .desktop file
cat << EOF > $HOME/.local/share/applications/org.ClockSpeeds.desktop
[Desktop Entry]
Version=0.13
Type=Application
Name=ClockSpeeds
Comment=Monitor and control your CPU
Exec=$python_full_path $clockspeeds_path/launch.py
Icon=$clockspeeds_path/icon/ClockSpeeds-Icon.png
Terminal=false
Categories=Utility;Application;
EOF

# Make the .desktop file executable
chmod +x $HOME/.local/share/applications/org.ClockSpeeds.desktop

echo "ClockSpeeds .desktop file has been created and made executable."
echo "Using Python executable: $python_full_path"