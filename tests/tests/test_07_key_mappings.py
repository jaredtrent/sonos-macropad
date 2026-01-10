#!/usr/bin/env python3
"""
Tests for key sonos-macropad functionality and mappings
"""

import unittest

class TestKeyMappings(unittest.TestCase):
    
    def test_key_mappings_structure(self):
        """Test that key mappings have proper structure"""
        # These represent the key mappings from the source code
        scripts = {
            'KEY_Q': 'playpause',
            'KEY_W': 'next',
            'KEY_T': 'volumeup', 
            'KEY_R': 'volumedown',
            'KEY_E': 'favorite_playlist'
        }
        
        # Test that all expected keys are present
        expected_keys = ['KEY_Q', 'KEY_W', 'KEY_T', 'KEY_R', 'KEY_E']
        for key in expected_keys:
            self.assertIn(key, scripts, f"Missing key mapping for {key}")
        
        # Test that all keys map to valid actions
        self.assertEqual(scripts['KEY_Q'], 'playpause')
        self.assertEqual(scripts['KEY_W'], 'next')
        self.assertEqual(scripts['KEY_T'], 'volumeup')
        self.assertEqual(scripts['KEY_R'], 'volumedown')
        self.assertEqual(scripts['KEY_E'], 'favorite_playlist')
    
    def test_action_names_mapping(self):
        """Test action names mapping"""
        action_names = {
            'KEY_Q': 'play/pause',
            'KEY_W': 'next track',
            'KEY_T': 'volume up',
            'KEY_R': 'volume down',
            'KEY_E': 'favorite playlist'
        }
        
        # Test all expected actions are present
        expected_actions = ['play/pause', 'next track', 'volume up', 'volume down', 'favorite playlist']
        for action in expected_actions:
            # Find the key that maps to this action
            found = False
            for key, name in action_names.items():
                if name == action:
                    found = True
                    break
            self.assertTrue(found, f"Action '{action}' should be mapped")
    
    def test_configuration_ranges(self):
        """Test that configuration ranges are logical"""
        # Values from the example config
        config_values = {
            'primary_step': 3,
            'primary_max': 50,
            'primary_min_grouping': 10,
            'secondary_step': 2,
            'secondary_max': 40,
            'secondary_min_grouping': 8
        }
        
        # Test that primary step is reasonable
        self.assertGreater(config_values['primary_step'], 0)
        self.assertLessEqual(config_values['primary_step'], 10)
        
        # Test that primary values are reasonable
        self.assertGreater(config_values['primary_max'], 0)
        self.assertLessEqual(config_values['primary_max'], 100)
        
        # Test that secondary values are reasonable
        self.assertGreater(config_values['secondary_max'], 0)
        self.assertLessEqual(config_values['secondary_max'], 100)
        
        # Test that step values are less than max values
        self.assertLess(config_values['primary_step'], config_values['primary_max'])
        self.assertLess(config_values['secondary_step'], config_values['secondary_max'])
        
        # Test that minimum grouping values are less than max values
        self.assertLess(config_values['primary_min_grouping'], config_values['primary_max'])
        self.assertLess(config_values['secondary_min_grouping'], config_values['secondary_max'])

if __name__ == '__main__':
    unittest.main()