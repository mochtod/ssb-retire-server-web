"""
Performance Data Collection and Analysis Module
Integrates with Ansible performance metrics for web monitoring
"""

import json
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any
import sqlite3
from dataclasses import dataclass, asdict
from functools import wraps


@dataclass
class PerformanceMetric:
    """Performance metric data structure"""
    timestamp: str
    component: str
    metric_name: str
    value: float
    unit: str
    threshold_warning: Optional[float] = None
    threshold_critical: Optional[float] = None
    tags: Optional[Dict[str, str]] = None


@dataclass
class OptimizationSummary:
    """Performance optimization summary"""
    netbox_api_calls: int
    netbox_optimization: float
    vcenter_searches: int
    vcenter_optimization: float
    parallel_efficiency: float
    schedule_optimization: float
    overall_performance_score: float


@dataclass
class RetirementJobMetrics:
    """Retirement job tracking metrics"""
    job_id: str
    status: str
    job_type: str
    target_hosts: List[str]
    start_time: str
    end_time: Optional[str] = None
    duration_seconds: Optional[float] = None
    success_rate: float = 0.0
    errors: List[str] = None
    aap_template_id: Optional[str] = None
    extra_vars: Optional[Dict[str, Any]] = None


class PerformanceMetricsCollector:
    """Collects and analyzes performance metrics from Ansible runs"""
    
    def __init__(self, metrics_dir: str = "../ssb-retire-server/performance/metrics"):
        self.metrics_dir = Path(metrics_dir)
        self.db_path = Path("performance_metrics.db")
        self._init_database()
    
    def _init_database(self):
        """Initialize SQLite database for metrics storage"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS performance_metrics (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    component TEXT NOT NULL,
                    metric_name TEXT NOT NULL,
                    value REAL NOT NULL,
                    unit TEXT NOT NULL,
                    threshold_warning REAL,
                    threshold_critical REAL,
                    tags TEXT,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            conn.execute("""
                CREATE TABLE IF NOT EXISTS optimization_summaries (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    netbox_api_calls INTEGER,
                    netbox_optimization REAL,
                    vcenter_searches INTEGER,
                    vcenter_optimization REAL,
                    parallel_efficiency REAL,
                    schedule_optimization REAL,
                    overall_performance_score REAL,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            conn.execute("""
                CREATE TABLE IF NOT EXISTS retirement_jobs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    job_id TEXT NOT NULL UNIQUE,
                    status TEXT NOT NULL,
                    job_type TEXT NOT NULL,
                    target_hosts TEXT NOT NULL,
                    start_time TEXT NOT NULL,
                    end_time TEXT,
                    duration_seconds REAL,
                    success_rate REAL DEFAULT 0.0,
                    errors TEXT,
                    aap_template_id TEXT,
                    extra_vars TEXT,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    updated_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            conn.execute("""
                CREATE TABLE IF NOT EXISTS job_status_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    job_id TEXT NOT NULL,
                    status TEXT NOT NULL,
                    timestamp TEXT NOT NULL,
                    details TEXT,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (job_id) REFERENCES retirement_jobs (job_id)
                )
            """)
    
    def collect_ansible_metrics(self) -> List[PerformanceMetric]:
        """Collect metrics from Ansible performance files"""
        metrics = []
        
        if not self.metrics_dir.exists():
            return metrics
        
        for metrics_file in self.metrics_dir.glob("metrics_*.md"):
            try:
                content = metrics_file.read_text()
                parsed_metrics = self._parse_ansible_metrics(content)
                metrics.extend(parsed_metrics)
            except Exception as e:
                print(f"Error parsing metrics file {metrics_file}: {e}")
        
        return metrics
    
    def _parse_ansible_metrics(self, content: str) -> List[PerformanceMetric]:
        """Parse Ansible metrics from markdown content"""
        metrics = []
        timestamp = datetime.now().isoformat()
        
        lines = content.split('\n')
        current_section = None
        
        for line in lines:
            line = line.strip()
            
            # Detect sections
            if line.startswith('## '):
                current_section = line[3:].strip()
                continue
            
            # Parse metric lines
            if ': ' in line and line.startswith('- '):
                try:
                    metric_line = line[2:]  # Remove '- '
                    name, value_str = metric_line.split(': ', 1)
                    
                    # Extract numeric value and unit
                    value, unit = self._extract_value_unit(value_str)
                    
                    if value is not None:
                        metric = PerformanceMetric(
                            timestamp=timestamp,
                            component=current_section or "Unknown",
                            metric_name=name.strip(),
                            value=value,
                            unit=unit,
                            tags={"source": "ansible"}
                        )
                        metrics.append(metric)
                        
                except ValueError:
                    continue
        
        return metrics
    
    def _extract_value_unit(self, value_str: str) -> tuple:
        """Extract numeric value and unit from string"""
        value_str = value_str.strip()
        
        # Handle percentage
        if value_str.endswith('%'):
            try:
                return float(value_str[:-1]), "percent"
            except ValueError:
                return None, None
        
        # Handle time units
        if value_str.endswith('s'):
            try:
                return float(value_str[:-1]), "seconds"
            except ValueError:
                return None, None
        
        # Handle plain numbers
        try:
            return float(value_str), "count"
        except ValueError:
            return None, None
    
    def store_metrics(self, metrics: List[PerformanceMetric]):
        """Store metrics in database"""
        with sqlite3.connect(self.db_path) as conn:
            for metric in metrics:
                conn.execute("""
                    INSERT INTO performance_metrics 
                    (timestamp, component, metric_name, value, unit, threshold_warning, threshold_critical, tags)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    metric.timestamp,
                    metric.component,
                    metric.metric_name,
                    metric.value,
                    metric.unit,
                    metric.threshold_warning,
                    metric.threshold_critical,
                    json.dumps(metric.tags) if metric.tags else None
                ))
    
    def get_optimization_summary(self, hours: int = 24) -> OptimizationSummary:
        """Get optimization summary for the last N hours"""
        since = datetime.now() - timedelta(hours=hours)
        
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            
            # Get latest metrics for each component
            netbox_calls = self._get_latest_metric(conn, "NetBox Performance Metrics", "API Calls Made") or 7
            netbox_opt = self._get_latest_metric(conn, "NetBox Performance Metrics", "Optimization Achieved") or 0
            vcenter_searches = self._get_latest_metric(conn, "vCenter Performance Metrics", "Searches Performed") or 16
            vcenter_opt = self._get_latest_metric(conn, "vCenter Performance Metrics", "Optimization Achieved") or 0
            parallel_eff = self._get_latest_metric(conn, "Parallel Processing Metrics", "Efficiency Gain") or 0
            schedule_opt = self._get_latest_metric(conn, "Schedule Creation Metrics", "Optimization Achieved") or 0
            
            # Calculate overall performance score
            overall_score = (netbox_opt + vcenter_opt + parallel_eff + schedule_opt) / 4
            
            return OptimizationSummary(
                netbox_api_calls=int(netbox_calls),
                netbox_optimization=netbox_opt,
                vcenter_searches=int(vcenter_searches),
                vcenter_optimization=vcenter_opt,
                parallel_efficiency=parallel_eff,
                schedule_optimization=schedule_opt,
                overall_performance_score=overall_score
            )
    
    def _get_latest_metric(self, conn, component: str, metric_name: str) -> Optional[float]:
        """Get the latest value for a specific metric"""
        cursor = conn.execute("""
            SELECT value FROM performance_metrics 
            WHERE component = ? AND metric_name = ?
            ORDER BY timestamp DESC 
            LIMIT 1
        """, (component, metric_name))
        
        row = cursor.fetchone()
        return row[0] if row else None
    
    def get_performance_trends(self, hours: int = 24) -> Dict[str, List[Dict]]:
        """Get performance trends over time"""
        since = datetime.now() - timedelta(hours=hours)
        
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            
            cursor = conn.execute("""
                SELECT timestamp, component, metric_name, value, unit
                FROM performance_metrics 
                WHERE timestamp > ?
                ORDER BY timestamp DESC
            """, (since.isoformat(),))
            
            trends = {}
            for row in cursor:
                component = row['component']
                if component not in trends:
                    trends[component] = []
                
                trends[component].append({
                    'timestamp': row['timestamp'],
                    'metric_name': row['metric_name'],
                    'value': row['value'],
                    'unit': row['unit']
                })
        
        return trends
    
    def get_alerts(self) -> List[Dict[str, Any]]:
        """Get current performance alerts"""
        alerts = []
        summary = self.get_optimization_summary()
        
        # Define thresholds
        thresholds = {
            'netbox_api_calls': {'warning': 5, 'critical': 10},
            'netbox_optimization': {'warning': 40, 'critical': 20},
            'vcenter_optimization': {'warning': 50, 'critical': 25},
            'schedule_optimization': {'warning': 60, 'critical': 40},
            'overall_performance_score': {'warning': 60, 'critical': 40}
        }
        
        # Check thresholds
        for metric, threshold in thresholds.items():
            value = getattr(summary, metric)
            
            if metric == 'netbox_api_calls':
                # Higher is worse for API calls
                if value > threshold['critical']:
                    alerts.append({
                        'level': 'critical',
                        'component': 'NetBox API',
                        'message': f'API calls ({value}) exceed critical threshold ({threshold["critical"]})',
                        'value': value,
                        'threshold': threshold['critical']
                    })
                elif value > threshold['warning']:
                    alerts.append({
                        'level': 'warning',
                        'component': 'NetBox API',
                        'message': f'API calls ({value}) exceed warning threshold ({threshold["warning"]})',
                        'value': value,
                        'threshold': threshold['warning']
                    })
            else:
                # Lower is worse for optimization percentages
                if value < threshold['critical']:
                    alerts.append({
                        'level': 'critical',
                        'component': metric.replace('_', ' ').title(),
                        'message': f'{metric} ({value:.1f}%) below critical threshold ({threshold["critical"]}%)',
                        'value': value,
                        'threshold': threshold['critical']
                    })
                elif value < threshold['warning']:
                    alerts.append({
                        'level': 'warning',
                        'component': metric.replace('_', ' ').title(),
                        'message': f'{metric} ({value:.1f}%) below warning threshold ({threshold["warning"]}%)',
                        'value': value,
                        'threshold': threshold['warning']
                    })
        
        return alerts
    
    def track_retirement_job(self, job_metrics: RetirementJobMetrics):
        """Track a retirement job in the database"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT OR REPLACE INTO retirement_jobs 
                (job_id, status, job_type, target_hosts, start_time, end_time, 
                 duration_seconds, success_rate, errors, aap_template_id, extra_vars, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                job_metrics.job_id,
                job_metrics.status,
                job_metrics.job_type,
                json.dumps(job_metrics.target_hosts),
                job_metrics.start_time,
                job_metrics.end_time,
                job_metrics.duration_seconds,
                job_metrics.success_rate,
                json.dumps(job_metrics.errors) if job_metrics.errors else None,
                job_metrics.aap_template_id,
                json.dumps(job_metrics.extra_vars) if job_metrics.extra_vars else None,
                datetime.now().isoformat()
            ))
            
            # Add status history entry
            conn.execute("""
                INSERT INTO job_status_history (job_id, status, timestamp, details)
                VALUES (?, ?, ?, ?)
            """, (
                job_metrics.job_id,
                job_metrics.status,
                datetime.now().isoformat(),
                f"Job {job_metrics.status.lower()}"
            ))
    
    def get_retirement_jobs(self, hours: int = 24, status: Optional[str] = None) -> List[RetirementJobMetrics]:
        """Get retirement jobs from the database"""
        since = datetime.now() - timedelta(hours=hours)
        
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            
            query = """
                SELECT * FROM retirement_jobs 
                WHERE start_time > ?
            """
            params = [since.isoformat()]
            
            if status:
                query += " AND status = ?"
                params.append(status)
            
            query += " ORDER BY start_time DESC"
            
            cursor = conn.execute(query, params)
            
            jobs = []
            for row in cursor:
                jobs.append(RetirementJobMetrics(
                    job_id=row['job_id'],
                    status=row['status'],
                    job_type=row['job_type'],
                    target_hosts=json.loads(row['target_hosts']),
                    start_time=row['start_time'],
                    end_time=row['end_time'],
                    duration_seconds=row['duration_seconds'],
                    success_rate=row['success_rate'],
                    errors=json.loads(row['errors']) if row['errors'] else None,
                    aap_template_id=row['aap_template_id'],
                    extra_vars=json.loads(row['extra_vars']) if row['extra_vars'] else None
                ))
            
            return jobs
    
    def get_job_status_history(self, job_id: str) -> List[Dict[str, str]]:
        """Get status history for a specific job"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            
            cursor = conn.execute("""
                SELECT status, timestamp, details FROM job_status_history 
                WHERE job_id = ? 
                ORDER BY timestamp ASC
            """, (job_id,))
            
            return [dict(row) for row in cursor]
    
    def get_retirement_job_summary(self, hours: int = 24) -> Dict[str, Any]:
        """Get summary statistics for retirement jobs"""
        jobs = self.get_retirement_jobs(hours)
        
        total_jobs = len(jobs)
        active_jobs = len([j for j in jobs if j.status in ['pending', 'running']])
        completed_jobs = len([j for j in jobs if j.status == 'successful'])
        failed_jobs = len([j for j in jobs if j.status == 'failed'])
        
        success_rate = (completed_jobs / total_jobs * 100) if total_jobs > 0 else 0
        
        # Calculate average duration for completed jobs
        completed_durations = [j.duration_seconds for j in jobs if j.duration_seconds and j.status == 'successful']
        avg_duration = sum(completed_durations) / len(completed_durations) if completed_durations else 0
        
        return {
            'total_jobs': total_jobs,
            'active_jobs': active_jobs,
            'completed_jobs': completed_jobs,
            'failed_jobs': failed_jobs,
            'success_rate': success_rate,
            'average_duration_minutes': avg_duration / 60 if avg_duration else 0,
            'jobs_per_hour': total_jobs / max(hours, 1) if hours > 0 else 0
        }


def performance_monitor(func):
    """Decorator to monitor function performance"""
    @wraps(func)
    def wrapper(*args, **kwargs):
        start_time = time.time()
        
        try:
            result = func(*args, **kwargs)
            success = True
            error = None
        except Exception as e:
            result = None
            success = False
            error = str(e)
            raise
        finally:
            execution_time = time.time() - start_time
            
            # Log performance metric
            metric = PerformanceMetric(
                timestamp=datetime.now().isoformat(),
                component="Flask Application",
                metric_name=f"{func.__name__}_execution_time",
                value=execution_time,
                unit="seconds",
                tags={
                    "function": func.__name__,
                    "success": str(success),
                    "error": error
                }
            )
            
            # Store in database (simplified for demo)
            try:
                collector = PerformanceMetricsCollector()
                collector.store_metrics([metric])
            except Exception:
                pass  # Don't fail the original function if metrics fail
        
        return result
    
    return wrapper


# Performance dashboard data aggregation
class PerformanceDashboard:
    """Aggregates performance data for dashboard display"""
    
    def __init__(self):
        self.collector = PerformanceMetricsCollector()
    
    def get_dashboard_data(self) -> Dict[str, Any]:
        """Get comprehensive dashboard data"""
        summary = self.collector.get_optimization_summary()
        trends = self.collector.get_performance_trends(hours=24)
        alerts = self.collector.get_alerts()
        
        # Add retirement job data
        retirement_summary = self.collector.get_retirement_job_summary(hours=24)
        recent_jobs = self.collector.get_retirement_jobs(hours=24)
        active_jobs = self.collector.get_retirement_jobs(hours=24, status='running')
        
        return {
            'summary': asdict(summary),
            'trends': trends,
            'alerts': alerts,
            'retirement_jobs': {
                'summary': retirement_summary,
                'recent_jobs': [asdict(job) for job in recent_jobs[:10]],  # Last 10 jobs
                'active_jobs': [asdict(job) for job in active_jobs],
                'total_active': len(active_jobs)
            },
            'last_updated': datetime.now().isoformat(),
            'optimization_status': self._get_optimization_status(summary),
            'performance_grade': self._calculate_performance_grade(summary)
        }
    
    def _get_optimization_status(self, summary: OptimizationSummary) -> str:
        """Determine overall optimization status"""
        if summary.overall_performance_score >= 80:
            return "Excellent"
        elif summary.overall_performance_score >= 60:
            return "Good"
        elif summary.overall_performance_score >= 40:
            return "Needs Improvement"
        else:
            return "Critical"
    
    def _calculate_performance_grade(self, summary: OptimizationSummary) -> str:
        """Calculate letter grade for performance"""
        score = summary.overall_performance_score
        
        if score >= 90:
            return "A+"
        elif score >= 85:
            return "A"
        elif score >= 80:
            return "A-"
        elif score >= 75:
            return "B+"
        elif score >= 70:
            return "B"
        elif score >= 65:
            return "B-"
        elif score >= 60:
            return "C+"
        elif score >= 55:
            return "C"
        elif score >= 50:
            return "C-"
        elif score >= 45:
            return "D+"
        elif score >= 40:
            return "D"
        else:
            return "F"


class AAPJobMonitor:
    """Monitor AAP jobs and update retirement job tracking"""
    
    def __init__(self, aap_url: str, aap_token: str):
        self.aap_url = aap_url
        self.aap_token = aap_token
        self.collector = PerformanceMetricsCollector()
        
    def monitor_job(self, job_id: str, target_hosts: List[str], job_type: str = "retirement") -> RetirementJobMetrics:
        """Monitor an AAP job and return current status"""
        import requests
        
        try:
            headers = {
                "Authorization": f"Bearer {self.aap_token}",
                "Content-Type": "application/json"
            }
            
            response = requests.get(
                f"{self.aap_url}/api/v2/jobs/{job_id}/",
                headers=headers,
                verify=False,
                timeout=10
            )
            
            if response.status_code == 200:
                job_data = response.json()
                
                # Map AAP status to our status
                aap_status = job_data.get('status', 'unknown')
                status = self._map_aap_status(aap_status)
                
                # Calculate duration if finished
                start_time = job_data.get('started')
                end_time = job_data.get('finished')
                duration = None
                
                if start_time and end_time:
                    start_dt = datetime.fromisoformat(start_time.replace('Z', '+00:00'))
                    end_dt = datetime.fromisoformat(end_time.replace('Z', '+00:00'))
                    duration = (end_dt - start_dt).total_seconds()
                
                # Calculate success rate
                failed_hosts = job_data.get('failed', 0)
                total_hosts = len(target_hosts)
                success_rate = ((total_hosts - failed_hosts) / total_hosts * 100) if total_hosts > 0 else 0
                
                job_metrics = RetirementJobMetrics(
                    job_id=str(job_id),
                    status=status,
                    job_type=job_type,
                    target_hosts=target_hosts,
                    start_time=start_time or datetime.now().isoformat(),
                    end_time=end_time,
                    duration_seconds=duration,
                    success_rate=success_rate,
                    errors=self._extract_job_errors(job_data),
                    aap_template_id=str(job_data.get('job_template', '')),
                    extra_vars=job_data.get('extra_vars', {})
                )
                
                # Store/update in database
                self.collector.track_retirement_job(job_metrics)
                
                return job_metrics
                
        except Exception as e:
            # Create error job metrics
            job_metrics = RetirementJobMetrics(
                job_id=str(job_id),
                status="error",
                job_type=job_type,
                target_hosts=target_hosts,
                start_time=datetime.now().isoformat(),
                errors=[f"Monitoring error: {str(e)}"]
            )
            
            self.collector.track_retirement_job(job_metrics)
            return job_metrics
    
    def _map_aap_status(self, aap_status: str) -> str:
        """Map AAP job status to our standardized status"""
        status_map = {
            'pending': 'pending',
            'waiting': 'pending',
            'running': 'running',
            'successful': 'successful',
            'failed': 'failed',
            'error': 'failed',
            'canceled': 'failed',
            'never updated': 'pending'
        }
        return status_map.get(aap_status.lower(), 'unknown')
    
    def _extract_job_errors(self, job_data: Dict[str, Any]) -> List[str]:
        """Extract error messages from AAP job data"""
        errors = []
        
        if job_data.get('status') in ['failed', 'error']:
            if job_data.get('result_stdout'):
                # Parse stdout for error messages
                stdout = job_data['result_stdout']
                if 'FAILED' in stdout or 'ERROR' in stdout:
                    errors.append("Job execution failed - check AAP logs for details")
            
            if job_data.get('job_explanation'):
                errors.append(job_data['job_explanation'])
        
        return errors if errors else None