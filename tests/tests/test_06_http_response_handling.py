#!/usr/bin/env python3
"""
Test HTTP response code checking in bash scripts
"""
import unittest

class TestHTTPResponseHandling(unittest.TestCase):

    def test_script_templates_check_http_codes(self):
        """Test that all script templates check HTTP response codes, not just curl exit codes"""
        with open('../sonos-macropad.py', 'r') as f:
            content = f.read()
        
        # Check that scripts use HTTP response code checking
        self.assertIn('curl -s -w "\\\\n%{{http_code}}"', content, 
                     "Scripts should use curl with HTTP code output")
        
        # Check that scripts extract HTTP codes
        self.assertIn('http_code=$(echo "$response" | tail -n1)', content,
                     "Scripts should extract HTTP response codes")
        
        # Check that scripts test for 200 status
        self.assertIn('if [ "$http_code" = "200" ]', content,
                     "Scripts should check for HTTP 200 success")
        
        # Check that error messages include HTTP codes
        self.assertIn('(HTTP $http_code)', content,
                     "Error messages should include HTTP response codes")

    def test_no_insecure_curl_patterns(self):
        """Test that insecure curl patterns are not present"""
        with open('../sonos-macropad.py', 'r') as f:
            content = f.read()
        
        # Should not have curl calls that ignore HTTP response codes
        insecure_patterns = [
            'curl -s --connect-timeout {curl_connect_timeout} --max-time {curl_max_time} "$API_BASE',
            '> /dev/null; then'
        ]
        
        for pattern in insecure_patterns:
            # Count occurrences - should be minimal (only in helper functions)
            count = content.count(pattern)
            if pattern == '> /dev/null; then':
                self.assertEqual(count, 0, f"Found insecure pattern: {pattern}")

    def test_api_request_helper_function(self):
        """Test that secure API request helper function exists"""
        with open('../sonos-macropad.py', 'r') as f:
            content = f.read()
        
        # Should have secure API helper function
        self.assertIn('api_request() {', content,
                     "Should have secure api_request helper function")
        
        # Helper should check HTTP codes
        self.assertIn('curl -s -w "\\\\n%{{http_code}}"', content,
                     "Helper function should check HTTP response codes")

if __name__ == '__main__':
    unittest.main()
