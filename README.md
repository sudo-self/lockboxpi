# Lockboxpi

<img width="981" height="651" alt="lockboxGUI" src="https://github.com/user-attachments/assets/46c7a8af-9055-422b-9e82-8d32661373c4" />

## Project Overview

LockboxPi is a professional-grade forensic dashboard and hardware control suite designed specifically for a 3.5-inch TFT touch interface on Raspberry Pi. It serves as a unified bridge between mobile forensic tools—specifically **MTKClient** and **LockKnife**—and a web-based management terminal. The system is optimized for high-contrast visibility and touch accuracy in moble environments.

----------

## System Components

### 1. Web Dashboard (`html`)

The frontend is a touch-optimized application using the **Tectonic Utility** design language.

-   **Resolution:** Native 480x320 alignment.
    
-   **Vitals:** Real-time monitoring of CPU temperature, available storage, system uptime, and dynamic IP address.
    
-   **Touch Navigation:** Large hitboxes for switching between ADB, MTK, Knife, and Terminal modes.
    
-   **Interactive Controls:** The center status orb functions as a trigger for the WiFi configuration utility.
    

### 2. Hardware Bridge (`python flask`)

A Flask-based backend that handles communication between the UI and the Linux system.

-   **Root Execution:** Handles sudo-level commands for forensic dumping.
    
-   **State Detection:** Monitors USB ports for BROM mode, Preloader, and ADB devices.
    
-   **Storage Management:** Direct injection of network credentials into the DietPi WiFi database.
    

### 3. Media Pipeline

Commands for generating and deploying assets optimized for the 3.5" TFT display.

#### Convert MOV to TFT GIF

Bash

```
ffmpeg -i lockbox.mov -vf "fps=10,scale=480:320:flags=lanczos,split[s0][s1];[s0]palettegen[p];[s1][p]paletteuse" lockbox.gif

```

#### Convert SVG to TFT GIF (Mac Method)

This process ensures animated SVGs are rasterized correctly with a high-quality palette.

Bash

```
magick -size 480x320 lockbox.svg -duplicate 29 frame_%03d.png && \
ffmpeg -i frame_%03d.png -vf "fps=10,scale=480:320:flags=lanczos,split[s0][s1];[s0]palettegen[p];[s1][p]paletteuse" -y lockbox.gif && \
rm frame_*.png

```
----------

## Deployment Strategy

### Git Repository Setup (Raspberry Pi)

To set up the project directly on your Raspberry Pi using Git, follow these steps:

1. Clone the repository into the web server directory:
```bash
sudo git clone https://github.com/sudo-self/lockboxpi.git /var/www/
```

2. Ensure correct permissions are applied so the web server and the bridge service can access the files:
```bash
sudo chown -R lockboxpi:www-data /var/www
sudo chmod -R 755 /var/www
sudo chmod -R 777 /var/www/dumps
```

3. Restart the background service to apply the new files:
```bash
sudo systemctl restart lockbox-bridge.service
sudo systemctl reload apache2
```

### Remote Refresh Configuration

The `push.sh` script automates the transfer of code and assets. To ensure the TFT display reflects changes immediately, the script uses `xdotool` combined with `XAUTHORITY` to bypass X11 permission locks.

#### Deployment Command

Bash

```
./push.sh
```

### Path Requirements

The following paths must be configured on the Raspberry Pi for the bridge to function:

-   **MTK Environment:** `/home/lockboxpi/mtk_env/bin/python3`
    
-   **MTK Script:** `/home/lockboxpi/mtkclient/mtk.py`
    
-   **LockKnife Script:** `/home/lockboxpi/LockKnife/LockKnife.sh`
    
-   **Dumps Directory:** `/var/www/dumps`
    
-   **WiFi Database:** `/var/lib/dietpi/dietpi-wifi.db`
    

----------

## Forensic Operation Modules

### ADB Mode

Used for standard device interaction and authorization. The status indicator glows green when an authorized device is detected.

### MTK Engine

Direct interface for MediaTek devices.

-   **BROM/Preloader Detection:** Visual feedback in the MTK status field.
    
-   **Read GPT:** Immediate output of the device partition table to the terminal.
    

### Forensic Knife

Advanced modules for data extraction.

-   **PULL KEY:** Extracts pattern/password files from the device.
    
-   **DUMP SYS:** Initiates a full forensic image of the system partition directly to the `/var/www/dumps` directory.
    

### Terminal (TERM)

A macro-enabled CLI for system-level operations.

-   **RE_BRIDGE:** Restarts the Flask service.
    
-   **REBOOT:** Cycles system power.
    
-   **EXP:** Opens the Apache directory index for file verification.
```
