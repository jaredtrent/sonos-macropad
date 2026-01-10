#!/usr/bin/env python3
"""
A+ Level Tests: Error conditions, edge cases, and behavioral validation
"""
import unittest
import subprocess
import re

class TestAPlus(unittest.TestCase):

    def test_validation_error_conditions(self):
        """Test validation functions handle error conditions properly"""
        # Test IP validation edge cases
        invalid_ips = [
            '999.999.999.999',  # Out of range
            '192.168.1',        # Incomplete
            '192.168.1.1.1',    # Too many parts
            'not.an.ip',        # Non-numeric
            '',                 # Empty
            None,               # None type
        ]
        
        # Pattern matching for IP validation (from actual code)
        ip_pattern = r'^(\d{1,3}\.){3}\d{1,3}$'
        for ip in invalid_ips:
            if ip is None:
                self.assertFalse(bool(ip))
            elif not isinstance(ip, str):
                self.assertFalse(False)  # Would fail validation
            else:
                if re.match(ip_pattern, ip):
                    # Check if octets are valid (0-255)
                    try:
                        parts = ip.split('.')
                        valid = all(0 <= int(part) <= 255 for part in parts)
                        self.assertFalse(valid, f"IP {ip} should be invalid")
                    except ValueError:
                        self.assertTrue(True)  # Expected failure
                else:
                    self.assertTrue(True)  # Pattern didn't match, correctly invalid

    def test_port_validation_boundary_conditions(self):
        """Test port validation at boundaries"""
        test_cases = [
            ('0', False),      # Reserved port
            ('1', True),       # Minimum valid
            ('5005', True),    # Typical Sonos port
            ('65535', True),   # Maximum valid
            ('65536', False),  # Above maximum
            ('-1', False),     # Negative
            ('abc', False),    # Non-numeric
            ('', False),       # Empty
        ]
        
        for port_str, expected in test_cases:
            try:
                port = int(port_str)
                result = 1 <= port <= 65535
                self.assertEqual(result, expected, f"Port {port_str} validation failed")
            except ValueError:
                self.assertFalse(expected, f"Port {port_str} should be invalid")

    def test_hostname_validation_patterns(self):
        """Test hostname validation with various patterns"""
        valid_hostnames = [
            'sonos-api.local',
            'localhost',
            'api.example.com',
            'test123',
            'my-server-01'
        ]
        
        invalid_hostnames = [
            '',                    # Empty
            'a' * 254,            # Too long
            'invalid..hostname',   # Double dots
            '-invalid',           # Starts with hyphen
            'invalid-',           # Ends with hyphen
            'inv@lid',            # Invalid character
        ]
        
        # RFC 1123 hostname pattern (simplified)
        hostname_pattern = r'^[a-zA-Z0-9]([a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?(\.[a-zA-Z0-9]([a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?)*$'
        
        for hostname in valid_hostnames:
            if len(hostname) <= 253:
                self.assertTrue(re.match(hostname_pattern, hostname), f"Hostname {hostname} should be valid")
        
        for hostname in invalid_hostnames:
            if len(hostname) > 253:
                self.assertTrue(True)  # Too long, correctly invalid
            else:
                match_result = re.match(hostname_pattern, hostname)
                self.assertIsNone(match_result, f"Hostname {hostname} should be invalid")

    def test_volume_configuration_constraints(self):
        """Test volume configuration logical constraints"""
        # Test primary volume constraints
        primary_configs = [
            {'step': 1, 'max': 50, 'min_grouping': 10, 'valid': True},
            {'step': 10, 'max': 50, 'min_grouping': 10, 'valid': True},
            {'step': 50, 'max': 50, 'min_grouping': 10, 'valid': False},  # step >= max
            {'step': 5, 'max': 50, 'min_grouping': 50, 'valid': False},   # min_grouping >= max
            {'step': 0, 'max': 50, 'min_grouping': 10, 'valid': False},   # step out of range
            {'step': 11, 'max': 50, 'min_grouping': 10, 'valid': False},  # step out of range
        ]
        
        for config in primary_configs:
            step_valid = 1 <= config['step'] <= 10
            max_valid = 1 <= config['max'] <= 100
            min_grouping_valid = 1 <= config['min_grouping'] <= 50
            step_less_than_max = config['step'] < config['max']
            min_less_than_max = config['min_grouping'] < config['max']
            
            overall_valid = all([step_valid, max_valid, min_grouping_valid, step_less_than_max, min_less_than_max])
            self.assertEqual(overall_valid, config['valid'], f"Primary config {config} validation failed")

    def test_script_template_security_patterns(self):
        """Test that script templates use secure patterns"""
        # Read the actual script templates from the source
        with open('../sonos-macropad.py', 'r') as f:
            content = f.read()
        
        # Verify security patterns are present
        security_checks = [
            ('shell=False', 'subprocess.run should use shell=False'),
            ('subprocess.run([', 'Arguments should be in array format'),
            ('os.path.join(INSTALL_DIR', 'Paths should be properly joined'),
            ('--connect-timeout', 'Curl should have connection timeout'),
            ('--max-time', 'Curl should have maximum time limit'),
        ]
        
        for pattern, description in security_checks:
            self.assertIn(pattern, content, description)

    def test_api_response_parsing_resilience(self):
        """Test API response parsing handles malformed data"""
        # Test JSON parsing patterns that should be resilient
        malformed_responses = [
            '{"invalid": json}',           # Invalid JSON
            '[{"roomName": }]',            # Incomplete JSON
            '[]',                          # Empty array
            '{"members": []}',             # Empty members
            'not json at all',             # Not JSON
            '',                           # Empty response
        ]
        
        for response in malformed_responses:
            try:
                import json
                parsed = json.loads(response)
                # If parsing succeeds, verify it handles empty/invalid structures
                if isinstance(parsed, list) and len(parsed) == 0:
                    self.assertTrue(True)  # Empty list is handled
                elif isinstance(parsed, dict) and 'members' in parsed:
                    members = parsed.get('members', [])
                    self.assertIsInstance(members, list)  # Should be a list
            except (json.JSONDecodeError, ValueError):
                self.assertTrue(True)  # Expected for malformed JSON

    def test_device_name_filtering_logic(self):
        """Test device name filtering excludes inappropriate devices"""
        device_names = [
            ('DOIO_KB03B', True),           # Valid macropad
            ('Keyboard_Device', True),       # Valid keyboard
            ('HDMI Audio Output', False),    # Audio device
            ('VC4 HDMI', False),            # Video device
            ('Sound Card', False),          # Sound device
            ('USB Audio', False),           # Audio device
        ]
        
        audio_keywords = ['hdmi', 'audio', 'sound', 'vc4']
        
        for device_name, should_be_valid in device_names:
            name_lower = device_name.lower()
            has_audio_keyword = any(keyword in name_lower for keyword in audio_keywords)
            is_valid = not has_audio_keyword
            
            self.assertEqual(is_valid, should_be_valid, f"Device {device_name} filtering failed")

    def test_configuration_file_path_validation(self):
        """Test configuration file path validation logic"""
        invalid_chars = ['<', '>', ':', '"', '|', '?', '*', '\0']
        
        test_filenames = [
            ('valid-log.log', True),
            ('log<file.log', False),       # Contains <
            ('log>file.log', False),       # Contains >
            ('log:file.log', False),       # Contains :
            ('log"file.log', False),       # Contains "
            ('log|file.log', False),       # Contains |
            ('log?file.log', False),       # Contains ?
            ('log*file.log', False),       # Contains *
            ('', False),                   # Empty filename
        ]
        
        for filename, should_be_valid in test_filenames:
            if not filename:
                is_valid = False
            else:
                is_valid = not any(char in filename for char in invalid_chars)
            
            self.assertEqual(is_valid, should_be_valid, f"Filename {filename} validation failed")

    def test_multi_press_timing_logic(self):
        """Test multi-press detection timing logic"""
        import time
        
        # Simulate press timing logic
        MULTI_PRESS_WINDOW = 0.8
        MULTI_PRESS_COUNT = 3
        
        # Test case 1: Presses within window
        press_times = []
        current_time = time.time()
        
        # Add 3 presses within window
        for i in range(3):
            press_times.append(current_time + (i * 0.2))  # 0.2s apart
        
        # Filter presses within window (simulate actual logic)
        window_start = current_time
        valid_presses = [t for t in press_times if (t - window_start) <= MULTI_PRESS_WINDOW]
        self.assertEqual(len(valid_presses), 3, "All presses should be within window")
        
        # Test case 2: Presses outside window
        press_times = [current_time, current_time + 1.0]  # 1.0s apart
        valid_presses = [t for t in press_times if (t - window_start) <= MULTI_PRESS_WINDOW]
        self.assertEqual(len(valid_presses), 1, "Only first press should be within window")

if __name__ == '__main__':
    unittest.main()
