#!/bin/bash

# Apply immediately for the current session
export DISPLAY=:0
xinput set-prop 'ADS7846 Touchscreen' 'Coordinate Transformation Matrix' 1.1 0 -0.05 0 1.1 -0.05 0 0 1
xinput set-prop 'ADS7846 Touchscreen' 'Evdev Axis Inversion' 1 0
echo "Touch calibration applied to current X11 session."

# Make it persistent across reboots and screen power cycles
CONF_DIR="/usr/share/X11/xorg.conf.d"
CONF_FILE="$CONF_DIR/99-calibration.conf"

write_config() {
    echo 'Section "InputClass"' | sudo tee $1 > /dev/null
    echo '        Identifier      "calibration"' | sudo tee -a $1 > /dev/null
    echo '        MatchProduct    "ADS7846 Touchscreen"' | sudo tee -a $1 > /dev/null
    echo '        Option  "TransformationMatrix"  "1.1 0 -0.05 0 1.1 -0.05 0 0 1"' | sudo tee -a $1 > /dev/null
    echo '        Option  "InvertX" "true"' | sudo tee -a $1 > /dev/null
    echo 'EndSection' | sudo tee -a $1 > /dev/null
}

if [ -d "$CONF_DIR" ]; then
    write_config "$CONF_FILE"
    echo "Persistent calibration installed to $CONF_FILE"
else
    echo "Warning: X11 config directory $CONF_DIR not found. Checking alternative /etc/X11..."
    ALT_DIR="/etc/X11/xorg.conf.d"
    if [ -d "$ALT_DIR" ]; then
        CONF_FILE="$ALT_DIR/99-calibration.conf"
        write_config "$CONF_FILE"
        echo "Persistent calibration installed to $CONF_FILE"
    else
        echo "Warning: Could not find X11 config directories to make calibration persistent."
    fi
fi
