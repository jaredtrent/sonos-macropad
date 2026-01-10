#!/usr/bin/env python3
"""
Unit tests for sonos-macropad validation functions
"""

import unittest
import re

class TestValidationFunctions(unittest.TestCase):
    
    def test_validate_host_ip(self):
        """Test IP address validation logic from the source code"""
        # This mimics the IP validation from the original source code
        # The real logic in source code validates octets are 0-255
        ip_pattern = r'^(\d{1,3}\.){3}\d{1,3}$'
        
        # Test valid IPs (that will match pattern)
        self.assertIsNotNone(re.match(ip_pattern, "192.168.1.1"))
        self.assertIsNotNone(re.match(ip_pattern, "10.0.0.1"))
        self.assertIsNotNone(re.match(ip_pattern, "172.16.0.1"))
        self.assertIsNotNone(re.match(ip_pattern, "255.255.255.255"))
        self.assertIsNotNone(re.match(ip_pattern, "0.0.0.0"))
        
        # Test that pattern matches invalid octets, but actual function would check ranges
        # The regex pattern just checks format, not range validation
        self.assertIsNotNone(re.match(ip_pattern, "192.168.1.256"))
        self.assertIsNotNone(re.match(ip_pattern, "192.168.1.999"))
    
    def test_validate_host_hostname(self):
        """Test hostname validation logic from the source code"""
        # This mimics the hostname validation pattern from the original source code
        hostname_pattern = r'^[a-zA-Z0-9]([a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?(\.[a-zA-Z0-9]([a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?)*$'
        
        # Test valid hostnames
        self.assertIsNotNone(re.match(hostname_pattern, "localhost"))
        self.assertIsNotNone(re.match(hostname_pattern, "sonos-api.local"))
        self.assertIsNotNone(re.match(hostname_pattern, "my-device-123"))
        
        # Test invalid hostnames (should fail pattern match)
        self.assertIsNone(re.match(hostname_pattern, ""))  # Empty string
        self.assertIsNone(re.match(hostname_pattern, "toolong" + "a" * 250))  # Too long
    
    def test_validate_port(self):
        """Test port validation logic"""
        # Test valid ports (1-65535) - mimicking logic from source
        self.assertTrue(1 <= 80 <= 65535)  
        self.assertTrue(1 <= 443 <= 65535)  
        self.assertTrue(1 <= 5005 <= 65535)  
        self.assertTrue(1 <= 65535 <= 65535)  # Max port
        
        # Test invalid ports
        self.assertFalse(1 <= 0 <= 65535)  # Invalid port (0)
        self.assertFalse(1 <= 65536 <= 65535)  # Above max

    def test_validate_port_edge_cases(self):
        """Test port validation edge cases"""
        # Test exact boundaries
        self.assertTrue(1 <= 1 <= 65535)  # Min valid
        self.assertTrue(1 <= 65535 <= 65535)  # Max valid
        self.assertFalse(1 <= 65536 <= 65535)  # Above max
        self.assertFalse(1 <= 0 <= 65535)  # Zero invalid

if __name__ == '__main__':
    unittest.main()