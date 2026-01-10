# Changelog

## [2026.1.9] - 2026-01-09

### Added
- Added tests to help with development (tools/*)
- Added more startup validations (with helpful error messages)

### Improved
- Improved security against malicious scripts

### Fixed
- Fixed an issue with error handling during device disconnects

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
