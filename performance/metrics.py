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
        
        return {
            'summary': asdict(summary),
            'trends': trends,
            'alerts': alerts,
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