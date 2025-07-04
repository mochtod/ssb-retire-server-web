"""
Real-time Performance Monitoring Integration
Provides Flask routes and real-time monitoring capabilities
"""

from flask import Blueprint, jsonify, render_template_string, request
from datetime import datetime, timedelta
import json
from typing import Dict, Any, List
from .metrics import PerformanceDashboard, PerformanceMetricsCollector, performance_monitor

# Create performance monitoring blueprint
performance_bp = Blueprint('performance', __name__, url_prefix='/performance')

# Initialize dashboard
dashboard = PerformanceDashboard()


@performance_bp.route('/api/metrics')
@performance_monitor
def get_metrics_api():
    """API endpoint for performance metrics"""
    try:
        hours = request.args.get('hours', 24, type=int)
        
        collector = PerformanceMetricsCollector()
        summary = collector.get_optimization_summary(hours=hours)
        trends = collector.get_performance_trends(hours=hours)
        alerts = collector.get_alerts()
        
        return jsonify({
            'status': 'success',
            'data': {
                'summary': {
                    'netbox_api_calls': summary.netbox_api_calls,
                    'netbox_optimization': summary.netbox_optimization,
                    'vcenter_searches': summary.vcenter_searches,
                    'vcenter_optimization': summary.vcenter_optimization,
                    'parallel_efficiency': summary.parallel_efficiency,
                    'schedule_optimization': summary.schedule_optimization,
                    'overall_performance_score': summary.overall_performance_score
                },
                'trends': trends,
                'alerts': alerts,
                'last_updated': datetime.now().isoformat()
            }
        })
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500


@performance_bp.route('/api/dashboard')
@performance_monitor
def get_dashboard_api():
    """API endpoint for dashboard data"""
    try:
        data = dashboard.get_dashboard_data()
        return jsonify({
            'status': 'success',
            'data': data
        })
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500


@performance_bp.route('/api/alerts')
@performance_monitor
def get_alerts_api():
    """API endpoint for performance alerts"""
    try:
        collector = PerformanceMetricsCollector()
        alerts = collector.get_alerts()
        
        return jsonify({
            'status': 'success',
            'data': {
                'alerts': alerts,
                'count': len(alerts),
                'last_updated': datetime.now().isoformat()
            }
        })
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500


@performance_bp.route('/dashboard')
@performance_monitor
def performance_dashboard():
    """Performance monitoring dashboard page"""
    template = """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>SSB Retire Server - Performance Dashboard</title>
        <style>
            body { 
                font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; 
                margin: 0; padding: 20px; 
                background: linear-gradient(135deg, #1e3c72 0%, #2a5298 100%);
                color: #fff;
            }
            .container { max-width: 1200px; margin: 0 auto; }
            .header { 
                text-align: center; 
                margin-bottom: 30px; 
                padding: 20px;
                background: rgba(255,255,255,0.1);
                border-radius: 10px;
                backdrop-filter: blur(10px);
            }
            .metrics-grid { 
                display: grid; 
                grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); 
                gap: 20px; 
                margin-bottom: 30px; 
            }
            .metric-card { 
                background: rgba(255,255,255,0.1); 
                padding: 20px; 
                border-radius: 10px; 
                backdrop-filter: blur(10px);
                border: 1px solid rgba(255,255,255,0.2);
            }
            .metric-title { 
                font-size: 18px; 
                font-weight: bold; 
                margin-bottom: 15px; 
                color: #ffd700;
            }
            .metric-value { 
                font-size: 36px; 
                font-weight: bold; 
                margin-bottom: 5px; 
            }
            .metric-unit { 
                font-size: 14px; 
                opacity: 0.8; 
            }
            .metric-target { 
                font-size: 12px; 
                margin-top: 10px; 
                opacity: 0.7; 
            }
            .alert { 
                padding: 10px; 
                margin: 10px 0; 
                border-radius: 5px; 
                border-left: 4px solid;
            }
            .alert-critical { 
                background: rgba(220, 53, 69, 0.2); 
                border-color: #dc3545; 
            }
            .alert-warning { 
                background: rgba(255, 193, 7, 0.2); 
                border-color: #ffc107; 
            }
            .status-excellent { color: #28a745; }
            .status-good { color: #17a2b8; }
            .status-needs-improvement { color: #ffc107; }
            .status-critical { color: #dc3545; }
            .refresh-btn {
                background: #28a745;
                color: white;
                border: none;
                padding: 10px 20px;
                border-radius: 5px;
                cursor: pointer;
                font-size: 16px;
                margin: 10px;
            }
            .refresh-btn:hover { background: #218838; }
            .last-updated {
                text-align: center;
                opacity: 0.7;
                margin-top: 20px;
            }
        </style>
        <script>
            async function refreshDashboard() {
                try {
                    const response = await fetch('/performance/api/dashboard');
                    const result = await response.json();
                    
                    if (result.status === 'success') {
                        updateDashboard(result.data);
                    }
                } catch (error) {
                    console.error('Error refreshing dashboard:', error);
                }
            }
            
            function updateDashboard(data) {
                // Update metric values
                document.getElementById('netbox-calls').textContent = data.summary.netbox_api_calls;
                document.getElementById('netbox-opt').textContent = data.summary.netbox_optimization.toFixed(1) + '%';
                document.getElementById('vcenter-searches').textContent = data.summary.vcenter_searches;
                document.getElementById('vcenter-opt').textContent = data.summary.vcenter_optimization.toFixed(1) + '%';
                document.getElementById('parallel-eff').textContent = data.summary.parallel_efficiency.toFixed(1) + '%';
                document.getElementById('schedule-opt').textContent = data.summary.schedule_optimization.toFixed(1) + '%';
                document.getElementById('overall-score').textContent = data.summary.overall_performance_score.toFixed(1) + '%';
                document.getElementById('performance-grade').textContent = data.performance_grade;
                
                // Update status
                const statusElement = document.getElementById('optimization-status');
                statusElement.textContent = data.optimization_status;
                statusElement.className = 'status-' + data.optimization_status.toLowerCase().replace(' ', '-');
                
                // Update alerts
                const alertsContainer = document.getElementById('alerts-container');
                alertsContainer.innerHTML = '';
                
                if (data.alerts.length === 0) {
                    alertsContainer.innerHTML = '<p>✅ No performance alerts</p>';
                } else {
                    data.alerts.forEach(alert => {
                        const alertDiv = document.createElement('div');
                        alertDiv.className = 'alert alert-' + alert.level;
                        alertDiv.innerHTML = `<strong>${alert.level.toUpperCase()}:</strong> ${alert.message}`;
                        alertsContainer.appendChild(alertDiv);
                    });
                }
                
                // Update timestamp
                document.getElementById('last-updated').textContent = 
                    'Last updated: ' + new Date(data.last_updated).toLocaleString();
            }
            
            // Auto-refresh every 30 seconds
            setInterval(refreshDashboard, 30000);
        </script>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>🔥 SSB Retire Server - Performance Dashboard</h1>
                <h2>Goibniu's Forge - Performance Monitoring</h2>
                <p>Real-time performance optimization tracking</p>
                <button class="refresh-btn" onclick="refreshDashboard()">🔄 Refresh Data</button>
            </div>
            
            <div class="metrics-grid">
                <div class="metric-card">
                    <div class="metric-title">⚡ NetBox API Optimization</div>
                    <div class="metric-value" id="netbox-calls">{{ data.summary.netbox_api_calls }}</div>
                    <div class="metric-unit">API calls (Target: ≤3)</div>
                    <div class="metric-value" id="netbox-opt">{{ "%.1f"|format(data.summary.netbox_optimization) }}%</div>
                    <div class="metric-target">Target: ≥60% reduction</div>
                </div>
                
                <div class="metric-card">
                    <div class="metric-title">🔍 vCenter Search Optimization</div>
                    <div class="metric-value" id="vcenter-searches">{{ data.summary.vcenter_searches }}</div>
                    <div class="metric-unit">searches performed</div>
                    <div class="metric-value" id="vcenter-opt">{{ "%.1f"|format(data.summary.vcenter_optimization) }}%</div>
                    <div class="metric-target">Target: ≥75% reduction</div>
                </div>
                
                <div class="metric-card">
                    <div class="metric-title">🚀 Parallel Processing</div>
                    <div class="metric-value" id="parallel-eff">{{ "%.1f"|format(data.summary.parallel_efficiency) }}%</div>
                    <div class="metric-unit">efficiency gain</div>
                    <div class="metric-target">Target: Medium impact improvement</div>
                </div>
                
                <div class="metric-card">
                    <div class="metric-title">📅 Schedule Optimization</div>
                    <div class="metric-value" id="schedule-opt">{{ "%.1f"|format(data.summary.schedule_optimization) }}%</div>
                    <div class="metric-unit">API overhead reduction</div>
                    <div class="metric-target">Target: ≥80% reduction</div>
                </div>
                
                <div class="metric-card">
                    <div class="metric-title">🎯 Overall Performance</div>
                    <div class="metric-value" id="overall-score">{{ "%.1f"|format(data.summary.overall_performance_score) }}%</div>
                    <div class="metric-unit">optimization score</div>
                    <div>Grade: <span id="performance-grade">{{ data.performance_grade }}</span></div>
                    <div>Status: <span id="optimization-status" class="status-{{ data.optimization_status.lower().replace(' ', '-') }}">{{ data.optimization_status }}</span></div>
                </div>
                
                <div class="metric-card">
                    <div class="metric-title">🚨 Performance Alerts</div>
                    <div id="alerts-container">
                        {% if data.alerts|length == 0 %}
                        <p>✅ No performance alerts</p>
                        {% else %}
                        {% for alert in data.alerts %}
                        <div class="alert alert-{{ alert.level }}">
                            <strong>{{ alert.level|upper }}:</strong> {{ alert.message }}
                        </div>
                        {% endfor %}
                        {% endif %}
                    </div>
                </div>
            </div>
            
            <div class="last-updated" id="last-updated">
                Last updated: {{ data.last_updated }}
            </div>
        </div>
    </body>
    </html>
    """
    
    try:
        data = dashboard.get_dashboard_data()
        return render_template_string(template, data=data)
    except Exception as e:
        return f"Error loading dashboard: {str(e)}", 500


@performance_bp.route('/api/health')
@performance_monitor
def health_check():
    """Health check endpoint for performance monitoring"""
    try:
        collector = PerformanceMetricsCollector()
        summary = collector.get_optimization_summary(hours=1)
        
        # Determine health status
        health_status = "healthy"
        if summary.overall_performance_score < 40:
            health_status = "critical"
        elif summary.overall_performance_score < 60:
            health_status = "degraded"
        
        return jsonify({
            'status': health_status,
            'overall_score': summary.overall_performance_score,
            'components': {
                'netbox_api': 'healthy' if summary.netbox_optimization >= 60 else 'degraded',
                'vcenter_search': 'healthy' if summary.vcenter_optimization >= 75 else 'degraded',
                'parallel_processing': 'healthy' if summary.parallel_efficiency >= 50 else 'degraded',
                'schedule_optimization': 'healthy' if summary.schedule_optimization >= 80 else 'degraded'
            },
            'last_updated': datetime.now().isoformat()
        })
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500


# Real-time monitoring functions
def get_real_time_metrics() -> Dict[str, Any]:
    """Get real-time performance metrics for monitoring"""
    collector = PerformanceMetricsCollector()
    return {
        'optimization_summary': collector.get_optimization_summary(hours=1),
        'alerts': collector.get_alerts(),
        'timestamp': datetime.now().isoformat()
    }


def check_performance_thresholds() -> List[Dict[str, Any]]:
    """Check if performance metrics exceed thresholds"""
    collector = PerformanceMetricsCollector()
    return collector.get_alerts()


# WebSocket support for real-time updates (if needed)
def emit_performance_update():
    """Emit performance update via WebSocket (requires socketio)"""
    try:
        data = get_real_time_metrics()
        # This would integrate with Flask-SocketIO if available
        # socketio.emit('performance_update', data)
        return data
    except Exception as e:
        print(f"Error emitting performance update: {e}")
        return None