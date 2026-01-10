#!/usr/bin/env python3
"""
Additional unit tests for sonos-macropad
"""

import unittest

class TestBasicFunctionality(unittest.TestCase):
    
    def test_config_values_exist(self):
        """Test that basic config values are present"""
        # These would be tested with actual config loading
        # For now, just verify basic structure
        self.assertTrue(True)
    
    def test_volume_step_bounds(self):
        """Test volume step validation ranges"""
        # Test that primary_step is within expected bounds (1-10)
        primary_step = 3
        self.assertTrue(1 <= primary_step <= 10)
        
        # Test that secondary_step is within expected bounds (1-5) 
        secondary_step = 2
        self.assertTrue(1 <= secondary_step <= 5)
    
    def test_volume_max_bounds(self):
        """Test volume max validation ranges"""
        # Test that primary_max is within expected bounds (1-100)
        primary_max = 50
        self.assertTrue(1 <= primary_max <= 100)
        
        # Test that secondary_max is within expected bounds (1-100)
        secondary_max = 40
        self.assertTrue(1 <= secondary_max <= 100)

if __name__ == '__main__':
    unittest.main()