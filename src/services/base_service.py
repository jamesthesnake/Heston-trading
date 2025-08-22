"""
Base Service Interface
Provides common service functionality and abstractions
"""
import asyncio
import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Dict, Any, Optional, List, Callable
from contextlib import asynccontextmanager

logger = logging.getLogger(__name__)

class ServiceStatus(Enum):
    """Service status states"""
    INITIALIZING = "initializing"
    RUNNING = "running"
    PAUSED = "paused"
    STOPPING = "stopping" 
    STOPPED = "stopped"
    ERROR = "error"

@dataclass
class ServiceConfig:
    """Base service configuration"""
    name: str
    enabled: bool = True
    auto_restart: bool = True
    heartbeat_interval: int = 30  # seconds
    timeout: int = 300  # seconds
    max_retries: int = 3
    retry_delay: int = 5  # seconds
    dependencies: List[str] = None
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.dependencies is None:
            self.dependencies = []
        if self.metadata is None:
            self.metadata = {}

class BaseService(ABC):
    """
    Base service class providing common functionality for all services
    All system services should inherit from this class
    """
    
    def __init__(self, config: ServiceConfig):
        """
        Initialize base service
        
        Args:
            config: Service configuration
        """
        self.config = config
        self.name = config.name
        self.status = ServiceStatus.INITIALIZING
        self.start_time: Optional[datetime] = None
        self.last_heartbeat: Optional[datetime] = None
        self.error_count = 0
        self.last_error: Optional[Exception] = None
        self.metrics: Dict[str, Any] = {}
        
        # Event callbacks
        self.on_start_callbacks: List[Callable] = []
        self.on_stop_callbacks: List[Callable] = []
        self.on_error_callbacks: List[Callable] = []
        
        # Internal state
        self._tasks: List[asyncio.Task] = []
        self._shutdown_event = asyncio.Event()
        self._heartbeat_task: Optional[asyncio.Task] = None
        
        logger.info(f"Service {self.name} initialized")
    
    @abstractmethod
    async def _initialize(self) -> bool:
        """
        Initialize the service - must be implemented by subclasses
        
        Returns:
            True if initialization successful
        """
        pass
    
    @abstractmethod
    async def _start(self) -> bool:
        """
        Start the service - must be implemented by subclasses
        
        Returns:
            True if start successful
        """
        pass
    
    @abstractmethod
    async def _stop(self) -> bool:
        """
        Stop the service - must be implemented by subclasses
        
        Returns:
            True if stop successful
        """
        pass
    
    @abstractmethod
    async def _health_check(self) -> Dict[str, Any]:
        """
        Perform health check - must be implemented by subclasses
        
        Returns:
            Health check results
        """
        pass
    
    async def start(self) -> bool:
        """
        Start the service with error handling and callbacks
        
        Returns:
            True if started successfully
        """
        try:
            if self.status in [ServiceStatus.RUNNING, ServiceStatus.INITIALIZING]:
                logger.warning(f"Service {self.name} already starting/running")
                return True
            
            logger.info(f"Starting service {self.name}")
            self.status = ServiceStatus.INITIALIZING
            
            # Initialize service
            if not await self._initialize():
                raise Exception("Service initialization failed")
            
            # Start service implementation
            if not await self._start():
                raise Exception("Service start failed")
            
            # Update status and timing
            self.status = ServiceStatus.RUNNING
            self.start_time = datetime.now()
            self.last_heartbeat = datetime.now()
            self.error_count = 0
            
            # Start heartbeat monitoring
            if self.config.heartbeat_interval > 0:
                self._heartbeat_task = asyncio.create_task(self._heartbeat_loop())
            
            # Call start callbacks
            for callback in self.on_start_callbacks:
                try:
                    if asyncio.iscoroutinefunction(callback):
                        await callback(self)
                    else:
                        callback(self)
                except Exception as e:
                    logger.error(f"Error in start callback for {self.name}: {e}")
            
            logger.info(f"Service {self.name} started successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to start service {self.name}: {e}")
            self.status = ServiceStatus.ERROR
            self.last_error = e
            self.error_count += 1
            await self._handle_error(e)
            return False
    
    async def stop(self) -> bool:
        """
        Stop the service with cleanup
        
        Returns:
            True if stopped successfully
        """
        try:
            if self.status == ServiceStatus.STOPPED:
                logger.warning(f"Service {self.name} already stopped")
                return True
            
            logger.info(f"Stopping service {self.name}")
            self.status = ServiceStatus.STOPPING
            
            # Set shutdown event
            self._shutdown_event.set()
            
            # Stop heartbeat monitoring
            if self._heartbeat_task:
                self._heartbeat_task.cancel()
                try:
                    await self._heartbeat_task
                except asyncio.CancelledError:
                    pass
            
            # Cancel all running tasks
            for task in self._tasks:
                if not task.done():
                    task.cancel()
            
            # Wait for tasks to complete
            if self._tasks:
                await asyncio.gather(*self._tasks, return_exceptions=True)
            
            # Stop service implementation
            await self._stop()
            
            # Update status
            self.status = ServiceStatus.STOPPED
            
            # Call stop callbacks
            for callback in self.on_stop_callbacks:
                try:
                    if asyncio.iscoroutinefunction(callback):
                        await callback(self)
                    else:
                        callback(self)
                except Exception as e:
                    logger.error(f"Error in stop callback for {self.name}: {e}")
            
            logger.info(f"Service {self.name} stopped successfully")
            return True
            
        except Exception as e:
            logger.error(f"Error stopping service {self.name}: {e}")
            self.status = ServiceStatus.ERROR
            self.last_error = e
            return False
    
    async def restart(self) -> bool:
        """
        Restart the service
        
        Returns:
            True if restarted successfully
        """
        logger.info(f"Restarting service {self.name}")
        
        if not await self.stop():
            logger.error(f"Failed to stop service {self.name} for restart")
            return False
        
        # Wait a moment before restarting
        await asyncio.sleep(1)
        
        return await self.start()
    
    async def pause(self):
        """Pause the service"""
        if self.status == ServiceStatus.RUNNING:
            self.status = ServiceStatus.PAUSED
            logger.info(f"Service {self.name} paused")
    
    async def resume(self):
        """Resume the service"""
        if self.status == ServiceStatus.PAUSED:
            self.status = ServiceStatus.RUNNING
            logger.info(f"Service {self.name} resumed")
    
    def is_healthy(self) -> bool:
        """Check if service is healthy"""
        return self.status == ServiceStatus.RUNNING and self.error_count < self.config.max_retries
    
    def is_running(self) -> bool:
        """Check if service is running"""
        return self.status == ServiceStatus.RUNNING
    
    def get_status(self) -> Dict[str, Any]:
        """
        Get comprehensive service status
        
        Returns:
            Service status information
        """
        uptime = None
        if self.start_time:
            uptime = (datetime.now() - self.start_time).total_seconds()
        
        return {
            'name': self.name,
            'status': self.status.value,
            'healthy': self.is_healthy(),
            'start_time': self.start_time,
            'uptime_seconds': uptime,
            'last_heartbeat': self.last_heartbeat,
            'error_count': self.error_count,
            'last_error': str(self.last_error) if self.last_error else None,
            'config': {
                'enabled': self.config.enabled,
                'auto_restart': self.config.auto_restart,
                'heartbeat_interval': self.config.heartbeat_interval,
                'dependencies': self.config.dependencies
            },
            'metrics': self.metrics
        }
    
    def add_callback(self, event: str, callback: Callable):
        """
        Add event callback
        
        Args:
            event: Event type ('start', 'stop', 'error')
            callback: Callback function
        """
        if event == 'start':
            self.on_start_callbacks.append(callback)
        elif event == 'stop':
            self.on_stop_callbacks.append(callback)
        elif event == 'error':
            self.on_error_callbacks.append(callback)
        else:
            raise ValueError(f"Unknown event type: {event}")
    
    def update_metrics(self, metrics: Dict[str, Any]):
        """Update service metrics"""
        self.metrics.update(metrics)
    
    async def _heartbeat_loop(self):
        """Internal heartbeat monitoring loop"""
        try:
            while not self._shutdown_event.is_set():
                try:
                    # Perform health check
                    health_results = await self._health_check()
                    
                    # Update heartbeat
                    self.last_heartbeat = datetime.now()
                    
                    # Update metrics with health check results
                    if health_results:
                        self.metrics.update(health_results)
                    
                    logger.debug(f"Heartbeat for service {self.name}")
                    
                except Exception as e:
                    logger.error(f"Health check failed for service {self.name}: {e}")
                    await self._handle_error(e)
                
                # Wait for next heartbeat
                try:
                    await asyncio.wait_for(
                        self._shutdown_event.wait(),
                        timeout=self.config.heartbeat_interval
                    )
                    break  # Shutdown requested
                except asyncio.TimeoutError:
                    continue  # Normal timeout, continue heartbeat
                    
        except asyncio.CancelledError:
            logger.debug(f"Heartbeat loop cancelled for service {self.name}")
        except Exception as e:
            logger.error(f"Unexpected error in heartbeat loop for service {self.name}: {e}")
    
    async def _handle_error(self, error: Exception):
        """Handle service errors"""
        self.last_error = error
        self.error_count += 1
        
        logger.error(f"Service {self.name} error #{self.error_count}: {error}")
        
        # Call error callbacks
        for callback in self.on_error_callbacks:
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback(self, error)
                else:
                    callback(self, error)
            except Exception as e:
                logger.error(f"Error in error callback for {self.name}: {e}")
        
        # Auto-restart if configured and not exceeded max retries
        if (self.config.auto_restart and 
            self.error_count < self.config.max_retries and 
            self.status not in [ServiceStatus.STOPPING, ServiceStatus.STOPPED]):
            
            logger.info(f"Auto-restarting service {self.name} in {self.config.retry_delay} seconds")
            await asyncio.sleep(self.config.retry_delay)
            await self.restart()
        else:
            self.status = ServiceStatus.ERROR
    
    def create_task(self, coro) -> asyncio.Task:
        """
        Create and track a task for this service
        
        Args:
            coro: Coroutine to execute
            
        Returns:
            Created task
        """
        task = asyncio.create_task(coro)
        self._tasks.append(task)
        
        # Remove completed tasks
        self._tasks = [t for t in self._tasks if not t.done()]
        
        return task
    
    @asynccontextmanager
    async def service_context(self):
        """Context manager for service lifecycle"""
        try:
            await self.start()
            yield self
        finally:
            await self.stop()