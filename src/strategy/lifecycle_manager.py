"""
Lifecycle Manager - System Health and Startup/Shutdown Module
Handles system initialization, health monitoring, and graceful shutdown
"""
import asyncio
import logging
import psutil
import time
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)

class SystemHealth(Enum):
    HEALTHY = "healthy"
    WARNING = "warning"
    CRITICAL = "critical"
    UNKNOWN = "unknown"

@dataclass
class HealthMetrics:
    """System health metrics"""
    cpu_usage: float = 0.0
    memory_usage: float = 0.0
    disk_usage: float = 0.0
    uptime_seconds: float = 0.0
    error_rate: float = 0.0
    data_latency: float = 0.0
    last_update: Optional[datetime] = None

@dataclass
class HealthAlert:
    """Health alert/warning"""
    timestamp: datetime
    level: str  # 'info', 'warning', 'error', 'critical'
    component: str
    message: str
    metrics: Dict[str, Any]

class LifecycleManager:
    """
    Lifecycle manager responsible for system startup, health monitoring,
    and graceful shutdown procedures
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize the lifecycle manager
        
        Args:
            config: Lifecycle configuration
        """
        self.config = config
        self.lifecycle_config = config.get('lifecycle', {})
        
        # Health monitoring parameters
        self.health_check_interval = self.lifecycle_config.get('health_check_interval', 30)  # seconds
        self.cpu_warning_threshold = self.lifecycle_config.get('cpu_warning_threshold', 80.0)  # %
        self.memory_warning_threshold = self.lifecycle_config.get('memory_warning_threshold', 85.0)  # %
        self.error_rate_threshold = self.lifecycle_config.get('error_rate_threshold', 0.1)  # 10%
        
        # System state
        self.is_initialized = False
        self.startup_time = None
        self.shutdown_requested = False
        self.health_monitor_task: Optional[asyncio.Task] = None
        
        # Health tracking
        self.current_health = SystemHealth.UNKNOWN
        self.health_metrics = HealthMetrics()
        self.health_alerts: List[HealthAlert] = []
        self.performance_history = []
        
        # Component health tracking
        self.component_health = {
            'data_feed': SystemHealth.UNKNOWN,
            'strategy_engine': SystemHealth.UNKNOWN,
            'portfolio_manager': SystemHealth.UNKNOWN,
            'risk_management': SystemHealth.UNKNOWN
        }
        
        # Error tracking
        self.error_count = 0
        self.error_history = []
        self.last_error_reset = datetime.now()
        
        logger.info("Lifecycle manager initialized")
    
    async def startup(self) -> bool:
        """
        Perform system startup procedures
        
        Returns:
            True if startup successful, False otherwise
        """
        try:
            logger.info("🚀 Starting system lifecycle manager...")
            
            self.startup_time = datetime.now()
            
            # 1. Initialize system health monitoring
            await self._initialize_health_monitoring()
            
            # 2. Check system prerequisites
            if not await self._check_system_prerequisites():
                logger.error("System prerequisites not met")
                return False
            
            # 3. Initialize logging and monitoring
            await self._initialize_monitoring()
            
            # 4. Start health monitoring task
            self.health_monitor_task = asyncio.create_task(self._health_monitoring_loop())
            
            self.is_initialized = True
            self.current_health = SystemHealth.HEALTHY
            
            logger.info("✅ System lifecycle manager started successfully")
            
            # Log system information
            await self._log_system_info()
            
            return True
            
        except Exception as e:
            logger.error(f"System startup failed: {e}")
            await self._cleanup_startup_failure()
            return False
    
    async def shutdown(self):
        """Perform graceful system shutdown"""
        try:
            logger.info("🛑 Starting graceful system shutdown...")
            
            self.shutdown_requested = True
            
            # 1. Stop health monitoring
            if self.health_monitor_task:
                self.health_monitor_task.cancel()
                try:
                    await self.health_monitor_task
                except asyncio.CancelledError:
                    pass
            
            # 2. Generate shutdown report
            await self._generate_shutdown_report()
            
            # 3. Clean up resources
            await self._cleanup_resources()
            
            self.is_initialized = False
            
            runtime = datetime.now() - self.startup_time if self.startup_time else timedelta(0)
            logger.info(f"✅ System shutdown complete (runtime: {runtime})")
            
        except Exception as e:
            logger.error(f"Error during system shutdown: {e}")
    
    async def check_health(self) -> Dict[str, Any]:
        """
        Perform comprehensive health check
        
        Returns:
            Dictionary with health status and metrics
        """
        try:
            # Update current health metrics
            await self._update_health_metrics()
            
            # Determine overall health status
            overall_health = self._calculate_overall_health()
            
            # Check for new alerts
            new_alerts = self._check_health_alerts()
            
            return {
                'overall_health': overall_health.value,
                'health_metrics': {
                    'cpu_usage': self.health_metrics.cpu_usage,
                    'memory_usage': self.health_metrics.memory_usage,
                    'disk_usage': self.health_metrics.disk_usage,
                    'uptime_seconds': self.health_metrics.uptime_seconds,
                    'error_rate': self.health_metrics.error_rate,
                    'data_latency': self.health_metrics.data_latency
                },
                'component_health': {k: v.value for k, v in self.component_health.items()},
                'new_alerts': len(new_alerts),
                'total_alerts': len(self.health_alerts),
                'last_update': datetime.now()
            }
            
        except Exception as e:
            logger.error(f"Error checking system health: {e}")
            return {
                'overall_health': SystemHealth.UNKNOWN.value,
                'error': str(e)
            }
    
    async def _initialize_health_monitoring(self):
        """Initialize health monitoring systems"""
        try:
            # Initialize system metrics
            self.health_metrics = HealthMetrics(last_update=datetime.now())
            
            # Clear previous alerts
            self.health_alerts.clear()
            
            # Reset error tracking
            self.error_count = 0
            self.error_history.clear()
            self.last_error_reset = datetime.now()
            
            logger.debug("Health monitoring initialized")
            
        except Exception as e:
            logger.error(f"Failed to initialize health monitoring: {e}")
            raise
    
    async def _check_system_prerequisites(self) -> bool:
        """Check system prerequisites and dependencies"""
        try:
            prerequisites_met = True
            
            # Check available memory
            memory = psutil.virtual_memory()
            available_gb = memory.available / (1024**3)
            
            if available_gb < 1.0:  # Less than 1GB available
                logger.warning(f"Low available memory: {available_gb:.1f}GB")
                prerequisites_met = False
            
            # Check disk space
            disk = psutil.disk_usage('/')
            free_gb = disk.free / (1024**3)
            
            if free_gb < 5.0:  # Less than 5GB free
                logger.warning(f"Low disk space: {free_gb:.1f}GB free")
                prerequisites_met = False
            
            # Check CPU load
            cpu_percent = psutil.cpu_percent(interval=1)
            
            if cpu_percent > 90.0:
                logger.warning(f"High CPU usage: {cpu_percent:.1f}%")
                # Don't fail startup for high CPU, just warn
            
            if prerequisites_met:
                logger.info("✅ System prerequisites check passed")
            else:
                logger.error("❌ System prerequisites check failed")
            
            return prerequisites_met
            
        except Exception as e:
            logger.error(f"Error checking system prerequisites: {e}")
            return False
    
    async def _initialize_monitoring(self):
        """Initialize logging and monitoring systems"""
        try:
            # This would set up additional monitoring systems
            # For now, just log that monitoring is initialized
            logger.debug("Monitoring systems initialized")
            
        except Exception as e:
            logger.error(f"Failed to initialize monitoring: {e}")
            raise
    
    async def _health_monitoring_loop(self):
        """Main health monitoring loop"""
        logger.info(f"Starting health monitoring loop (interval: {self.health_check_interval}s)")
        
        try:
            while not self.shutdown_requested:
                # Update health metrics
                await self._update_health_metrics()
                
                # Check for alerts
                new_alerts = self._check_health_alerts()
                
                # Log alerts
                for alert in new_alerts:
                    if alert.level == 'critical':
                        logger.error(f"CRITICAL: {alert.component} - {alert.message}")
                    elif alert.level == 'warning':
                        logger.warning(f"WARNING: {alert.component} - {alert.message}")
                    elif alert.level == 'error':
                        logger.error(f"ERROR: {alert.component} - {alert.message}")
                
                # Update overall health status
                self.current_health = self._calculate_overall_health()
                
                # Wait for next check
                await asyncio.sleep(self.health_check_interval)
                
        except asyncio.CancelledError:
            logger.info("Health monitoring loop cancelled")
        except Exception as e:
            logger.error(f"Error in health monitoring loop: {e}")
    
    async def _update_health_metrics(self):
        """Update current health metrics"""
        try:
            # CPU usage
            self.health_metrics.cpu_usage = psutil.cpu_percent(interval=0.1)
            
            # Memory usage
            memory = psutil.virtual_memory()
            self.health_metrics.memory_usage = memory.percent
            
            # Disk usage
            disk = psutil.disk_usage('/')
            self.health_metrics.disk_usage = (disk.used / disk.total) * 100
            
            # Uptime
            if self.startup_time:
                uptime = datetime.now() - self.startup_time
                self.health_metrics.uptime_seconds = uptime.total_seconds()
            
            # Error rate (errors per minute)
            current_time = datetime.now()
            time_window = timedelta(minutes=5)
            recent_errors = [e for e in self.error_history 
                           if current_time - e['timestamp'] <= time_window]
            self.health_metrics.error_rate = len(recent_errors) / 5.0  # errors per minute
            
            # Data latency (placeholder - would be calculated from actual data feed)
            self.health_metrics.data_latency = 0.1  # 100ms placeholder
            
            self.health_metrics.last_update = datetime.now()
            
        except Exception as e:
            logger.error(f"Error updating health metrics: {e}")
    
    def _check_health_alerts(self) -> List[HealthAlert]:
        """Check for new health alerts"""
        new_alerts = []
        
        try:
            current_time = datetime.now()
            
            # CPU usage alert
            if self.health_metrics.cpu_usage > self.cpu_warning_threshold:
                alert = HealthAlert(
                    timestamp=current_time,
                    level='warning' if self.health_metrics.cpu_usage < 95 else 'critical',
                    component='system',
                    message=f"High CPU usage: {self.health_metrics.cpu_usage:.1f}%",
                    metrics={'cpu_usage': self.health_metrics.cpu_usage}
                )
                new_alerts.append(alert)
            
            # Memory usage alert
            if self.health_metrics.memory_usage > self.memory_warning_threshold:
                alert = HealthAlert(
                    timestamp=current_time,
                    level='warning' if self.health_metrics.memory_usage < 95 else 'critical',
                    component='system',
                    message=f"High memory usage: {self.health_metrics.memory_usage:.1f}%",
                    metrics={'memory_usage': self.health_metrics.memory_usage}
                )
                new_alerts.append(alert)
            
            # Error rate alert
            if self.health_metrics.error_rate > self.error_rate_threshold:
                alert = HealthAlert(
                    timestamp=current_time,
                    level='warning' if self.health_metrics.error_rate < 0.5 else 'critical',
                    component='strategy',
                    message=f"High error rate: {self.health_metrics.error_rate:.2f} errors/min",
                    metrics={'error_rate': self.health_metrics.error_rate}
                )
                new_alerts.append(alert)
            
            # Add new alerts to history
            self.health_alerts.extend(new_alerts)
            
            # Keep only recent alerts
            alert_retention = timedelta(hours=24)
            self.health_alerts = [a for a in self.health_alerts 
                                if current_time - a.timestamp <= alert_retention]
            
            return new_alerts
            
        except Exception as e:
            logger.error(f"Error checking health alerts: {e}")
            return []
    
    def _calculate_overall_health(self) -> SystemHealth:
        """Calculate overall system health status"""
        try:
            # Check for critical conditions
            if (self.health_metrics.cpu_usage > 95 or 
                self.health_metrics.memory_usage > 95 or
                self.health_metrics.error_rate > 0.5):
                return SystemHealth.CRITICAL
            
            # Check for warning conditions
            if (self.health_metrics.cpu_usage > self.cpu_warning_threshold or
                self.health_metrics.memory_usage > self.memory_warning_threshold or
                self.health_metrics.error_rate > self.error_rate_threshold):
                return SystemHealth.WARNING
            
            # Check component health
            critical_components = [h for h in self.component_health.values() 
                                 if h == SystemHealth.CRITICAL]
            if critical_components:
                return SystemHealth.CRITICAL
            
            warning_components = [h for h in self.component_health.values() 
                                if h == SystemHealth.WARNING]
            if warning_components:
                return SystemHealth.WARNING
            
            return SystemHealth.HEALTHY
            
        except Exception as e:
            logger.error(f"Error calculating overall health: {e}")
            return SystemHealth.UNKNOWN
    
    async def _log_system_info(self):
        """Log system information at startup"""
        try:
            # System information
            logger.info("📊 System Information:")
            logger.info(f"   CPU Count: {psutil.cpu_count()}")
            logger.info(f"   CPU Usage: {psutil.cpu_percent():.1f}%")
            
            memory = psutil.virtual_memory()
            logger.info(f"   Memory Total: {memory.total / (1024**3):.1f}GB")
            logger.info(f"   Memory Available: {memory.available / (1024**3):.1f}GB")
            
            disk = psutil.disk_usage('/')
            logger.info(f"   Disk Total: {disk.total / (1024**3):.1f}GB")
            logger.info(f"   Disk Free: {disk.free / (1024**3):.1f}GB")
            
        except Exception as e:
            logger.error(f"Error logging system info: {e}")
    
    async def _generate_shutdown_report(self):
        """Generate system shutdown report"""
        try:
            if not self.startup_time:
                return
            
            runtime = datetime.now() - self.startup_time
            
            logger.info("📊 System Shutdown Report:")
            logger.info(f"   Runtime: {runtime}")
            logger.info(f"   Total Errors: {len(self.error_history)}")
            logger.info(f"   Total Alerts: {len(self.health_alerts)}")
            logger.info(f"   Final Health Status: {self.current_health.value}")
            
            # Alert summary
            alert_counts = {}
            for alert in self.health_alerts:
                alert_counts[alert.level] = alert_counts.get(alert.level, 0) + 1
            
            if alert_counts:
                logger.info(f"   Alert Summary: {alert_counts}")
            
        except Exception as e:
            logger.error(f"Error generating shutdown report: {e}")
    
    async def _cleanup_startup_failure(self):
        """Clean up after startup failure"""
        try:
            if self.health_monitor_task:
                self.health_monitor_task.cancel()
            
            logger.info("Cleaned up after startup failure")
            
        except Exception as e:
            logger.error(f"Error cleaning up startup failure: {e}")
    
    async def _cleanup_resources(self):
        """Clean up system resources"""
        try:
            # Resource cleanup would go here
            logger.debug("System resources cleaned up")
            
        except Exception as e:
            logger.error(f"Error cleaning up resources: {e}")
    
    # Public API methods
    
    def record_error(self, error: Exception, component: str = 'unknown'):
        """Record an error for health monitoring"""
        try:
            error_entry = {
                'timestamp': datetime.now(),
                'component': component,
                'error_type': type(error).__name__,
                'message': str(error)
            }
            
            self.error_history.append(error_entry)
            self.error_count += 1
            
            # Keep only recent errors
            retention_period = timedelta(hours=24)
            current_time = datetime.now()
            self.error_history = [e for e in self.error_history 
                                if current_time - e['timestamp'] <= retention_period]
            
        except Exception as e:
            logger.error(f"Error recording error: {e}")
    
    def update_component_health(self, component: str, health: SystemHealth):
        """Update health status of a specific component"""
        try:
            if component in self.component_health:
                self.component_health[component] = health
                logger.debug(f"Component {component} health updated to {health.value}")
            
        except Exception as e:
            logger.error(f"Error updating component health: {e}")
    
    def get_status(self) -> Dict[str, Any]:
        """Get lifecycle manager status"""
        try:
            return {
                'is_initialized': self.is_initialized,
                'startup_time': self.startup_time,
                'uptime_seconds': self.health_metrics.uptime_seconds,
                'current_health': self.current_health.value,
                'error_count': self.error_count,
                'shutdown_requested': self.shutdown_requested
            }
        except Exception as e:
            return {'error': str(e)}
    
    def get_detailed_health(self) -> Dict[str, Any]:
        """Get detailed health information"""
        try:
            recent_alerts = [
                {
                    'timestamp': a.timestamp,
                    'level': a.level,
                    'component': a.component,
                    'message': a.message
                }
                for a in self.health_alerts[-10:]  # Last 10 alerts
            ]
            
            return {
                'current_health': self.current_health.value,
                'health_metrics': {
                    'cpu_usage': self.health_metrics.cpu_usage,
                    'memory_usage': self.health_metrics.memory_usage,
                    'disk_usage': self.health_metrics.disk_usage,
                    'error_rate': self.health_metrics.error_rate,
                    'uptime_seconds': self.health_metrics.uptime_seconds
                },
                'component_health': {k: v.value for k, v in self.component_health.items()},
                'recent_alerts': recent_alerts,
                'total_alerts': len(self.health_alerts),
                'total_errors': len(self.error_history)
            }
        except Exception as e:
            return {'error': str(e)}