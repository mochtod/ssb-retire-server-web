# Security Headers Middleware for SSB Retire Server Web Application
# Implements enterprise-grade security headers and protection

from flask import Flask, request, g
from typing import Dict
import logging

logger = logging.getLogger(__name__)

class SecurityHeadersMiddleware:
    """Middleware to add security headers to all responses"""
    
    def __init__(self, app: Flask = None, headers: Dict[str, str] = None):
        self.headers = headers or {}
        if app:
            self.init_app(app)
    
    def init_app(self, app: Flask):
        """Initialize security headers middleware with Flask app"""
        app.after_request(self.add_security_headers)
        
        # Add request security validation
        app.before_request(self.validate_request_security)
    
    def add_security_headers(self, response):
        """Add security headers to response"""
        for header, value in self.headers.items():
            response.headers[header] = value
        
        # Add security headers specific to enterprise environment
        if not response.headers.get('X-Content-Type-Options'):
            response.headers['X-Content-Type-Options'] = 'nosniff'
        
        if not response.headers.get('X-Frame-Options'):
            response.headers['X-Frame-Options'] = 'DENY'
        
        if not response.headers.get('X-XSS-Protection'):
            response.headers['X-XSS-Protection'] = '1; mode=block'
        
        # Enterprise-specific headers for internal network
        response.headers['X-Enterprise-App'] = 'SSB-Retire-Server'
        response.headers['X-Security-Level'] = 'Enterprise'
        
        return response
    
    def validate_request_security(self):
        """Validate request for security compliance"""
        # Log security-relevant request information (without sensitive data)
        if request.endpoint:
            logger.info(f"Request to {request.endpoint} from {request.remote_addr}")
        
        # Enterprise network validation (internal use only)
        if request.headers.get('X-Forwarded-Proto') == 'http' and request.endpoint != 'health':
            # Log HTTP access attempt for security monitoring
            logger.warning(f"HTTP request attempted to {request.endpoint} from {request.remote_addr}")
        
        # Track authentication attempts for monitoring
        if hasattr(g, 'auth_attempted'):
            g.auth_attempted = True

def create_security_middleware(security_config) -> SecurityHeadersMiddleware:
    """Factory function to create security middleware with configuration"""
    return SecurityHeadersMiddleware(headers=security_config.secure_headers)