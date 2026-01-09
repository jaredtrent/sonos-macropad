# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Calendar Versioning](https://calver.org/).

## [2026.1.8] - 2026-01-08

### Added
- Initial release of Sonos Macropad Controller
- Main controller script (`sonos-macropad.py`) with device monitoring and key press handling
  - Action scripts for Sonos control:
    - Play/pause toggle
    - Next track
    - Volume up/down with multi-room support
    - Favorite playlist playback
    - Room grouping/ungrouping
  - Triple key press detection for secondary actions
  - Automatic device reconnection on bluetooth disconnect
  - Configuration validation with error logging
  - Volume burst optimization to reduce API calls
  - Multi-room volume control with different step sizes
- Configuration file (`config.ini`) for API, device, and volume settings
- Installation and setup documentation
- Troubleshooting guide with diagnostic commands

### Requirements
- Python 3.7+ with evdev library
- Sonos HTTP API server running on network
- DOIO KB03B macropad with VIA key mappings
- Raspberry Pi with Bluetooth capability
- User permissions for input device access
