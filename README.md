# Sonos Macropad Controller

Add physical controls to your [sonos-vinyl](https://github.com/deichten/sonos-vinyl) setup using a DOIO KB03B macropad. Press keys to control playback, adjust volume, and manage multi-room audio.

Essentially, sonos-macropad turns key presses into http requests to your sonos-http-api server. 

When you run sonos-macropad, it first generates action scripts (bash scripts that contain curl commands) with your settings baked in. It then finds and monitors your macropad continuously, sending actions when you press a key.

Sonos-macropad is designed to control a primary room by default, while also supporting grouping or ungrouping secondary rooms.

## Features

- Performs one of the following Sonos actions when you press a key: Play/pause, next track, play a playlist, group or ungroup rooms (triple key press detection), or change volume.
- Handles volume levels in a useful way. You can adjust volume stepping for knob turns, set volume limits, or set a minimum volume when grouping rooms. Silences all rooms when you turn your primary room's volume all the way down.
- Automatically recovers from bluetooth disconnects.
- Writes helpful logs; supports additional validation checks (to help with any troubleshooting).

## Requirements

Before installing sonos-macropad, make sure your system meets these prerequisites.

**Hardware:**
- Raspberry Pi with Bluetooth capability
- DOIO KB03B macropad (already paired with bluetoothctl)
- Sonos speakers on your network

**Software:**
- Python 3.7+ with evdev library (input device event interface)
- Sonos HTTP API server running on your network
- Pi user has input group permissions for device access

The DOIO KB03B requires custom VIA key mappings to work with this project. VIA is an open-source keyboard configuration tool, available at: https://usevia.app 

You have to map the following keys to your macropad ahead of time:
- **3 keyboard keys** on the front face: Q (left key), W (middle key), E (right key)
- **Rotary encoder knob** in the center with display: R (knob counter-clockwise), T (knob clockwise)

## Installation

Follow these steps to get sonos-macropad running on your system. This guide assumes you've already installed sonos-http-api as part of a sonos-vinyl installation.

1. **Install dependencies:**
   ```bash
   pip install evdev
   sudo usermod -a -G input $USER
   # Log out and back in after adding user to input group
   ```

2. **Download and configure:**
   ```bash
   # Download project files
   curl -L https://github.com/jaredtrent/sonos-macropad/archive/refs/heads/main.zip -o sonos-macropad.zip
   unzip sonos-macropad.zip
   cd sonos-macropad-main
   
   # Edit config.ini with your settings
   nano config.ini
   ```

3. **Optionally validate settings, Sonos configuration, and API and device connectivity**
   ```bash
   # Test your settings
   python3 sonos-macropad.py --validate
   # Check sonos-macropad.config-errors.log for any errors
   
   # Run sonos-macropad normally (Ctrl+C to stop)
   python3 sonos-macropad.py
   ```

After installing, I recommend that you configure it to run as a service. See docs/SETUP.md for more information.

## How It Works

**Configuration Loading and Validation:**
Prevents common setup errors by validating your config.ini settings on startup. Supports startup flags for validating any or all settings, including API connectivity, room names, favorite playlist name, volume settings, device permissions, and file paths. When validation fails, sonos-macropad logs specific error messages with resolution steps to `sonos-macropad.config-errors.log`.

**Action Scripts:**
Generates six bash scripts with your configuration values embedded directly to perform Sonos actions: `playpause`, `next`, `volumeup`, `volumedown`, `favorite_playlist`, and `groups-and-volume`. Action scripts regenerate automatically when your config.ini changes or when scripts are missing.

Each bash script contains curl commands that embed your settings. For example, with `api_host = 192.168.1.100` and `primary_room = Living Room`:

```bash
# playpause script checks state and toggles
curl -s "http://192.168.1.100:5005/Living%20Room/playpause"

# next script skips track
curl -s "http://192.168.1.100:5005/Living%20Room/next"

# favorite_playlist script starts playlist
curl -s "http://192.168.1.100:5005/Living%20Room/favorite/My%20Playlist"
```

**Comprehensive Logging:**
Provides visibility into system behavior for troubleshooting and monitoring. Offers three types of logging:
- `sonos-macropad.config-errors.log` - Configuration validation errors with solutions
- `sonos-macropad.log` - Key presses and operational events
- `sonos-macropad.debug.log` - Automatic function tracing (with --debug flag)

**Device Discovery:**
Scans `/dev/input/event0-4` to find your configured device name, then monitors that device for key events. Automatically recovers if there's a bluetooth issue. Note that you must manually pair your device with your Pi before running the script for the first time. For more information, see docs/SETUP.md

**Multi-Press Detection:**
Supports multi-press functionality without interfering with single-press actions. Waits 0.8 seconds after detecting Q or W key presses to check for triple presses. If you press the same key three times within this window, sonos-macropad cancels the single action and runs the triple action instead. T, R, and E keys execute immediately since they don't have triple-press actions.

**Volume Burst Optimization:**
Reduces API calls and improves responsiveness during rapid volume adjustments. Accumulates rapid knob turns within 100ms and sends single API command instead of multiple calls. This eliminates lag when you're quickly adjusting volume and reduces load on your Sonos HTTP API server.

**Multi-Room Volume Control:**
Adjusts volume differently based on your current room grouping. When your primary room is alone, volume changes affect only that room. When your primary room is grouped with secondary rooms, adjusts all rooms simultaneously using different step sizes. Includes a setting for minimum grouping volume, which sets all rooms in a group to a minimum volume level. 

**Queue-Based Processing:**
Ensures thread-safe operation and consistent processing across all actions. Uses dedicated worker threads for volume and key actions with proper queue management. Volume accumulator sends accumulated changes to volume queue, eliminating race conditions.


## Configuration

Customize sonos-macropad behavior by editing these settings in the config.ini file.

```ini
[sonos]
# Your Sonos HTTP API server's IP address or hostname
api_host = 192.168.1.100
# API server port
api_port = 5005                 
# Main room name from Sonos app
primary_room = Living Room
# Additional rooms for grouping, comma separated
secondary_rooms = Kitchen,Dining Room, Bathroom  
# Playlist name from Sonos favorites
favorite_playlist = Discovery Weekly

[macropad]
# Device name pattern to search for
device_name = DOIO_KB03B    
# Installation directory (action scripts, error log, and debug log are written here)
install_dir = /home/pi/sonos-macropad
# Main log file name
log_file = sonos-macropad.log 

[volume]
# Primary room volume change per knob turn (1-10)
primary_single_step = 3 
# Maximum volume limit (1-100), helps keep you from blasting your speakers if there's lag
primary_max = 50               
# Minimum volume when grouping (1-50), if your primary speakers are below this volume and you group all, set your primary speakers to this volume 
primary_min_grouping = 10      
# Volume change for secondary rooms (1-5)
secondary_step = 2             
# Maximum volume for secondary rooms (1-100)
secondary_max = 40          
# Minimum volume for secondary rooms (1-20)   
secondary_min_grouping = 8     
```

**Discovery Commands:**
You can use these commands and check sonos-macropad.config-errors.log for any errors to help find the correct values for your system:
```bash
python3 sonos-macropad.py --validate rooms      # Discover room names
python3 sonos-macropad.py --validate playlist   # Discover playlists
python3 sonos-macropad.py --validate device     # Discover device name
```

## Command Line Options

This section covers the flags you can use when running sonos-macropad for testing and debugging.

```bash
python3 sonos-macropad.py --help                    # Show all available options
python3 sonos-macropad.py --debug                   # Enable automatic function tracing
python3 sonos-macropad.py --validate                # Test external settings (api, rooms, playlist, device)
python3 sonos-macropad.py --validate api,rooms      # Test specific components
python3 sonos-macropad.py --skip-validation host    # Skip specific local validations
```

## License

This project is licensed under the GPL-3.0 License - see the [LICENSE](LICENSE) file for details.

## Contributing

Issues and pull requests are welcome! Please feel free to contribute to this project.

## Credits

Entirely vibe coded, so, proceed with caution.

AI says it looks good. But AI also helped make it. 

Props to [node-sonos-http-api](https://github.com/jishi/node-sonos-http-api) for Sonos communication.
And to [sonos-vinyl](https://github.com/deichten/sonos-vinyl) for the great NFC reader project.

This is a personal project and is not affiliated with or endorsed by Sonos, Inc.

**Version:** 2026.1.8