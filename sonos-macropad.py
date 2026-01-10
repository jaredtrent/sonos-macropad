#!/usr/bin/env python3

"""
======================================
SONOS MACROPAD CONTROLLER
======================================
Monitors macropad input device for key presses and controls Sonos
speakers via HTTP API. Supports multi-room grouping, volume
control, and playlists.

Project: https://github.com/jaredtrent/sonos-macropad

Copyright (C) 2026 Jared Trent

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program. If not, see <https://www.gnu.org/licenses/>.

TABLE OF CONTENTS:
--------------------------------------
 1. Imports and Dependencies
 2. Constants
 3. Version and Command Line Handling
 4. Embedded Bash Action Script Templates
 5. Action Script Generation
 6. Automatic Debug Tracing System
 7. Logging
 8. Validation Helper Functions
 9. Configuration Loading and Validation
10. Sonos-Macropad Key Mappings
11. Device Discovery
12. Graceful Shutdown Handling
13. Queue-Based Action Processing
14. Main Event Loop and Input Processing
15. Entry Point
======================================
"""

"""
======================================
IMPORTS AND DEPENDENCIES
======================================
Required libraries for device monitoring, HTTP calls, and config parsing.
Evdev handles input devices - required for normal operation, optional for --help
"""

# Standard library imports - loaded first before any validation
import os
import time
import configparser
import threading
import queue
import urllib.parse
import re
import subprocess
import sys
import signal
import logging
import logging.handlers
import json
import shutil
import inspect
from pathlib import Path

# External dependency with graceful fallback - allows --help to work without evdev installed
# evdev handles input devices - required for normal operation, optional for --help

# Validate command line arguments early - before any imports that might fail
VALID_FLAGS = ['--help', '-h', '--debug', '-d', '--validate', '-v', '--skip-validation', '--s']
FLAGS_WITH_VALUES = ['--validate', '-v', '--skip-validation', '--s']
for i, arg in enumerate(sys.argv[1:], 1):
    if arg.startswith('-'):
        if arg not in VALID_FLAGS:
            print(f"Error: Unknown flag '{arg}'")
            print("Use --help to see available options")
            exit(1)
    else:
        # Check if this is a value for a flag that takes arguments
        prev_arg = sys.argv[i-1] if i > 0 else None
        if prev_arg not in FLAGS_WITH_VALUES:
            print(f"Error: Unexpected argument '{arg}'")
            print("Use --help to see available options")
            exit(1)

try:
    from evdev import InputDevice, categorize, ecodes, list_devices
except ImportError:
    if '--help' not in sys.argv and '-h' not in sys.argv:
        print("evdev module not found. Install it with: pip install evdev")
        exit(1)
    # Allows --help to work even without evdev installed
    InputDevice = categorize = ecodes = list_devices = None

"""
======================================
CONSTANTS
======================================
Tunable behavior settings: device paths, timeouts, multi-press detection.
Change these to adjust timing or device scanning behavior.
"""

DEVICE_PATH_PATTERN = "/dev/input/event{}"
DEVICE_EVENT_NUMBERS = [0, 1, 2, 3, 4]
DEVICE_RETRY_MAX = 30  # max attempts per device search cycle
DEVICE_RETRY_INTERVAL = 0.5  # seconds between retry attempts
BLUETOOTH_INIT_DELAY = 2  # seconds to wait after bluetooth reconnect
MULTI_PRESS_WINDOW = 0.8  # seconds
VOLUME_BURST_WINDOW = 0.1  # seconds - window for accumulating rapid volume turns
MULTI_PRESS_COUNT = 3  # triple-press threshold
CURL_CONNECT_TIMEOUT = 2  # seconds
CURL_MAX_TIME = 5  # seconds - increased for volume operations
SCRIPT_TIMEOUT = 10  # seconds for action script execution
GROUP_SCRIPT_TIMEOUT = 15  # seconds for group/ungroup scripts
QUEUE_TIMEOUT = 1  # seconds for queue operations

# Logging configuration constants - centralized format strings and rotation settings
LOG_FORMATS = {
    'standard': '[%(asctime)s] %(levelname)s: %(message)s',
    'debug': '[%(asctime)s.%(msecs)03d] DEBUG: %(message)s',
    'config_error': '[%(asctime)s] CONFIG ERROR: %(message)s'
}
LOG_ROTATION = {
    'max_bytes': 10*1024*1024,  # 10MB - consistent across all loggers
    'backup_count': 3
}

"""
======================================
VERSION AND COMMAND LINE HANDLING
======================================
Command-line flags control script behavior: --help shows usage, --debug enables
automatic function tracing, --skip-validation bypasses specific validation checks.
"""

# Release version format: YYYY-MM-DD-Description-Increment - used in logs and help output
VERSION = "2026.1.9"

# Process --help first so it works even without dependencies - exits immediately if found
if '--help' in sys.argv or '-h' in sys.argv:
    print(f"Sonos Macropad Controller v{VERSION}")
    print()
    print("DESCRIPTION:")
    print("  Controls Sonos speakers via macropad key presses. Monitors input device for")
    print("  Q/W/E/R/T keys and executes corresponding Sonos actions via HTTP API.")
    print()
    print("USAGE:")
    print("  python3 sonos-macropad.py [options]")
    print()
    print("OPTIONS:")
    print("  --debug, -d")
    print("      Enables verbose debug logging to sonos-macropad.debug.log")
    print("      Used for troubleshooting device detection, API calls, and key events")
    print()
    print("  --validate [types], -v [types]")
    print("      Enables external validations that require network/device connectivity")
    print("      By default, external validations are SKIPPED for reliable service startup")
    print("      Use this flag for comprehensive validation during setup/testing")
    print()
    print("      Available types (default: all if no types specified):")
    print("        api           - Tests API connectivity")
    print("        rooms         - Validates rooms exist in Sonos system")
    print("        playlist      - Validates playlist exists in Sonos system")
    print("        device        - Validates device exists and is accessible")
    print()
    print("      Examples:")
    print("        --validate              (enables all external validations)")
    print("        --validate api,rooms    (enables only API and room validation)")
    print("        -v device               (enables only device validation)")
    print()
    print("  --skip-validation <types>, --s <types>")
    print("      Skips specific local validations (comma-separated list)")
    print("      Note: External validations (api, rooms, playlist, device) are controlled by --validate")
    print()
    print("      Available types:")
    print("        all           - Skips ALL local validations")
    print("        host          - Skips API host format validation")
    print("        port          - Skips API port format validation")
    print("        rooms         - Skips room logic checks (duplicates, conflicts)")
    print("        paths         - Skips log file + install directory checks")
    print("        volume        - Skips volume range + logic checks")
    print("        config        - Skips config sections/options validation - DANGEROUS!")
    print("        scripts-gen   - Skips script generation")
    print("        scripts-check - Skips script validation - existence/outdated")
    print()
    print("      Examples:")
    print("        --skip-validation host,port")
    print("        --skip-validation volume")
    print("        --skip-validation all")
    print()
    print("  --help, -h")
    print("      Shows this help message and exits")
    print()
    print("CONFIGURATION:")
    print("  Edit config.ini in the same directory as this script")
    print("  See docs/SETUP.md for detailed configuration instructions")
    print()
    print("LOGS:")
    print("  sonos-macropad.config-errors.log - Configuration validation errors")
    print("  sonos-macropad.debug.log         - Debug output (only with --debug)")
    print("  <configured>.log      - Operational events (configured in config.ini)")
    exit(0)

DEBUG_MODE = '--debug' in sys.argv or '-d' in sys.argv

# Parses validation skip flags
SKIP_VALIDATIONS = []
if '--skip-validation' in sys.argv or '--s' in sys.argv:
    idx = sys.argv.index('--skip-validation') if '--skip-validation' in sys.argv else sys.argv.index('--s')
    if idx + 1 < len(sys.argv) and not sys.argv[idx + 1].startswith('-'):
        requested_types = [v.strip().lower() for v in sys.argv[idx + 1].split(',')]
        # Validate that all requested types are valid for skipping
        valid_skip_types = ['all', 'host', 'port', 'rooms', 'paths', 'volume', 'config', 'scripts-gen', 'scripts-check']
        invalid_types = [t for t in requested_types if t not in valid_skip_types]
        if invalid_types:
            print(f"Error: Invalid skip-validation types: {', '.join(invalid_types)}")
            print(f"Valid types: {', '.join(valid_skip_types)}")
            print("Note: External validations (api, rooms, playlist, device) are controlled by --validate")
            exit(1)
        SKIP_VALIDATIONS = requested_types
    else:
        pass  # Skipped validation
        print("Error: --skip-validation requires validation types")
        print("Example: --skip-validation host,port")
        exit(1)

# Parses validation enable flags - opposite of skip, enables external validations
VALIDATE_EXTERNAL = '--validate' in sys.argv or '-v' in sys.argv
VALIDATE_TYPES = []
if VALIDATE_EXTERNAL and ('--validate' in sys.argv or '-v' in sys.argv):
    try:
        idx = sys.argv.index('--validate') if '--validate' in sys.argv else sys.argv.index('-v')
        if idx + 1 < len(sys.argv) and not sys.argv[idx + 1].startswith('-'):
            requested_types = [v.strip().lower() for v in sys.argv[idx + 1].split(',')]
            # Validate that all requested types are valid
            valid_types = ['api', 'rooms', 'playlist', 'device']
            invalid_types = [t for t in requested_types if t not in valid_types]
            if invalid_types:
                print(f"Error: Invalid validation types: {', '.join(invalid_types)}")
                print(f"Valid types: {', '.join(valid_types)}")
                exit(1)
            VALIDATE_TYPES = requested_types
        else:
            VALIDATE_TYPES = ['api', 'rooms', 'playlist', 'device']  # Default: all external validations
    except (IndexError, ValueError):
        VALIDATE_TYPES = ['api', 'rooms', 'playlist', 'device']  # Default: all external validations

SKIP_ALL = 'all' in SKIP_VALIDATIONS
# External validations - controlled only by --validate flag (cannot be skipped since they're skipped by default)
SKIP_API = not VALIDATE_EXTERNAL or 'api' not in VALIDATE_TYPES
SKIP_ROOMS_EXTERNAL = not VALIDATE_EXTERNAL or 'rooms' not in VALIDATE_TYPES
SKIP_PLAYLIST = not VALIDATE_EXTERNAL or 'playlist' not in VALIDATE_TYPES  
SKIP_DEVICE = not VALIDATE_EXTERNAL or 'device' not in VALIDATE_TYPES
# Always validate these unless explicitly skipped via --skip-validation
SKIP_HOST = 'host' in SKIP_VALIDATIONS or SKIP_ALL
SKIP_PORT = 'port' in SKIP_VALIDATIONS or SKIP_ALL
SKIP_ROOMS_LOGIC = 'rooms' in SKIP_VALIDATIONS or SKIP_ALL  # Room logic validation (duplicates, etc.)
SKIP_PATHS = 'paths' in SKIP_VALIDATIONS or SKIP_ALL
SKIP_VOLUME = 'volume' in SKIP_VALIDATIONS or SKIP_ALL
SKIP_CONFIG = 'config' in SKIP_VALIDATIONS or SKIP_ALL
SKIP_SCRIPTS_GEN = 'scripts-gen' in SKIP_VALIDATIONS or SKIP_ALL
SKIP_SCRIPTS_CHECK = 'scripts-check' in SKIP_VALIDATIONS or SKIP_ALL

"""
======================================
EMBEDDED BASH ACTION SCRIPT TEMPLATES
======================================
Six bash action script templates: groups-and-volume, playpause, next, volumeup,
volumedown, favorite_playlist. Generated from config.ini at startup.
"""

# Script templates that get converted to executable files - generated after config validation
SCRIPT_TEMPLATES = {
    # Smart volume and grouping with multi-room coordination - handles primary alone vs grouped scenarios
    'groups-and-volume': '''#!/bin/bash
# Sonos Macropad Controller - Volume Script v{version}
API_BASE="{api_base}"
PRIMARY_ROOM="{primary_room}"
PRIMARY_ROOM_ENCODED="{primary_room_encoded}"
PRIMARY_STEP="{primary_step}"
PRIMARY_MAX="{primary_max}"
PRIMARY_MIN_GROUPING="{primary_min_grouping}"
SECONDARY_STEP="{secondary_step}"
SECONDARY_MAX="{secondary_max}"
SECONDARY_MIN_GROUPING="{secondary_min_grouping}"
SECONDARY_ROOMS=({secondary_rooms})
SECONDARY_ROOMS_ENCODED=({secondary_rooms_encoded})

is_primary_alone() {{
    local zones=$(curl -s --connect-timeout {curl_connect_timeout} --max-time {curl_max_time} "$API_BASE/zones")
    local member_count=$(echo "$zones" | python3 -c "
import sys, json
try:
    zones = json.load(sys.stdin)
    primary_room = '$PRIMARY_ROOM'
    primary_zone = [z for z in zones if any(m['roomName']==primary_room for m in z['members'])]
    if primary_zone:
        print(len(primary_zone[0]['members']))
    else:
        print(0)
except (json.JSONDecodeError, KeyError, IndexError):
    print(0)
")
    [ "$member_count" -eq 1 ] && return 0 || return 1
}}

is_room_in_primary_zone() {{
    local room="$1"
    local zones=$(curl -s --connect-timeout {curl_connect_timeout} --max-time {curl_max_time} "$API_BASE/zones")
    echo "$zones" | grep -q "\\"roomName\\":\\"$room\\""
}}

# Secure API request function - checks HTTP response codes
api_request() {{
    local url="$1"
    local description="$2"
    local response=$(curl -s -w "\\n%{{http_code}}" --connect-timeout {curl_connect_timeout} --max-time {curl_max_time} "$url")
    local http_code=$(echo "$response" | tail -n1)
    
    if [ "$http_code" = "200" ]; then
        return 0  # Success
    else
        echo "$description (HTTP $http_code)" >&2
        return 1  # Failure
    fi
}}

get_volume() {{
    local room_encoded="$1"
    local response=$(curl -s --connect-timeout {curl_connect_timeout} --max-time {curl_max_time} "$API_BASE/$room_encoded/state")
    echo "$response" | grep -o '"volume":[0-9]*' | grep -o '[0-9]*'
}}


volume_up() {{
    local amount=${{1:-$PRIMARY_STEP}}
    if is_primary_alone; then
        current_primary=$(get_volume "$PRIMARY_ROOM_ENCODED")
        if [ "$current_primary" -ge "$PRIMARY_MAX" ]; then
            echo "KNOB ACTION SKIPPED - Volume up skipped on $PRIMARY_ROOM (already at maximum $PRIMARY_MAX)"
        else
            if [ "$current_primary" -ge $((PRIMARY_MAX - amount + 1)) ]; then
                if api_request "$API_BASE/$PRIMARY_ROOM_ENCODED/volume/$PRIMARY_MAX" "Volume up on $PRIMARY_ROOM"; then
                    echo "KNOB ACTION COMPLETE - Volume up on $PRIMARY_ROOM (set to maximum $PRIMARY_MAX)"
                else
                    echo "KNOB ACTION FAILED - Volume up on $PRIMARY_ROOM (API error)"
                fi
            else
                if api_request "$API_BASE/$PRIMARY_ROOM_ENCODED/volume/+$amount" "Volume up on $PRIMARY_ROOM"; then
                    echo "KNOB ACTION COMPLETE - Volume up on $PRIMARY_ROOM (+$amount)"
                else
                    echo "KNOB ACTION FAILED - Volume up on $PRIMARY_ROOM (API error)"
                fi
            fi
        fi
    else
        current_primary=$(get_volume "$PRIMARY_ROOM_ENCODED")
        if [ "$current_primary" -ge "$PRIMARY_MAX" ]; then
            echo "KNOB ACTION SKIPPED - Volume up skipped on $PRIMARY_ROOM (already at maximum $PRIMARY_MAX)"
        else
            if [ "$current_primary" -ge $((PRIMARY_MAX - amount + 1)) ]; then
                if api_request "$API_BASE/$PRIMARY_ROOM_ENCODED/volume/$PRIMARY_MAX" "Volume up on $PRIMARY_ROOM"; then
                    echo "KNOB ACTION COMPLETE - Volume up on $PRIMARY_ROOM (set to maximum $PRIMARY_MAX)"
                else
                    echo "KNOB ACTION FAILED - Volume up on $PRIMARY_ROOM (API error)"
                fi
            else
                if api_request "$API_BASE/$PRIMARY_ROOM_ENCODED/volume/+$amount" "Volume up on $PRIMARY_ROOM"; then
                    echo "KNOB ACTION COMPLETE - Volume up on $PRIMARY_ROOM (+$amount)"
                else
                    echo "KNOB ACTION FAILED - Volume up on $PRIMARY_ROOM (API error)"
                fi
            fi
        fi
        
        # Calculate proportional amount for secondary rooms
        secondary_amount=$((amount * SECONDARY_STEP / PRIMARY_STEP))
        [ "$secondary_amount" -lt 1 ] && secondary_amount=1
        
        for i in "${{!SECONDARY_ROOMS[@]}}"; do
            room="${{SECONDARY_ROOMS[$i]}}"
            room_encoded="${{SECONDARY_ROOMS_ENCODED[$i]}}"
            if is_room_in_primary_zone "$room"; then
                current_secondary=$(get_volume "$room_encoded")
                if [ "$current_secondary" -ge "$SECONDARY_MAX" ]; then
                    echo "KNOB ACTION SKIPPED - Volume up skipped on $room (already at maximum $SECONDARY_MAX)"
                elif [ "$current_secondary" -ge $((SECONDARY_MAX - secondary_amount + 1)) ]; then
                    (if api_request "$API_BASE/$room_encoded/volume/$SECONDARY_MAX" "Volume up on $room"; then
                        echo "KNOB ACTION COMPLETE - Volume up on $room (set to maximum $SECONDARY_MAX)"
                    else
                        echo "KNOB ACTION FAILED - Volume up on $room (API error)"
                    fi) &
                else
                    (if api_request "$API_BASE/$room_encoded/volume/+$secondary_amount" "Volume up on $room"; then
                        echo "KNOB ACTION COMPLETE - Volume up on $room (+$secondary_amount)"
                    else
                        echo "KNOB ACTION FAILED - Volume up on $room (API error)"
                    fi) &
                fi
            fi
        done
        wait
    fi
}}

volume_down() {{
    local amount=${{1:-$PRIMARY_STEP}}
    local current_primary=$(get_volume "$PRIMARY_ROOM_ENCODED")
    
    if [ "$current_primary" -le 0 ]; then
        echo "KNOB ACTION SKIPPED - Volume down skipped on $PRIMARY_ROOM (already at 0)"
    else
        # Calculate actual decrease (don't go below 0)
        local actual_decrease=$((current_primary < amount ? current_primary : amount))
        if api_request "$API_BASE/$PRIMARY_ROOM_ENCODED/volume/-$actual_decrease" "Volume down on $PRIMARY_ROOM"; then
            echo "KNOB ACTION COMPLETE - Volume down on $PRIMARY_ROOM (-$actual_decrease)"
        else
            echo "KNOB ACTION FAILED - Volume down on $PRIMARY_ROOM (API error)"
        fi
    fi
    
    # Check if primary is at 0 and in a group, then silence secondaries
    if ! is_primary_alone; then
        primary_vol=$(get_volume "$PRIMARY_ROOM_ENCODED")
        if [ "$primary_vol" -eq 0 ]; then
            for i in "${{!SECONDARY_ROOMS[@]}}"; do
                room="${{SECONDARY_ROOMS[$i]}}"
                room_encoded="${{SECONDARY_ROOMS_ENCODED[$i]}}"
                if is_room_in_primary_zone "$room"; then
                    (if api_request "$API_BASE/$room_encoded/volume/0" "Silence $room"; then
                        echo "KNOB ACTION COMPLETE - Silence $room ($PRIMARY_ROOM at 0)"
                    else
                        echo "KNOB ACTION FAILED - Silence $room (API error)"
                    fi) &
                fi
            done
            wait
        else
            # Calculate proportional amount for secondary rooms
            secondary_amount=$((amount * SECONDARY_STEP / PRIMARY_STEP))
            [ "$secondary_amount" -lt 1 ] && secondary_amount=1
            
            for i in "${{!SECONDARY_ROOMS[@]}}"; do
                room="${{SECONDARY_ROOMS[$i]}}"
                room_encoded="${{SECONDARY_ROOMS_ENCODED[$i]}}"
                if is_room_in_primary_zone "$room"; then
                    (if api_request "$API_BASE/$room_encoded/volume/-$secondary_amount" "Volume down on $room"; then
                        echo "KNOB ACTION COMPLETE - Volume down on $room (-$secondary_amount)"
                    else
                        echo "KNOB ACTION FAILED - Volume down on $room (API error)"
                    fi) &
                fi
            done
            wait
        fi
    fi
}}

smart_group() {{
    declare -A room_volumes
    # Save current volumes before grouping to restore appropriate levels after joining
    local primary_vol=$(get_volume "$PRIMARY_ROOM_ENCODED")
    for i in "${{!SECONDARY_ROOMS[@]}}"; do
        room="${{SECONDARY_ROOMS[$i]}}"
        room_encoded="${{SECONDARY_ROOMS_ENCODED[$i]}}"
        room_volumes["$room"]=$(get_volume "$room_encoded")
    done
    
    # Joins all rooms to primary zone in parallel for faster grouping
    for i in "${{!SECONDARY_ROOMS[@]}}"; do
        room="${{SECONDARY_ROOMS[$i]}}"
        room_encoded="${{SECONDARY_ROOMS_ENCODED[$i]}}"
        (if api_request "$API_BASE/$room_encoded/join/$PRIMARY_ROOM_ENCODED" "Group $room with $PRIMARY_ROOM"; then
            echo "KEY ACTION COMPLETE - Group $room with $PRIMARY_ROOM"
        else
            echo "KEY ACTION FAILED - Group $room with $PRIMARY_ROOM (API error)"
        fi) &
    done
    wait
    sleep 1
    
    # Boost primary room if below minimum grouping volume
    if [ "$primary_vol" -lt "$PRIMARY_MIN_GROUPING" ]; then
        if api_request "$API_BASE/$PRIMARY_ROOM_ENCODED/volume/$PRIMARY_MIN_GROUPING" "Boost $PRIMARY_ROOM to minimum grouping volume"; then
            echo "KEY ACTION COMPLETE - Boost $PRIMARY_ROOM to minimum grouping volume ($PRIMARY_MIN_GROUPING)"
        else
            echo "KEY ACTION FAILED - Boost $PRIMARY_ROOM to minimum grouping volume (API error)"
        fi
    fi
    
    # Boosts quiet rooms to minimum audible volume - prevents silent rooms after grouping
    for i in "${{!SECONDARY_ROOMS[@]}}"; do
        room="${{SECONDARY_ROOMS[$i]}}"
        room_encoded="${{SECONDARY_ROOMS_ENCODED[$i]}}"
        current_vol="${{room_volumes[$room]}}"
        if [ "$current_vol" -lt "$SECONDARY_MIN_GROUPING" ]; then
            (if api_request "$API_BASE/$room_encoded/volume/$SECONDARY_MIN_GROUPING" "Boost $room to minimum grouping volume"; then
                echo "KEY ACTION COMPLETE - Boost $room to minimum grouping volume ($SECONDARY_MIN_GROUPING)"
            else
                echo "KEY ACTION FAILED - Boost $room to minimum grouping volume (API error)"
            fi) &
        elif [ "$current_vol" -gt "$SECONDARY_MAX" ]; then
            (if api_request "$API_BASE/$room_encoded/volume/$SECONDARY_MAX" "Reduce $room to maximum volume"; then
                echo "KEY ACTION COMPLETE - Reduce $room to maximum volume ($SECONDARY_MAX)"
            else
                echo "KEY ACTION FAILED - Reduce $room to maximum volume (API error)"
            fi) &
        fi
    done
    wait
}}

ungroup_all() {{
    for i in "${{!SECONDARY_ROOMS[@]}}"; do
        room="${{SECONDARY_ROOMS[$i]}}"
        room_encoded="${{SECONDARY_ROOMS_ENCODED[$i]}}"
        (if api_request "$API_BASE/$room_encoded/leave" "Ungroup $room from $PRIMARY_ROOM"; then
            echo "KEY ACTION COMPLETE - Ungroup $room from $PRIMARY_ROOM"
        else
            echo "KEY ACTION FAILED - Ungroup $room from $PRIMARY_ROOM (API error)"
        fi) &
    done
    wait
}}

case "$1" in
    "up") 
        AMOUNT=${{2:-$PRIMARY_STEP}}
        volume_up $AMOUNT ;;
    "down") 
        AMOUNT=${{2:-$PRIMARY_STEP}}
        volume_down $AMOUNT ;;
    "group") smart_group ;;
    "ungroup") ungroup_all ;;
    *) echo "Usage: $0 {{up|down|group|ungroup}} [amount]"; exit 1 ;;
esac''',

    # Play/pause toggle - API handles state detection
    'playpause': '''#!/bin/bash
# Sonos Macropad Controller - Play/Pause Script v{version}
API_BASE="{api_base}"
PRIMARY_ROOM="{primary_room}"
PRIMARY_ROOM_ENCODED="{primary_room_encoded}"
response=$(curl -s -w "\\n%{{http_code}}" --connect-timeout {curl_connect_timeout} --max-time {curl_max_time} "$API_BASE/$PRIMARY_ROOM_ENCODED/playpause")
http_code=$(echo "$response" | tail -n1)
if [ "$http_code" = "200" ]; then
    echo "KEY ACTION COMPLETE - Play/pause on $PRIMARY_ROOM"
else
    echo "KEY ACTION FAILED - Play/pause on $PRIMARY_ROOM (HTTP $http_code)"
fi''',

    # Skips to next track
    'next': '''#!/bin/bash
# Sonos Macropad Controller - Next Track Script v{version}
API_BASE="{api_base}"
PRIMARY_ROOM="{primary_room}"
PRIMARY_ROOM_ENCODED="{primary_room_encoded}"
response=$(curl -s -w "\\n%{{http_code}}" --connect-timeout {curl_connect_timeout} --max-time {curl_max_time} "$API_BASE/$PRIMARY_ROOM_ENCODED/next")
http_code=$(echo "$response" | tail -n1)
if [ "$http_code" = "200" ]; then
    echo "KEY ACTION COMPLETE - Next track on $PRIMARY_ROOM"
else
    echo "KEY ACTION FAILED - Next track on $PRIMARY_ROOM (HTTP $http_code)"
fi''',

    # Volume up - calls main volume script with 'up' parameter
    'volumeup': '''#!/bin/bash
# Sonos Macropad Controller - Volume Up Script v{version}
INSTALL_DIR="{install_dir}"
"$INSTALL_DIR/groups-and-volume" up''',

    # Volume down - calls main volume script with 'down' parameter
    'volumedown': '''#!/bin/bash
# Sonos Macropad Controller - Volume Down Script v{version}
INSTALL_DIR="{install_dir}"
"$INSTALL_DIR/groups-and-volume" down''',

    # Starts the favorite playlist - uses URL-encoded playlist name from config
    'favorite_playlist': '''#!/bin/bash
# Sonos Macropad Controller - Favorite Playlist Script v{version}
API_BASE="{api_base}"
PRIMARY_ROOM="{primary_room}"
PRIMARY_ROOM_ENCODED="{primary_room_encoded}"
FAVORITE_PLAYLIST="{favorite_playlist}"
response=$(curl -s -w "\\n%{{http_code}}" --connect-timeout {curl_connect_timeout} --max-time {curl_max_time} "$API_BASE/$PRIMARY_ROOM_ENCODED/favorite/$FAVORITE_PLAYLIST")
http_code=$(echo "$response" | tail -n1)
if [ "$http_code" = "200" ]; then
    echo "KEY ACTION COMPLETE - Favorite playlist on $PRIMARY_ROOM"
else
    echo "KEY ACTION FAILED - Favorite playlist on $PRIMARY_ROOM (HTTP $http_code)"
fi'''
}

"""
======================================
ACTION SCRIPT GENERATION
======================================
Converts templates into executable bash scripts from config.ini values.
Regenerates when config.ini changes or scripts are missing.
"""

def scripts_need_update(config_path, install_dir):
    # Determines if action scripts require regeneration based on config file modification time and version
    if not config_path.exists():
        return True
    
    config_mtime = config_path.stat().st_mtime
    
    # Checks if any script is missing, older than config, or has wrong version
    for script_name in SCRIPT_TEMPLATES.keys():
        script_path = Path(install_dir) / script_name
        if not script_path.exists():
            return True
        if script_path.stat().st_mtime < config_mtime:
            return True
        
        # Check script version
        try:
            with open(script_path, 'r') as f:
                first_lines = f.read(200)  # Read first 200 chars to find version
                if f"v{VERSION}" not in first_lines:
                    return True
        except Exception as e:
            return True
    
    return False

def check_disk_space(path, min_mb=100):
    # Check available disk space before file operations
    try:
        stat = shutil.disk_usage(path)
        available_mb = stat.free / (1024 * 1024)
        return available_mb >= min_mb
    except Exception as e:
        return True  # Assume OK if check fails

def generate_embedded_scripts(config_values, install_dir):
    # Creates all 6 executable scripts with config values embedded - called after config validation passes
    # Overwrites existing files and sets permissions to 755
    
    # Add version to config values
    config_values_with_version = config_values.copy()
    config_values_with_version['version'] = VERSION
    
    # Check disk space before generating scripts
    if not check_disk_space(install_dir, 10):  # Require 10MB free space for script generation
        logging.warning("CONFIG - Low disk space, script generation may fail")
    
    try:
        for script_name, template in SCRIPT_TEMPLATES.items():
            script_path = os.path.join(install_dir, script_name)
            content = template.format(**config_values_with_version)
            
            with open(script_path, 'w') as f:
                f.write(content)
            os.chmod(script_path, 0o755)  # Make executable (owner: rwx, others: rx)
            
            # Verify file was created with correct permissions
            file_stat = os.stat(script_path)
            file_size = file_stat.st_size
            file_perms = oct(file_stat.st_mode)[-3:]
    except Exception as e:
        logging.warning(f"CONFIG - Action script generation failed: {e}")
        raise Exception(f"Failed to generate scripts: {e}") from e

"""
======================================
AUTOMATIC DEBUG TRACING SYSTEM
======================================
Replaces manual debug logging with automatic function tracing when --debug is enabled.
"""

class AutoDebugTracer:
    def __init__(self, debug_logger):
        self.debug_logger = debug_logger
        self.call_depth = 0
        self.max_depth = 8
        self.trace_functions = {
            'validate_host', 'validate_port', 'get_available_devices', 
            'get_available_playlists', 'get_available_rooms', 'test_device_exists',
            'find_doio_device', 'find_device_with_retry', 'main',
            'get_device_mac_address', 'attempt_bluetooth_reconnect',
            'volume_worker', 'key_worker', 'scripts_need_update', 'generate_embedded_scripts'
        }
    
    def trace_calls(self, frame, event, arg):
        if not DEBUG_MODE or self.call_depth > self.max_depth:
            return self.trace_calls
            
        func_name = frame.f_code.co_name
        filename = Path(frame.f_code.co_filename).name
        
        if filename != 'sonos-macropad.py' or func_name not in self.trace_functions:
            return self.trace_calls
            
        indent = "  " * self.call_depth
        
        if event == 'call':
            self.call_depth += 1
            args_info = inspect.getargvalues(frame)
            args_str = ", ".join([f"{k}={str(v)[:50]}" for k, v in args_info.locals.items() 
                                if not k.startswith('_')])[:200]
            self.debug_logger.debug(f"{indent}ENTER {func_name}({args_str})")
            
        elif event == 'return':
            self.call_depth = max(0, self.call_depth - 1)
            return_str = str(arg)[:100]
            self.debug_logger.debug(f"{indent}EXIT {func_name} -> {return_str}")
            
        elif event == 'exception':
            exc_type, exc_value, exc_tb = arg
            self.debug_logger.debug(f"{indent}EXCEPTION {func_name}: {exc_type.__name__}: {exc_value}")
            
        return self.trace_calls

"""
======================================
LOGGING
======================================
Three log types: config file validation (sonos-macropad.config-errors.log), debug mode (sonos-macropad.debug.log),
and standard sonos-macropad events (default: sonos-macropad.log).
"""

def setup_config_error_logging():
    # Creates configuration error logger with file handler on first error
    config_logger = logging.getLogger('config_errors')
    config_logger.setLevel(logging.ERROR)
    config_logger.propagate = False  # Prevent propagation to root logger
    return config_logger

def setup_debug_logging():
    # Debug logger for troubleshooting - only active with --debug flag, helps diagnose issues
    # Writes to sonos-macropad.debug.log with rotation and shows on console
    if not DEBUG_MODE:
        return None
    
    debug_log_path = Path(__file__).parent / 'sonos-macropad.debug.log'
    debug_logger = logging.getLogger('debug')
    debug_logger.setLevel(logging.DEBUG)
    debug_logger.propagate = False  # Prevent propagation to root logger
    handler = logging.handlers.RotatingFileHandler(
        debug_log_path, mode='a', 
        maxBytes=LOG_ROTATION['max_bytes'], 
        backupCount=LOG_ROTATION['backup_count']
    )
    formatter = logging.Formatter(LOG_FORMATS['debug'])
    handler.setFormatter(formatter)
    debug_logger.addHandler(handler)
    
    # Also shows debug messages on console - provides real-time feedback during troubleshooting
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    debug_logger.addHandler(console_handler)
    
    debug_logger.debug("=== DEBUG MODE ENABLED ===")
    debug_logger.debug(f"Script version: {VERSION}")
    
    # Enable automatic function tracing
    tracer = AutoDebugTracer(debug_logger)
    sys.settrace(tracer.trace_calls)
    debug_logger.debug("Automatic function tracing enabled")
    
    return debug_logger



def log_config_error(config_logger, error, resolution):
    # Log config errors with clear steps to fix them - creates file handler on first error
    if not config_logger.handlers:
        config_log_path = Path(__file__).parent / 'sonos-macropad.config-errors.log'
        handler = logging.FileHandler(config_log_path, mode='a')
        formatter = logging.Formatter(LOG_FORMATS['config_error'])
        handler.setFormatter(formatter)
        config_logger.addHandler(handler)
    
    config_logger.error(f"{error}")
    config_logger.error(f"To resolve: {resolution}")


"""
======================================
VALIDATION HELPER FUNCTIONS
======================================
Helper functions called by Configuration Loading and Validation section.
Provides validation logic for host/port, device scanning, and API data fetching.
"""

def validate_host(host):
    # Accept both IP addresses and hostnames - validates format only, no connectivity testing
    if not host or not isinstance(host, str):
        return False
        
    # Validate IP address format and check each octet is 0-255
    ip_pattern = r'^(\d{1,3}\.){3}\d{1,3}$'
    if re.match(ip_pattern, host):
        try:
            parts = host.split('.')
            if len(parts) != 4:  # Validate IP has exactly 4 octets (prevents incomplete IPs like '192.168.1')
                return False
            if not all(0 <= int(part) <= 255 for part in parts):
                return False
            return True  # Valid IP format
        except ValueError:
            return False
    else:
        # Validate hostname format per RFC 1123 (letters, numbers, dots, hyphens)
        if len(host) > 253:  # Hostname too long
            return False
        hostname_pattern = r'^[a-zA-Z0-9]([a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?(\.[a-zA-Z0-9]([a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?)*$'
        return re.match(hostname_pattern, host) is not None

def validate_port(port_str):
    # Validate port is in range 1-65535 (port 0 is reserved)
    try:
        port = int(port_str)
        is_valid = 1 <= port <= 65535
        return is_valid
    except ValueError as e:
        return False

def get_available_devices():
    # Enumerate available input devices from /dev/input for validation and suggestions
    # Implementation: Use evdev.list_devices() to enumerate paths, create InputDevice for each, extract name attribute, close devices after reading, handle exceptions gracefully
    try:
        devices = []
        for device_path in list_devices():
            try:
                dev = InputDevice(device_path)
                devices.append(dev.name)
                dev.close()
            except Exception as e:
                continue
        return devices
    except Exception as e:
        return []

def get_available_playlists(api_base):
    # Retrieve playlists from Sonos API with timeout, filtering to Spotify/streaming services
    try:
        start_time = time.time()
        result = subprocess.run(
            ['curl', '-s', '--connect-timeout', str(CURL_CONNECT_TIMEOUT), '--max-time', str(CURL_MAX_TIME), f"{api_base}/favorites"],
            capture_output=True, text=True, timeout=CURL_MAX_TIME
        )
        duration = time.time() - start_time
        
        if result.returncode == 0:
            favorites = json.loads(result.stdout)
            playlists = []
            for fav in favorites:
                if isinstance(fav, str):
                    # Simple string format - keep original name for validation
                    playlists.append(fav)
                elif isinstance(fav, dict) and fav.get('uri', '').startswith(('spotify:', 'x-sonosapi-stream:')):
                    # Object format - only include Spotify and streaming playlists
                    title = fav.get('title', '')
                    if title:
                        playlists.append(title)
            return sorted(playlists)
        else:
            return []
    except Exception as e:
        return []

def get_available_rooms(api_base):
    # Retrieve room names from Sonos /zones API with connection timeout
    try:
        start_time = time.time()
        result = subprocess.run(
            ['curl', '-s', '--connect-timeout', str(CURL_CONNECT_TIMEOUT), '--max-time', str(CURL_MAX_TIME), f"{api_base}/zones"],
            capture_output=True, text=True, timeout=CURL_MAX_TIME
        )
        duration = time.time() - start_time
        
        if result.returncode == 0:
            zones = json.loads(result.stdout)
            rooms = []
            for zone in zones:
                for member in zone.get('members', []):
                    room_name = member.get('roomName')
                    if room_name and room_name not in rooms:
                        rooms.append(room_name)
            return sorted(rooms)
        else:
            return []
    except Exception as e:
        return []

def test_device_exists(device_name):
    # Verify device exists, is accessible, and supports required keys (Q,W,E,R,T)
    # Returns (bool, suggestions_list) - filters out audio/video hardware
    available_devices = get_available_devices()
    
    if device_name in available_devices:
        # Device exists, now check if it's a valid input device for macropad use
        for event_num in DEVICE_EVENT_NUMBERS:
            device_path = DEVICE_PATH_PATTERN.format(event_num)
            try:
                if os.path.exists(device_path):
                    dev = InputDevice(device_path)
                    if hasattr(dev, 'name') and dev.name == device_name:
                        # Test readability
                        if not os.access(device_path, os.R_OK):
                            dev.close()
                            return False, [f"Device found but not readable - check permissions: sudo usermod -a -G input $USER"]
                        
                        # Check if device is suitable for macropad use
                        caps = dev.capabilities()
                        if 1 not in caps:  # No key capabilities
                            dev.close()
                            return False, [f"Device has no key capabilities"]
                        
                        # Filter out audio/HDMI devices that aren't real input devices
                        name_lower = device_name.lower()
                        if any(keyword in name_lower for keyword in ['hdmi', 'audio', 'sound', 'vc4']):
                            dev.close()
                            return False, [f"Device is audio/video hardware, not input device"]
                        
                        # Check if device supports the required keys (Q, W, E, R, T)
                        required_keys = [ecodes.KEY_Q, ecodes.KEY_W, ecodes.KEY_E, ecodes.KEY_R, ecodes.KEY_T]
                        supported_keys = caps.get(1, [])  # EV_KEY events
                        missing_keys = [key for key in required_keys if key not in supported_keys]
                        
                        if missing_keys:
                            key_names = ['KEY_Q', 'KEY_W', 'KEY_E', 'KEY_R', 'KEY_T']
                            missing_names = [key_names[required_keys.index(key)] for key in missing_keys]
                            dev.close()
                            return False, [f"Device missing required keys: {', '.join(missing_names)}"]
                        
                        dev.close()
                        return True, []
            except Exception as e:
                continue
        return False, []
    
    # Look for similar devices using common patterns - matches DOIO, KB, macropad keywords
    suggestions = []
    patterns = ['DOIO', 'KB', 'macropad', 'pad']
    if '_' in device_name:
        patterns.append(device_name.split('_')[0])  # Add prefix before underscore - handles device variants
    
    for device in available_devices:
        device_lower = device.lower()
        for pattern in patterns:
            if pattern.lower() in device_lower:
                suggestions.append(device)
                break
    
    return False, list(set(suggestions))

"""
======================================
CONFIGURATION LOADING AND VALIDATION
======================================
Loads config.ini and validates all settings using helper functions from previous section.
Exits with helpful error messages if validation fails. Respects --skip-validation flags.
"""

# Sets up logging before validation starts - ensures errors get captured from the beginning
config_logger = setup_config_error_logging()
debug_logger = setup_debug_logging()

# Set up basic operational logging early so validation messages appear
logging.basicConfig(level=logging.INFO, format=LOG_FORMATS['standard'], force=True)


# Loads the config file - exits immediately if not found
config = configparser.ConfigParser(interpolation=None)
config_path = Path(__file__).parent / 'config.ini'

try:
    if not config_path.exists():
        log_config_error(config_logger, 
                        "config.ini file not found in script directory",
                        "Create config.ini file in same directory as sonos-macropad.py. For example, copy from docs/config.ini.example or see docs/SETUP.md")
        print("Configuration error: config.ini file not found - check sonos-macropad.config-errors.log")
        exit(1)
    
    config.read(config_path)
    
    # Make sure all required sections exist - [sonos], [macropad], [volume]
    if not SKIP_CONFIG:
        required_sections = ['sonos', 'macropad', 'volume']
        for section in required_sections:
            if not config.has_section(section):
                log_config_error(config_logger, 
                                f"[{section}] section is missing from config.ini",
                                f"Edit config.ini and add [{section}] section header. For example: [{section}] (see docs/SETUP.md)")
                print(f"Configuration error: Missing section [{section}] - check sonos-macropad.config-errors.log")
                exit(1)
    else:
        pass  # Skipped validation
        logging.warning("CONFIG - Skipping config sections validation")
    
    # Make sure all required options are present - validates each section has its required keys
    if not SKIP_CONFIG:
        required_options = {
            'sonos': ['api_host', 'api_port', 'primary_room', 'secondary_rooms', 'favorite_playlist'],
            'macropad': ['log_file', 'install_dir', 'device_name'],
            'volume': ['primary_single_step', 'primary_max', 'primary_min_grouping', 'secondary_step', 'secondary_max', 'secondary_min_grouping']
        }
        
        for section, options in required_options.items():
            for option in options:
                if not config.has_option(section, option):
                    log_config_error(config_logger, 
                                    f"Required option '{option}' is missing from [{section}] section in config.ini",
                                    f"Edit config.ini and add '{option} = value' to [{section}] section. For example: {option} = example_value (see docs/SETUP.md)")
                    print(f"Configuration error: Missing option {section}.{option} - check sonos-macropad.config-errors.log")
                    exit(1)
    else:
        pass  # Skipped validation
        logging.warning("CONFIG - Skipping config options validation")
    
    # Extract and validate paths early so we can set up operational logging
    INSTALL_DIR = config.get('macropad', 'install_dir').strip()
    LOG_FILE_NAME = config.get('macropad', 'log_file').strip()
    DEVICE_NAME = config.get('macropad', 'device_name').strip()


    
    # Validate log file and install directory paths
    if not LOG_FILE_NAME:
        log_config_error(config_logger, 
                        "log_file in config.ini is empty: log_file = ''",
                        "Edit config.ini and enter a valid filename. For example: log_file = sonos-macropad.log")
        print(f"Configuration error: Invalid 'log_file' '' in config.ini - For more information, see: sonos-macropad.config-errors.log")
        exit(1)
    
    if not SKIP_PATHS:
        # Check for invalid filename characters
        invalid_chars = ['<', '>', ':', '"', '|', '?', '*', '\0']
        if any(char in LOG_FILE_NAME for char in invalid_chars):
            log_config_error(config_logger, 
                            f"log_file in config.ini contains invalid characters: log_file = {LOG_FILE_NAME}",
                            "Edit config.ini and remove invalid characters from log_file name. For example: log_file = sonos-macropad.log")
            print(f"Configuration error: Invalid 'log_file' '{LOG_FILE_NAME}' in config.ini - For more information, see: sonos-macropad.config-errors.log")
            exit(1)
        
        # Handle absolute vs relative paths
        if os.path.isabs(LOG_FILE_NAME):
            # Absolute path - check if parent directory exists
            log_dir = os.path.dirname(LOG_FILE_NAME)
            if not os.path.isdir(log_dir):
                log_config_error(config_logger, 
                                f"log_file in config.ini has directory that does not exist: {log_dir}",
                                f"Edit config.ini to use relative path (log_file = sonos-macropad.log) or create directory: mkdir -p {log_dir}")
                print(f"Configuration error: Invalid 'log_file' '{LOG_FILE_NAME}' in config.ini - For more information, see: sonos-macropad.config-errors.log")
                exit(1)
            if not os.access(log_dir, os.W_OK):
                log_config_error(config_logger, 
                                f"log_file in config.ini has directory that is not writable: {log_dir}",
                                f"Edit config.ini to use different directory or fix permissions: chmod 755 {log_dir}")
                print(f"Configuration error: Invalid 'log_file' '{LOG_FILE_NAME}' in config.ini - For more information, see: sonos-macropad.config-errors.log")
                exit(1)
    else:
        pass  # Skipped validation
        logging.warning("CONFIG - Skipping log file path validation")
    
    # Validate install directory exists and is writable for script generation
    if not INSTALL_DIR:
        log_config_error(config_logger, 
                        "install_dir in config.ini is empty: install_dir = ''",
                        "Edit config.ini and enter a valid directory path. For example: install_dir = /home/pi/sonos-macropad")
        print(f"Configuration error: Invalid 'install_dir' '' in config.ini - For more information, see: sonos-macropad.config-errors.log")
        exit(1)
    
    if not SKIP_PATHS:
        if os.path.isfile(INSTALL_DIR):
            log_config_error(config_logger, 
                            f"install_dir in config.ini points to a file, not a directory: install_dir = {INSTALL_DIR}",
                            f"Edit config.ini and enter a valid directory path. For example: install_dir = /home/pi/sonos-macropad")
            print(f"Configuration error: Invalid 'install_dir' '{INSTALL_DIR}' in config.ini - For more information, see: sonos-macropad.config-errors.log")
            exit(1)
        elif not os.path.isdir(INSTALL_DIR):
            log_config_error(config_logger, 
                            f"install_dir in config.ini does not exist: install_dir = {INSTALL_DIR}",
                            f"Edit config.ini to use existing directory or create it: mkdir -p {INSTALL_DIR}")
            print(f"Configuration error: Invalid 'install_dir' '{INSTALL_DIR}' in config.ini - For more information, see: sonos-macropad.config-errors.log")
            exit(1)
        elif not os.access(INSTALL_DIR, os.W_OK):
            log_config_error(config_logger, 
                            f"install_dir in config.ini is not writable: install_dir = {INSTALL_DIR}",
                            f"Edit config.ini to use different directory or fix permissions: chmod 755 {INSTALL_DIR}")
            print(f"Configuration error: Invalid 'install_dir' '{INSTALL_DIR}' in config.ini - For more information, see: sonos-macropad.config-errors.log")
            exit(1)
    else:
        pass  # Skipped validation
        logging.warning("CONFIG - Skipping install directory validation")
    
    # Set up operational logging now that paths are validated
    LOG_FILE = os.path.join(INSTALL_DIR, LOG_FILE_NAME) if not os.path.isabs(LOG_FILE_NAME) else LOG_FILE_NAME
    op_handler = logging.handlers.RotatingFileHandler(
        LOG_FILE, mode='a', 
        maxBytes=LOG_ROTATION['max_bytes'], 
        backupCount=LOG_ROTATION['backup_count']
    )
    op_formatter = logging.Formatter(LOG_FORMATS['standard'])
    op_handler.setFormatter(op_formatter)
    logging.getLogger().addHandler(op_handler)
    
    # Check API host and port settings - validates format but doesn't test connectivity yet
    API_HOST = config.get('sonos', 'api_host').strip()
    if not SKIP_HOST and not validate_host(API_HOST):
        log_config_error(config_logger, 
                        f"api_host in config.ini has invalid format: api_host = {API_HOST}",
                        f"Must be valid IP address (192.168.1.100) or RFC 1123 hostname (sonos-api.local). Check format - connectivity is not tested during validation.")
        logging.error("CONFIG - Failed config.ini validation - check sonos-macropad.config-errors.log")
        print(f"Configuration error: Invalid 'api_host' '{API_HOST}' in config.ini - For more information, see: sonos-macropad.config-errors.log")
        exit(1)
    
    if SKIP_HOST:
        logging.warning("CONFIG - Skipping API host format validation")
    
    API_PORT = config.get('sonos', 'api_port').strip()
    if not SKIP_PORT and not validate_port(API_PORT):
        log_config_error(config_logger, 
                        f"api_port in config.ini is not a valid port number: api_port = {API_PORT}",
                        f"Must be integer between 1-65535 (port 0 is reserved). For example: api_port = 5005")
        logging.error("CONFIG - Failed config.ini validation - check sonos-macropad.config-errors.log")
        print(f"Configuration error: Invalid 'api_port' '{API_PORT}' in config.ini - For more information, see: sonos-macropad.config-errors.log")
        exit(1)
    
    if SKIP_PORT:
        logging.warning("CONFIG - Skipping API port format validation")
    
    API_BASE = f"http://{API_HOST}:{API_PORT}"
    
    # Test Sonos API connectivity
    if not SKIP_API:
        try:
            start_time = time.time()
            result = subprocess.run(['curl', '-s', '--connect-timeout', str(CURL_CONNECT_TIMEOUT), '--max-time', str(CURL_MAX_TIME), API_BASE], 
                                  capture_output=True, text=True, timeout=5)
            duration = time.time() - start_time
            if result.returncode != 0:
                log_config_error(config_logger, 
                                f"Cannot connect to Sonos HTTP API at {API_BASE}",
                                f"Edit config.ini with correct API settings or verify Sonos HTTP API is running at {API_BASE}")
                print(f"Configuration error: Cannot connect to Sonos API at {API_BASE} - For more information, see: sonos-macropad.config-errors.log")
                exit(1)
        except Exception as e:
            log_config_error(config_logger, 
                            f"Cannot connect to Sonos HTTP API at {API_BASE}: {e}",
                            f"Edit config.ini with correct API settings or verify Sonos HTTP API is running at {API_BASE}")
            print(f"Configuration error: Cannot connect to Sonos API at {API_BASE} - For more information, see: sonos-macropad.config-errors.log")
            exit(1)
    else:
        logging.debug("CONFIG - Skipping API connectivity validation (use --validate api to enable)")
    
    # Check primary room setting - validates room exists in Sonos system
    PRIMARY_ROOM = config.get('sonos', 'primary_room').strip()
    if not PRIMARY_ROOM:
        log_config_error(config_logger, 
                        f"primary_room in config.ini is empty: primary_room = '{PRIMARY_ROOM}'",
                        "Edit config.ini and enter a room name from your Sonos app. For example: primary_room = Living Room")
        print(f"Configuration error: Invalid 'primary_room' '{PRIMARY_ROOM}' in config.ini - For more information, see: sonos-macropad.config-errors.log")
        exit(1)
    
    if not SKIP_ROOMS_EXTERNAL:
        available_rooms = get_available_rooms(API_BASE)
        if available_rooms:
            if PRIMARY_ROOM not in available_rooms:
                room_list = ", ".join(available_rooms)
                log_config_error(config_logger, 
                                f"primary_room in config.ini not found in Sonos system: primary_room = {PRIMARY_ROOM}",
                                f"Edit config.ini and enter a valid room name. Available rooms: {room_list}")
                logging.error("CONFIG - Failed config.ini validation - check sonos-macropad.config-errors.log")
                print(f"Configuration error: Invalid 'primary_room' '{PRIMARY_ROOM}' in config.ini - For more information, see: sonos-macropad.config-errors.log")
                exit(1)
        else:
            log_config_error(config_logger, 
                            f"Cannot get room list from Sonos API at {API_BASE}",
                            "Edit config.ini with correct API settings or check Sonos HTTP API functionality")
            print(f"Configuration error: Cannot get room list from Sonos API - For more information, see: sonos-macropad.config-errors.log")
            exit(1)
    else:
        pass  # Skipped validation
    
    PRIMARY_ROOM_ENCODED = urllib.parse.quote(PRIMARY_ROOM)
    
    # Check secondary rooms setting - validates each room exists in Sonos system
    secondary_rooms_raw = config.get('sonos', 'secondary_rooms').strip()
    if not secondary_rooms_raw:
        log_config_error(config_logger, 
                        f"secondary_rooms in config.ini is empty: secondary_rooms = {secondary_rooms_raw}",
                        "Edit config.ini and enter comma-separated room names. For example: secondary_rooms = Kitchen,Bedroom")
        print(f"Configuration error: Invalid 'secondary_rooms' '{secondary_rooms_raw}' in config.ini - For more information, see: sonos-macropad.config-errors.log")
        exit(1)
    
    SECONDARY_ROOMS = [room.strip() for room in secondary_rooms_raw.split(',') if room.strip()]
    if not SECONDARY_ROOMS:
        log_config_error(config_logger, 
                        f"secondary_rooms in config.ini contains no valid room names: secondary_rooms = {secondary_rooms_raw}",
                        "Edit config.ini and enter valid room names. For example: secondary_rooms = Kitchen,Bedroom")
        print(f"Configuration error: Invalid 'secondary_rooms' '{secondary_rooms_raw}' in config.ini - For more information, see: sonos-macropad.config-errors.log")
        exit(1)
    
    # Validates each room exists in Sonos system (only if external validation enabled)
    if not SKIP_ROOMS_EXTERNAL:
        available_rooms = get_available_rooms(API_BASE)
        if available_rooms:
            invalid_rooms = [room for room in SECONDARY_ROOMS if room not in available_rooms]
            if invalid_rooms:
                room_list = ", ".join(available_rooms)
                invalid_list = ", ".join(invalid_rooms)
                log_config_error(config_logger, 
                                f"secondary_rooms in config.ini contains invalid room names: {invalid_list}",
                                f"Edit config.ini and use valid room names. Available rooms: {room_list}")
                logging.error("CONFIG - Failed config.ini validation - check sonos-macropad.config-errors.log")
                print(f"Configuration error: Invalid 'secondary_rooms' '{secondary_rooms_raw}' in config.ini - For more information, see: sonos-macropad.config-errors.log")
                exit(1)
        else:
            log_config_error(config_logger, 
                            f"Cannot validate secondary_rooms - Sonos HTTP API connection failed at {API_BASE}",
                            f"Edit config.ini with correct API settings or verify Sonos HTTP API is running at {API_BASE}")
            print(f"Configuration error: Cannot connect to Sonos API at {API_BASE} - For more information, see: sonos-macropad.config-errors.log")
            exit(1)
    else:
        pass  # Skipped validation
    
    # Make sure primary room isn't listed in secondary rooms - prevents logical conflicts
    if not SKIP_ROOMS_LOGIC and PRIMARY_ROOM in SECONDARY_ROOMS:
        log_config_error(config_logger, 
                        f"primary_room in config.ini cannot be in secondary_rooms list: primary_room = {PRIMARY_ROOM}",
                        f"Edit config.ini and remove '{PRIMARY_ROOM}' from secondary_rooms. Secondary rooms should be different from primary room.")
        print(f"Configuration error: Invalid 'secondary_rooms' '{secondary_rooms_raw}' in config.ini - For more information, see: sonos-macropad.config-errors.log")
        exit(1)
    
    # Check for duplicate rooms in secondary list - prevents script errors during grouping
    if not SKIP_ROOMS_LOGIC:
        if len(SECONDARY_ROOMS) != len(set(SECONDARY_ROOMS)):
            duplicates = [room for room in set(SECONDARY_ROOMS) if SECONDARY_ROOMS.count(room) > 1]
            log_config_error(config_logger, 
                            f"secondary_rooms in config.ini contains duplicate room names: {', '.join(duplicates)}",
                            f"Edit config.ini and remove duplicate room names from secondary_rooms.")
            print(f"Configuration error: Invalid 'secondary_rooms' '{secondary_rooms_raw}' in config.ini - For more information, see: sonos-macropad.config-errors.log")
            exit(1)
    else:
        pass  # Skipped validation
        logging.warning("CONFIG - Skipping room logic validation")
    
    SECONDARY_ROOMS_ENCODED = [urllib.parse.quote(room) for room in SECONDARY_ROOMS]
    
    FAVORITE_PLAYLIST = config.get('sonos', 'favorite_playlist').strip()
    if not FAVORITE_PLAYLIST:
        log_config_error(config_logger, 
                        "favorite_playlist in config.ini is empty: favorite_playlist = ''",
                        "Edit config.ini and enter a playlist name. For example: favorite_playlist = My Playlist")
        print(f"Configuration error: Invalid 'favorite_playlist' '' in config.ini - For more information, see: sonos-macropad.config-errors.log")
        exit(1)
    
    # Validate playlist exists in Sonos system
    if not SKIP_PLAYLIST:
        available_playlists = get_available_playlists(API_BASE)
        if available_playlists:
            if FAVORITE_PLAYLIST not in available_playlists:
                playlist_list = ", ".join(available_playlists)
                log_config_error(config_logger, 
                                f"favorite_playlist in config.ini not found in Sonos system: favorite_playlist = {FAVORITE_PLAYLIST}",
                                f"Edit config.ini and enter a valid playlist name. Available playlists: {playlist_list}")
                logging.error("CONFIG - Failed config.ini validation - check sonos-macropad.config-errors.log")
                print(f"Configuration error: Invalid 'favorite_playlist' '{FAVORITE_PLAYLIST}' in config.ini - For more information, see: sonos-macropad.config-errors.log")
                exit(1)
        else:
            log_config_error(config_logger, 
                            f"Cannot get playlist list from Sonos API at {API_BASE}",
                            "Edit config.ini with correct API settings or check Sonos HTTP API functionality")
            print(f"Configuration error: Cannot get playlist list from Sonos API - For more information, see: sonos-macropad.config-errors.log")
            exit(1)
    else:
        pass  # Skipped validation
    
    # Check device name format and validate it exists
    device_name = config.get('macropad', 'device_name', fallback=None)
    if not device_name:
        log_config_error(config_logger, 
                        "device_name not specified in config.ini",
                        "Add 'device_name' to the [macropad] section of config.ini. For example: device_name = DOIO_KB03B")
        print("Configuration error: device_name not specified in config.ini - check sonos-macropad.config-errors.log")
        exit(1)
    
    # Validate device name contains only safe characters
    if not re.match(r'^[a-zA-Z0-9_.-]+$', device_name):
        log_config_error(config_logger, 
                        f"device_name in config.ini contains invalid characters: device_name = {device_name}",
                        "Must match pattern ^[a-zA-Z0-9_.-]+$ (letters, numbers, underscores, dots, hyphens only). For example: device_name = DOIO_KB03B")
        print(f"Configuration error: Invalid 'device_name' '{device_name}' in config.ini - For more information, see: sonos-macropad.config-errors.log")
        exit(1)
    
    # Validate device exists and is accessible
    if not SKIP_DEVICE:
        device_exists, suggestions = test_device_exists(device_name)
        if not device_exists:
            log_config_error(config_logger, 
                            f"device_name in config.ini not found: device_name = {device_name}",
                            f"Edit config.ini with correct device name or check device connection. Suggestions: {', '.join(suggestions) if suggestions else 'None'}")
            print(f"Configuration error: Invalid 'device_name' '{device_name}' in config.ini - For more information, see: sonos-macropad.config-errors.log")
            exit(1)
    else:
        pass  # Skipped validation

    # Extract configuration values from validated config file
    INSTALL_DIR = config.get('macropad', 'install_dir').strip()
    LOG_FILE_NAME = config.get('macropad', 'log_file').strip()
    DEVICE_NAME = config.get('macropad', 'device_name').strip()


    
    # Validate log file and install directory paths
    if not LOG_FILE_NAME:
        log_config_error(config_logger, 
                        "log_file in config.ini is empty: log_file = ''",
                        "Edit config.ini and enter a valid filename. For example: log_file = sonos-macropad.log")
        print(f"Configuration error: Invalid 'log_file' '' in config.ini - For more information, see: sonos-macropad.config-errors.log")
        exit(1)
    
    if not SKIP_PATHS:
        # Check for invalid filename characters
        invalid_chars = ['<', '>', ':', '"', '|', '?', '*', '\0']
        if any(char in LOG_FILE_NAME for char in invalid_chars):
            log_config_error(config_logger, 
                            f"log_file in config.ini contains invalid characters: log_file = {LOG_FILE_NAME}",
                            "Edit config.ini and remove invalid characters from log_file name. For example: log_file = sonos-macropad.log")
            print(f"Configuration error: Invalid 'log_file' '{LOG_FILE_NAME}' in config.ini - For more information, see: sonos-macropad.config-errors.log")
            exit(1)
        
        # Handle absolute vs relative paths
        if os.path.isabs(LOG_FILE_NAME):
            # Absolute path - check if parent directory exists
            log_dir = os.path.dirname(LOG_FILE_NAME)
            if not os.path.isdir(log_dir):
                log_config_error(config_logger, 
                                f"log_file in config.ini has directory that does not exist: {log_dir}",
                                f"Edit config.ini to use relative path (log_file = sonos-macropad.log) or create directory: mkdir -p {log_dir}")
                print(f"Configuration error: Invalid 'log_file' '{LOG_FILE_NAME}' in config.ini - For more information, see: sonos-macropad.config-errors.log")
                exit(1)
            if not os.access(log_dir, os.W_OK):
                log_config_error(config_logger, 
                                f"log_file in config.ini has directory that is not writable: {log_dir}",
                                f"Edit config.ini to use different directory or fix permissions: chmod 755 {log_dir}")
                print(f"Configuration error: Invalid 'log_file' '{LOG_FILE_NAME}' in config.ini - For more information, see: sonos-macropad.config-errors.log")
                exit(1)
    else:
        pass  # Skipped validation
        logging.warning("CONFIG - Skipping log file path validation")
    
    # Validate install directory exists and is writable for script generation
    if not INSTALL_DIR:
        log_config_error(config_logger, 
                        "install_dir in config.ini is empty: install_dir = ''",
                        "Edit config.ini and enter a valid directory path. For example: install_dir = /home/pi/sonos-macropad")
        print(f"Configuration error: Invalid 'install_dir' '' in config.ini - For more information, see: sonos-macropad.config-errors.log")
        exit(1)
    
    if not SKIP_PATHS:
        if os.path.isfile(INSTALL_DIR):
            log_config_error(config_logger, 
                            f"install_dir in config.ini points to a file, not a directory: install_dir = {INSTALL_DIR}",
                            f"Edit config.ini and enter a valid directory path. For example: install_dir = /home/pi/sonos-macropad")
            print(f"Configuration error: Invalid 'install_dir' '{INSTALL_DIR}' in config.ini - For more information, see: sonos-macropad.config-errors.log")
            exit(1)
        elif not os.path.isdir(INSTALL_DIR):
            log_config_error(config_logger, 
                            f"install_dir in config.ini does not exist: install_dir = {INSTALL_DIR}",
                            f"Edit config.ini to use existing directory or create it: mkdir -p {INSTALL_DIR}")
            print(f"Configuration error: Invalid 'install_dir' '{INSTALL_DIR}' in config.ini - For more information, see: sonos-macropad.config-errors.log")
            exit(1)
        elif not os.access(INSTALL_DIR, os.W_OK):
            log_config_error(config_logger, 
                            f"install_dir in config.ini is not writable: install_dir = {INSTALL_DIR}",
                            f"Edit config.ini to use different directory or fix permissions: chmod 755 {INSTALL_DIR}")
            print(f"Configuration error: Invalid 'install_dir' '{INSTALL_DIR}' in config.ini - For more information, see: sonos-macropad.config-errors.log")
            exit(1)
    else:
        pass  # Skipped validation
        logging.warning("CONFIG - Skipping install directory validation")
    
    # Set up operational logging now that paths are validated
    # Extract and validate volume configuration values
    try:
        PRIMARY_STEP = config.getint('volume', 'primary_single_step')
        PRIMARY_MAX = config.getint('volume', 'primary_max')
        PRIMARY_MIN_GROUPING = config.getint('volume', 'primary_min_grouping')
        SECONDARY_STEP = config.getint('volume', 'secondary_step')
        SECONDARY_MAX = config.getint('volume', 'secondary_max')
        SECONDARY_MIN_GROUPING = config.getint('volume', 'secondary_min_grouping')
        
        # Create temporary volume accumulator for config validation
        class TempVolumeAccumulator:
            def set_config(self, *args): pass
        volume_accumulator = TempVolumeAccumulator()
        volume_accumulator.set_config(API_BASE, PRIMARY_ROOM, PRIMARY_MAX, PRIMARY_STEP, SECONDARY_ROOMS)
    except (ValueError, configparser.NoOptionError) as e:
        log_config_error(config_logger, 
                        f"volume setting in config.ini has invalid value: {e}",
                        "Edit config.ini and enter a valid integer. For example: primary_single_step = 3")
        print(f"Configuration error: Invalid volume setting in config.ini - For more information, see: sonos-macropad.config-errors.log")
        exit(1)
    
    # Check volume ranges are sensible - prevents unusable or dangerous volume levels
    if not SKIP_VOLUME:
        if not (1 <= PRIMARY_STEP <= 10):
            log_config_error(config_logger, 
                            f"primary_single_step in config.ini not in valid range: primary_single_step = {PRIMARY_STEP}",
                            f"Must be integer 1-10 (reasonable volume increment for Sonos 0-100 range). For example: primary_single_step = 3")
            print(f"Configuration error: Invalid 'primary_single_step' '{PRIMARY_STEP}' in config.ini - For more information, see: sonos-macropad.config-errors.log")
            exit(1)
        
        if not (1 <= PRIMARY_MAX <= 100):
            log_config_error(config_logger, 
                            f"primary_max in config.ini not in valid range: primary_max = {PRIMARY_MAX}",
                            f"Must be integer 1-100 (Sonos volume range). For example: primary_max = 50")
            print(f"Configuration error: Invalid 'primary_max' '{PRIMARY_MAX}' in config.ini - For more information, see: sonos-macropad.config-errors.log")
            exit(1)
        
        if not (1 <= PRIMARY_MIN_GROUPING <= 50):
            log_config_error(config_logger, 
                            f"primary_min_grouping in config.ini not in valid range: primary_min_grouping = {PRIMARY_MIN_GROUPING}",
                            f"Must be integer 1-50 (reasonable minimum for multi-room audio). For example: primary_min_grouping = 10")
            print(f"Configuration error: Invalid 'primary_min_grouping' '{PRIMARY_MIN_GROUPING}' in config.ini - For more information, see: sonos-macropad.config-errors.log")
            exit(1)
        
        if not (1 <= SECONDARY_STEP <= 5):
            log_config_error(config_logger, 
                            f"secondary_step in config.ini not in valid range: secondary_step = {SECONDARY_STEP}",
                            f"Must be integer 1-5 (smaller increments for secondary rooms). For example: secondary_step = 2")
            print(f"Configuration error: Invalid 'secondary_step' '{SECONDARY_STEP}' in config.ini - For more information, see: sonos-macropad.config-errors.log")
            exit(1)
        
        if not (1 <= SECONDARY_MAX <= 100):
            log_config_error(config_logger, 
                            f"secondary_max in config.ini not in valid range: secondary_max = {SECONDARY_MAX}",
                            f"Must be integer 1-100 (Sonos volume range, typically lower than primary). For example: secondary_max = 40")
            print(f"Configuration error: Invalid 'secondary_max' '{SECONDARY_MAX}' in config.ini - For more information, see: sonos-macropad.config-errors.log")
            exit(1)
        
        if not (1 <= SECONDARY_MIN_GROUPING <= 20):
            log_config_error(config_logger, 
                            f"secondary_min_grouping in config.ini not in valid range: secondary_min_grouping = {SECONDARY_MIN_GROUPING}",
                            f"Must be integer 1-20 (reasonable minimum for secondary rooms). For example: secondary_min_grouping = 8")
            print(f"Configuration error: Invalid 'secondary_min_grouping' '{SECONDARY_MIN_GROUPING}' in config.ini - For more information, see: sonos-macropad.config-errors.log")
            exit(1)
        
        # Make sure step size doesn't exceed max volume - prevents volume from going over limit
        if PRIMARY_STEP >= PRIMARY_MAX:
            log_config_error(config_logger, 
                            f"primary_single_step in config.ini must be less than primary_max: primary_single_step = {PRIMARY_STEP}, primary_max = {PRIMARY_MAX}",
                            "primary_single_step must be less than primary_max to allow volume increases. Reduce step size or increase max volume.")
            print(f"Configuration error: Invalid 'primary_single_step' '{PRIMARY_STEP}' in config.ini - For more information, see: sonos-macropad.config-errors.log")
            exit(1)
        
        if PRIMARY_MIN_GROUPING >= PRIMARY_MAX:
            log_config_error(config_logger, 
                            f"primary_min_grouping in config.ini must be less than primary_max: primary_min_grouping = {PRIMARY_MIN_GROUPING}, primary_max = {PRIMARY_MAX}",
                            "primary_min_grouping must be less than primary_max for valid grouping behavior. Reduce min grouping or increase max volume.")
            print(f"Configuration error: Invalid 'primary_min_grouping' '{PRIMARY_MIN_GROUPING}' in config.ini - For more information, see: sonos-macropad.config-errors.log")
            exit(1)
        
        if SECONDARY_STEP >= SECONDARY_MAX:
            log_config_error(config_logger, 
                            f"secondary_step in config.ini must be less than secondary_max: secondary_step = {SECONDARY_STEP}, secondary_max = {SECONDARY_MAX}",
                            "secondary_step must be less than secondary_max to allow volume increases. Reduce step size or increase max volume.")
            print(f"Configuration error: Invalid 'secondary_step' '{SECONDARY_STEP}' in config.ini - For more information, see: sonos-macropad.config-errors.log")
            exit(1)
        
        if SECONDARY_MIN_GROUPING >= SECONDARY_MAX:
            log_config_error(config_logger, 
                            f"secondary_min_grouping in config.ini must be less than secondary_max: secondary_min_grouping = {SECONDARY_MIN_GROUPING}, secondary_max = {SECONDARY_MAX}",
                            "secondary_min_grouping must be less than secondary_max for valid grouping behavior. Reduce min grouping or increase max volume.")
            print(f"Configuration error: Invalid 'secondary_min_grouping' '{SECONDARY_MIN_GROUPING}' in config.ini - For more information, see: sonos-macropad.config-errors.log")
            exit(1)
        
        if SECONDARY_MAX > PRIMARY_MAX:
            log_config_error(config_logger, 
                            f"secondary_max in config.ini cannot exceed primary_max: secondary_max = {SECONDARY_MAX}, primary_max = {PRIMARY_MAX}",
                            "secondary_max cannot exceed primary_max (secondary rooms should not be louder than primary). Reduce secondary_max or increase primary_max.")
            print(f"Configuration error: Invalid 'secondary_max' '{SECONDARY_MAX}' in config.ini - For more information, see: sonos-macropad.config-errors.log")
            exit(1)
        

    # Validate that all required configuration values are present
    if not all([INSTALL_DIR, LOG_FILE_NAME, DEVICE_NAME, PRIMARY_STEP, PRIMARY_MAX, PRIMARY_MIN_GROUPING, SECONDARY_STEP, SECONDARY_MAX, SECONDARY_MIN_GROUPING]):
        log_config_error(config_logger, 
                        "Missing required configuration values",
                        "Edit config.ini and ensure all required configuration values are present")
        print("Configuration error: Missing required configuration values - check sonos-macropad.config-errors.log")
        exit(1)

    # Generate action scripts after configuration validation
    if not SKIP_SCRIPTS_GEN:
        config_values = {
            'api_base': API_BASE,
            'primary_room': PRIMARY_ROOM,
            'primary_room_encoded': PRIMARY_ROOM_ENCODED,
            'primary_step': PRIMARY_STEP,
            'primary_max': PRIMARY_MAX,
            'primary_min_grouping': PRIMARY_MIN_GROUPING,
            'secondary_step': SECONDARY_STEP,
            'secondary_max': SECONDARY_MAX,
            'secondary_min_grouping': SECONDARY_MIN_GROUPING,
            'secondary_rooms': ' '.join([f'"{room}"' for room in SECONDARY_ROOMS]),
            'secondary_rooms_encoded': ' '.join([f'"{room}"' for room in SECONDARY_ROOMS_ENCODED]),
            'favorite_playlist': urllib.parse.quote(FAVORITE_PLAYLIST),
            'install_dir': INSTALL_DIR,
            'curl_connect_timeout': CURL_CONNECT_TIMEOUT,
            'curl_max_time': CURL_MAX_TIME,
            'bash_log_format': ''  # Removed - no longer used in templates
        }
        
        if not SKIP_SCRIPTS_CHECK and scripts_need_update(config_path, INSTALL_DIR):
            SCRIPTS_GENERATED = True
            try:
                generate_embedded_scripts(config_values, INSTALL_DIR)
            except Exception as e:
                log_config_error(config_logger, 
                                f"Action script generation failed: {e}",
                                f"Edit config.ini with different directory or check permissions and disk space: {INSTALL_DIR}")
                print(f"Configuration error: Script generation failed - check sonos-macropad.config-errors.log")
                exit(1)
        else:
            SCRIPTS_GENERATED = False
    else:
        pass  # Skipped validation
        SCRIPTS_GENERATED = False
        logging.warning("CONFIG - Skipping script generation")

except Exception as e:
    log_config_error(config_logger, 
                    f"config.ini validation failed: {e}",
                    "Edit config.ini settings and fix any validation errors")
    print(f"config.ini validation failed: {e}")
    exit(1)

"""
======================================
SONOS-MACROPAD KEY MAPPINGS
======================================
Maps five macropad keys to action scripts and log-friendly names.
Used by sonos-macropad event loop for script execution and logging.
"""

SCRIPTS = {
    'KEY_Q': os.path.join(INSTALL_DIR, "playpause"),
    'KEY_W': os.path.join(INSTALL_DIR, "next"),
    'KEY_T': os.path.join(INSTALL_DIR, "volumeup"),
    'KEY_R': os.path.join(INSTALL_DIR, "volumedown"),
    'KEY_E': os.path.join(INSTALL_DIR, "favorite_playlist")
}

ACTION_NAMES = {
    'KEY_Q': 'play/pause',
    'KEY_W': 'next track',
    'KEY_T': 'volume up',
    'KEY_R': 'volume down',
    'KEY_E': 'favorite playlist'
}

"""
======================================
DEVICE DISCOVERY
======================================
Finds and connects macropad by scanning /dev/input/event0-4 for device name.
Returns InputDevice object for event monitoring, None if not found.
"""

def find_doio_device(device_name):
    # Scans /dev/input/event0-4 for device matching exact name - supports any input device type
    # Returns InputDevice object if found, None otherwise
    for event_num in DEVICE_EVENT_NUMBERS:
        device_path = DEVICE_PATH_PATTERN.format(event_num)
        dev = None
        try:
            if os.path.exists(device_path):
                dev = InputDevice(device_path)
                if hasattr(dev, 'name') and dev.name == device_name:
                    return dev  # Return without closing - caller will manage
        except Exception as e:
            pass  # Continue to next device path
        finally:
            # Close device if opened but not the target device
            if dev and (not hasattr(dev, 'name') or dev.name != device_name):
                try:
                    dev.close()
                except (OSError, AttributeError) as e:
                    pass  # Device already closed or invalid
    return None

def find_device_with_retry(device_name, max_retries=None, cycle_number=1):
    # Find device with retry logic for Bluetooth devices
    if max_retries is None:
        max_retries = DEVICE_RETRY_MAX
    retry_count = 0
    while retry_count < max_retries:
        dev = find_doio_device(device_name)
        if dev:
            return dev
        retry_count += 1
        if not shutdown_event.is_set():
            shutdown_event.wait(DEVICE_RETRY_INTERVAL)
    return None

def get_device_mac_address(device_name):
    # Gets MAC address for Bluetooth device by parsing bluetoothctl output
    def is_valid_mac(mac):
        return re.match(r'^([0-9A-Fa-f]{2}[:-]){5}([0-9A-Fa-f]{2})$', mac) is not None
    
    try:
        result = subprocess.run(['bluetoothctl', 'devices'], 
                              capture_output=True, timeout=5, text=True)
        if result.returncode == 0:
            for line in result.stdout.split('\n'):
                if device_name in line:
                    # Format: "Device XX:XX:XX:XX:XX:XX DeviceName"
                    parts = line.split()
                    if len(parts) >= 2:
                        mac_address = parts[1]
                        if is_valid_mac(mac_address):
                            return mac_address
                        else:
                            pass  # Invalid MAC format
        else:
            pass  # Device not found in line
        return None
    except Exception as e:
        return None

def attempt_bluetooth_reconnect(device_name, mac_address):
    # Attempts Bluetooth reconnection using trust-first method for better reliability
    # Validate MAC address format first
    if not re.match(r'^([0-9A-Fa-f]{2}[:-]){5}([0-9A-Fa-f]{2})$', mac_address):
        return False
    
    
    try:
        # Try simple connect first
        result = subprocess.run(['bluetoothctl', 'connect', mac_address], 
                              capture_output=True, timeout=10, text=True)
        if result.returncode == 0:
            return True
        
        # If simple connect fails, try trust-first method
        
        # Trust the device first
        trust_result = subprocess.run(['bluetoothctl', 'trust', mac_address], 
                                    capture_output=True, timeout=5, text=True)
        
        # Attempt connection after trusting
        connect_result = subprocess.run(['bluetoothctl', 'connect', mac_address], 
                                      capture_output=True, timeout=10, text=True)
        
        if connect_result.returncode == 0:
            return True
        
        return False
        
    except subprocess.TimeoutExpired:
        return False
    except Exception as e:
        return False

"""
======================================
GRACEFUL SHUTDOWN HANDLING
======================================
Cleans up pending actions and threads when service receives SIGINT or SIGTERM.
Prevents action scripts from executing during shutdown process.
"""

# Thread-safe action management
volume_queue = queue.Queue(maxsize=5)
key_queue = queue.Queue(maxsize=3)
shutdown_event = threading.Event()
shutdown_in_progress = False
# Cancellation flags for multi-press detection (thread-safe)
cancelled_actions = set()
cancelled_actions_lock = threading.Lock()

def signal_handler(signum, frame):
    global shutdown_in_progress
    if shutdown_in_progress:
        return
    
    shutdown_in_progress = True
    logging.info(f"SONOS-MACROPAD - Shutdown signal received (signal {signum})")
    
    shutdown_event.set()
    
    # Send shutdown signals to workers and cancel volume accumulator
    try:
        key_queue.put(None, timeout=QUEUE_TIMEOUT)
        # Cancel any pending volume accumulator timer
        if volume_accumulator.execution_timer:
            volume_accumulator.execution_timer.cancel()
    except queue.Full:
        pass
    
    sys.exit(0)

signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)

"""
======================================
QUEUE-BASED ACTION PROCESSING
======================================
Thread-safe action execution using producer/consumer queues.
Volume and key actions processed by dedicated worker threads with proper cancellation.

VOLUME BURST OPTIMIZATION:
VolumeAccumulator class accumulates rapid volume turns (within 100ms) and sends single API command
to reduce latency from 2N API calls to 2 calls per burst.
"""

class VolumeAccumulator:
    # Accumulates rapid volume changes to reduce API calls and improve responsiveness
    def __init__(self):
        self.pending_up = 0
        self.pending_down = 0
        self.turn_count = 0
        self.last_turn_time = 0
        self.burst_timeout = VOLUME_BURST_WINDOW  # Use configurable window
        self.execution_timer = None
        self.lock = threading.Lock()
        # Config variables set when main() runs
        self.api_base = None
        self.primary_room = None
        self.primary_max = None
        self.primary_step = None
        self.secondary_rooms = None
    
    def set_config(self, api_base, primary_room, primary_max, primary_step, secondary_rooms):
        # Set configuration variables from main function
        self.api_base = api_base
        self.primary_room = primary_room
        self.primary_max = primary_max
        self.primary_step = primary_step
        self.secondary_rooms = secondary_rooms
    
    def add_turn(self, keycode):
        # Add a volume turn to the accumulator and schedule execution
        with self.lock:
            current_time = time.time()
            
            # Reset if this is a new burst (after timeout)
            if current_time - self.last_turn_time > self.burst_timeout:
                self.pending_up = 0
                self.pending_down = 0
                self.turn_count = 0
            
            # Accumulate the turn
            if keycode == 'KEY_T':  # Volume up
                self.pending_up += PRIMARY_STEP
                self.turn_count += 1
            elif keycode == 'KEY_R':  # Volume down
                self.pending_down += PRIMARY_STEP
                self.turn_count += 1
            
            self.last_turn_time = current_time
            
            # Cancel previous timer and schedule new execution
            if self.execution_timer:
                self.execution_timer.cancel()
            
            self.execution_timer = threading.Timer(self.burst_timeout, self._execute_accumulated)
            self.execution_timer.start()
    
    def _execute_accumulated(self):
        # Execute the accumulated volume changes by sending to volume queue
        with self.lock:
            if self.pending_up > 0:
                # Log summary only if multiple turns
                if self.turn_count > 1:
                    # Log volume up burst with actual keycode (always KEY_T for up direction)
                    logging.info(f"KNOB TURN - {self.turn_count} knob turns detected (KEY_T)")
                try:
                    volume_queue.put(('KEY_T', self.pending_up), block=False)
                except queue.Full:
                    pass  # Queue full, drop volume change
                self.pending_up = 0
                self.turn_count = 0
            elif self.pending_down > 0:
                # Log summary only if multiple turns
                if self.turn_count > 1:
                    # Log volume down burst with actual keycode (always KEY_R for down direction)
                    logging.info(f"KNOB TURN - {self.turn_count} knob turns detected (KEY_R)")
                try:
                    volume_queue.put(('KEY_R', self.pending_down), block=False)
                except queue.Full:
                    pass  # Queue full, drop volume change
                self.pending_down = 0
                self.turn_count = 0
    
# Global volume accumulator instance
volume_accumulator = VolumeAccumulator()

def volume_worker():
    # Processes volume actions from queue with timeout handling
    while not shutdown_event.is_set():
        try:
            item = volume_queue.get(timeout=QUEUE_TIMEOUT)
            if item is None:
                break
            
            # Handle both single keycode and accumulated (keycode, amount) tuple
            if isinstance(item, tuple):
                keycode, total_change = item
            else:
                keycode = item
                total_change = PRIMARY_STEP
            
            action_name = ACTION_NAMES[keycode]
            start_time = time.time()
            try:
                if keycode == 'KEY_T':
                    # Sanitize script path and change arguments to separated components to prevent command injection
                    script_path = os.path.join(INSTALL_DIR, 'groups-and-volume')
                    result = subprocess.run([script_path, 'up', str(total_change)], shell=False, timeout=SCRIPT_TIMEOUT, capture_output=True, text=True)
                elif keycode == 'KEY_R':
                    # Sanitize script path and change arguments to separated components to prevent command injection
                    script_path = os.path.join(INSTALL_DIR, 'groups-and-volume')
                    result = subprocess.run([script_path, 'down', str(total_change)], shell=False, timeout=SCRIPT_TIMEOUT, capture_output=True, text=True)
                else:
                    # Already safe since SCRIPTS are pre-defined and sanitized paths
                    script_path = SCRIPTS[keycode]
                    if not os.path.isabs(script_path):
                        script_path = os.path.abspath(script_path)
                    # Validate that path is within expected directory (secure against path traversal)
                    real_script = os.path.realpath(script_path)
                    real_install = os.path.realpath(INSTALL_DIR)
                    if not real_script.startswith(real_install + os.sep):
                        raise ValueError(f"Script path {script_path} is outside of allowed directory")
                    result = subprocess.run([script_path], shell=False, timeout=SCRIPT_TIMEOUT, capture_output=True, text=True)
                exit_code = result.returncode
                
                # Script output logged automatically by tracer
            except subprocess.TimeoutExpired:
                exit_code = 124
            duration = time.time() - start_time
            
            if exit_code != 0:
                # Parse HTTP error codes from script stderr output
                http_error = None
                if result.stderr:
                    import re
                    # Look for HTTP error codes in stderr: "description (HTTP 404)"
                    http_match = re.search(r'\(HTTP (\d+)\)', result.stderr)
                    if http_match:
                        http_error = http_match.group(1)
                
                if http_error:
                    logging.warning(f"KNOB ACTION FAILED - {action_name} (HTTP {http_error}, {duration:.2f}s)")
                elif exit_code == 124:
                    logging.warning(f"KNOB ACTION FAILED - {action_name} (timeout: {SCRIPT_TIMEOUT}s, {duration:.2f}s)")
                else:
                    logging.warning(f"KNOB ACTION FAILED - {action_name} (exit: {exit_code}, {duration:.2f}s)")
            else:
                # Parse actual volume changes from script output
                if keycode in ['KEY_T', 'KEY_R']:
                    actual_changes = []
                    if result.stdout:
                        pass
                        import re
                        # Extract volume changes from script output - be more flexible
                        for line in result.stdout.strip().split('\n'):
                            if 'KNOB ACTION COMPLETE' in line:
                                # Match any volume change pattern
                                volume_match = re.search(r'Volume (up|down) on ([^(]+) \(([+-]\d+)\)', line)
                                if volume_match:
                                    direction, room, amount = volume_match.groups()
                                    actual_changes.append(f"{room.strip()} {amount}")
                                    continue
                                
                                # Match set to maximum pattern
                                max_match = re.search(r'Volume up on ([^(]+) \(set to maximum (\d+)\)', line)
                                if max_match:
                                    room, max_vol = max_match.groups()
                                    actual_changes.append(f"{room.strip()} (at max {max_vol})")
                                    continue
                                
                                # Match silence pattern
                                silence_match = re.search(r'Silence ([^(]+) \(', line)
                                if silence_match:
                                    room = silence_match.group(1).strip()
                                    actual_changes.append(f"{room} (silenced)")
                                    continue
                            
                            elif 'KNOB ACTION SKIPPED' in line:
                                # Match already at maximum pattern
                                at_max_match = re.search(r'Volume up skipped on ([^(]+) \(already at maximum (\d+)\)', line)
                                if at_max_match:
                                    room, max_vol = at_max_match.groups()
                                    actual_changes.append(f"{room.strip()} (at max {max_vol})")
                                    continue
                                
                                # Match already at 0 pattern (silenced)
                                at_zero_match = re.search(r'Volume down skipped on ([^(]+) \(already at 0\)', line)
                                if at_zero_match:
                                    room = at_zero_match.group(1).strip()
                                    actual_changes.append(f"{room} (silenced)")
                                    continue
                    
                    if actual_changes:
                        action_type = "Increase" if keycode == 'KEY_T' else "Decrease"
                        changes_str = ", ".join(actual_changes)
                        logging.info(f"KNOB ACTION COMPLETE - {action_type} volume: {changes_str} ({duration:.2f}s)")
                    else:
                        # Fallback when volume parsing fails
                        action_name = ACTION_NAMES[keycode]
                        logging.info(f"KNOB ACTION COMPLETE - {action_name} ({duration:.2f}s)")
                else:
                    action_name = ACTION_NAMES[keycode]
                    logging.info(f"KNOB ACTION COMPLETE - {action_name} ({duration:.2f}s)")
            volume_queue.task_done()
        except queue.Empty:
            continue

def key_worker():
    # Processes key actions from queue with multi-press detection delay
    while not shutdown_event.is_set():
        try:
            keycode = key_queue.get(timeout=QUEUE_TIMEOUT)
            if keycode is None:
                break
            
            
            # Delay Q/W actions for multi-press detection
            if keycode in ['KEY_Q', 'KEY_W']:
                time.sleep(MULTI_PRESS_WINDOW)
                # Check if action was cancelled by triple-press
                with cancelled_actions_lock:
                    if keycode in cancelled_actions:
                        cancelled_actions.discard(keycode)
                        key_queue.task_done()
                        continue
                if shutdown_event.is_set():
                    break
            
            action_name = ACTION_NAMES[keycode]
            
            start_time = time.time()
            try:
                # Use shell=False for security - script paths are pre-validated
                script_path = SCRIPTS[keycode]
                if not os.path.isabs(script_path):
                    script_path = os.path.abspath(script_path)
                # Validate that path is within expected directory
                if not script_path.startswith(INSTALL_DIR):
                    raise ValueError(f"Script path {script_path} is outside of allowed directory")
                result = subprocess.run([script_path], shell=False, timeout=SCRIPT_TIMEOUT, capture_output=True, text=True)
                exit_code = result.returncode
                
                # Script output logged automatically by tracer
            except subprocess.TimeoutExpired:
                exit_code = 124
            duration = time.time() - start_time
            
            if exit_code != 0:
                # Parse HTTP error codes from script stderr output
                http_error = None
                if result.stderr:
                    import re
                    # Look for HTTP error codes in stderr: "description (HTTP 404)"
                    http_match = re.search(r'\(HTTP (\d+)\)', result.stderr)
                    if http_match:
                        http_error = http_match.group(1)
                
                if http_error:
                    logging.warning(f"KEY ACTION FAILED - {action_name} (HTTP {http_error}, {duration:.2f}s)")
                elif exit_code == 124:
                    logging.warning(f"KEY ACTION FAILED - {action_name} (timeout: {SCRIPT_TIMEOUT}s, {duration:.2f}s)")
                else:
                    logging.warning(f"KEY ACTION FAILED - {action_name} (exit: {exit_code}, {duration:.2f}s)")
            else:
                # Always use our duration-enhanced completion messages
                if keycode == 'KEY_Q':
                    logging.info(f"KEY ACTION COMPLETE - Play/pause ({duration:.2f}s)")
                elif keycode == 'KEY_W':
                    logging.info(f"KEY ACTION COMPLETE - Next track ({duration:.2f}s)")
                elif keycode == 'KEY_E':
                    logging.info(f"KEY ACTION COMPLETE - Play favorite playlist ({duration:.2f}s)")
                else:
                    logging.info(f"KEY ACTION COMPLETE - {action_name} ({duration:.2f}s)")
            key_queue.task_done()
        except queue.Empty:
            continue


"""
======================================
MAIN EVENT LOOP AND INPUT PROCESSING
======================================
Monitors macropad for key presses and executes corresponding action scripts.
Detects multi-press patterns, handles device reconnection, logs all activity.
"""

def main():
    logging.info(f"SONOS-MACROPAD STARTING - v{VERSION}")
    
    # Log script generation after startup if scripts were generated during config
    if SCRIPTS_GENERATED:
        logging.info(f"ACTION - Generated {len(SCRIPT_TEMPLATES)} action scripts during startup")
        logging.info(f"ACTION - Play/pause: curl {API_BASE}/{PRIMARY_ROOM_ENCODED}/playpause")
        logging.info(f"ACTION - Next track: curl {API_BASE}/{PRIMARY_ROOM_ENCODED}/next")
        logging.info(f"ACTION - Favorite playlist: curl {API_BASE}/{PRIMARY_ROOM_ENCODED}/favorite/{urllib.parse.quote(FAVORITE_PLAYLIST)}")
        logging.info(f"ACTION - Volume up: curl {API_BASE}/{PRIMARY_ROOM_ENCODED}/volume/+{PRIMARY_STEP}")
        logging.info(f"ACTION - Volume down: curl {API_BASE}/{PRIMARY_ROOM_ENCODED}/volume/-{PRIMARY_STEP}")
        logging.info(f"ACTION - Group room: curl {API_BASE}/[secondary_room]/join/{PRIMARY_ROOM_ENCODED}")
        logging.info(f"ACTION - Ungroup room: curl {API_BASE}/[secondary_room]/leave")
    logging.info(f"CONFIG - Primary room: {PRIMARY_ROOM}")
    logging.info(f"CONFIG - Secondary rooms: {', '.join(SECONDARY_ROOMS)}")
    logging.info(f"CONFIG - Favorite playlist: {FAVORITE_PLAYLIST}")
    logging.info(f"CONFIG - SONOS HTTP API host: {API_HOST}")
    logging.info(f"CONFIG - SONOS HTTP API port: {API_PORT}")
    logging.info(f"CONFIG - SONOS HTTP API endpoint: {API_BASE}")
    logging.info(f"CONFIG - Device: {DEVICE_NAME}")
    logging.info(f"CONFIG - SONOS-MACROPAD installation directory: {INSTALL_DIR}")
    logging.info(f"CONFIG - Log file: {LOG_FILE_NAME}")
    logging.info(f"CONFIG - Primary room volume step: {PRIMARY_STEP}")
    logging.info(f"CONFIG - Primary room volume max: {PRIMARY_MAX}")
    logging.info(f"CONFIG - Primary room volume min grouping: {PRIMARY_MIN_GROUPING}")
    logging.info(f"CONFIG - Secondary rooms volume step: {SECONDARY_STEP}")
    logging.info(f"CONFIG - Secondary rooms volume max: {SECONDARY_MAX}")
    logging.info(f"CONFIG - Secondary rooms volume min grouping: {SECONDARY_MIN_GROUPING}")
    
    # Configure volume accumulator
    volume_accumulator.set_config(API_BASE, PRIMARY_ROOM, PRIMARY_MAX, PRIMARY_STEP, SECONDARY_ROOMS)
    
    # Start worker threads
    volume_thread = threading.Thread(target=volume_worker, daemon=True)
    key_thread = threading.Thread(target=key_worker, daemon=True)
    volume_thread.start()
    key_thread.start()
    
    logging.info(f"DEVICE - Starting search for device: {DEVICE_NAME}")
    
    # Show Bluetooth MAC address at startup for debugging (debug mode only)
    if DEBUG_MODE:
        device_mac = get_device_mac_address(DEVICE_NAME)
        if device_mac:
            pass
        else:
            pass
    
    q_press_times = []
    w_press_times = []
    smart_volume_script = os.path.join(INSTALL_DIR, "groups-and-volume")
    
    while not shutdown_event.is_set():
        cycle_number = getattr(main, 'device_retry_count', 0) + 1
        dev = find_device_with_retry(DEVICE_NAME, cycle_number=cycle_number)
        
        if not dev:
            if not hasattr(main, 'device_retry_count'):
                main.device_retry_count = 0
                main.bluetooth_retry_count = 0
                logging.info(f"DEVICE - Waiting for {DEVICE_NAME} to connect...")
            main.device_retry_count += 1
            
            # Try Bluetooth reconnection every DEVICE_RETRY_MAX cycles to avoid excessive attempts
            if main.device_retry_count % DEVICE_RETRY_MAX == 0:
                main.bluetooth_retry_count += 1
                
                # Get MAC address dynamically
                device_mac = get_device_mac_address(DEVICE_NAME)
                if device_mac:
                    
                    if attempt_bluetooth_reconnect(DEVICE_NAME, device_mac):
                        logging.info(f"DEVICE - Bluetooth reconnection successful for {DEVICE_NAME}")
                        # Reset counters and give device time to initialize
                        main.device_retry_count = 0
                        main.bluetooth_retry_count = 0
                        time.sleep(BLUETOOTH_INIT_DELAY)
                        continue
                    # Bluetooth reconnection failed, continue searching
            
            if shutdown_event.wait(QUEUE_TIMEOUT):
                break
            continue
            
        try:
            logging.info(f"DEVICE - {DEVICE_NAME} connected, monitoring for key presses")
            
            if hasattr(main, 'device_retry_count'):
                main.device_retry_count = 0
            
            for event in dev.read_loop():
                if shutdown_event.is_set():
                    break
                
                if event.type == ecodes.EV_KEY:
                    key = categorize(event)
                    if key.keystate == key.key_down:
                        keycode = key.keycode
                        current_time = time.time()
                        
                        is_volume_key = keycode in ['KEY_T', 'KEY_R']
                        
                        # Log detection immediately for responsiveness
                        if is_volume_key:
                            logging.info(f"KNOB TURN - {keycode} detected")
                        else:
                            logging.info(f"KEY PRESS - {keycode} detected")
                        
                        if keycode == 'KEY_Q':
                            q_press_times.append(current_time)
                            q_press_times = [t for t in q_press_times if current_time - t < MULTI_PRESS_WINDOW]
                            
                            if len(q_press_times) >= MULTI_PRESS_COUNT:
                                # Cancel any pending single press action
                                with cancelled_actions_lock:
                                    cancelled_actions.add('KEY_Q')
                                
                                logging.info(f"KEY PRESS - 3 key presses detected (KEY_Q)")
                                secondary_rooms_str = ", ".join(SECONDARY_ROOMS) if SECONDARY_ROOMS else "no secondary rooms"
                                start_time = time.time()
                                try:
                                    result = subprocess.run([smart_volume_script, "group"], timeout=GROUP_SCRIPT_TIMEOUT, capture_output=True, text=True)
                                    exit_code = result.returncode
                                except subprocess.TimeoutExpired:
                                    exit_code = 124
                                    result = None
                                duration = time.time() - start_time
                                if exit_code != 0:
                                    # Parse HTTP error code from stderr if available
                                    error_msg = f"Group {secondary_rooms_str}"
                                    if result and result.stderr and "HTTP" in result.stderr:
                                        error_msg += f" ({result.stderr.strip()}, {duration:.2f}s)"
                                    elif exit_code == 124:
                                        error_msg += f" (timeout: {GROUP_SCRIPT_TIMEOUT}s, {duration:.2f}s)"
                                    else:
                                        error_msg += f" (exit: {exit_code}, {duration:.2f}s)"
                                    logging.warning(f"KEY ACTION FAILED - {error_msg}")
                                else:
                                    logging.info(f"KEY ACTION COMPLETE - Group {secondary_rooms_str} ({duration:.2f}s)")
                                q_press_times.clear()
                            elif len(q_press_times) == 1:
                                try:
                                    key_queue.put(keycode, block=False)
                                    logging.info(f"KEY ACTION WAITING - Play/pause or Group rooms ({MULTI_PRESS_WINDOW}s delay)")
                                except queue.Full:
                                    logging.info(f"KEY PRESS - {keycode} (ignored, queue full)")
                                
                        elif keycode == 'KEY_W':
                            w_press_times.append(current_time)
                            w_press_times = [t for t in w_press_times if current_time - t < MULTI_PRESS_WINDOW]
                            
                            if len(w_press_times) >= MULTI_PRESS_COUNT:
                                # Cancel any pending single press action
                                with cancelled_actions_lock:
                                    cancelled_actions.add('KEY_W')
                                
                                logging.info(f"KEY PRESS - 3 key presses detected (KEY_W)")
                                secondary_rooms_str = ", ".join(SECONDARY_ROOMS) if SECONDARY_ROOMS else "no secondary rooms"
                                start_time = time.time()
                                try:
                                    result = subprocess.run([smart_volume_script, "ungroup"], timeout=GROUP_SCRIPT_TIMEOUT, capture_output=True, text=True)
                                    exit_code = result.returncode
                                except subprocess.TimeoutExpired:
                                    exit_code = 124
                                    result = None
                                duration = time.time() - start_time
                                if exit_code != 0:
                                    # Parse HTTP error code from stderr if available
                                    error_msg = f"Ungroup {secondary_rooms_str}"
                                    if result and result.stderr and "HTTP" in result.stderr:
                                        error_msg += f" ({result.stderr.strip()}, {duration:.2f}s)"
                                    elif exit_code == 124:
                                        error_msg += f" (timeout: {GROUP_SCRIPT_TIMEOUT}s, {duration:.2f}s)"
                                    else:
                                        error_msg += f" (exit: {exit_code}, {duration:.2f}s)"
                                    logging.warning(f"KEY ACTION FAILED - {error_msg}")
                                else:
                                    logging.info(f"KEY ACTION COMPLETE - Ungroup {secondary_rooms_str} ({duration:.2f}s)")
                                w_press_times.clear()
                            elif len(w_press_times) == 1:
                                try:
                                    key_queue.put(keycode, block=False)
                                    logging.info(f"KEY ACTION WAITING - Next track or Ungroup rooms ({MULTI_PRESS_WINDOW}s delay)")
                                except queue.Full:
                                    logging.info(f"KEY PRESS - {keycode} (ignored, queue full)")
                        else:
                            if keycode in SCRIPTS:
                                if is_volume_key:
                                    # Use volume accumulator for burst optimization
                                    volume_accumulator.add_turn(keycode)
                                else:
                                    try:
                                        key_queue.put(keycode, block=False)
                                    except queue.Full:
                                        logging.info(f"KEY PRESS - {keycode} (ignored, queue full)")
                        
        except Exception as e:
            if not shutdown_event.is_set():
                logging.info(f"DEVICE - {DEVICE_NAME} disconnected, waiting for device to reconnect...")
                # Add a small delay before trying to reconnect
                shutdown_event.wait(DEVICE_RETRY_INTERVAL)
        finally:
            try:
                dev.close()
            except (OSError, AttributeError):
                    pass  # Device already closed or invalid
    
    logging.info("SONOS-MACROPAD STOPPED - Controller shutdown complete")

"""
======================================
ENTRY POINT
======================================
Starts main() when script is executed directly (not imported as module).
Prints debug mode status if enabled.
"""

if __name__ == "__main__":
    if DEBUG_MODE:
        print(f"Debug mode enabled - logging to sonos-macropad.debug.log")
    
    main()
