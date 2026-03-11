#!/bin/bash

# Apply immediately for the current session
export DISPLAY=:0
xinput set-prop 'ADS7846 Touchscreen' 'Coordinate Transformation Matrix' -1 0 1 0 1 0 0 0 1
echo "Touch calibration applied to current X11 session."

# Make it persistent across reboots and screen power cycles
CONF_DIR="/usr/share/X11/xorg.conf.d"
CONF_FILE="$CONF_DIR/99-calibration.conf"

if [ -d "$CONF_DIR" ]; then
    echo 'Section "InputClass"' | sudo tee $CONF_FILE > /dev/null
    echo '        Identifier      "calibration"' | sudo tee -a $CONF_FILE > /dev/null
    echo '        MatchProduct    "ADS7846 Touchscreen"' | sudo tee -a $CONF_FILE > /dev/null
    echo '        Option  "TransformationMatrix"  "-1 0 1 0 1 0 0 0 1"' | sudo tee -a $CONF_FILE > /dev/null
    echo 'EndSection' | sudo tee -a $CONF_FILE > /dev/null
    echo "Persistent calibration installed to $CONF_FILE"
else
    echo "Warning: X11 config directory $CONF_DIR not found. Checking alternative /etc/X11..."
    ALT_DIR="/etc/X11/xorg.conf.d"
    if [ -d "$ALT_DIR" ]; then
        CONF_FILE="$ALT_DIR/99-calibration.conf"
        echo 'Section "InputClass"' | sudo tee $CONF_FILE > /dev/null
        echo '        Identifier      "calibration"' | sudo tee -a $CONF_FILE > /dev/null
        echo '        MatchProduct    "ADS7846 Touchscreen"' | sudo tee -a $CONF_FILE > /dev/null
        echo '        Option  "TransformationMatrix"  "-1 0 1 0 1 0 0 0 1"' | sudo tee -a $CONF_FILE > /dev/null
        echo 'EndSection' | sudo tee -a $CONF_FILE > /dev/null
        echo "Persistent calibration installed to $CONF_FILE"
    else
        echo "Warning: Could not find X11 config directories to make calibration persistent."
    fi
fi
