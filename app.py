from flask import Flask, render_template, request, jsonify
import requests
import json
import os
import logging
from functools import wraps

# Suppress InsecureRequestWarning
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Configure logging
logging.basicConfig(level=logging.DEBUG)

app = Flask(__name__)

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
def index():
    return render_template('index.html')

@app.route('/api/test-connection', methods=['GET'])
@requires_auth
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
@requires_auth
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
        
        return jsonify({
            'success': True,
            'job_id': job_data.get('id'),
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

# Handle 500 errors for better user experience
@app.errorhandler(500)
def server_error(e):
    app.logger.error(f"500 error: {str(e)}")
    return jsonify({
        'error': 'Internal Server Error',
        'message': 'An unexpected error occurred on the server. Please check the logs for details.'
    }), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
