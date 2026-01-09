# Sonos Macropad Controller Setup Guide

[AI-generated, human-reviewed]

Complete setup instructions for getting your macropad controlling Sonos speakers. This guide walks you through installation, configuration, and troubleshooting to get you up and running quickly.

## Overview

This setup process takes about 15-20 minutes and assumes you have basic Linux command line familiarity.

You'll install dependencies, configure your macropad device, set up the Sonos connection, and optionally install as a system service for automatic startup.

## Prerequisites

Make sure your system has these components before starting installation.

### Required Hardware
- Raspberry Pi (or Linux system) with Bluetooth capability
- DOIO KB03B macropad (or compatible input device)
- Sonos speakers on your network

### Required Software
- Python 3.7+ with pip package manager
- Sonos HTTP API server running on your network
- VIA software for macropad key configuration

### Network Requirements
- Macropad paired via Bluetooth (if wireless)
- Sonos HTTP API accessible from your Pi
- All devices on same network as Sonos speakers

## Installation

Follow these steps in order to install sonos-macropad on your system.

### 1. Install Python Dependencies

Install the required Python library for input device monitoring:

```bash
# Install evdev for input device access
pip install evdev

# Add your user to input group for device permissions
sudo usermod -a -G input $USER

# Log out and back in for group changes to take effect
# Or reboot your system
```

### 2. (Optional) Install Sonos HTTP API

Set up the Sonos HTTP API server that sonos-macropad uses to communicate with your speakers, if you haven't already. Note that if you've already set up vinylemulator, then you've already set up sonos-http-api as part of that process:

```bash
# Install Node.js if not already installed
curl -fsSL https://deb.nodesource.com/setup_lts.x | sudo -E bash -
sudo apt-get install -y nodejs

# Clone and install Sonos HTTP API
git clone https://github.com/jishi/node-sonos-http-api.git
cd node-sonos-http-api
npm install

# Start the API server (runs on port 5005 by default)
npm start
```

The Sonos HTTP API is a separate project. Follow their documentation for advanced configuration and service setup.

### 3. Download Sonos Macropad Controller

Get the sonos-macropad files and prepare for configuration:

```bash
# Download project files to your preferred location
cd ~
# Extract downloaded files to sonos-macropad-controller directory
cd sonos-macropad-controller

# Verify files are present
ls -la
# Should see: sonos-macropad.py, config.ini.example, docs/, etc.
```

## Configuration

Set up sonos-macropad to work with your specific Sonos system and macropad device.

### 1. Create Configuration File

Start with the provided example and customize for your system:

```bash

# Edit with your settings
nano config.ini
```

### 2. Configure Sonos Settings

Edit the `[sonos]` section with your system details:

```ini
[sonos]
# IP address of your Sonos HTTP API server
api_host = 192.168.1.100        # Change to your API server IP
api_port = 5005                 # Usually 5005, change if different

# Room names (must match Sonos app exactly)
primary_room = Living Room      # Your main Sonos room
secondary_rooms = Kitchen,Bed   # Other rooms for grouping

# Playlist name (must match Sonos app exactly)
favorite_playlist = My Mix      # Your favorite playlist
```

**Finding Your Settings:**
Use these discovery commands to find the correct values (external validations are skipped by default):

```bash
# Discover available rooms in your Sonos system
python3 sonos-macropad.py --validate rooms

# Discover available playlists
python3 sonos-macropad.py --validate playlist

# Test API connectivity
python3 sonos-macropad.py --validate api
```

### 3. Configure Macropad Settings

Edit the `[macropad]` section for your device and file locations:

```ini
[macropad]
# Device name (discover with --validate device command, after you've paired it with bluetooth)
device_name = DOIO_KB03B        # Change if using different device

# File locations
install_dir = /home/pi/sonos-macropad # Where scripts, debug, and error logs are generated
log_file = sonos-macropad.log   # Log file name
```

### 4. Configure Volume Settings

Edit the `[volume]` section to control volume behavior:

```ini
[volume]
# Primary room volume settings
primary_single_step = 3         # Volume change per knob turn (1-10)
primary_max = 50               # Maximum volume limit (1-100)
primary_min_grouping = 10      # Minimum volume when grouping (1-50)

# Secondary room volume settings
secondary_step = 2             # Volume change for other rooms (1-5)
secondary_max = 40             # Maximum volume for other rooms (1-100)
secondary_min_grouping = 8     # Minimum volume for other rooms (1-20)
```

**Volume Logic:**
- When primary room is alone: only primary room volume changes
- When rooms are grouped: all rooms adjust with different step sizes
- Minimum grouping volumes prevent silent rooms after grouping
- Automatically prevents sending volume increases for values above your max 

## Macropad Setup

Configure your DOIO KB03B macropad to send the correct key codes.

### Key Mapping Requirements

Your macropad must send these specific key codes for sonos-macropad to work:

| Physical Key | Required Key Code | Action |
|--------------|-------------------|--------|
| Left key | Q | Play/pause |
| Middle key | W | Next track |
| Right key | E | Favorite playlist |
| Knob turn right | T | Volume up |
| Knob turn left | R | Volume down |

### Configure with VIA Software

Use VIA software to program your macropad with the required key mappings:

1. **Download VIA:** Get VIA from https://github.com/the-via or use the web version at https://usevia.app

2. [TBD additional steps here, VIA is janky]

### Pair your device with bluetoothctl ###

1. [TBD additional steps here]

## Validation and Testing

Verify your configuration works correctly before running as a service.

### 1. Validate Configuration

Test all your settings against your live Sonos system (external validations enabled):

```bash
# Test all external settings (comprehensive validation)
python3 sonos-macropad.py --validate

# Test specific components if needed
python3 sonos-macropad.py --validate api,rooms,device
```

**Common Validation Issues:**
- Room names don't match Sonos app exactly (check capitalization/spaces)
- Playlist name not found (check spelling and favorites list)
- Device not accessible (check permissions and pairing)
- API not reachable (verify Sonos HTTP API is running)

### 2. Test Manual Operation

Run sonos-macropad manually to verify key presses work:

```bash
# Start controller (Ctrl+C to stop)
python3 sonos-macropad.py

# Test each key on your macropad:
# - Left key (Q): Should play/pause music
# - Middle key (W): Should skip to next track  
# - Right key (E): Should start your favorite playlist
# - Knob right (T): Should increase volume
# - Knob left (R): Should decrease volume
```

### 3. Test Multi-Press Actions

Verify triple-press functionality works correctly:

```bash
# With sonos-macropad running:
# - Press left key 3 times quickly: Should group all rooms
# - Press middle key 3 times quickly: Should ungroup all rooms
```

**Note:** Triple-press actions have a 0.8 second detection window.

## Service Installation

Set up sonos-macropad to start automatically with your system.

### 1. Create Service File

Create a systemd service file for automatic startup:

```bash
# Create service file
sudo nano /etc/systemd/system/sonos-macropad.service

# Add this content (adjust paths as needed):
[Unit]
Description=Sonos Macropad Controller
After=network.target

[Service]
Type=simple
User=pi
WorkingDirectory=/home/pi/sonos-macropad-controller
ExecStart=/usr/bin/python3 /home/pi/sonos-macropad-controller/sonos-macropad.py
Restart=on-failure
RestartSec=10

[Install]
WantedBy=multi-user.target
```

### 2. Enable and Start Service

Configure the service to start automatically:

```bash
# Reload systemd configuration
sudo systemctl daemon-reload

# Enable service for automatic startup
sudo systemctl enable sonos-macropad

# Start service now
sudo systemctl start sonos-macropad

# Check service status
sudo systemctl status sonos-macropad
```

### 3. Monitor Service Operation

Verify the service is running correctly:

```bash
# Check service logs
sudo journalctl -u sonos-macropad -f

# Check application logs
tail -f /home/pi/sonos-macropad/sonos-macropad.log

# Test key presses work with service running
```

## Advanced Configuration

Additional options for customizing sonos-macropad behavior.

### Debug Mode

Enable automatic function tracing for troubleshooting issues:

```bash
# Run with debug tracing
python3 sonos-macropad.py --debug

# Debug traces go to: sonos-macropad.debug.log
tail -f sonos-macropad.debug.log
```

### Skip Validations

Skip time-consuming validations for faster startup:

```bash
# Skip specific validations
python3 sonos-macropad.py --skip-validation host,port

# Skip all local validations (use carefully)
python3 sonos-macropad.py --skip-validation all
```

### Custom Installation Directory

Change where action scripts are generated:

```ini
[macropad]
install_dir = /custom/path/macropad  # Must be writable by your user
```

### Volume Behavior Tuning

Adjust volume control for your preferences:

```ini
[volume]
primary_single_step = 5         # Larger steps for faster volume changes
primary_max = 75               # Lower maximum for hearing protection
secondary_step = 1             # Smaller steps for fine control
```

## Log Files

Understanding the different log files sonos-macropad creates.

### Log File Types

sonos-macropad creates three types of log files for different purposes:

- **`sonos-macropad.log`** - Normal operation events (key presses, actions, status)
- **`sonos-macropad.debug.log`** - Automatic function tracing (only with --debug flag)
- **`sonos-macropad.config-errors.log`** - Configuration errors with resolution steps

### Log Rotation

All log files automatically rotate to prevent disk space issues:
- Maximum size: 10MB per log file
- Backup files: 3 previous versions kept
- Old logs automatically compressed and removed

### Monitoring Logs

Use these commands to monitor sonos-macropad operation:

```bash
# Watch normal operation
tail -f sonos-macropad.log

# Watch debug output (if debug mode enabled)
tail -f sonos-macropad.debug.log

# Check for configuration errors
cat sonos-macropad.config-errors.log
```

## Getting Help

Resources for additional assistance and troubleshooting.

### Built-in Help

sonos-macropad includes comprehensive help information:

```bash
# Show all command line options
python3 sonos-macropad.py --help

# Validate specific components
python3 sonos-macropad.py --validate [type]

# Enable debug mode for automatic function tracing
python3 sonos-macropad.py --debug
```

### Common Issues

Most setup issues fall into these categories:

1. **Configuration errors:** Check `sonos-macropad.config-errors.log`
2. **Device connection:** Use `--validate device` and check Bluetooth pairing
3. **API connection:** Verify Sonos HTTP API is running and accessible
4. **Permission issues:** Ensure user is in input group and directories are writable
5. **Room/playlist names:** Must match Sonos app exactly (case-sensitive)

For detailed troubleshooting steps, enable debug mode and check the debug log for specific error messages. Or see docs/TROUBLESHOOTING.md
