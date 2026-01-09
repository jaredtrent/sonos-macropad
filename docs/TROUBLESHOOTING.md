# Sonos Macropad Controller Troubleshooting Guide

[AI-generated]

Common issues you might encounter with sonos-macropad. This guide helps you diagnose problems quickly and get your system working reliably. AI-generated, but, 

## Quick Diagnosis

Start here to identify what type of problem you're experiencing.

### Symptom Categories

**Configuration Issues:**
- Script won't start or exits immediately
- Error messages about config.ini
- Validation failures

**Device Connection Issues:**
- Macropad not detected
- Keys don't respond
- Bluetooth connection problems

**Sonos API Issues:**
- Can't connect to Sonos system
- Room or playlist not found
- API calls fail

**Service Issues:**
- Service won't start automatically
- Service stops unexpectedly
- Permission errors

### First Steps

Before diving into specific solutions, try these quick fixes:

```bash
# 1. Check if sonos-macropad is running
ps aux | grep sonos-macropad

# 2. Look at recent log entries
tail -20 sonos-macropad.log

# 3. Test basic functionality
python3 sonos-macropad.py --help

# 4. Run validation to identify issues
python3 sonos-macropad.py --validate
```

## Configuration Issues

Problems with config.ini settings and validation failures.

### Config File Not Found

**Symptoms:**
- "config.ini file not found" error message
- Script exits immediately on startup

**Solution:**
```bash
# Check if config.ini exists in the correct location
ls -la config.ini

# If missing, copy from example
cp config.ini.example config.ini

# Edit with your settings
nano config.ini
```

**Prevention:** Always keep config.ini in the same directory as sonos-macropad.py.

### Invalid Room Names

**Symptoms:**
- "Room not found in Sonos system" error
- Validation fails for rooms

**Diagnosis:**
```bash
# Check what rooms Sonos sees
python3 sonos-macropad.py --validate rooms

# Compare with your config
grep "primary_room\|secondary_rooms" config.ini
```

**Solution:**
Room names must match your Sonos app exactly (case-sensitive):
```ini
# Wrong
primary_room = living room
secondary_rooms = kitchen, bedroom

# Correct  
primary_room = Living Room
secondary_rooms = Kitchen,Bedroom
```

**Common Mistakes:**
- Incorrect capitalization
- Extra spaces around commas
- Abbreviated room names
- Special characters not matching

### Invalid Playlist Names

**Symptoms:**
- "Playlist not found in Sonos system" error
- Favorite playlist action doesn't work

**Diagnosis:**
```bash
# Check available playlists
python3 sonos-macropad.py --validate playlist

# Check your config setting
grep "favorite_playlist" config.ini
```

**Solution:**
Use the exact playlist name from your Sonos favorites:
```ini
# Must match Sonos app exactly
favorite_playlist = Discover Weekly
```

**Note:** The playlist must be in your Sonos favorites, not just your music library.

### Volume Settings Out of Range

**Symptoms:**
- "Volume setting not in valid range" error
- Validation fails for volume section

**Solution:**
Check volume ranges in config.ini:
```ini
[volume]
primary_single_step = 3      # Must be 1-10
primary_max = 50            # Must be 1-100
primary_min_grouping = 10   # Must be 1-50
secondary_step = 2          # Must be 1-5
secondary_max = 40          # Must be 1-100
secondary_min_grouping = 8  # Must be 1-20
```

**Logic Requirements:**
- `primary_single_step` < `primary_max`
- `primary_min_grouping` < `primary_max`
- `secondary_step` < `secondary_max`
- `secondary_min_grouping` < `secondary_max`
- `secondary_max` ≤ `primary_max`

## Device Connection Issues

Problems with macropad detection and key response.

### Device Not Found

**Symptoms:**
- "Device not found" error
- Script starts but keys don't respond
- Device validation fails

**Diagnosis:**
```bash
# Check if device is connected
python3 sonos-macropad.py --validate device

# List all input devices
ls -la /dev/input/event*

# Check device permissions
ls -la /dev/input/event* | grep "$(whoami)\|input"
```

**Solution 1 - Permission Issues:**
```bash
# Add user to input group
sudo usermod -a -G input $USER

# Log out and back in, or reboot
# Verify group membership
groups | grep input
```

**Solution 2 - Wrong Device Name:**
```bash
# Find correct device name
python3 sonos-macropad.py --validate device

# Update config.ini with correct name
nano config.ini
# Change device_name to match discovered name
```

**Solution 3 - Device Not Connected:**
For Bluetooth devices:
```bash
# Check Bluetooth status
bluetoothctl devices

# Reconnect if needed
bluetoothctl connect [MAC_ADDRESS]

# Check connection status
bluetoothctl info [MAC_ADDRESS]
```

### Keys Don't Respond

**Symptoms:**
- Device detected but key presses do nothing
- No log entries when pressing keys
- Wrong actions triggered

**Diagnosis:**
```bash
# Enable debug mode to see function tracing
python3 sonos-macropad.py --debug

# Press keys and watch for function call traces
# Should see function entry/exit messages
```

**Solution 1 - Wrong Key Mapping:**
Your macropad must send these key codes:
- Left key → Q
- Middle key → W  
- Right key → E
- Knob right → T
- Knob left → R

Use VIA software to configure: https://usevia.app

**Solution 2 - Device Path Changed:**
```bash
# Device path may have changed after reboot
python3 sonos-macropad.py --validate device

# Restart sonos-macropad to detect new path
sudo systemctl restart sonos-macropad
```

### Bluetooth Connection Problems

**Symptoms:**
- Device connects then disconnects
- Intermittent key response
- "Device disconnected" messages in logs

**Diagnosis:**
```bash
# Check Bluetooth service status
sudo systemctl status bluetooth

# Check device connection quality
bluetoothctl info [MAC_ADDRESS] | grep "Connected\|RSSI"

# Monitor connection in debug mode
python3 sonos-macropad.py --debug
```

**Solution 1 - Improve Connection:**
```bash
# Restart Bluetooth service
sudo systemctl restart bluetooth

# Re-pair device
bluetoothctl remove [MAC_ADDRESS]
bluetoothctl scan on
bluetoothctl pair [MAC_ADDRESS]
bluetoothctl trust [MAC_ADDRESS]
bluetoothctl connect [MAC_ADDRESS]
```

**Solution 2 - Power Management:**
```bash
# Disable USB power management (if using USB Bluetooth adapter)
echo 'SUBSYSTEM=="usb", ATTRS{idVendor}=="[vendor]", ATTRS{idProduct}=="[product]", ATTR{power/autosuspend}="-1"' | sudo tee /etc/udev/rules.d/50-usb-bluetooth.rules

# Reboot after adding rule
sudo reboot
```

## Sonos API Issues

Problems connecting to your Sonos system through the HTTP API.

### API Connection Failed

**Symptoms:**
- "Cannot connect to Sonos HTTP API" error
- API validation fails
- All Sonos actions fail

**Diagnosis:**
```bash
# Test API manually
curl http://[API_HOST]:[API_PORT]/zones

# Check if API server is running
ps aux | grep node-sonos-http-api

# Test network connectivity
ping [API_HOST]
```

**Solution 1 - Start API Server:**
```bash
# Navigate to API directory
cd ~/node-sonos-http-api

# Start API server
npm start

# Or install as service (see API documentation)
```

**Solution 2 - Fix Network Issues:**
```bash
# Check API host in config
grep "api_host\|api_port" config.ini

# Update with correct IP address
nano config.ini
```

**Solution 3 - Firewall Issues:**
```bash
# Check if port 5005 is accessible
telnet [API_HOST] 5005

# If using firewall, allow port 5005
sudo ufw allow 5005
```

### Sonos Speakers Not Found

**Symptoms:**
- API connects but no rooms found
- Empty room list from validation
- "No Sonos speakers detected" error

**Diagnosis:**
```bash
# Check API zones endpoint
curl http://[API_HOST]:[API_PORT]/zones

# Verify Sonos speakers are on network
# Check Sonos app on phone/computer
```

**Solution:**
This usually indicates network issues between the API server and Sonos speakers:

1. **Same Network:** Ensure API server and Sonos speakers are on same network
2. **Network Discovery:** Restart API server to re-discover speakers
3. **Firewall:** Check firewall isn't blocking Sonos discovery ports
4. **Sonos App:** Verify speakers work in official Sonos app

### API Calls Timeout

**Symptoms:**
- Actions start but never complete
- "API timeout" errors in logs
- Slow response to key presses

**Diagnosis:**
```bash
# Test API response time
time curl http://[API_HOST]:[API_PORT]/zones

# Check network latency
ping -c 5 [API_HOST]
```

**Solution:**
```bash
# Increase timeout values in generated scripts
# (Scripts regenerate automatically when config changes)

# Or reduce network latency:
# - Use wired connection instead of WiFi
# - Move devices closer to router
# - Check for network congestion
```

## Service Issues

Problems with systemd service installation and operation.

### Service Won't Start

**Symptoms:**
- `systemctl start sonos-macropad` fails
- Service shows "failed" status
- No log entries generated

**Diagnosis:**
```bash
# Check service status
sudo systemctl status sonos-macropad

# Check service logs
sudo journalctl -u sonos-macropad -n 20

# Check service file syntax
sudo systemctl cat sonos-macropad
```

**Solution 1 - Fix Service File:**
```bash
# Check service file exists
ls -la /etc/systemd/system/sonos-macropad.service

# Verify paths in service file
sudo nano /etc/systemd/system/sonos-macropad.service

# Reload after changes
sudo systemctl daemon-reload
```

**Solution 2 - Permission Issues:**
```bash
# Check file permissions
ls -la /home/pi/sonos-macropad/sonos-macropad.py

# Make executable if needed
chmod +x /home/pi/sonos-macropad/sonos-macropad.py

# Check directory permissions
ls -la /home/pi/sonos-macropad/
```

**Solution 3 - User Issues:**
```bash
# Verify user in service file matches system user
grep "User=" /etc/systemd/system/sonos-macropad.service

# Check user exists and has proper groups
id pi
groups pi
```

### Service Stops Unexpectedly

**Symptoms:**
- Service starts but stops after short time
- "Restart" messages in service logs
- Intermittent operation

**Diagnosis:**
```bash
# Check recent service logs
sudo journalctl -u sonos-macropad -f

# Check application logs
tail -f /home/pi/sonos-macropad/sonos-macropad.log

# Check system resources
top
df -h
```

**Solution 1 - Fix Application Errors:**
```bash
# Run manually to see errors
cd /home/pi/sonos-macropad
python3 sonos-macropad.py --debug

# Fix any configuration issues found
```

**Solution 2 - Resource Issues:**
```bash
# Check disk space
df -h /home/pi/sonos-macropad

# Check memory usage
free -h

# Clean up log files if needed
sudo journalctl --vacuum-time=7d
```

### Permission Denied Errors

**Symptoms:**
- "Permission denied" in service logs
- Can't access device files
- Can't write to log files

**Solution:**
```bash
# Fix input device permissions
sudo usermod -a -G input pi

# Fix directory permissions
sudo chown -R pi:pi /home/pi/sonos-macropad
chmod 755 /home/pi/sonos-macropad

# Fix log file permissions
touch /home/pi/sonos-macropad/sonos-macropad.log
chmod 644 /home/pi/sonos-macropad/sonos-macropad.log

# Restart service after permission changes
sudo systemctl restart sonos-macropad
```

## Performance Issues

Problems with slow response or high resource usage.

### Slow Key Response

**Symptoms:**
- Delay between key press and Sonos action
- Actions queue up and execute slowly
- System feels sluggish

**Diagnosis:**
```bash
# Check system load
top
htop

# Check network latency to API
ping -c 10 [API_HOST]

# Enable debug mode to see timing
python3 sonos-macropad.py --debug
```

**Solution 1 - Network Optimization:**
```bash
# Use wired connection if possible
# Move closer to WiFi router
# Check for network interference

# Test API response time
time curl http://[API_HOST]:[API_PORT]/zones
```

**Solution 2 - System Optimization:**
```bash
# Check available memory
free -h

# Check disk I/O
iostat 1 5

# Reduce log verbosity if needed
# (Remove --debug flag from service)
```

### High CPU Usage

**Symptoms:**
- sonos-macropad using high CPU
- System becomes unresponsive
- High load average

**Diagnosis:**
```bash
# Check CPU usage
top -p $(pgrep -f sonos-macropad)

# Check for infinite loops with function tracing
python3 sonos-macropad.py --debug
```

**Solution:**
```bash
# Usually indicates device connection issues
# causing rapid reconnection attempts

# Check device connection stability
python3 sonos-macropad.py --validate device

# Fix Bluetooth connection issues (see Device Connection section)
```

## Advanced Troubleshooting

Techniques for diagnosing complex or unusual problems.

### Enable Debug Mode

Get automatic function tracing for sonos-macropad operation:

```bash
# Run with automatic function tracing
python3 sonos-macropad.py --debug

# Debug traces show:
# - Function entry/exit points
# - Function parameters and return values
# - Exception details
# - Call stack information
```

### Log Analysis

Understanding what the logs tell you:

**Normal Operation Log (`sonos-macropad.log`):**
```
[2026-01-08 10:30:15] INFO: SONOS-MACROPAD STARTING - v2026.1.8
[2026-01-08 10:30:15] INFO: DEVICE - Starting search for device: DOIO_KB03B
[2026-01-08 10:30:17] INFO: DEVICE - DOIO_KB03B connected, monitoring for key presses
[2026-01-08 10:30:25] INFO: KEY PRESS - Q detected
[2026-01-08 10:30:25] INFO: KEY ACTION COMPLETE - Play/pause (0.85s)
```

**Debug Log (`sonos-macropad.debug.log`):**
```
[2026-01-08 10:30:15.123] DEBUG: ENTER find_doio_device(device_name=DOIO_KB03B)
[2026-01-08 10:30:15.124] DEBUG:   ENTER InputDevice(/dev/input/event0)
[2026-01-08 10:30:15.125] DEBUG:   EXIT InputDevice -> <InputDevice /dev/input/event0>
[2026-01-08 10:30:17.200] DEBUG: EXIT find_doio_device -> <InputDevice /dev/input/event2>
```

**Config Error Log (`sonos-macropad.config-errors.log`):**
```
[2026-01-08 10:30:10] CONFIG ERROR: primary_room in config.ini not found in Sonos system: primary_room = Living room
[2026-01-08 10:30:10] CONFIG ERROR: To resolve: Edit config.ini and enter a valid room name. Available rooms: Living Room, Kitchen, Bedroom
```

### Manual Testing

Test components individually to isolate problems:

```bash
# Test API connectivity
curl http://192.168.1.100:5005/zones

# Test specific room control
curl http://192.168.1.100:5005/Living%20Room/playpause

# Test device access
ls -la /dev/input/event*
cat /dev/input/event2  # (Ctrl+C to stop, press keys to see events)

# Test Python dependencies
python3 -c "import evdev; print('evdev OK')"
```

### Network Diagnostics

Diagnose network-related issues:

```bash
# Test basic connectivity
ping [API_HOST]

# Test port accessibility
telnet [API_HOST] 5005

# Check routing
traceroute [API_HOST]

# Check DNS resolution (if using hostname)
nslookup [API_HOST]

# Monitor network traffic
sudo tcpdump -i any port 5005
```

### System Resource Monitoring

Check if system resources are causing issues:

```bash
# Monitor CPU and memory
htop

# Check disk usage
df -h
du -sh /home/pi/sonos-macropad/*

# Check I/O wait
iostat 1 5

# Check system logs for hardware issues
sudo dmesg | tail -20
```

## Getting Additional Help

When standard troubleshooting doesn't resolve your issue.

### Collecting Diagnostic Information

Gather this information when seeking help:

```bash
# System information
uname -a
python3 --version
pip list | grep evdev

# Configuration (remove sensitive info)
cat config.ini

# Recent logs
tail -50 sonos-macropad.log
tail -20 sonos-macropad.config-errors.log

# Service status (if using service)
sudo systemctl status sonos-macropad
```

### Debug Mode Output

Run with automatic function tracing and check the debug log:

```bash
# Run with function tracing
python3 sonos-macropad.py --debug

# In another terminal, watch the debug log
tail -f sonos-macropad.debug.log

# Test the problematic functionality
# Stop with Ctrl+C

# Review sonos-macropad.debug.log for function call patterns
```

### Validation Results

Run comprehensive validation and check results:

```bash
# Full validation 
python3 sonos-macropad.py --validate

# Check config error log for validation failures
cat sonos-macropad.config-errors.log

# Check operational log for validation results
tail -20 sonos-macropad.log
```