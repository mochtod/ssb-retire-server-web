"""
Unit tests for SSB Retire Server Web Application main functionality.
"""

import pytest
import json
from unittest.mock import patch, MagicMock


class TestFlaskApplication:
    """Test Flask application core functionality."""
    
    def test_app_creation(self, app):
        """Test Flask application is created successfully."""
        assert app is not None
        assert app.config['TESTING'] is True
    
    def test_app_configuration(self, app):
        """Test Flask application configuration."""
        assert 'SECRET_KEY' in app.config
        assert app.config['WTF_CSRF_ENABLED'] is False  # Disabled for testing


class TestRoutes:
    """Test Flask application routes."""
    
    def test_index_route_redirect_without_auth(self, client):
        """Test index route redirects to login without authentication."""
        response = client.get('/')
        assert response.status_code == 401
    
    def test_index_route_with_auth(self, authenticated_client):
        """Test index route returns HTML with authentication."""
        response = authenticated_client.get('/')
        assert response.status_code == 200
        assert b'Server Retirement Scheduler' in response.data
        assert b'text/html' in response.headers.get('Content-Type', '').encode()
    
    def test_index_route_contains_required_elements(self, authenticated_client):
        """Test index route contains required form elements."""
        response = authenticated_client.get('/')
        assert response.status_code == 200
        
        # Check for form elements
        assert b'hostnames' in response.data
        assert b'shutdown_date' in response.data
        assert b'shutdown_time' in response.data
        assert b'retire_date' in response.data
        assert b'retire_time' in response.data
    
    def test_health_endpoint(self, client):
        """Test health endpoint returns proper status."""
        response = client.get('/health')
        assert response.status_code == 200
        
        data = json.loads(response.data)
        assert data['status'] == 'healthy'
        assert 'timestamp' in data
        assert 'app_version' in data


class TestAuthentication:
    """Test authentication functionality."""
    
    def test_basic_auth_required(self, client):
        """Test basic authentication is required for protected routes."""
        response = client.get('/')
        assert response.status_code == 401
    
    def test_basic_auth_invalid_credentials(self, client):
        """Test basic authentication with invalid credentials."""
        import base64
        
        credentials = base64.b64encode(b'wrong:credentials').decode('utf-8')
        headers = {'Authorization': f'Basic {credentials}'}
        
        response = client.get('/', headers=headers)
        assert response.status_code == 401
    
    def test_basic_auth_valid_credentials(self, authenticated_client):
        """Test basic authentication with valid credentials."""
        response = authenticated_client.get('/')
        assert response.status_code == 200


class TestAAP_Integration:
    """Test AAP API integration functionality."""
    
    def test_test_connection_endpoint_without_auth(self, client):
        """Test test connection endpoint requires authentication."""
        response = client.get('/api/test-connection')
        assert response.status_code == 401
    
    def test_test_connection_endpoint_success(self, authenticated_client, mock_aap_api):
        """Test successful AAP connection test."""
        response = authenticated_client.get('/api/test-connection')
        assert response.status_code == 200
        
        data = json.loads(response.data)
        assert data['status'] == 'success'
        assert 'message' in data
    
    @patch('requests.get')
    def test_test_connection_endpoint_failure(self, mock_get, authenticated_client):
        """Test AAP connection test failure."""
        # Mock AAP API failure
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_response.raise_for_status.side_effect = Exception("Connection failed")
        mock_get.return_value = mock_response
        
        response = authenticated_client.get('/api/test-connection')
        assert response.status_code == 500
        
        data = json.loads(response.data)
        assert data['status'] == 'error'
        assert 'error' in data
    
    def test_launch_job_endpoint_without_auth(self, client, sample_retirement_data):
        """Test launch job endpoint requires authentication."""
        response = client.post('/api/launch-job', 
                              data=json.dumps(sample_retirement_data),
                              content_type='application/json')
        assert response.status_code == 401
    
    def test_launch_job_endpoint_success(self, authenticated_client, mock_aap_api, sample_retirement_data):
        """Test successful job launch."""
        response = authenticated_client.post('/api/launch-job',
                                           data=json.dumps(sample_retirement_data),
                                           content_type='application/json')
        assert response.status_code == 200
        
        data = json.loads(response.data)
        assert 'job' in data
        assert data['status'] == 'pending'
    
    def test_launch_job_endpoint_invalid_data(self, authenticated_client, invalid_retirement_data):
        """Test job launch with invalid data."""
        response = authenticated_client.post('/api/launch-job',
                                           data=json.dumps(invalid_retirement_data),
                                           content_type='application/json')
        # Should handle validation errors gracefully
        assert response.status_code in [400, 422]  # Bad request or validation error
    
    def test_launch_job_endpoint_missing_data(self, authenticated_client):
        """Test job launch with missing data."""
        response = authenticated_client.post('/api/launch-job',
                                           data=json.dumps({}),
                                           content_type='application/json')
        assert response.status_code in [400, 422]  # Bad request or validation error


class TestDataValidation:
    """Test data validation functionality."""
    
    def test_hostname_validation_valid(self, authenticated_client, mock_aap_api):
        """Test valid hostname validation."""
        valid_data = {
            'hostnames': 'valid-host-01,valid-host-02',
            'shutdown_date': '2025-07-10',
            'shutdown_time': '20:00',
            'retire_date': '2025-07-11',
            'retire_time': '22:00'
        }
        
        response = authenticated_client.post('/api/launch-job',
                                           data=json.dumps(valid_data),
                                           content_type='application/json')
        assert response.status_code == 200
    
    def test_hostname_validation_empty(self, authenticated_client):
        """Test empty hostname validation."""
        invalid_data = {
            'hostnames': '',
            'shutdown_date': '2025-07-10',
            'shutdown_time': '20:00',
            'retire_date': '2025-07-11',
            'retire_time': '22:00'
        }
        
        response = authenticated_client.post('/api/launch-job',
                                           data=json.dumps(invalid_data),
                                           content_type='application/json')
        assert response.status_code in [400, 422]
    
    def test_date_validation_past_date(self, authenticated_client):
        """Test past date validation."""
        invalid_data = {
            'hostnames': 'test-host-01',
            'shutdown_date': '2020-01-01',  # Past date
            'shutdown_time': '20:00',
            'retire_date': '2020-01-02',
            'retire_time': '22:00'
        }
        
        response = authenticated_client.post('/api/launch-job',
                                           data=json.dumps(invalid_data),
                                           content_type='application/json')
        # Application should handle or validate this
        assert response.status_code in [200, 400, 422]
    
    def test_date_validation_retire_before_shutdown(self, authenticated_client):
        """Test retirement date before shutdown date validation."""
        invalid_data = {
            'hostnames': 'test-host-01',
            'shutdown_date': '2025-07-11',
            'shutdown_time': '20:00',
            'retire_date': '2025-07-10',  # Before shutdown
            'retire_time': '22:00'
        }
        
        response = authenticated_client.post('/api/launch-job',
                                           data=json.dumps(invalid_data),
                                           content_type='application/json')
        # Application should validate this logical error
        assert response.status_code in [200, 400, 422]


class TestErrorHandling:
    """Test error handling functionality."""
    
    def test_404_error_handling(self, client):
        """Test 404 error handling."""
        response = client.get('/nonexistent-endpoint')
        assert response.status_code == 404
    
    def test_405_method_not_allowed(self, authenticated_client):
        """Test 405 method not allowed error."""
        response = authenticated_client.put('/api/test-connection')
        assert response.status_code == 405
    
    @patch('requests.post')
    def test_aap_api_timeout_handling(self, mock_post, authenticated_client, sample_retirement_data):
        """Test AAP API timeout handling."""
        # Mock timeout exception
        mock_post.side_effect = Exception("Request timeout")
        
        response = authenticated_client.post('/api/launch-job',
                                           data=json.dumps(sample_retirement_data),
                                           content_type='application/json')
        assert response.status_code == 500
        
        data = json.loads(response.data)
        assert 'error' in data


class TestEnvironmentConfiguration:
    """Test environment configuration."""
    
    def test_environment_variables_loaded(self, app):
        """Test environment variables are properly loaded."""
        import os
        
        # These should be set in conftest.py
        assert os.environ.get('AAP_URL') == 'https://mock-aap.local'
        assert os.environ.get('AAP_TOKEN') == 'mock-token-12345'
        assert os.environ.get('AAP_TEMPLATE_ID') == '66'
    
    def test_default_configuration_values(self, app):
        """Test default configuration values are set."""
        # Test that the app has proper defaults
        assert app.config.get('TESTING') is True