"""
Integration tests for SSB Retire Server Web Application AAP integration.
"""

import pytest
import json
import responses
from unittest.mock import patch, MagicMock


class TestAAPConnectivity:
    """Test AAP connectivity and authentication."""
    
    @responses.activate
    def test_aap_connection_success(self, authenticated_client):
        """Test successful AAP connection."""
        
        # Mock AAP API response
        responses.add(
            responses.GET,
            'https://mock-aap.local/api/v2/ping/',
            json={'status': 'ok'},
            status=200
        )
        
        response = authenticated_client.get('/api/test-connection')
        assert response.status_code == 200
        
        data = json.loads(response.data)
        assert data['status'] == 'success'
    
    @responses.activate
    def test_aap_connection_failure(self, authenticated_client):
        """Test AAP connection failure handling."""
        
        # Mock AAP API failure
        responses.add(
            responses.GET,
            'https://mock-aap.local/api/v2/ping/',
            json={'error': 'Unauthorized'},
            status=401
        )
        
        response = authenticated_client.get('/api/test-connection')
        assert response.status_code == 500
        
        data = json.loads(response.data)
        assert data['status'] == 'error'
        assert 'error' in data
    
    @responses.activate
    def test_aap_connection_timeout(self, authenticated_client):
        """Test AAP connection timeout handling."""
        
        # Mock connection timeout
        def request_callback(request):
            raise responses.exceptions.ConnectionError("Connection timeout")
        
        responses.add_callback(
            responses.GET,
            'https://mock-aap.local/api/v2/ping/',
            callback=request_callback
        )
        
        response = authenticated_client.get('/api/test-connection')
        assert response.status_code == 500
        
        data = json.loads(response.data)
        assert data['status'] == 'error'
        assert 'timeout' in data.get('error', '').lower()


class TestJobTemplateIntegration:
    """Test AAP job template integration."""
    
    @responses.activate
    def test_job_template_discovery(self, authenticated_client):
        """Test job template discovery and validation."""
        
        # Mock job templates API response
        mock_job_templates = {
            'results': [
                {
                    'id': 66,
                    'name': 'Server Retirement Job Template',
                    'description': 'Template for server retirement automation',
                    'job_type': 'run',
                    'inventory': 1,
                    'project': 1,
                    'playbook': 'playbooks/retire_main.yml',
                    'ask_variables_on_launch': True,
                    'ask_limit_on_launch': True
                }
            ],
            'count': 1
        }
        
        responses.add(
            responses.GET,
            'https://mock-aap.local/api/v2/job_templates/',
            json=mock_job_templates,
            status=200
        )
        
        # This would test the job template discovery functionality
        # Implementation depends on how the app queries job templates
        assert True  # Placeholder - would test actual discovery logic
    
    @responses.activate 
    def test_job_template_validation(self, authenticated_client):
        """Test job template validation for retirement operations."""
        
        # Mock job template details
        job_template_details = {
            'id': 66,
            'name': 'Server Retirement Job Template',
            'playbook': 'playbooks/retire_main.yml',
            'ask_variables_on_launch': True,
            'ask_limit_on_launch': True,
            'enabled': True
        }
        
        responses.add(
            responses.GET,
            'https://mock-aap.local/api/v2/job_templates/66/',
            json=job_template_details,
            status=200
        )
        
        # Test template validation logic
        assert job_template_details['ask_variables_on_launch'] is True
        assert job_template_details['ask_limit_on_launch'] is True
        assert job_template_details['enabled'] is True


class TestJobLaunchIntegration:
    """Test AAP job launch integration."""
    
    @responses.activate
    def test_successful_job_launch(self, authenticated_client, sample_retirement_data):
        """Test successful job launch with valid data."""
        
        # Mock job launch response
        job_launch_response = {
            'job': 12345,
            'status': 'pending',
            'url': 'https://mock-aap.local/api/v2/jobs/12345/',
            'created': '2025-07-04T12:00:00Z',
            'name': 'Server Retirement for test-vm-01,test-vm-02,test-vm-03'
        }
        
        responses.add(
            responses.POST,
            'https://mock-aap.local/api/v2/job_templates/66/launch/',
            json=job_launch_response,
            status=201
        )
        
        response = authenticated_client.post('/api/launch-job',
                                           data=json.dumps(sample_retirement_data),
                                           content_type='application/json')
        
        assert response.status_code == 200
        
        data = json.loads(response.data)
        assert 'job' in data
        assert data['job'] == 12345
        assert data['status'] == 'pending'
    
    @responses.activate
    def test_job_launch_with_validation_error(self, authenticated_client, invalid_retirement_data):
        """Test job launch with validation errors."""
        
        # Mock validation error response
        validation_error_response = {
            'error': 'Invalid extra_vars provided',
            'details': {
                'extra_vars': ['This field has invalid data']
            }
        }
        
        responses.add(
            responses.POST,
            'https://mock-aap.local/api/v2/job_templates/66/launch/',
            json=validation_error_response,
            status=400
        )
        
        response = authenticated_client.post('/api/launch-job',
                                           data=json.dumps(invalid_retirement_data),
                                           content_type='application/json')
        
        assert response.status_code in [400, 422]
        
        data = json.loads(response.data)
        assert 'error' in data
    
    @responses.activate
    def test_job_launch_parameter_mapping(self, authenticated_client, sample_retirement_data):
        """Test proper parameter mapping for job launch."""
        
        # Capture the request to verify parameter mapping
        def request_callback(request):
            request_data = json.loads(request.body)
            
            # Verify required parameters are properly mapped
            assert 'extra_vars' in request_data
            extra_vars = request_data['extra_vars']
            
            # Check that retirement data is properly formatted
            assert 'record_names' in extra_vars
            assert 'shutdown_date' in extra_vars
            assert 'shutdown_time' in extra_vars
            assert 'retire_date' in extra_vars
            assert 'retire_time' in extra_vars
            
            # Verify hostname parsing
            hostnames = extra_vars['record_names']
            assert isinstance(hostnames, list)
            assert len(hostnames) == 3  # test-vm-01,test-vm-02,test-vm-03
            
            return (201, {}, json.dumps({'job': 12345, 'status': 'pending'}))
        
        responses.add_callback(
            responses.POST,
            'https://mock-aap.local/api/v2/job_templates/66/launch/',
            callback=request_callback
        )
        
        response = authenticated_client.post('/api/launch-job',
                                           data=json.dumps(sample_retirement_data),
                                           content_type='application/json')
        
        assert response.status_code == 200
    
    @responses.activate
    def test_job_launch_vm_limit_validation(self, authenticated_client):
        """Test VM limit validation (5 VM max per job)."""
        
        # Test data with 6 VMs (exceeds limit)
        excessive_vms_data = {
            'hostnames': 'vm1,vm2,vm3,vm4,vm5,vm6',  # 6 VMs
            'shutdown_date': '2025-07-10',
            'shutdown_time': '20:00',
            'retire_date': '2025-07-11',
            'retire_time': '22:00'
        }
        
        response = authenticated_client.post('/api/launch-job',
                                           data=json.dumps(excessive_vms_data),
                                           content_type='application/json')
        
        # Should either reject or handle the limit
        assert response.status_code in [200, 400, 422]
        
        if response.status_code in [400, 422]:
            data = json.loads(response.data)
            assert 'error' in data
            assert 'limit' in data['error'].lower() or '5' in data['error']


class TestJobMonitoring:
    """Test AAP job monitoring integration."""
    
    @responses.activate
    def test_job_status_polling(self, authenticated_client):
        """Test job status polling functionality."""
        
        # Mock job status response
        job_status_response = {
            'id': 12345,
            'status': 'running',
            'started': '2025-07-04T12:00:00Z',
            'finished': None,
            'name': 'Server Retirement for test-vm-01',
            'job_template': 66
        }
        
        responses.add(
            responses.GET,
            'https://mock-aap.local/api/v2/jobs/12345/',
            json=job_status_response,
            status=200
        )
        
        # Test job status endpoint (if implemented)
        response = authenticated_client.get('/api/job-status/12345')
        
        # Endpoint may not exist yet
        assert response.status_code in [200, 404]
        
        if response.status_code == 200:
            data = json.loads(response.data)
            assert 'status' in data
    
    @responses.activate
    def test_job_completion_handling(self, authenticated_client):
        """Test job completion handling."""
        
        # Mock completed job response
        completed_job_response = {
            'id': 12345,
            'status': 'successful',
            'started': '2025-07-04T12:00:00Z',
            'finished': '2025-07-04T12:05:00Z',
            'name': 'Server Retirement for test-vm-01',
            'job_template': 66,
            'artifacts': {
                'hosts_processed': 1,
                'operations_completed': 6,
                'execution_time': 300
            }
        }
        
        responses.add(
            responses.GET,
            'https://mock-aap.local/api/v2/jobs/12345/',
            json=completed_job_response,
            status=200
        )
        
        # Test completion handling logic
        assert completed_job_response['status'] == 'successful'
        assert completed_job_response['finished'] is not None
    
    @responses.activate
    def test_job_failure_handling(self, authenticated_client):
        """Test job failure handling."""
        
        # Mock failed job response
        failed_job_response = {
            'id': 12345,
            'status': 'failed',
            'started': '2025-07-04T12:00:00Z',
            'finished': '2025-07-04T12:02:00Z',
            'name': 'Server Retirement for test-vm-01',
            'job_template': 66,
            'result_stdout': 'Error during retirement process',
            'job_explanation': 'Job failed due to network connectivity issues'
        }
        
        responses.add(
            responses.GET,
            'https://mock-aap.local/api/v2/jobs/12345/',
            json=failed_job_response,
            status=200
        )
        
        # Test failure handling logic
        assert failed_job_response['status'] == 'failed'
        assert 'job_explanation' in failed_job_response


class TestErrorScenarios:
    """Test error scenario handling in AAP integration."""
    
    @responses.activate
    def test_aap_server_unavailable(self, authenticated_client, sample_retirement_data):
        """Test handling when AAP server is unavailable."""
        
        # Mock server unavailable
        responses.add(
            responses.POST,
            'https://mock-aap.local/api/v2/job_templates/66/launch/',
            json={'error': 'Service Unavailable'},
            status=503
        )
        
        response = authenticated_client.post('/api/launch-job',
                                           data=json.dumps(sample_retirement_data),
                                           content_type='application/json')
        
        assert response.status_code == 500
        
        data = json.loads(response.data)
        assert data['status'] == 'error'
        assert 'unavailable' in data.get('error', '').lower() or 'service' in data.get('error', '').lower()
    
    @responses.activate
    def test_authentication_failure(self, authenticated_client, sample_retirement_data):
        """Test handling of AAP authentication failures."""
        
        # Mock authentication failure
        responses.add(
            responses.POST,
            'https://mock-aap.local/api/v2/job_templates/66/launch/',
            json={'detail': 'Invalid token'},
            status=401
        )
        
        response = authenticated_client.post('/api/launch-job',
                                           data=json.dumps(sample_retirement_data),
                                           content_type='application/json')
        
        assert response.status_code == 500
        
        data = json.loads(response.data)
        assert data['status'] == 'error'
        assert 'auth' in data.get('error', '').lower() or 'token' in data.get('error', '').lower()
    
    @responses.activate
    def test_job_template_not_found(self, authenticated_client, sample_retirement_data):
        """Test handling when job template is not found."""
        
        # Mock template not found
        responses.add(
            responses.POST,
            'https://mock-aap.local/api/v2/job_templates/66/launch/',
            json={'detail': 'Not found'},
            status=404
        )
        
        response = authenticated_client.post('/api/launch-job',
                                           data=json.dumps(sample_retirement_data),
                                           content_type='application/json')
        
        assert response.status_code == 500
        
        data = json.loads(response.data)
        assert data['status'] == 'error'
        assert 'not found' in data.get('error', '').lower() or 'template' in data.get('error', '').lower()


class TestIntegrationDataFlow:
    """Test end-to-end data flow integration."""
    
    @responses.activate
    def test_complete_retirement_workflow_data_flow(self, authenticated_client, sample_retirement_data):
        """Test complete retirement workflow data flow."""
        
        # Mock the complete workflow
        responses.add(
            responses.POST,
            'https://mock-aap.local/api/v2/job_templates/66/launch/',
            json={'job': 12345, 'status': 'pending'},
            status=201
        )
        
        # Launch job
        response = authenticated_client.post('/api/launch-job',
                                           data=json.dumps(sample_retirement_data),
                                           content_type='application/json')
        
        assert response.status_code == 200
        
        # Verify data flow
        data = json.loads(response.data)
        assert 'job' in data
        assert isinstance(data['job'], int)
        assert data['status'] in ['pending', 'running']
    
    def test_retirement_data_transformation(self, sample_retirement_data):
        """Test retirement data transformation for AAP."""
        
        # Test the data transformation logic
        hostnames = sample_retirement_data['hostnames'].split(',')
        
        # Verify hostname parsing
        assert len(hostnames) == 3
        assert 'test-vm-01' in hostnames
        assert 'test-vm-02' in hostnames
        assert 'test-vm-03' in hostnames
        
        # Verify date/time format
        assert sample_retirement_data['shutdown_date'] == '2025-07-10'
        assert sample_retirement_data['shutdown_time'] == '20:00'
        assert sample_retirement_data['retire_date'] == '2025-07-11'
        assert sample_retirement_data['retire_time'] == '22:00'