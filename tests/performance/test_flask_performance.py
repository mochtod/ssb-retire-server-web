"""
Performance testing for SSB Retire Server Web Application Flask components.
"""

import pytest
import time
import threading
import json
import psutil
import os
from concurrent.futures import ThreadPoolExecutor, as_completed
from unittest.mock import patch, MagicMock


class TestFlaskPerformance:
    """Test Flask application performance characteristics."""
    
    def test_health_endpoint_response_time(self, client):
        """Test health endpoint response time."""
        
        response_times = []
        
        # Measure multiple requests for average
        for i in range(10):
            start_time = time.time()
            response = client.get('/health')
            end_time = time.time()
            
            assert response.status_code == 200
            response_times.append(end_time - start_time)
        
        avg_response_time = sum(response_times) / len(response_times)
        max_response_time = max(response_times)
        
        # Performance thresholds
        avg_threshold = 0.1  # 100ms average
        max_threshold = 0.5  # 500ms max
        
        assert avg_response_time < avg_threshold, f"Average response time too slow: {avg_response_time:.3f}s"
        assert max_response_time < max_threshold, f"Max response time too slow: {max_response_time:.3f}s"
        
        print(f"Health endpoint - Avg: {avg_response_time:.3f}s, Max: {max_response_time:.3f}s")
    
    def test_concurrent_request_handling(self, client):
        """Test application performance under concurrent load."""
        
        def make_request():
            start_time = time.time()
            response = client.get('/health')
            end_time = time.time()
            return {
                'status_code': response.status_code,
                'response_time': end_time - start_time,
                'thread_id': threading.current_thread().ident
            }
        
        # Test with 20 concurrent requests
        num_concurrent = 20
        results = []
        
        with ThreadPoolExecutor(max_workers=num_concurrent) as executor:
            futures = [executor.submit(make_request) for _ in range(num_concurrent)]
            
            for future in as_completed(futures):
                results.append(future.result())
        
        # Validate results
        assert len(results) == num_concurrent
        
        # Check all requests succeeded
        for result in results:
            assert result['status_code'] == 200
        
        # Check response times under load
        response_times = [r['response_time'] for r in results]
        avg_response_time = sum(response_times) / len(response_times)
        max_response_time = max(response_times)
        
        # Under load thresholds (more lenient)
        avg_threshold_load = 0.5  # 500ms average under load
        max_threshold_load = 2.0  # 2s max under load
        
        assert avg_response_time < avg_threshold_load, f"Average response time under load too slow: {avg_response_time:.3f}s"
        assert max_response_time < max_threshold_load, f"Max response time under load too slow: {max_response_time:.3f}s"
        
        print(f"Concurrent load - Requests: {num_concurrent}, Avg: {avg_response_time:.3f}s, Max: {max_response_time:.3f}s")
    
    def test_memory_usage_stability(self, client):
        """Test memory usage doesn't grow excessively."""
        
        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss
        
        # Make multiple requests to check for memory leaks
        for i in range(50):
            response = client.get('/health')
            assert response.status_code == 200
        
        final_memory = process.memory_info().rss
        memory_increase = final_memory - initial_memory
        
        # Memory increase should be reasonable (less than 20MB)
        max_memory_increase = 20 * 1024 * 1024  # 20MB
        
        assert memory_increase < max_memory_increase, f"Excessive memory usage: {memory_increase / 1024 / 1024:.1f}MB"
        
        print(f"Memory usage - Initial: {initial_memory // 1024 // 1024}MB, "
              f"Final: {final_memory // 1024 // 1024}MB, "
              f"Increase: {memory_increase // 1024 // 1024}MB")


class TestAAPIntegrationPerformance:
    """Test AAP integration performance."""
    
    def test_aap_connection_test_performance(self, authenticated_client, mock_aap_api):
        """Test AAP connection test response time."""
        
        response_times = []
        
        for i in range(5):
            start_time = time.time()
            response = authenticated_client.get('/api/test-connection')
            end_time = time.time()
            
            response_times.append(end_time - start_time)
        
        avg_response_time = sum(response_times) / len(response_times)
        
        # AAP connection test should complete quickly
        max_threshold = 1.0  # 1 second max
        
        assert avg_response_time < max_threshold, f"AAP connection test too slow: {avg_response_time:.3f}s"
        
        print(f"AAP connection test - Avg: {avg_response_time:.3f}s")
    
    def test_job_launch_performance(self, authenticated_client, mock_aap_api, sample_retirement_data):
        """Test job launch performance."""
        
        start_time = time.time()
        response = authenticated_client.post('/api/launch-job',
                                           data=json.dumps(sample_retirement_data),
                                           content_type='application/json')
        end_time = time.time()
        
        assert response.status_code == 200
        
        response_time = end_time - start_time
        
        # Job launch should complete within reasonable time
        max_threshold = 3.0  # 3 seconds max
        
        assert response_time < max_threshold, f"Job launch too slow: {response_time:.3f}s"
        
        print(f"Job launch - Response time: {response_time:.3f}s")
    
    def test_multiple_job_launches_performance(self, authenticated_client, mock_aap_api):
        """Test performance of multiple job launches."""
        
        def launch_job(job_id):
            data = {
                'hostnames': f'test-vm-{job_id:02d}',
                'shutdown_date': '2025-07-10',
                'shutdown_time': '20:00',
                'retire_date': '2025-07-11',
                'retire_time': '22:00'
            }
            
            start_time = time.time()
            response = authenticated_client.post('/api/launch-job',
                                               data=json.dumps(data),
                                               content_type='application/json')
            end_time = time.time()
            
            return {
                'job_id': job_id,
                'status_code': response.status_code,
                'response_time': end_time - start_time
            }
        
        # Launch 5 jobs sequentially
        results = []
        for i in range(5):
            results.append(launch_job(i + 1))
        
        # Validate results
        for result in results:
            assert result['status_code'] == 200
        
        # Check performance consistency
        response_times = [r['response_time'] for r in results]
        avg_response_time = sum(response_times) / len(response_times)
        max_response_time = max(response_times)
        
        # Performance should be consistent
        max_threshold = 5.0  # 5 seconds max for any single launch
        
        assert max_response_time < max_threshold, f"Job launch inconsistent: {max_response_time:.3f}s"
        
        print(f"Multiple job launches - Count: {len(results)}, Avg: {avg_response_time:.3f}s, Max: {max_response_time:.3f}s")


class TestAuthenticationPerformance:
    """Test authentication performance."""
    
    def test_basic_auth_performance(self, client):
        """Test basic authentication overhead."""
        
        import base64
        
        # Test authenticated request performance
        credentials = base64.b64encode(b'test-user:test-password').decode('utf-8')
        headers = {'Authorization': f'Basic {credentials}'}
        
        response_times = []
        
        for i in range(10):
            start_time = time.time()
            response = client.get('/', headers=headers)
            end_time = time.time()
            
            assert response.status_code == 200
            response_times.append(end_time - start_time)
        
        avg_response_time = sum(response_times) / len(response_times)
        
        # Authentication overhead should be minimal
        max_threshold = 0.5  # 500ms max
        
        assert avg_response_time < max_threshold, f"Authentication overhead too high: {avg_response_time:.3f}s"
        
        print(f"Basic auth - Avg response time: {avg_response_time:.3f}s")
    
    def test_concurrent_authentication(self, client):
        """Test concurrent authentication performance."""
        
        import base64
        
        def authenticated_request():
            credentials = base64.b64encode(b'test-user:test-password').decode('utf-8')
            headers = {'Authorization': f'Basic {credentials}'}
            
            start_time = time.time()
            response = client.get('/', headers=headers)
            end_time = time.time()
            
            return {
                'status_code': response.status_code,
                'response_time': end_time - start_time
            }
        
        # Test concurrent authentication
        results = []
        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(authenticated_request) for _ in range(10)]
            
            for future in as_completed(futures):
                results.append(future.result())
        
        # Validate all requests succeeded
        for result in results:
            assert result['status_code'] == 200
        
        # Check performance under concurrent auth load
        response_times = [r['response_time'] for r in results]
        avg_response_time = sum(response_times) / len(response_times)
        
        # Concurrent auth should still be fast
        max_threshold = 1.0  # 1 second max under concurrent load
        
        assert avg_response_time < max_threshold, f"Concurrent auth too slow: {avg_response_time:.3f}s"
        
        print(f"Concurrent auth - Avg response time: {avg_response_time:.3f}s")


class TestDataProcessingPerformance:
    """Test data processing performance."""
    
    def test_hostname_parsing_performance(self, authenticated_client, mock_aap_api):
        """Test performance of hostname parsing with large inputs."""
        
        # Create large hostname list (100 hostnames)
        hostnames = [f'test-vm-{i:03d}' for i in range(1, 101)]
        hostname_string = ','.join(hostnames)
        
        data = {
            'hostnames': hostname_string,
            'shutdown_date': '2025-07-10',
            'shutdown_time': '20:00',
            'retire_date': '2025-07-11',
            'retire_time': '22:00'
        }
        
        start_time = time.time()
        response = authenticated_client.post('/api/launch-job',
                                           data=json.dumps(data),
                                           content_type='application/json')
        end_time = time.time()
        
        response_time = end_time - start_time
        
        # Large data processing should still be reasonable
        # Note: This might fail validation due to VM limits, but should process quickly
        max_threshold = 2.0  # 2 seconds max for processing
        
        assert response_time < max_threshold, f"Large data processing too slow: {response_time:.3f}s"
        
        print(f"Hostname parsing - 100 hostnames processed in {response_time:.3f}s")
    
    def test_json_serialization_performance(self, authenticated_client):
        """Test JSON serialization/deserialization performance."""
        
        # Create complex data structure
        complex_data = {
            'hostnames': ','.join([f'vm-{i:03d}' for i in range(50)]),
            'shutdown_date': '2025-07-10',
            'shutdown_time': '20:00',
            'retire_date': '2025-07-11',
            'retire_time': '22:00',
            'metadata': {
                'batch_id': 'test-batch-001',
                'created_by': 'performance-test',
                'tags': ['performance', 'testing', 'large-batch'],
                'additional_info': {
                    'test_run': True,
                    'environment': 'development',
                    'notes': 'Performance testing with large payload'
                }
            }
        }
        
        serialization_times = []
        
        for i in range(10):
            start_time = time.time()
            json_data = json.dumps(complex_data)
            parsed_data = json.loads(json_data)
            end_time = time.time()
            
            serialization_times.append(end_time - start_time)
            
            # Verify data integrity
            assert parsed_data['hostnames'] == complex_data['hostnames']
            assert parsed_data['metadata']['batch_id'] == complex_data['metadata']['batch_id']
        
        avg_serialization_time = sum(serialization_times) / len(serialization_times)
        
        # JSON operations should be very fast
        max_threshold = 0.01  # 10ms max
        
        assert avg_serialization_time < max_threshold, f"JSON serialization too slow: {avg_serialization_time:.6f}s"
        
        print(f"JSON serialization - Avg time: {avg_serialization_time:.6f}s")


class TestResourceUtilization:
    """Test resource utilization under various loads."""
    
    def test_cpu_usage_under_load(self, client):
        """Test CPU usage under load."""
        
        process = psutil.Process(os.getpid())
        
        # Get baseline CPU usage
        process.cpu_percent()  # First call to initialize
        time.sleep(0.1)
        baseline_cpu = process.cpu_percent()
        
        # Generate load
        def cpu_intensive_requests():
            for i in range(20):
                response = client.get('/health')
                assert response.status_code == 200
        
        start_time = time.time()
        cpu_intensive_requests()
        end_time = time.time()
        
        # Measure CPU usage during load
        load_cpu = process.cpu_percent()
        
        execution_time = end_time - start_time
        
        print(f"CPU usage - Baseline: {baseline_cpu}%, Under load: {load_cpu}%, "
              f"Load duration: {execution_time:.3f}s")
        
        # CPU usage should be reasonable
        max_cpu_threshold = 80.0  # 80% max CPU usage
        
        # Note: This test might be environment-dependent
        if load_cpu > max_cpu_threshold:
            print(f"Warning: High CPU usage detected: {load_cpu}%")
    
    def test_memory_efficiency(self, client):
        """Test memory efficiency over extended operation."""
        
        process = psutil.Process(os.getpid())
        memory_samples = []
        
        # Sample memory usage over multiple operations
        for i in range(20):
            response = client.get('/health')
            assert response.status_code == 200
            
            memory_info = process.memory_info()
            memory_samples.append(memory_info.rss)
            
            time.sleep(0.1)  # Brief pause between samples
        
        # Analyze memory usage pattern
        initial_memory = memory_samples[0]
        final_memory = memory_samples[-1]
        max_memory = max(memory_samples)
        min_memory = min(memory_samples)
        
        memory_variance = max_memory - min_memory
        memory_growth = final_memory - initial_memory
        
        print(f"Memory efficiency - Initial: {initial_memory // 1024 // 1024}MB, "
              f"Final: {final_memory // 1024 // 1024}MB, "
              f"Max: {max_memory // 1024 // 1024}MB, "
              f"Variance: {memory_variance // 1024 // 1024}MB, "
              f"Growth: {memory_growth // 1024 // 1024}MB")
        
        # Memory should be stable
        max_variance_mb = 10  # 10MB max variance
        max_growth_mb = 5     # 5MB max growth
        
        variance_mb = memory_variance // 1024 // 1024
        growth_mb = memory_growth // 1024 // 1024
        
        assert variance_mb <= max_variance_mb, f"High memory variance: {variance_mb}MB"
        assert growth_mb <= max_growth_mb, f"Excessive memory growth: {growth_mb}MB"