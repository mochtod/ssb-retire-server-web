from flask import Flask, render_template, request, jsonify
import requests
import json
import os
import logging
from datetime import datetime
from functools import wraps

# Security imports
from flask_talisman import Talisman
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from config.security import SecurityConfig, validate_security_config
from middleware.security_headers import create_security_middleware

# Performance monitoring imports
from performance.monitoring import performance_bp, performance_monitor
from performance.metrics import PerformanceMetricsCollector, AAPJobMonitor, RetirementJobMetrics

# WebSocket imports for real-time monitoring
from flask_socketio import SocketIO, emit

# Suppress InsecureRequestWarning
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Configure logging
logging.basicConfig(level=logging.DEBUG)

# Create Flask app with security configuration
app = Flask(__name__)

# Load security configuration
security_config = SecurityConfig.from_environment()

# Validate security configuration
security_errors = validate_security_config()
if security_errors:
    app.logger.error(f"Security configuration errors: {security_errors}")
    if os.environ.get('FLASK_ENV') == 'production':
        raise RuntimeError(f"Security validation failed: {security_errors}")

# Configure Flask security settings
app.config.update(security_config.session_config)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-key-change-in-production')

# Initialize security middleware
security_middleware = create_security_middleware(security_config)
security_middleware.init_app(app)

# Initialize Flask-Talisman for HTTPS and security headers
talisman = Talisman(app, **security_config.get_talisman_config())

# Initialize rate limiting
limiter = Limiter(
    get_remote_address,
    app=app,
    default_limits=["200 per day", "50 per hour"],
    storage_uri="memory://"
)

# Initialize SocketIO for real-time monitoring
socketio = SocketIO(app, cors_allowed_origins="*", logger=True, engineio_logger=True)

# Register performance monitoring blueprint
app.register_blueprint(performance_bp)

# Initialize performance collector and job monitor
performance_collector = PerformanceMetricsCollector()
job_monitor = None  # Will be initialized when AAP credentials are available

# Configuration
AAP_URL = os.environ.get('AAP_URL', 'https://ansibleaap.chrobinson.com')
AAP_TOKEN = os.environ.get('AAP_TOKEN', '')  # Bearer token
AAP_TEMPLATE_ID = os.environ.get('AAP_TEMPLATE_ID', '66')

# Basic Auth for the web app
BASIC_AUTH_USERNAME = os.environ.get('BASIC_AUTH_USERNAME', 'admin')
BASIC_AUTH_PASSWORD = os.environ.get('BASIC_AUTH_PASSWORD', 'password')

# Log configuration (without exposing sensitive data)
app.logger.info(f"AAP URL: {AAP_URL}")
app.logger.info(f"AAP TOKEN: {'Set' if AAP_TOKEN else 'Not set'}")
app.logger.info(f"AAP TEMPLATE ID: {AAP_TEMPLATE_ID}")

def check_auth(username, password):
    """Verify if the username/password combination is valid."""
    return username == BASIC_AUTH_USERNAME and password == BASIC_AUTH_PASSWORD

def authenticate():
    """Send a 401 response that enables basic auth."""
    return jsonify({'error': 'Authentication required'}), 401, {
        'WWW-Authenticate': 'Basic realm="Login Required"'
    }

def requires_auth(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        auth = request.authorization
        if not auth or not check_auth(auth.username, auth.password):
            return authenticate()
        return f(*args, **kwargs)
    return decorated

@app.route('/')
@requires_auth
@performance_monitor
def index():
    return render_template('index.html')


@app.route('/retirement-monitor')
@requires_auth
@performance_monitor
def retirement_monitor():
    """Dedicated retirement job monitoring page"""
    return render_template('retirement_monitor.html')

@app.route('/api/test-connection', methods=['GET'])
@limiter.limit("10 per minute")
@requires_auth
@performance_monitor
def test_connection():
    """Test AAP API connection without launching job"""
    try:
        app.logger.debug(f"Testing connection to AAP API: {AAP_URL}/api/v2/")
        
        if not AAP_TOKEN:
            return jsonify({
                'status': 'error',
                'message': 'No AAP token configured. Set the AAP_TOKEN environment variable.'
            }), 500
            
        # Use Bearer token authentication
        headers = {
            "Authorization": f"Bearer {AAP_TOKEN}",
            "Content-Type": "application/json"
        }
        
        # Add timeout and error handling
        response = requests.get(
            f"{AAP_URL}/api/v2/",
            headers=headers,
            verify=False,  # Disabled SSL verification for internal server
            timeout=10
        )
        
        app.logger.debug(f"Response status code: {response.status_code}")
        
        if response.status_code == 200:
            return jsonify({
                'status': 'success',
                'message': 'Successfully connected to AAP API',
                'api_version': response.headers.get('Api-Version', 'Unknown')
            })
        else:
            app.logger.error(f"API Error response: {response.text}")
            return jsonify({
                'status': 'error',
                'message': f'AAP API returned status code {response.status_code}',
                'response': response.text[:500]
            }), 500
            
    except requests.exceptions.Timeout:
        app.logger.error("Timeout connecting to AAP API")
        return jsonify({
            'status': 'error',
            'message': 'Timeout connecting to AAP API. Check the URL and network connectivity.'
        }), 500
        
    except requests.exceptions.ConnectionError:
        app.logger.error("Connection error to AAP API")
        return jsonify({
            'status': 'error',
            'message': 'Could not connect to AAP API. Check the URL and network connectivity.'
        }), 500
        
    except requests.exceptions.RequestException as e:
        app.logger.error(f"Request error: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': f'Error connecting to AAP API: {str(e)}'
        }), 500
        
    except Exception as e:
        app.logger.error(f"General error: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': f'Unexpected error: {str(e)}'
        }), 500

@app.route('/api/launch-job', methods=['POST'])
@limiter.limit("5 per minute")
@requires_auth
@performance_monitor
def launch_job():
    try:
        data = request.json
        app.logger.debug(f"Received data: {json.dumps(data)}")
        
        if not AAP_TOKEN:
            return jsonify({
                'error': 'No AAP token configured. Set the AAP_TOKEN environment variable.'
            }), 500
            
        record_names = data.get("record_names", [])
        
        # Validate that 1-5 record names are provided
        if len(record_names) < 1 or len(record_names) > 5:
            app.logger.warning(f"Attempted to schedule job with {len(record_names)} VMs. Must be between 1-5.")
            return jsonify({
                'error': 'Invalid request: Between 1 and 5 VM record names must be provided per job.'
            }), 400
            
        # Format the extra vars
        extra_vars = {
            "record_names": record_names, # List with 1-5 items
            "schedule_shutdown_date": data.get("schedule_shutdown_date"),
            "schedule_retire_date": data.get("schedule_retire_date"),
            "schedule_shutdown_time": data.get("schedule_shutdown_time"),
            "schedule_retire_time": data.get("schedule_retire_time"),
            "dns_server": data.get("dns_server", "chrpr2dc38.chrobinson.com"),
            "dns_zone": data.get("dns_zone", "chrobinson.com")
        }
        
        app.logger.debug(f"Launching job with extra vars: {json.dumps(extra_vars)}")
        
        # Launch the job template using Bearer token
        try:
            headers = {
                "Authorization": f"Bearer {AAP_TOKEN}",
                "Content-Type": "application/json"
            }
            
            payload = {
                "extra_vars": extra_vars
            }
            
            job_url = f"{AAP_URL}/api/v2/job_templates/{AAP_TEMPLATE_ID}/launch/"
            app.logger.debug(f"Job launch URL: {job_url}")
            
            job_response = requests.post(
                job_url,
                headers=headers,
                json=payload,
                verify=False,  # Disabled SSL verification for internal server
                timeout=15
            )
            
            app.logger.debug(f"Job launch response status: {job_response.status_code}")
            
            if job_response.status_code >= 400:
                app.logger.error(f"Job launch error response: {job_response.text}")
                return jsonify({
                    'error': f"Error launching job: {job_response.text}"
                }), 500
                
            job_response.raise_for_status()
            
        except requests.exceptions.RequestException as e:
            app.logger.error(f"Job launch error: {str(e)}")
            return jsonify({
                'error': f"Error launching job: {str(e)}. Check token and template ID."
            }), 500
            
        job_data = job_response.json()
        app.logger.debug(f"Job response: {json.dumps(job_data)}")
        
        # Track the job in our monitoring system
        job_id = job_data.get('id')
        if job_id:
            try:
                # Initialize job monitor if not already done
                global job_monitor
                if not job_monitor and AAP_TOKEN:
                    job_monitor = AAPJobMonitor(AAP_URL, AAP_TOKEN)
                
                # Create initial job tracking entry
                job_metrics = RetirementJobMetrics(
                    job_id=str(job_id),
                    status="pending",
                    job_type="retirement",
                    target_hosts=record_names,
                    start_time=datetime.now().isoformat(),
                    aap_template_id=AAP_TEMPLATE_ID,
                    extra_vars=extra_vars
                )
                
                performance_collector.track_retirement_job(job_metrics)
                
                # Emit real-time update
                socketio.emit('job_started', {
                    'job_id': str(job_id),
                    'status': 'pending',
                    'target_hosts': record_names,
                    'job_type': 'retirement'
                })
                
            except Exception as e:
                app.logger.error(f"Error tracking job: {str(e)}")
        
        return jsonify({
            'success': True,
            'job_id': job_id,
            'job_url': job_data.get('url')
        })
        
    except Exception as e:
        app.logger.error(f"Server error: {str(e)}")
        return jsonify({'error': f"Server error: {str(e)}"}), 500

@app.route('/status')
@requires_auth
def status():
    """Simple status page to check if the app is running"""
    return jsonify({
        'status': 'ok',
        'app': 'VM Retirement Scheduler',
        'aap_url': AAP_URL,
        'aap_token_set': bool(AAP_TOKEN),
        'aap_template_id': AAP_TEMPLATE_ID
    })

@app.route('/health')
def health():
    """Health check endpoint for monitoring and security validation"""
    return jsonify({
        'status': 'healthy',
        'security': {
            'talisman_enabled': talisman is not None,
            'rate_limiting_enabled': limiter is not None,
            'session_security': 'configured',
            'security_headers': 'enabled'
        },
        'app': 'SSB Retire Server Web',
        'version': '1.0.0-security-hardened'
    })


@app.route('/api/retirement/jobs')
@requires_auth
@performance_monitor
def get_retirement_jobs():
    """Get retirement jobs with optional filtering"""
    try:
        hours = request.args.get('hours', 24, type=int)
        status = request.args.get('status', None)
        
        jobs = performance_collector.get_retirement_jobs(hours=hours, status=status)
        summary = performance_collector.get_retirement_job_summary(hours=hours)
        
        return jsonify({
            'status': 'success',
            'data': {
                'jobs': [job.__dict__ for job in jobs],
                'summary': summary,
                'total_count': len(jobs)
            },
            'timestamp': datetime.now().isoformat()
        })
        
    except Exception as e:
        app.logger.error(f"Error getting retirement jobs: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500


@app.route('/api/retirement/jobs/<job_id>')
@requires_auth
@performance_monitor
def get_job_details(job_id):
    """Get detailed information about a specific job"""
    try:
        # Get job from database
        jobs = performance_collector.get_retirement_jobs(hours=168)  # Last week
        job = next((j for j in jobs if j.job_id == job_id), None)
        
        if not job:
            return jsonify({
                'status': 'error',
                'message': 'Job not found'
            }), 404
        
        # Get status history
        status_history = performance_collector.get_job_status_history(job_id)
        
        # If we have AAP access, get live status
        if job_monitor and job.status in ['pending', 'running']:
            try:
                updated_job = job_monitor.monitor_job(job_id, job.target_hosts, job.job_type)
                job = updated_job
            except Exception as e:
                app.logger.warning(f"Could not get live job status: {str(e)}")
        
        return jsonify({
            'status': 'success',
            'data': {
                'job': job.__dict__,
                'status_history': status_history
            },
            'timestamp': datetime.now().isoformat()
        })
        
    except Exception as e:
        app.logger.error(f"Error getting job details: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500


@app.route('/api/retirement/jobs/<job_id>/monitor', methods=['POST'])
@requires_auth
@performance_monitor
def monitor_job_status(job_id):
    """Manually trigger job status monitoring"""
    try:
        if not job_monitor:
            return jsonify({
                'status': 'error',
                'message': 'Job monitoring not available - AAP credentials not configured'
            }), 503
        
        # Get target hosts from request or database
        target_hosts = request.json.get('target_hosts', [])
        if not target_hosts:
            # Try to get from database
            jobs = performance_collector.get_retirement_jobs(hours=168)
            job = next((j for j in jobs if j.job_id == job_id), None)
            if job:
                target_hosts = job.target_hosts
        
        if not target_hosts:
            return jsonify({
                'status': 'error',
                'message': 'Target hosts not found for job'
            }), 400
        
        # Monitor the job
        job_metrics = job_monitor.monitor_job(job_id, target_hosts)
        
        # Emit real-time update
        socketio.emit('job_update', {
            'job_id': job_id,
            'status': job_metrics.status,
            'duration_seconds': job_metrics.duration_seconds,
            'success_rate': job_metrics.success_rate,
            'errors': job_metrics.errors
        })
        
        return jsonify({
            'status': 'success',
            'data': job_metrics.__dict__,
            'timestamp': datetime.now().isoformat()
        })
        
    except Exception as e:
        app.logger.error(f"Error monitoring job: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500


@app.route('/api/retirement/dashboard')
@requires_auth
@performance_monitor
def get_retirement_dashboard():
    """Get comprehensive retirement monitoring dashboard data"""
    try:
        hours = request.args.get('hours', 24, type=int)
        
        # Get job summary and active jobs
        summary = performance_collector.get_retirement_job_summary(hours=hours)
        recent_jobs = performance_collector.get_retirement_jobs(hours=hours)
        active_jobs = performance_collector.get_retirement_jobs(hours=hours, status='running')
        
        # Get performance metrics too
        from performance.monitoring import dashboard
        perf_data = dashboard.get_dashboard_data()
        
        dashboard_data = {
            'retirement_summary': summary,
            'recent_jobs': [job.__dict__ for job in recent_jobs[:20]],  # Last 20 jobs
            'active_jobs': [job.__dict__ for job in active_jobs],
            'performance_data': perf_data,
            'statistics': {
                'total_active': len(active_jobs),
                'success_rate_24h': summary['success_rate'],
                'avg_duration_minutes': summary['average_duration_minutes'],
                'jobs_per_hour': summary['jobs_per_hour']
            },
            'timestamp': datetime.now().isoformat()
        }
        
        return jsonify({
            'status': 'success',
            'data': dashboard_data
        })
        
    except Exception as e:
        app.logger.error(f"Error getting retirement dashboard: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

# Handle 500 errors for better user experience
@app.errorhandler(500)
def server_error(e):
    app.logger.error(f"500 error: {str(e)}")
    return jsonify({
        'error': 'Internal Server Error',
        'message': 'An unexpected error occurred on the server. Please check the logs for details.'
    }), 500


# WebSocket event handlers
@socketio.on('connect')
def handle_connect():
    """Handle client connection"""
    app.logger.info('Client connected to monitoring WebSocket')
    emit('connected', {'status': 'Connected to retirement monitoring'})


@socketio.on('disconnect')
def handle_disconnect():
    """Handle client disconnection"""
    app.logger.info('Client disconnected from monitoring WebSocket')


@socketio.on('subscribe_job_updates')
def handle_subscribe_job_updates(data):
    """Subscribe to job updates for specific jobs"""
    job_ids = data.get('job_ids', [])
    app.logger.info(f'Client subscribed to job updates for: {job_ids}')
    
    # Send current status for requested jobs
    try:
        for job_id in job_ids:
            jobs = performance_collector.get_retirement_jobs(hours=168)
            job = next((j for j in jobs if j.job_id == job_id), None)
            if job:
                emit('job_update', {
                    'job_id': job_id,
                    'status': job.status,
                    'duration_seconds': job.duration_seconds,
                    'success_rate': job.success_rate,
                    'errors': job.errors
                })
    except Exception as e:
        app.logger.error(f"Error sending job updates: {str(e)}")


@socketio.on('get_dashboard_update')
def handle_dashboard_update():
    """Send dashboard update to client"""
    try:
        hours = 24
        summary = performance_collector.get_retirement_job_summary(hours=hours)
        active_jobs = performance_collector.get_retirement_jobs(hours=hours, status='running')
        
        emit('dashboard_update', {
            'summary': summary,
            'active_jobs': [job.__dict__ for job in active_jobs],
            'timestamp': datetime.now().isoformat()
        })
    except Exception as e:
        app.logger.error(f"Error sending dashboard update: {str(e)}")


def background_job_monitoring():
    """Background task to monitor active jobs and emit updates"""
    import time
    
    last_checked_jobs = set()
    
    while True:
        try:
            if job_monitor:
                # Get active jobs
                active_jobs = performance_collector.get_retirement_jobs(hours=48, status='running')
                pending_jobs = performance_collector.get_retirement_jobs(hours=48, status='pending')
                
                current_jobs = set()
                
                # Monitor each active/pending job
                for job in active_jobs + pending_jobs:
                    current_jobs.add(job.job_id)
                    
                    try:
                        # Get updated status from AAP
                        updated_job = job_monitor.monitor_job(job.job_id, job.target_hosts, job.job_type)
                        
                        # Check if status changed
                        if job.status != updated_job.status or job.job_id not in last_checked_jobs:
                            # Emit update
                            socketio.emit('job_update', {
                                'job_id': job.job_id,
                                'status': updated_job.status,
                                'duration_seconds': updated_job.duration_seconds,
                                'success_rate': updated_job.success_rate,
                                'errors': updated_job.errors,
                                'target_hosts': updated_job.target_hosts
                            })
                            
                            app.logger.info(f"Job {job.job_id} status updated: {updated_job.status}")
                    
                    except Exception as e:
                        app.logger.error(f"Error monitoring job {job.job_id}: {str(e)}")
                
                last_checked_jobs = current_jobs
                
                # Send periodic dashboard updates
                if len(current_jobs) > 0:
                    summary = performance_collector.get_retirement_job_summary(hours=24)
                    socketio.emit('dashboard_stats_update', {
                        'total_active': len(active_jobs),
                        'success_rate': summary['success_rate'],
                        'avg_duration': summary['average_duration_minutes'],
                        'timestamp': datetime.now().isoformat()
                    })
            
        except Exception as e:
            app.logger.error(f"Error in background monitoring: {str(e)}")
        
        # Wait 30 seconds before next check
        time.sleep(30)

if __name__ == '__main__':
    # Initialize job monitor if credentials are available
    if AAP_TOKEN:
        job_monitor = AAPJobMonitor(AAP_URL, AAP_TOKEN)
        
        # Start background monitoring task
        socketio.start_background_task(background_job_monitoring)
    
    # Run with SocketIO
    socketio.run(app, host='0.0.0.0', port=5000, debug=True)
