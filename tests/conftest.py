"""
Pytest configuration and fixtures for SSB Retire Server Web Application testing.
"""

import os
import pytest
import tempfile
from unittest.mock import patch, MagicMock

# Set test environment variables before importing app
os.environ.update({
    'AAP_URL': 'https://mock-aap.local',
    'AAP_TOKEN': 'mock-token-12345',
    'AAP_TEMPLATE_ID': '66',
    'BASIC_AUTH_USERNAME': 'test-user',
    'BASIC_AUTH_PASSWORD': 'test-password',
    'FLASK_ENV': 'testing'
})

# Import app after setting environment variables
import app as flask_app


@pytest.fixture
def app():
    """Create Flask application for testing."""
    
    # Configure app for testing
    flask_app.app.config.update({
        'TESTING': True,
        'WTF_CSRF_ENABLED': False,
        'SECRET_KEY': 'test-secret-key'
    })
    
    return flask_app.app


@pytest.fixture
def client(app):
    """Create test client for Flask application."""
    return app.test_client()


@pytest.fixture
def authenticated_client(client):
    """Create authenticated test client with basic auth."""
    import base64
    
    credentials = base64.b64encode(b'test-user:test-password').decode('utf-8')
    client.environ_base['HTTP_AUTHORIZATION'] = f'Basic {credentials}'
    
    return client


@pytest.fixture
def mock_aap_api():
    """Mock AAP API responses for testing."""
    
    mock_responses = {
        'test_connection': {
            'status': 'success',
            'message': 'AAP connection successful'
        },
        'launch_job': {
            'job': 12345,
            'status': 'pending',
            'url': 'https://mock-aap.local/api/v2/jobs/12345/'
        },
        'job_templates': {
            'results': [{
                'id': 66,
                'name': 'Server Retirement Job Template',
                'description': 'Template for server retirement automation'
            }]
        }
    }
    
    with patch('requests.post') as mock_post, \
         patch('requests.get') as mock_get:
        
        # Configure mock responses based on URL patterns
        def mock_post_side_effect(url, **kwargs):
            mock_response = MagicMock()
            mock_response.status_code = 200
            
            if 'job_templates' in url and 'launch' in url:
                mock_response.json.return_value = mock_responses['launch_job']
            else:
                mock_response.json.return_value = {'error': 'Unknown endpoint'}
                mock_response.status_code = 404
            
            return mock_response
        
        def mock_get_side_effect(url, **kwargs):
            mock_response = MagicMock()
            mock_response.status_code = 200
            
            if 'job_templates' in url:
                mock_response.json.return_value = mock_responses['job_templates']
            else:
                mock_response.json.return_value = mock_responses['test_connection']
            
            return mock_response
        
        mock_post.side_effect = mock_post_side_effect
        mock_get.side_effect = mock_get_side_effect
        
        yield {
            'mock_post': mock_post,
            'mock_get': mock_get,
            'responses': mock_responses
        }


@pytest.fixture
def sample_retirement_data():
    """Sample retirement request data for testing."""
    return {
        'hostnames': 'test-vm-01,test-vm-02,test-vm-03',
        'shutdown_date': '2025-07-10',
        'shutdown_time': '20:00',
        'retire_date': '2025-07-11',
        'retire_time': '22:00'
    }


@pytest.fixture
def invalid_retirement_data():
    """Invalid retirement request data for testing."""
    return {
        'hostnames': '',  # Empty hostnames
        'shutdown_date': '2025-07-10',
        'shutdown_time': '20:00',
        'retire_date': '2025-07-09',  # Retire date before shutdown date
        'retire_time': '22:00'
    }


@pytest.fixture
def temp_test_file():
    """Create temporary file for testing file operations."""
    
    with tempfile.NamedTemporaryFile(mode='w+', delete=False) as f:
        f.write('test content')
        temp_path = f.name
    
    yield temp_path
    
    # Cleanup
    try:
        os.unlink(temp_path)
    except FileNotFoundError:
        pass


@pytest.fixture
def mock_performance_metrics():
    """Mock performance metrics for testing."""
    
    return {
        'execution_time': 120.5,
        'api_calls': 8,
        'hosts_processed': 3,
        'success_rate': 100.0,
        'timestamp': '2025-07-04T12:00:00Z'
    }


@pytest.fixture
def mock_security_config():
    """Mock security configuration for testing."""
    
    return {
        'talisman_enabled': True,
        'rate_limiting_enabled': True,
        'session_security': True,
        'security_headers': True,
        'csrf_protection': True
    }


@pytest.fixture(autouse=True)
def clean_environment():
    """Clean environment variables after each test."""
    
    # Store original environment
    original_env = dict(os.environ)
    
    yield
    
    # Restore original environment
    os.environ.clear()
    os.environ.update(original_env)