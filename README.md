# Lockboxpi

<img width="1485" height="914" alt="Untitled" src="https://github.com/user-attachments/assets/1c23a401-9ea9-4795-ae8a-67b298640615" />



## Project Overview

LockboxPi is a professional-grade forensic dashboard and hardware control suite designed specifically for a 3.5-inch TFT touch interface on Raspberry Pi. It serves as a unified bridge between mobile forensic tools—specifically **MTKClient** and **LockKnife**—and a web-based management terminal. The system is optimized for high-contrast visibility and touch accuracy in mobile environments.

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

```bash
ffmpeg -i lockbox.mov -vf "fps=10,scale=480:320:flags=lanczos,split[s0][s1];[s0]palettegen[p];[s1][p]paletteuse" lockbox.gif
```

#### Convert SVG to TFT GIF (Mac Method)

This process ensures animated SVGs are rasterized correctly with a high-quality palette.

```bash
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

```bash
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

## Telegram Bot Integration

LockboxPi features a powerful Telegram bot that allows for remote administration and execution of forensic operations. The bot runs as a systemd service (`telegram-bot.service`).

### Basic Usage & System Commands

You can interact with the bot to check system status or connected devices:

```text
/lsusb       - Lists connected USB devices
/whoami      - Shows current user info
/ipaddr      - Displays IP address
/diskfree    - Shows free disk space
/syslog      - Shows the last 30 lines of the system log (dmesg)
/reboot      - Initiates a system reboot
```

### ADB Operations

The bot provides direct access to ADB commands:

```text
/adb           - Checks ADB connection status
/adbdevices    - Lists connected ADB devices
/adbbootloader - Reboots the connected device to bootloader
/installapk    - Installs an APK (Usage: /installapk <path_to_apk>)
```

### MTKClient Commands

Execute MediaTek bypass and dumping operations remotely:

```text
/mtkhelp            - Shows MTK Client help
/mtkgpt             - Dumps MTK GPT partition table
/mtkgettargetconfig - Gets MTK target config
/mtkfrp             - Erases MTK FRP partition
/mtkunlock          - Unlocks MTK device via seccfg
```

### LockKnife & Dumps Management

Extract keys or partitions and manage the output files:

```text
/knifekey   - Extracts keys via LockKnife
/knifedumpr - Dumps partitions via LockKnife
/listdumps  - Lists all files stored in the dumps folder
/sendfile   - Sends a specific file from the dumps folder (Usage: /sendfile filename.img)
```

**File Uploads:** You can also upload any file directly by sending it to the chat. The bot will automatically save it to the dumps folder.

### Display & Bridge Controls

```text
/touchrotate - Rotates touch orientation by 90 degrees
/touchcalib  - Runs the touchscreen calibrator tool
/rebridge    - Restarts the lockbox-bridge service
/terminal    - Run raw shell commands (Usage: /terminal <command>)
```

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
