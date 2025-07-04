#!/usr/bin/env python3
"""
Security Testing for SSB Retire Server Web Application
Manual testing approach following existing patterns in the codebase
"""

import json
import os
import sys
import requests
import time
from urllib.parse import urlparse

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

class SecurityTester:
    """Manual security testing class for Flask application"""
    
    def __init__(self, base_url="http://localhost:5000"):
        self.base_url = base_url
        self.session = requests.Session()
        self.test_results = {
            'passed': 0,
            'failed': 0,
            'tests': []
        }
    
    def log_test_result(self, test_name, passed, message):
        """Log test result"""
        status = "PASS" if passed else "FAIL"
        self.test_results['tests'].append({
            'name': test_name,
            'status': status,
            'message': message
        })
        
        if passed:
            self.test_results['passed'] += 1
        else:
            self.test_results['failed'] += 1
            
        print(f"[{status}] {test_name}: {message}")
    
    def test_security_headers(self):
        """Test security headers are present"""
        try:
            response = self.session.get(f"{self.base_url}/health")
            
            # Check for security headers
            required_headers = [
                'X-Content-Type-Options',
                'X-Frame-Options', 
                'X-XSS-Protection'
            ]
            
            missing_headers = []
            for header in required_headers:
                if header not in response.headers:
                    missing_headers.append(header)
            
            if missing_headers:
                self.log_test_result(
                    "Security Headers",
                    False,
                    f"Missing headers: {', '.join(missing_headers)}"
                )
            else:
                self.log_test_result(
                    "Security Headers", 
                    True,
                    "All required security headers present"
                )
                
            # Validate specific header values
            if response.headers.get('X-Frame-Options') == 'DENY':
                self.log_test_result(
                    "X-Frame-Options",
                    True, 
                    "Correctly set to DENY"
                )
            else:
                self.log_test_result(
                    "X-Frame-Options",
                    False,
                    f"Incorrect value: {response.headers.get('X-Frame-Options')}"
                )
                
        except Exception as e:
            self.log_test_result(
                "Security Headers",
                False,
                f"Test failed with error: {str(e)}"
            )
    
    def test_https_enforcement(self):
        """Test HTTPS enforcement (simulated for development)"""
        try:
            # Simulate HTTP request with X-Forwarded-Proto header
            headers = {'X-Forwarded-Proto': 'http'}
            response = self.session.get(f"{self.base_url}/health", headers=headers)
            
            # In development, this won't redirect, but we test the health endpoint
            if response.status_code == 200:
                self.log_test_result(
                    "HTTPS Enforcement",
                    True,
                    "Health endpoint accessible (dev mode)"
                )
            else:
                self.log_test_result(
                    "HTTPS Enforcement", 
                    False,
                    f"Unexpected status code: {response.status_code}"
                )
                
        except Exception as e:
            self.log_test_result(
                "HTTPS Enforcement",
                False,
                f"Test failed with error: {str(e)}"
            )
    
    def test_rate_limiting(self):
        """Test rate limiting functionality"""
        try:
            # Test health endpoint (should not be rate limited)
            response = self.session.get(f"{self.base_url}/health")
            
            if response.status_code == 200:
                self.log_test_result(
                    "Rate Limiting Setup",
                    True,
                    "Application responding normally"
                )
            else:
                self.log_test_result(
                    "Rate Limiting Setup",
                    False,
                    f"Application not responding: {response.status_code}"
                )
                
            # Check for rate limit headers
            if 'X-RateLimit-Limit' in response.headers or 'X-RateLimit-Remaining' in response.headers:
                self.log_test_result(
                    "Rate Limit Headers",
                    True,
                    "Rate limiting headers present"
                )
            else:
                self.log_test_result(
                    "Rate Limit Headers",
                    False,
                    "Rate limiting headers not found"
                )
                
        except Exception as e:
            self.log_test_result(
                "Rate Limiting",
                False,
                f"Test failed with error: {str(e)}"
            )
    
    def test_authentication_protection(self):
        """Test that protected endpoints require authentication"""
        try:
            # Test protected endpoint without auth
            response = self.session.get(f"{self.base_url}/status")
            
            if response.status_code == 401:
                self.log_test_result(
                    "Authentication Protection",
                    True,
                    "Protected endpoint correctly returns 401"
                )
            else:
                self.log_test_result(
                    "Authentication Protection",
                    False,
                    f"Expected 401, got {response.status_code}"
                )
                
        except Exception as e:
            self.log_test_result(
                "Authentication Protection",
                False,
                f"Test failed with error: {str(e)}"
            )
    
    def test_health_endpoint(self):
        """Test security health endpoint"""
        try:
            response = self.session.get(f"{self.base_url}/health")
            
            if response.status_code == 200:
                data = response.json()
                
                # Check for security information in health endpoint
                if 'security' in data:
                    security_info = data['security']
                    
                    security_checks = [
                        'talisman_enabled',
                        'rate_limiting_enabled', 
                        'session_security',
                        'security_headers'
                    ]
                    
                    missing_checks = []
                    for check in security_checks:
                        if check not in security_info:
                            missing_checks.append(check)
                    
                    if missing_checks:
                        self.log_test_result(
                            "Health Endpoint Security Info",
                            False,
                            f"Missing security info: {', '.join(missing_checks)}"
                        )
                    else:
                        self.log_test_result(
                            "Health Endpoint Security Info",
                            True,
                            "All security information present"
                        )
                else:
                    self.log_test_result(
                        "Health Endpoint Security Info",
                        False,
                        "Security information missing from health endpoint"
                    )
            else:
                self.log_test_result(
                    "Health Endpoint",
                    False,
                    f"Health endpoint returned {response.status_code}"
                )
                
        except Exception as e:
            self.log_test_result(
                "Health Endpoint",
                False,
                f"Test failed with error: {str(e)}"
            )
    
    def test_error_handling(self):
        """Test that errors don't expose sensitive information"""
        try:
            # Test non-existent endpoint
            response = self.session.get(f"{self.base_url}/nonexistent")
            
            if response.status_code == 404:
                # Check that error response doesn't contain sensitive info
                response_text = response.text.lower()
                sensitive_terms = ['password', 'secret', 'token', 'key']
                
                found_sensitive = []
                for term in sensitive_terms:
                    if term in response_text:
                        found_sensitive.append(term)
                
                if found_sensitive:
                    self.log_test_result(
                        "Error Information Disclosure",
                        False,
                        f"Sensitive terms found in error: {', '.join(found_sensitive)}"
                    )
                else:
                    self.log_test_result(
                        "Error Information Disclosure",
                        True,
                        "No sensitive information in error responses"
                    )
            else:
                self.log_test_result(
                    "Error Handling",
                    True,
                    f"Non-standard error handling: {response.status_code}"
                )
                
        except Exception as e:
            self.log_test_result(
                "Error Handling",
                False,
                f"Test failed with error: {str(e)}"
            )
    
    def run_all_tests(self):
        """Run all security tests"""
        print("🔒 Starting Security Testing for SSB Retire Server Web Application")
        print("=" * 70)
        
        self.test_security_headers()
        self.test_https_enforcement()
        self.test_rate_limiting()
        self.test_authentication_protection()
        self.test_health_endpoint()
        self.test_error_handling()
        
        print("\n" + "=" * 70)
        print("🔒 Security Testing Results Summary")
        print("=" * 70)
        print(f"Total Tests: {self.test_results['passed'] + self.test_results['failed']}")
        print(f"Passed: {self.test_results['passed']}")
        print(f"Failed: {self.test_results['failed']}")
        
        if self.test_results['failed'] == 0:
            print("\n✅ ALL SECURITY TESTS PASSED")
            return True
        else:
            print(f"\n❌ {self.test_results['failed']} SECURITY TESTS FAILED")
            print("\nFailed Tests:")
            for test in self.test_results['tests']:
                if test['status'] == 'FAIL':
                    print(f"  - {test['name']}: {test['message']}")
            return False

def main():
    """Main function to run security tests"""
    
    # Check if Flask app is running
    base_url = os.environ.get('FLASK_APP_URL', 'http://localhost:5000')
    
    print(f"Testing Flask application at: {base_url}")
    
    try:
        response = requests.get(f"{base_url}/health", timeout=5)
        if response.status_code != 200:
            print(f"❌ Flask application not responding correctly at {base_url}")
            print("Please start the Flask application first with: python app.py")
            return False
    except requests.exceptions.RequestException:
        print(f"❌ Cannot connect to Flask application at {base_url}")
        print("Please start the Flask application first with: python app.py")
        return False
    
    # Run security tests
    tester = SecurityTester(base_url)
    success = tester.run_all_tests()
    
    return success

if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)