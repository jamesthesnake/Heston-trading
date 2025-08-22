"""
Notification Service
Unified interface for system notifications with multiple channels and priority handling
"""
import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Callable, Set
from dataclasses import dataclass, field
from enum import Enum
import json
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

from .base_service import BaseService, ServiceConfig

logger = logging.getLogger(__name__)

class NotificationLevel(Enum):
    """Notification priority levels"""
    DEBUG = "debug"
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"

class NotificationChannel(Enum):
    """Notification delivery channels"""
    EMAIL = "email"
    SLACK = "slack"
    WEBHOOK = "webhook"
    SMS = "sms"
    CONSOLE = "console"
    FILE = "file"

class NotificationStatus(Enum):
    """Notification delivery status"""
    PENDING = "pending"
    SENT = "sent"
    FAILED = "failed"
    RETRY = "retry"

@dataclass
class NotificationTemplate:
    """Notification template"""
    name: str
    subject_template: str
    body_template: str
    channels: List[NotificationChannel]
    level: NotificationLevel
    throttle_minutes: int = 0
    max_retries: int = 3
    
@dataclass
class Notification:
    """Notification message"""
    id: str
    level: NotificationLevel
    title: str
    message: str
    
    # Delivery settings
    channels: List[NotificationChannel] = field(default_factory=list)
    recipients: List[str] = field(default_factory=list)
    
    # Metadata
    source: Optional[str] = None
    category: Optional[str] = None
    tags: List[str] = field(default_factory=list)
    data: Dict[str, Any] = field(default_factory=dict)
    
    # Delivery tracking
    status: NotificationStatus = NotificationStatus.PENDING
    created_time: datetime = field(default_factory=datetime.now)
    sent_time: Optional[datetime] = None
    retry_count: int = 0
    max_retries: int = 3
    
    # Delivery results
    delivery_results: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    error_message: Optional[str] = None

class NotificationService(BaseService):
    """
    Notification Service providing unified message delivery
    across multiple channels with priority handling and throttling
    """
    
    def __init__(self, config: ServiceConfig, strategy_config: Dict[str, Any]):
        super().__init__(config)
        
        self.strategy_config = strategy_config
        self.notification_config = strategy_config.get('notifications', {})
        
        # Notification storage
        self.notifications: Dict[str, Notification] = {}
        self.notification_queue = asyncio.PriorityQueue()
        self.notification_counter = 0
        
        # Templates
        self.templates: Dict[str, NotificationTemplate] = {}
        
        # Channel configurations
        self.channel_configs: Dict[NotificationChannel, Dict[str, Any]] = {}
        self.enabled_channels: Set[NotificationChannel] = set()
        
        # Throttling
        self.throttle_cache: Dict[str, datetime] = {}  # key -> last_sent_time
        self.throttle_counts: Dict[str, int] = {}      # key -> count_today
        
        # Subscribers
        self.subscribers: Dict[str, List[Callable]] = {level.value: [] for level in NotificationLevel}
        self.channel_subscribers: Dict[NotificationChannel, List[str]] = {}
        
        # Statistics
        self.notification_stats = {
            'total_sent': 0,
            'failed_deliveries': 0,
            'by_level': {level.value: 0 for level in NotificationLevel},
            'by_channel': {channel.value: 0 for channel in NotificationChannel},
            'avg_delivery_time_ms': 0.0,
            'throttled_messages': 0
        }
        
        # Configuration
        self.max_queue_size = self.notification_config.get('max_queue_size', 1000)
        self.batch_size = self.notification_config.get('batch_size', 10)
        self.retry_delay = self.notification_config.get('retry_delay', 60)  # seconds
        self.daily_limit = self.notification_config.get('daily_limit', 1000)
        
        logger.info("Notification Service initialized")
    
    async def _initialize(self) -> bool:
        """Initialize notification channels and templates"""
        try:
            # Initialize channels
            channels_config = self.notification_config.get('channels', {})
            
            for channel_name, channel_config in channels_config.items():
                try:
                    channel = NotificationChannel(channel_name)
                    if channel_config.get('enabled', True):
                        self.channel_configs[channel] = channel_config
                        self.enabled_channels.add(channel)
                        logger.info(f"Notification channel {channel_name} enabled")
                        
                        # Initialize channel-specific settings
                        await self._initialize_channel(channel, channel_config)
                        
                except ValueError:
                    logger.warning(f"Unknown notification channel: {channel_name}")
                except Exception as e:
                    logger.error(f"Failed to initialize channel {channel_name}: {e}")
            
            # Load templates
            templates_config = self.notification_config.get('templates', {})
            for template_name, template_config in templates_config.items():
                try:
                    template = NotificationTemplate(
                        name=template_name,
                        subject_template=template_config['subject'],
                        body_template=template_config['body'],
                        channels=[NotificationChannel(c) for c in template_config.get('channels', ['email'])],
                        level=NotificationLevel(template_config.get('level', 'info')),
                        throttle_minutes=template_config.get('throttle_minutes', 0),
                        max_retries=template_config.get('max_retries', 3)
                    )
                    self.templates[template_name] = template
                    logger.info(f"Notification template {template_name} loaded")
                except Exception as e:
                    logger.error(f"Failed to load template {template_name}: {e}")
            
            # Setup default subscribers
            await self._setup_default_subscribers()
            
            logger.info(f"Notification service initialized with {len(self.enabled_channels)} channels")
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize notification service: {e}")
            return False
    
    async def _start(self) -> bool:
        """Start notification processing"""
        try:
            # Start notification processor
            self.create_task(self._process_notification_queue())
            
            # Start retry processor
            self.create_task(self._process_retries())
            
            # Start daily reset
            self.create_task(self._daily_reset_loop())
            
            # Start cleanup
            self.create_task(self._cleanup_loop())
            
            logger.info("Notification service started")
            return True
            
        except Exception as e:
            logger.error(f"Failed to start notification service: {e}")
            return False
    
    async def _stop(self) -> bool:
        """Stop notification service"""
        try:
            # Process remaining notifications
            remaining = self.notification_queue.qsize()
            if remaining > 0:
                logger.info(f"Processing {remaining} remaining notifications")
                # Give some time to process
                await asyncio.sleep(5)
            
            logger.info("Notification service stopped")
            return True
            
        except Exception as e:
            logger.error(f"Error stopping notification service: {e}")
            return False
    
    async def _health_check(self) -> Dict[str, Any]:
        """Perform health check"""
        health_data = {
            'channels': {
                'enabled': len(self.enabled_channels),
                'configured': len(self.channel_configs),
                'available': [c.value for c in self.enabled_channels]
            },
            'queue': {
                'pending': self.notification_queue.qsize(),
                'max_size': self.max_queue_size,
                'total_processed': self.notification_stats['total_sent']
            },
            'templates': {
                'loaded': len(self.templates)
            },
            'throttling': {
                'active_throttles': len(self.throttle_cache),
                'throttled_today': self.notification_stats['throttled_messages']
            },
            'performance': {
                'avg_delivery_time_ms': self.notification_stats['avg_delivery_time_ms'],
                'success_rate': (self.notification_stats['total_sent'] / 
                               max(self.notification_stats['total_sent'] + self.notification_stats['failed_deliveries'], 1))
            }
        }
        
        return health_data
    
    async def send_notification(self, notification: Notification) -> str:
        """
        Send notification
        
        Args:
            notification: Notification to send
            
        Returns:
            Notification ID
        """
        try:
            # Generate ID if not provided
            if not notification.id:
                self.notification_counter += 1
                notification.id = f"notif_{self.notification_counter}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            
            # Store notification
            self.notifications[notification.id] = notification
            
            # Check throttling
            if await self._is_throttled(notification):
                self.notification_stats['throttled_messages'] += 1
                logger.info(f"Notification {notification.id} throttled")
                return notification.id
            
            # Check daily limit
            total_today = sum(self.throttle_counts.values())
            if total_today >= self.daily_limit:
                logger.warning(f"Daily notification limit reached: {total_today}")
                notification.status = NotificationStatus.FAILED
                notification.error_message = "Daily limit exceeded"
                return notification.id
            
            # Add to queue with priority
            priority = self._get_priority(notification.level)
            await self.notification_queue.put((priority, notification))
            
            logger.info(f"Notification {notification.id} queued: {notification.title}")
            return notification.id
            
        except Exception as e:
            logger.error(f"Error sending notification: {e}")
            if notification.id:
                notification.status = NotificationStatus.FAILED
                notification.error_message = str(e)
            raise
    
    async def send_from_template(self, template_name: str, data: Dict[str, Any],
                                recipients: List[str] = None) -> str:
        """Send notification using template"""
        try:
            template = self.templates.get(template_name)
            if not template:
                raise ValueError(f"Template {template_name} not found")
            
            # Render template
            subject = self._render_template(template.subject_template, data)
            body = self._render_template(template.body_template, data)
            
            # Create notification
            notification = Notification(
                id="",  # Will be generated
                level=template.level,
                title=subject,
                message=body,
                channels=template.channels,
                recipients=recipients or [],
                source=data.get('source', 'template'),
                category=template_name,
                data=data,
                max_retries=template.max_retries
            )
            
            return await self.send_notification(notification)
            
        except Exception as e:
            logger.error(f"Error sending notification from template {template_name}: {e}")
            raise
    
    async def send_alert(self, level: NotificationLevel, title: str, message: str,
                        channels: List[NotificationChannel] = None,
                        recipients: List[str] = None, **kwargs) -> str:
        """Send alert notification"""
        notification = Notification(
            id="",
            level=level,
            title=title,
            message=message,
            channels=channels or [NotificationChannel.EMAIL, NotificationChannel.CONSOLE],
            recipients=recipients or [],
            source=kwargs.get('source', 'alert'),
            category=kwargs.get('category', 'general'),
            tags=kwargs.get('tags', []),
            data=kwargs.get('data', {})
        )
        
        return await self.send_notification(notification)
    
    def subscribe(self, level: NotificationLevel, callback: Callable):
        """Subscribe to notifications of a specific level"""
        self.subscribers[level.value].append(callback)
    
    def subscribe_channel(self, channel: NotificationChannel, recipient: str):
        """Subscribe recipient to channel"""
        if channel not in self.channel_subscribers:
            self.channel_subscribers[channel] = []
        if recipient not in self.channel_subscribers[channel]:
            self.channel_subscribers[channel].append(recipient)
    
    def get_notification(self, notification_id: str) -> Optional[Notification]:
        """Get notification by ID"""
        return self.notifications.get(notification_id)
    
    def get_recent_notifications(self, hours: int = 24) -> List[Notification]:
        """Get recent notifications"""
        cutoff = datetime.now() - timedelta(hours=hours)
        return [n for n in self.notifications.values() if n.created_time > cutoff]
    
    # Internal methods
    
    async def _initialize_channel(self, channel: NotificationChannel, config: Dict[str, Any]):
        """Initialize specific notification channel"""
        try:
            if channel == NotificationChannel.EMAIL:
                # Validate email configuration
                required_fields = ['smtp_server', 'smtp_port', 'username', 'password']
                for field in required_fields:
                    if field not in config:
                        logger.warning(f"Email channel missing required field: {field}")
            
            elif channel == NotificationChannel.SLACK:
                # Validate Slack configuration
                if 'webhook_url' not in config and 'bot_token' not in config:
                    logger.warning("Slack channel missing webhook_url or bot_token")
            
            elif channel == NotificationChannel.WEBHOOK:
                # Validate webhook configuration
                if 'url' not in config:
                    logger.warning("Webhook channel missing URL")
            
            elif channel == NotificationChannel.FILE:
                # Create log file directory
                log_file = config.get('log_file', 'logs/notifications.log')
                import os
                os.makedirs(os.path.dirname(log_file), exist_ok=True)
            
        except Exception as e:
            logger.error(f"Error initializing channel {channel.value}: {e}")
    
    async def _setup_default_subscribers(self):
        """Setup default notification subscribers"""
        # Subscribe console handler for critical messages
        def console_handler(notification: Notification):
            print(f"[{notification.level.value.upper()}] {notification.title}: {notification.message}")
        
        self.subscribe(NotificationLevel.CRITICAL, console_handler)
        self.subscribe(NotificationLevel.ERROR, console_handler)
    
    def _get_priority(self, level: NotificationLevel) -> int:
        """Get queue priority for notification level (lower = higher priority)"""
        priority_map = {
            NotificationLevel.CRITICAL: 1,
            NotificationLevel.ERROR: 2,
            NotificationLevel.WARNING: 3,
            NotificationLevel.INFO: 4,
            NotificationLevel.DEBUG: 5
        }
        return priority_map.get(level, 5)
    
    async def _is_throttled(self, notification: Notification) -> bool:
        """Check if notification should be throttled"""
        # Create throttle key
        throttle_key = f"{notification.category or 'general'}:{notification.level.value}"
        
        # Check if we have a throttle rule
        throttle_minutes = 0
        if notification.category in self.templates:
            throttle_minutes = self.templates[notification.category].throttle_minutes
        
        if throttle_minutes <= 0:
            return False
        
        # Check last sent time
        if throttle_key in self.throttle_cache:
            last_sent = self.throttle_cache[throttle_key]
            if (datetime.now() - last_sent).total_seconds() < (throttle_minutes * 60):
                return True
        
        return False
    
    def _render_template(self, template: str, data: Dict[str, Any]) -> str:
        """Render notification template"""
        try:
            # Simple template rendering (in production, use Jinja2 or similar)
            result = template
            for key, value in data.items():
                result = result.replace(f"{{{key}}}", str(value))
            return result
        except Exception as e:
            logger.error(f"Error rendering template: {e}")
            return template
    
    async def _process_notification_queue(self):
        """Process notification queue"""
        try:
            while not self._shutdown_event.is_set():
                try:
                    # Get notification from queue (with timeout)
                    try:
                        priority, notification = await asyncio.wait_for(
                            self.notification_queue.get(), timeout=1.0
                        )
                    except asyncio.TimeoutError:
                        continue
                    
                    # Process notification
                    await self._deliver_notification(notification)
                    
                    # Mark queue task as done
                    self.notification_queue.task_done()
                    
                except Exception as e:
                    logger.error(f"Error processing notification queue: {e}")
                
        except asyncio.CancelledError:
            logger.debug("Notification queue processor cancelled")
        except Exception as e:
            logger.error(f"Error in notification queue processor: {e}")
    
    async def _deliver_notification(self, notification: Notification):
        """Deliver notification through configured channels"""
        start_time = datetime.now()
        
        try:
            # Determine delivery channels
            channels = notification.channels or [NotificationChannel.CONSOLE]
            channels = [c for c in channels if c in self.enabled_channels]
            
            if not channels:
                logger.warning(f"No enabled channels for notification {notification.id}")
                notification.status = NotificationStatus.FAILED
                notification.error_message = "No enabled channels available"
                return
            
            # Deliver to each channel
            success_count = 0
            for channel in channels:
                try:
                    result = await self._deliver_to_channel(notification, channel)
                    notification.delivery_results[channel.value] = result
                    
                    if result.get('success', False):
                        success_count += 1
                        self.notification_stats['by_channel'][channel.value] += 1
                    
                except Exception as e:
                    logger.error(f"Error delivering to channel {channel.value}: {e}")
                    notification.delivery_results[channel.value] = {
                        'success': False,
                        'error': str(e)
                    }
            
            # Update notification status
            if success_count > 0:
                notification.status = NotificationStatus.SENT
                notification.sent_time = datetime.now()
                
                # Update throttle cache
                throttle_key = f"{notification.category or 'general'}:{notification.level.value}"
                self.throttle_cache[throttle_key] = datetime.now()
                
                # Update daily count
                date_key = datetime.now().strftime('%Y-%m-%d')
                if date_key not in self.throttle_counts:
                    self.throttle_counts[date_key] = 0
                self.throttle_counts[date_key] += 1
                
            else:
                notification.status = NotificationStatus.FAILED
                notification.error_message = "All channel deliveries failed"
            
            # Update statistics
            self.notification_stats['total_sent'] += 1
            self.notification_stats['by_level'][notification.level.value] += 1
            
            # Calculate average delivery time
            delivery_time = (datetime.now() - start_time).total_seconds() * 1000
            total_deliveries = self.notification_stats['total_sent']
            current_avg = self.notification_stats['avg_delivery_time_ms']
            self.notification_stats['avg_delivery_time_ms'] = (
                (current_avg * (total_deliveries - 1) + delivery_time) / total_deliveries
            )
            
            # Call subscribers
            await self._call_subscribers(notification)
            
            logger.info(f"Notification {notification.id} delivered via {success_count}/{len(channels)} channels")
            
        except Exception as e:
            logger.error(f"Error delivering notification {notification.id}: {e}")
            notification.status = NotificationStatus.FAILED
            notification.error_message = str(e)
            self.notification_stats['failed_deliveries'] += 1
    
    async def _deliver_to_channel(self, notification: Notification, 
                                 channel: NotificationChannel) -> Dict[str, Any]:
        """Deliver notification to specific channel"""
        try:
            if channel == NotificationChannel.EMAIL:
                return await self._send_email(notification)
            elif channel == NotificationChannel.SLACK:
                return await self._send_slack(notification)
            elif channel == NotificationChannel.WEBHOOK:
                return await self._send_webhook(notification)
            elif channel == NotificationChannel.CONSOLE:
                return await self._send_console(notification)
            elif channel == NotificationChannel.FILE:
                return await self._send_file(notification)
            else:
                return {'success': False, 'error': f'Channel {channel.value} not implemented'}
        
        except Exception as e:
            logger.error(f"Error in channel delivery {channel.value}: {e}")
            return {'success': False, 'error': str(e)}
    
    async def _send_email(self, notification: Notification) -> Dict[str, Any]:
        """Send email notification"""
        try:
            config = self.channel_configs.get(NotificationChannel.EMAIL, {})
            if not config:
                return {'success': False, 'error': 'Email not configured'}
            
            # Get recipients
            recipients = notification.recipients or self.channel_subscribers.get(NotificationChannel.EMAIL, [])
            if not recipients:
                return {'success': False, 'error': 'No email recipients'}
            
            # Create message
            msg = MIMEMultipart()
            msg['From'] = config.get('from_address', config.get('username'))
            msg['To'] = ', '.join(recipients)
            msg['Subject'] = notification.title
            
            # Add body
            body = f"{notification.message}\n\n"
            if notification.data:
                body += "Additional Data:\n"
                for key, value in notification.data.items():
                    body += f"  {key}: {value}\n"
            
            msg.attach(MIMEText(body, 'plain'))
            
            # Send email
            server = smtplib.SMTP(config['smtp_server'], config['smtp_port'])
            if config.get('use_tls', True):
                server.starttls()
            if config.get('username') and config.get('password'):
                server.login(config['username'], config['password'])
            
            server.send_message(msg)
            server.quit()
            
            return {'success': True, 'recipients': len(recipients)}
            
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    async def _send_slack(self, notification: Notification) -> Dict[str, Any]:
        """Send Slack notification (mock implementation)"""
        # In production, would use Slack SDK
        logger.info(f"[SLACK] {notification.level.value.upper()}: {notification.title}")
        return {'success': True, 'channel': 'mock'}
    
    async def _send_webhook(self, notification: Notification) -> Dict[str, Any]:
        """Send webhook notification (mock implementation)"""
        # In production, would make HTTP POST request
        logger.info(f"[WEBHOOK] {notification.level.value.upper()}: {notification.title}")
        return {'success': True, 'url': 'mock'}
    
    async def _send_console(self, notification: Notification) -> Dict[str, Any]:
        """Send console notification"""
        timestamp = notification.created_time.strftime('%Y-%m-%d %H:%M:%S')
        level = notification.level.value.upper()
        print(f"[{timestamp}] [{level}] {notification.title}")
        if notification.message != notification.title:
            print(f"    {notification.message}")
        return {'success': True}
    
    async def _send_file(self, notification: Notification) -> Dict[str, Any]:
        """Send file notification"""
        try:
            config = self.channel_configs.get(NotificationChannel.FILE, {})
            log_file = config.get('log_file', 'logs/notifications.log')
            
            timestamp = notification.created_time.strftime('%Y-%m-%d %H:%M:%S')
            level = notification.level.value.upper()
            
            log_entry = f"[{timestamp}] [{level}] {notification.title}: {notification.message}\n"
            
            with open(log_file, 'a') as f:
                f.write(log_entry)
            
            return {'success': True, 'file': log_file}
            
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    async def _call_subscribers(self, notification: Notification):
        """Call notification subscribers"""
        subscribers = self.subscribers.get(notification.level.value, [])
        for subscriber in subscribers:
            try:
                if asyncio.iscoroutinefunction(subscriber):
                    await subscriber(notification)
                else:
                    subscriber(notification)
            except Exception as e:
                logger.error(f"Error calling subscriber: {e}")
    
    async def _process_retries(self):
        """Process failed notifications for retry"""
        try:
            while not self._shutdown_event.is_set():
                try:
                    # Find notifications that need retry
                    now = datetime.now()
                    retry_notifications = []
                    
                    for notification in self.notifications.values():
                        if (notification.status == NotificationStatus.FAILED and 
                            notification.retry_count < notification.max_retries):
                            # Check if enough time has passed for retry
                            time_since_failure = (now - notification.created_time).total_seconds()
                            if time_since_failure >= self.retry_delay:
                                retry_notifications.append(notification)
                    
                    # Retry notifications
                    for notification in retry_notifications:
                        notification.retry_count += 1
                        notification.status = NotificationStatus.RETRY
                        
                        # Add back to queue
                        priority = self._get_priority(notification.level)
                        await self.notification_queue.put((priority, notification))
                        
                        logger.info(f"Retrying notification {notification.id} (attempt {notification.retry_count})")
                    
                except Exception as e:
                    logger.error(f"Error processing retries: {e}")
                
                # Wait before next retry check
                try:
                    await asyncio.wait_for(
                        self._shutdown_event.wait(),
                        timeout=300  # Check every 5 minutes
                    )
                    break
                except asyncio.TimeoutError:
                    continue
                    
        except asyncio.CancelledError:
            logger.debug("Retry processor cancelled")
        except Exception as e:
            logger.error(f"Error in retry processor: {e}")
    
    async def _daily_reset_loop(self):
        """Reset daily counters"""
        try:
            while not self._shutdown_event.is_set():
                try:
                    now = datetime.now()
                    if now.hour == 0 and now.minute == 0:  # Midnight reset
                        # Clear old throttle counts
                        current_date = now.strftime('%Y-%m-%d')
                        old_dates = [date for date in self.throttle_counts.keys() if date != current_date]
                        for date in old_dates:
                            del self.throttle_counts[date]
                        
                        # Reset daily stats
                        self.notification_stats['throttled_messages'] = 0
                        
                        logger.info("Daily notification counters reset")
                    
                except Exception as e:
                    logger.error(f"Error in daily reset: {e}")
                
                # Wait for next check
                try:
                    await asyncio.wait_for(
                        self._shutdown_event.wait(),
                        timeout=60  # Check every minute
                    )
                    break
                except asyncio.TimeoutError:
                    continue
                    
        except asyncio.CancelledError:
            logger.debug("Daily reset loop cancelled")
        except Exception as e:
            logger.error(f"Error in daily reset loop: {e}")
    
    async def _cleanup_loop(self):
        """Cleanup old notifications"""
        try:
            while not self._shutdown_event.is_set():
                try:
                    # Remove notifications older than 7 days
                    cutoff = datetime.now() - timedelta(days=7)
                    old_notifications = [
                        nid for nid, notification in self.notifications.items()
                        if notification.created_time < cutoff
                    ]
                    
                    for nid in old_notifications:
                        del self.notifications[nid]
                    
                    if old_notifications:
                        logger.info(f"Cleaned up {len(old_notifications)} old notifications")
                    
                    # Clean old throttle cache
                    throttle_cutoff = datetime.now() - timedelta(hours=24)
                    old_throttles = [
                        key for key, timestamp in self.throttle_cache.items()
                        if timestamp < throttle_cutoff
                    ]
                    
                    for key in old_throttles:
                        del self.throttle_cache[key]
                    
                except Exception as e:
                    logger.error(f"Error in cleanup: {e}")
                
                # Wait for next cleanup
                try:
                    await asyncio.wait_for(
                        self._shutdown_event.wait(),
                        timeout=3600  # Cleanup every hour
                    )
                    break
                except asyncio.TimeoutError:
                    continue
                    
        except asyncio.CancelledError:
            logger.debug("Cleanup loop cancelled")
        except Exception as e:
            logger.error(f"Error in cleanup loop: {e}")
    
    def get_service_metrics(self) -> Dict[str, Any]:
        """Get detailed service metrics"""
        return {
            'notification_stats': self.notification_stats.copy(),
            'channels': {
                'enabled': len(self.enabled_channels),
                'available': [c.value for c in self.enabled_channels],
                'subscribers': {c.value: len(subs) for c, subs in self.channel_subscribers.items()}
            },
            'templates': {
                'loaded': len(self.templates),
                'names': list(self.templates.keys())
            },
            'queue': {
                'pending': self.notification_queue.qsize(),
                'max_size': self.max_queue_size
            },
            'throttling': {
                'active_throttles': len(self.throttle_cache),
                'daily_counts': self.throttle_counts.copy()
            }
        }