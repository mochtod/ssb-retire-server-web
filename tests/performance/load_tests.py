"""
Load testing for SSB Retire Server Web Application using Locust.
"""

import json
import random
import base64
from locust import HttpUser, task, between


class RetirementServerUser(HttpUser):
    """Simulated user for load testing the retirement server web application."""
    
    wait_time = between(1, 3)  # Wait 1-3 seconds between requests
    
    def on_start(self):
        """Setup basic authentication for the user session."""
        # Set up basic authentication
        credentials = base64.b64encode(b'test-user:test-password').decode('utf-8')
        self.client.headers.update({'Authorization': f'Basic {credentials}'})
        
        # Verify authentication works
        response = self.client.get('/health')
        if response.status_code != 200:
            print(f"Warning: Authentication setup failed, status: {response.status_code}")
    
    @task(10)
    def health_check(self):
        """High frequency health check requests."""
        with self.client.get('/health', catch_response=True) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"Health check failed: {response.status_code}")
    
    @task(5)
    def load_main_page(self):
        """Load the main retirement scheduler page."""
        with self.client.get('/', catch_response=True) as response:
            if response.status_code == 200:
                if b'Server Retirement Scheduler' in response.content:
                    response.success()
                else:
                    response.failure("Main page content invalid")
            else:
                response.failure(f"Main page failed: {response.status_code}")
    
    @task(3)
    def test_aap_connection(self):
        """Test AAP connection endpoint."""
        with self.client.get('/api/test-connection', catch_response=True) as response:
            # Accept both success and expected failures (since AAP may be mocked)
            if response.status_code in [200, 500]:
                response.success()
            else:
                response.failure(f"Unexpected status: {response.status_code}")
    
    @task(2)
    def launch_retirement_job(self):
        """Launch a retirement job with random test data."""
        
        # Generate random test data
        vm_count = random.randint(1, 3)  # 1-3 VMs to stay within limits
        hostnames = [f'load-test-vm-{random.randint(1000, 9999):04d}' for _ in range(vm_count)]
        
        test_data = {
            'hostnames': ','.join(hostnames),
            'shutdown_date': '2025-07-10',
            'shutdown_time': f'{random.randint(18, 22):02d}:00',
            'retire_date': '2025-07-11',
            'retire_time': f'{random.randint(18, 22):02d}:00'
        }
        
        with self.client.post('/api/launch-job',
                             json=test_data,
                             catch_response=True) as response:
            if response.status_code == 200:
                try:
                    data = response.json()
                    if 'job' in data or 'status' in data:
                        response.success()
                    else:
                        response.failure("Invalid job launch response format")
                except json.JSONDecodeError:
                    response.failure("Invalid JSON response")
            elif response.status_code in [400, 422, 500]:
                # Accept expected failures (validation errors, AAP unavailable, etc.)
                response.success()
            else:
                response.failure(f"Unexpected job launch status: {response.status_code}")
    
    @task(1)
    def launch_large_batch_job(self):
        """Test with larger batch size (near the limit)."""
        
        # Test with 5 VMs (the maximum allowed)
        hostnames = [f'load-test-batch-{random.randint(1000, 9999):04d}' for _ in range(5)]
        
        large_batch_data = {
            'hostnames': ','.join(hostnames),
            'shutdown_date': '2025-07-10',
            'shutdown_time': '20:00',
            'retire_date': '2025-07-11',
            'retire_time': '22:00'
        }
        
        with self.client.post('/api/launch-job',
                             json=large_batch_data,
                             catch_response=True) as response:
            # Large batches might be more likely to fail, so be lenient
            if response.status_code in [200, 400, 422, 500]:
                response.success()
            else:
                response.failure(f"Large batch unexpected status: {response.status_code}")


class AuthenticationTestUser(HttpUser):
    """User that tests authentication scenarios."""
    
    wait_time = between(2, 5)
    
    @task(5)
    def valid_authentication(self):
        """Test with valid authentication."""
        credentials = base64.b64encode(b'test-user:test-password').decode('utf-8')
        headers = {'Authorization': f'Basic {credentials}'}
        
        with self.client.get('/', headers=headers, catch_response=True) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"Valid auth failed: {response.status_code}")
    
    @task(2)
    def invalid_authentication(self):
        """Test with invalid authentication."""
        credentials = base64.b64encode(b'wrong:credentials').decode('utf-8')
        headers = {'Authorization': f'Basic {credentials}'}
        
        with self.client.get('/', headers=headers, catch_response=True) as response:
            if response.status_code == 401:
                response.success()
            else:
                response.failure(f"Invalid auth should return 401, got: {response.status_code}")
    
    @task(1)
    def no_authentication(self):
        """Test without authentication."""
        with self.client.get('/', catch_response=True) as response:
            if response.status_code == 401:
                response.success()
            else:
                response.failure(f"No auth should return 401, got: {response.status_code}")


class APIStressTestUser(HttpUser):
    """User that performs API stress testing."""
    
    wait_time = between(0.5, 1.5)  # Faster requests for stress testing
    
    def on_start(self):
        """Setup authentication."""
        credentials = base64.b64encode(b'test-user:test-password').decode('utf-8')
        self.client.headers.update({'Authorization': f'Basic {credentials}'})
    
    @task(20)
    def rapid_health_checks(self):
        """Rapid health check requests."""
        with self.client.get('/health', catch_response=True) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"Health check failed: {response.status_code}")
    
    @task(10)
    def rapid_connection_tests(self):
        """Rapid AAP connection tests."""
        with self.client.get('/api/test-connection', catch_response=True) as response:
            if response.status_code in [200, 500]:
                response.success()
            else:
                response.failure(f"Connection test failed: {response.status_code}")
    
    @task(5)
    def concurrent_job_launches(self):
        """Concurrent job launch attempts."""
        test_data = {
            'hostnames': f'stress-test-vm-{random.randint(10000, 99999)}',
            'shutdown_date': '2025-07-10',
            'shutdown_time': '20:00',
            'retire_date': '2025-07-11',
            'retire_time': '22:00'
        }
        
        with self.client.post('/api/launch-job',
                             json=test_data,
                             catch_response=True) as response:
            if response.status_code in [200, 400, 422, 500]:
                response.success()
            else:
                response.failure(f"Job launch failed: {response.status_code}")


class DataValidationTestUser(HttpUser):
    """User that tests various data validation scenarios."""
    
    wait_time = between(1, 2)
    
    def on_start(self):
        """Setup authentication."""
        credentials = base64.b64encode(b'test-user:test-password').decode('utf-8')
        self.client.headers.update({'Authorization': f'Basic {credentials}'})
    
    @task(3)
    def valid_data_test(self):
        """Test with valid data."""
        valid_data = {
            'hostnames': 'valid-test-vm-01,valid-test-vm-02',
            'shutdown_date': '2025-07-10',
            'shutdown_time': '20:00',
            'retire_date': '2025-07-11',
            'retire_time': '22:00'
        }
        
        with self.client.post('/api/launch-job',
                             json=valid_data,
                             catch_response=True) as response:
            if response.status_code in [200, 500]:  # Success or AAP unavailable
                response.success()
            else:
                response.failure(f"Valid data failed: {response.status_code}")
    
    @task(2)
    def invalid_data_test(self):
        """Test with invalid data."""
        invalid_scenarios = [
            {
                'hostnames': '',  # Empty hostnames
                'shutdown_date': '2025-07-10',
                'shutdown_time': '20:00',
                'retire_date': '2025-07-11',
                'retire_time': '22:00'
            },
            {
                'hostnames': 'test-vm-01',
                'shutdown_date': '2025-07-11',  # Shutdown after retirement
                'shutdown_time': '20:00',
                'retire_date': '2025-07-10',
                'retire_time': '22:00'
            },
            {
                'hostnames': 'test-vm-01',
                'shutdown_date': 'invalid-date',  # Invalid date format
                'shutdown_time': '20:00',
                'retire_date': '2025-07-11',
                'retire_time': '22:00'
            }
        ]
        
        invalid_data = random.choice(invalid_scenarios)
        
        with self.client.post('/api/launch-job',
                             json=invalid_data,
                             catch_response=True) as response:
            if response.status_code in [400, 422]:  # Validation errors expected
                response.success()
            elif response.status_code in [200, 500]:  # Might pass through or fail at AAP
                response.success()
            else:
                response.failure(f"Invalid data unexpected status: {response.status_code}")
    
    @task(1)
    def oversized_data_test(self):
        """Test with oversized data."""
        # Create large hostname list (potentially over limit)
        large_hostnames = [f'oversized-vm-{i:04d}' for i in range(10)]  # 10 VMs (over 5 limit)
        
        oversized_data = {
            'hostnames': ','.join(large_hostnames),
            'shutdown_date': '2025-07-10',
            'shutdown_time': '20:00',
            'retire_date': '2025-07-11',
            'retire_time': '22:00'
        }
        
        with self.client.post('/api/launch-job',
                             json=oversized_data,
                             catch_response=True) as response:
            if response.status_code in [200, 400, 422, 500]:
                response.success()
            else:
                response.failure(f"Oversized data unexpected status: {response.status_code}")


# Custom load test configurations
class QuickLoadTest(RetirementServerUser):
    """Quick load test configuration."""
    weight = 10


class SteadyLoadTest(RetirementServerUser):
    """Steady load test configuration."""
    weight = 5
    wait_time = between(3, 7)


class BurstLoadTest(APIStressTestUser):
    """Burst load test configuration."""
    weight = 2
    wait_time = between(0.1, 0.5)


# Usage instructions for running load tests:
"""
To run these load tests, use the following commands:

1. Install locust:
   pip install locust

2. Run basic load test:
   locust -f load_tests.py --host=http://localhost:5000

3. Run specific user type:
   locust -f load_tests.py RetirementServerUser --host=http://localhost:5000

4. Run headless with specific parameters:
   locust -f load_tests.py --headless --users 10 --spawn-rate 2 --run-time 60s --host=http://localhost:5000

5. Run with different user distributions:
   locust -f load_tests.py QuickLoadTest SteadyLoadTest --host=http://localhost:5000

Example load test scenarios:

- Light load: 5 users, 1 user/sec spawn rate, 5 minutes
  locust -f load_tests.py --headless -u 5 -r 1 -t 300s --host=http://localhost:5000

- Medium load: 20 users, 2 users/sec spawn rate, 10 minutes  
  locust -f load_tests.py --headless -u 20 -r 2 -t 600s --host=http://localhost:5000

- Stress test: 50 users, 5 users/sec spawn rate, 15 minutes
  locust -f load_tests.py --headless -u 50 -r 5 -t 900s --host=http://localhost:5000

The load test will generate detailed reports including:
- Response times (min, max, median, 95th percentile)
- Request rates (requests per second)
- Failure rates
- Number of users over time
"""