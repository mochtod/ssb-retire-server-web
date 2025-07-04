# Security Configuration for SSB Retire Server Web Application
# Enterprise Flask Security Hardening Implementation

import os
from dataclasses import dataclass
from typing import Dict, List, Optional

@dataclass 
class SecurityConfig:
    """Enterprise security configuration for Flask application"""
    
    # Secret Server Integration (DO NOT MODIFY - Production Specific)
    secret_server_ids: Dict[str, str]
    
    # Security Headers
    secure_headers: Dict[str, str]
    
    # Session Security
    session_config: Dict[str, any]
    
    # CSRF Protection
    csrf_protection: bool
    
    # Content Security Policy
    csp_policy: Dict[str, str]
    
    @classmethod
    def from_environment(cls) -> 'SecurityConfig':
        """Load security configuration from environment variables"""
        
        # Determine if we're in production mode
        is_production = os.environ.get('FLASK_ENV', 'development') == 'production'
        
        return cls(
            secret_server_ids={
                'vcenter': '89817', 
                'netbox': '91797'
            },
            secure_headers={
                'X-Content-Type-Options': 'nosniff',
                'X-Frame-Options': 'DENY', 
                'X-XSS-Protection': '1; mode=block',
                'Referrer-Policy': 'strict-origin-when-cross-origin',
                'X-Robots-Tag': 'noindex, nofollow',
                'Cache-Control': 'no-cache, no-store, must-revalidate',
                'Pragma': 'no-cache',
                'Expires': '0'
            },
            session_config={
                'SESSION_COOKIE_SECURE': is_production,  # Only HTTPS in production
                'SESSION_COOKIE_HTTPONLY': True,
                'SESSION_COOKIE_SAMESITE': 'Lax',
                'SESSION_COOKIE_NAME': 'ssb_retire_session',
                'PERMANENT_SESSION_LIFETIME': 3600,  # 1 hour
                'SESSION_REFRESH_EACH_REQUEST': True
            },
            csrf_protection=True,
            csp_policy={
                'default-src': "'self'",
                'script-src': "'self' 'unsafe-inline' cdn.jsdelivr.net",
                'style-src': "'self' 'unsafe-inline' cdn.jsdelivr.net fonts.googleapis.com",
                'font-src': "'self' fonts.gstatic.com cdn.jsdelivr.net",
                'img-src': "'self' data:",
                'connect-src': "'self'",
                'frame-ancestors': "'none'",
                'base-uri': "'self'",
                'form-action': "'self'"
            }
        )

    def get_talisman_config(self) -> Dict:
        """Get Flask-Talisman configuration"""
        return {
            'force_https': os.environ.get('FLASK_ENV') == 'production',
            'strict_transport_security': True,
            'strict_transport_security_max_age': 31536000,  # 1 year
            'content_security_policy': self.csp_policy,
            'content_security_policy_nonce_in': ['script-src', 'style-src'],
            'referrer_policy': 'strict-origin-when-cross-origin',
            'feature_policy': {
                'geolocation': "'none'",
                'microphone': "'none'",
                'camera': "'none'"
            }
        }

# Rate limiting configuration
RATE_LIMIT_CONFIG = {
    'RATELIMIT_STORAGE_URL': 'memory://',
    'RATELIMIT_DEFAULT': '200 per day, 50 per hour',
    'RATELIMIT_HEADERS_ENABLED': True
}

# Enterprise security validation
def validate_security_config():
    """Validate security configuration for enterprise deployment"""
    errors = []
    
    # Check for production security requirements
    if os.environ.get('FLASK_ENV') == 'production':
        if not os.environ.get('SECRET_KEY'):
            errors.append("SECRET_KEY must be set in production")
        if not os.environ.get('AAP_TOKEN'):
            errors.append("AAP_TOKEN must be set in production") 
        if os.environ.get('BASIC_AUTH_PASSWORD') == 'password':
            errors.append("Default password must be changed in production")
    
    return errors