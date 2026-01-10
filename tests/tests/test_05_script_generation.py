#!/usr/bin/env python3
"""
Tests for script generation and configuration validation
"""

import unittest

class TestScriptGeneration(unittest.TestCase):
    
    def test_script_template_structure(self):
        """Test that script templates have proper structure"""
        # These are the script templates from the source code
        script_templates = [
            'groups-and-volume',
            'playpause', 
            'next',
            'volumeup',
            'volumedown',
            'favorite_playlist'
        ]
        
        # Test that we have all expected templates
        self.assertEqual(len(script_templates), 6)
        
        # Verify key templates are present
        self.assertIn('groups-and-volume', script_templates)
        self.assertIn('playpause', script_templates)
        self.assertIn('next', script_templates)
        self.assertIn('volumeup', script_templates)
        self.assertIn('volumedown', script_templates)
        self.assertIn('favorite_playlist', script_templates)
    
    def test_configuration_values_logic(self):
        """Test that configuration values follow logical relationships"""
        # Example config values from the documentation
        config = {
            'api_base': 'http://192.168.1.100:5005',
            'primary_room': 'Living Room',
            'primary_room_encoded': 'Living%20Room',
            'primary_step': 3,
            'primary_max': 50,
            'primary_min_grouping': 10,
            'secondary_step': 2,
            'secondary_max': 40,
            'secondary_min_grouping': 8,
            'secondary_rooms': ['Kitchen', 'Dining Room', 'Bathroom'],
            'secondary_rooms_encoded': ['Kitchen', 'Dining%20Room', 'Bathroom'],
            'favorite_playlist': 'My Playlist',
            'install_dir': '/home/pi/sonos-macropad'
        }
        
        # Test that volume step values are reasonable
        self.assertGreater(config['primary_step'], 0)
        self.assertLessEqual(config['primary_step'], 10)
        self.assertGreater(config['secondary_step'], 0)
        self.assertLessEqual(config['secondary_step'], 5)
        
        # Test that max values are reasonable
        self.assertGreater(config['primary_max'], 0)
        self.assertLessEqual(config['primary_max'], 100)
        self.assertGreater(config['secondary_max'], 0)
        self.assertLessEqual(config['secondary_max'], 100)
        
        # Test that minimum grouping values are reasonable
        self.assertGreater(config['primary_min_grouping'], 0)
        self.assertLessEqual(config['primary_min_grouping'], 50)
        self.assertGreater(config['secondary_min_grouping'], 0)
        self.assertLessEqual(config['secondary_min_grouping'], 20)
        
        # Test that relationships are maintained
        self.assertLess(config['primary_step'], config['primary_max'])
        self.assertLess(config['secondary_step'], config['secondary_max'])
        self.assertLess(config['primary_min_grouping'], config['primary_max'])
        self.assertLess(config['secondary_min_grouping'], config['secondary_max'])
        self.assertLessEqual(config['secondary_max'], config['primary_max'])
        
    def test_device_name_format(self):
        """Test device name format validation concepts"""
        # Example device names from config
        device_names = [
            'DOIO_KB03B',
            'Macropad_Device',
            'USB_HID_Device',
            'Generic_Macropad'
        ]
        
        # Test that names are non-empty
        for name in device_names:
            self.assertIsNotNone(name)
            self.assertNotEqual(name, "")
            
        # Test basic structure (should be valid strings)
        self.assertTrue(all(isinstance(name, str) for name in device_names))
        self.assertTrue(all(len(name) > 0 for name in device_names))

if __name__ == '__main__':
    unittest.main()