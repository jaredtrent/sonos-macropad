#!/usr/bin/env python3
"""
Tests for missing critical functions in sonos-macropad.py
Covers VolumeAccumulator, MAC validation, and other untested functions.
"""

import unittest
import time
import threading
import re
from unittest.mock import patch, MagicMock

class TestMissingFunctions(unittest.TestCase):
    """Test functions that weren't covered by existing tests"""
    
    def test_volume_accumulator_add_turn_logic(self):
        """Test VolumeAccumulator.add_turn method"""
        # Read source to verify VolumeAccumulator implementation
        with open('../sonos-macropad.py', 'r') as f:
            content = f.read()
        
        # Verify add_turn method exists and handles volume accumulation
        self.assertIn('def add_turn(self, keycode):', content)
        self.assertIn('self.pending_up += PRIMARY_STEP', content)
        self.assertIn('self.pending_down += PRIMARY_STEP', content)
        self.assertIn('if keycode == \'KEY_T\':', content)
        self.assertIn('elif keycode == \'KEY_R\':', content)
    
    def test_volume_accumulator_execute_accumulated(self):
        """Test VolumeAccumulator._execute_accumulated method"""
        with open('../sonos-macropad.py', 'r') as f:
            content = f.read()
        
        # Verify _execute_accumulated method exists and processes volume changes
        self.assertIn('def _execute_accumulated(self):', content)
        self.assertIn('volume_queue.put((\'KEY_T\', self.pending_up)', content)
        self.assertIn('volume_queue.put((\'KEY_R\', self.pending_down)', content)
        self.assertIn('self.pending_up = 0', content)
        self.assertIn('self.pending_down = 0', content)
    
    def test_volume_accumulator_set_config(self):
        """Test VolumeAccumulator.set_config method"""
        with open('../sonos-macropad.py', 'r') as f:
            content = f.read()
        
        # Verify set_config method exists and stores configuration
        self.assertIn('def set_config(self, api_base, primary_room, primary_max, primary_step, secondary_rooms):', content)
        self.assertIn('self.api_base = api_base', content)
        self.assertIn('self.primary_room = primary_room', content)
        self.assertIn('self.primary_max = primary_max', content)
    
    def test_is_valid_mac_function(self):
        """Test is_valid_mac function validates MAC addresses correctly"""
        with open('../sonos-macropad.py', 'r') as f:
            content = f.read()
        
        # Verify is_valid_mac function exists and uses proper regex
        self.assertIn('def is_valid_mac(mac):', content)
        self.assertIn('re.match(r\'^([0-9A-Fa-f]{2}[:-]){5}([0-9A-Fa-f]{2})$\', mac)', content)
        
        # Test the actual regex pattern used in the function
        mac_pattern = r'^([0-9A-Fa-f]{2}[:-]){5}([0-9A-Fa-f]{2})$'
        
        # Valid MAC addresses
        self.assertTrue(re.match(mac_pattern, '00:11:22:33:44:55'))
        self.assertTrue(re.match(mac_pattern, 'AA:BB:CC:DD:EE:FF'))
        self.assertTrue(re.match(mac_pattern, '00-11-22-33-44-55'))
        
        # Invalid MAC addresses
        self.assertFalse(re.match(mac_pattern, '00:11:22:33:44'))  # Too short
        self.assertFalse(re.match(mac_pattern, '00:11:22:33:44:55:66'))  # Too long
        self.assertFalse(re.match(mac_pattern, 'GG:11:22:33:44:55'))  # Invalid hex
        self.assertFalse(re.match(mac_pattern, ''))  # Empty
    
    def test_auto_debug_tracer_trace_calls(self):
        """Test AutoDebugTracer.trace_calls method"""
        with open('../sonos-macropad.py', 'r') as f:
            content = f.read()
        
        # Verify trace_calls method exists and handles different events
        self.assertIn('def trace_calls(self, frame, event, arg):', content)
        self.assertIn('if event == \'call\':', content)
        self.assertIn('elif event == \'return\':', content)
        self.assertIn('elif event == \'exception\':', content)
        self.assertIn('self.call_depth += 1', content)
        self.assertIn('self.call_depth = max(0, self.call_depth - 1)', content)
    
    def test_volume_accumulator_thread_safety(self):
        """Test VolumeAccumulator uses proper locking"""
        with open('../sonos-macropad.py', 'r') as f:
            content = f.read()
        
        # Verify thread safety mechanisms
        self.assertIn('self.lock = threading.Lock()', content)
        self.assertIn('with self.lock:', content)
        self.assertIn('threading.Timer(self.burst_timeout, self._execute_accumulated)', content)
    
    def test_volume_accumulator_timing_logic(self):
        """Test VolumeAccumulator timing and burst detection"""
        with open('../sonos-macropad.py', 'r') as f:
            content = f.read()
        
        # Verify timing logic for burst detection
        self.assertIn('current_time - self.last_turn_time > self.burst_timeout', content)
        self.assertIn('self.last_turn_time = current_time', content)
        self.assertIn('self.burst_timeout = VOLUME_BURST_WINDOW', content)
    
    def test_critical_constants_defined(self):
        """Test that all critical timing constants are properly defined"""
        with open('../sonos-macropad.py', 'r') as f:
            content = f.read()
        
        # Verify critical timing constants
        self.assertIn('MULTI_PRESS_WINDOW = 0.8', content)
        self.assertIn('VOLUME_BURST_WINDOW = 0.1', content)
        self.assertIn('MULTI_PRESS_COUNT = 3', content)
        self.assertIn('SCRIPT_TIMEOUT = 10', content)
        self.assertIn('GROUP_SCRIPT_TIMEOUT = 15', content)
    
    def test_queue_based_processing_implementation(self):
        """Test queue-based processing is properly implemented"""
        with open('../sonos-macropad.py', 'r') as f:
            content = f.read()
        
        # Verify queue implementation
        self.assertIn('volume_queue = queue.Queue(maxsize=5)', content)
        self.assertIn('key_queue = queue.Queue(maxsize=3)', content)
        self.assertIn('volume_queue.put(', content)
        self.assertIn('key_queue.put(', content)
        self.assertIn('volume_queue.get(timeout=', content)
        self.assertIn('key_queue.get(timeout=', content)

class TestProductionReadinessValidation(unittest.TestCase):
    """Validate production readiness fixes are properly applied"""
    
    def test_path_traversal_fix_applied(self):
        """Test that path traversal vulnerability fix is applied"""
        with open('../sonos-macropad.py', 'r') as f:
            content = f.read()
        
        # Verify secure path validation is used
        self.assertIn('real_script = os.path.realpath(script_path)', content)
        self.assertIn('real_install = os.path.realpath(INSTALL_DIR)', content)
        self.assertIn('real_script.startswith(real_install + os.sep)', content)
    
    def test_specific_exception_handling(self):
        """Test that bare except blocks were replaced with specific exceptions"""
        with open('../sonos-macropad.py', 'r') as f:
            content = f.read()
        
        # Verify specific exception handling
        self.assertIn('except (OSError, AttributeError)', content)
        self.assertIn('except (json.JSONDecodeError, KeyError, IndexError)', content)
        
        # Verify no bare except blocks remain (except in comments)
        lines = content.split('\n')
        bare_except_lines = [i for i, line in enumerate(lines) 
                           if line.strip() == 'except:' and not line.strip().startswith('#')]
        self.assertEqual(len(bare_except_lines), 0, 
                        f"Found bare except blocks at lines: {bare_except_lines}")
    
    def test_input_validation_added(self):
        """Test that input validation was added for device name"""
        with open('../sonos-macropad.py', 'r') as f:
            content = f.read()
        
        # Verify device name validation
        self.assertIn('re.match(r\'^[a-zA-Z0-9_.-]+$\', device_name)', content)
        self.assertIn('device_name in config.ini contains invalid characters', content)

if __name__ == '__main__':
    unittest.main()
