"""
Macro Event Handling with Blackout Periods
"""
import numpy as np
import pandas as pd
from typing import Dict, List, Tuple, Optional
import logging
from datetime import datetime, timedelta
from enum import Enum
from dataclasses import dataclass

logger = logging.getLogger(__name__)

class EventType(Enum):
    FOMC = "fomc"
    CPI = "cpi"
    NFP = "nfp"
    GDP = "gdp"
    EARNINGS = "earnings"
    OTHER = "other"

@dataclass
class MacroEvent:
    """Macro economic event definition"""
    event_type: EventType
    scheduled_time: datetime
    description: str
    importance: str  # "high", "medium", "low"
    blackout_before_min: int = 2
    blackout_after_min: int = 3
    position_size_multiplier: float = 0.5

class MacroEventHandler:
    """
    Handles macro event detection and trading restrictions
    """
    
    def __init__(self, config: dict):
        self.config = config
        self.macro_config = config.get('macro_events', {})
        
        # Event configurations
        self.event_configs = {
            EventType.FOMC: {
                'blackout_before_min': self.macro_config.get('fomc', {}).get('blackout_before_min', 2),
                'blackout_after_min': self.macro_config.get('fomc', {}).get('blackout_after_min', 3),
                'position_size_multiplier': self.macro_config.get('fomc', {}).get('position_size_multiplier', 0.5)
            },
            EventType.CPI: {
                'blackout_before_min': self.macro_config.get('cpi', {}).get('blackout_before_min', 2),
                'blackout_after_min': self.macro_config.get('cpi', {}).get('blackout_after_min', 3),
                'position_size_multiplier': self.macro_config.get('cpi', {}).get('position_size_multiplier', 0.5)
            }
        }
        
        # Default settings
        self.default_blackout_before = self.macro_config.get('default_blackout_before_min', 2)
        self.default_blackout_after = self.macro_config.get('default_blackout_after_min', 3)
        self.default_size_multiplier = self.macro_config.get('default_size_multiplier', 0.5)
        
        # Event calendar
        self.event_calendar: List[MacroEvent] = []
        self.current_blackout_event: Optional[MacroEvent] = None
        
        # Load predefined events
        self._load_event_calendar()
    
    def _load_event_calendar(self):
        """Load predefined macro events calendar"""
        
        # This would typically load from external calendar API or database
        # For now, we'll create some sample events
        
        base_date = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        
        # Sample FOMC meetings (typically 8 per year)
        fomc_dates = [
            base_date + timedelta(days=30),   # Next month
            base_date + timedelta(days=75),   # ~2.5 months
            base_date + timedelta(days=120),  # ~4 months
        ]
        
        for date in fomc_dates:
            # FOMC typically at 2:00 PM ET
            event_time = date.replace(hour=14, minute=0)
            self.event_calendar.append(MacroEvent(
                event_type=EventType.FOMC,
                scheduled_time=event_time,
                description="FOMC Meeting Decision",
                importance="high",
                **self.event_configs.get(EventType.FOMC, {})
            ))
        
        # Sample CPI releases (monthly, typically 8:30 AM ET)
        for month_offset in range(1, 4):
            # CPI usually mid-month
            cpi_date = (base_date.replace(day=15) + timedelta(days=30*month_offset)).replace(hour=8, minute=30)
            self.event_calendar.append(MacroEvent(
                event_type=EventType.CPI,
                scheduled_time=cpi_date,
                description="CPI Release",
                importance="high",
                **self.event_configs.get(EventType.CPI, {})
            ))
        
        # Sort by time
        self.event_calendar.sort(key=lambda x: x.scheduled_time)
        
        logger.info(f"Loaded {len(self.event_calendar)} macro events")
    
    def add_event(self, event: MacroEvent):
        """Add a new macro event to calendar"""
        self.event_calendar.append(event)
        self.event_calendar.sort(key=lambda x: x.scheduled_time)
        logger.info(f"Added macro event: {event.description} at {event.scheduled_time}")
    
    def check_blackout_status(self, current_time: datetime = None) -> Dict:
        """
        Check if we're currently in a macro event blackout period
        
        Args:
            current_time: Current time (defaults to now)
            
        Returns:
            Blackout status with event details
        """
        
        if current_time is None:
            current_time = datetime.now()
        
        # Check each event for blackout
        for event in self.event_calendar:
            blackout_start = event.scheduled_time - timedelta(minutes=event.blackout_before_min)
            blackout_end = event.scheduled_time + timedelta(minutes=event.blackout_after_min)
            
            if blackout_start <= current_time <= blackout_end:
                self.current_blackout_event = event
                
                # Determine blackout phase
                if current_time < event.scheduled_time:
                    phase = "pre_event"
                    time_to_event = (event.scheduled_time - current_time).total_seconds() / 60
                else:
                    phase = "post_event"
                    time_to_event = -(current_time - event.scheduled_time).total_seconds() / 60
                
                return {
                    'in_blackout': True,
                    'event': event,
                    'phase': phase,
                    'time_to_event_min': time_to_event,
                    'blackout_start': blackout_start,
                    'blackout_end': blackout_end,
                    'actions': {
                        'block_new_entries': True,
                        'allow_exits': True,
                        'allow_hedges': True
                    }
                }
        
        # No blackout active
        self.current_blackout_event = None
        return {
            'in_blackout': False,
            'event': None,
            'phase': None,
            'time_to_event_min': None,
            'actions': {
                'block_new_entries': False,
                'allow_exits': True,
                'allow_hedges': True
            }
        }
    
    def get_position_size_multiplier(self, current_time: datetime = None) -> float:
        """
        Get position size multiplier for current session
        
        For high-impact events, we halve position sizes for the entire session
        """
        
        if current_time is None:
            current_time = datetime.now()
        
        # Check if any high-impact event is scheduled today
        today = current_time.date()
        
        for event in self.event_calendar:
            if event.scheduled_time.date() == today and event.importance == "high":
                logger.info(f"Reducing position sizes due to {event.description} today")
                return event.position_size_multiplier
        
        return 1.0  # Normal sizing
    
    def get_upcoming_events(self, hours_ahead: int = 24) -> List[MacroEvent]:
        """Get upcoming events within specified hours"""
        
        current_time = datetime.now()
        cutoff_time = current_time + timedelta(hours=hours_ahead)
        
        upcoming = [
            event for event in self.event_calendar
            if current_time <= event.scheduled_time <= cutoff_time
        ]
        
        return upcoming
    
    def should_allow_new_position(self, current_time: datetime = None) -> Dict:
        """
        Check if new positions should be allowed considering macro events
        
        Returns:
            Decision with reasoning
        """
        
        blackout_status = self.check_blackout_status(current_time)
        
        if blackout_status['in_blackout']:
            event = blackout_status['event']
            phase = blackout_status['phase']
            
            return {
                'allowed': False,
                'reason': f"Macro event blackout: {event.description} ({phase})",
                'event_type': event.event_type.value,
                'time_to_event_min': blackout_status['time_to_event_min']
            }
        
        return {
            'allowed': True,
            'reason': "No macro event restrictions",
            'event_type': None,
            'time_to_event_min': None
        }
    
    def get_volatility_regime_adjustment(self, current_time: datetime = None) -> Dict:
        """
        Get volatility regime adjustments around macro events
        
        Returns adjustments to signal thresholds and position sizing
        """
        
        if current_time is None:
            current_time = datetime.now()
        
        # Check for events within next 2 hours
        upcoming_events = []
        for event in self.event_calendar:
            time_diff = (event.scheduled_time - current_time).total_seconds() / 3600  # hours
            if 0 <= time_diff <= 2 and event.importance == "high":
                upcoming_events.append((event, time_diff))
        
        if upcoming_events:
            # Sort by time to event
            upcoming_events.sort(key=lambda x: x[1])
            next_event, hours_to_event = upcoming_events[0]
            
            # Increase signal threshold as we approach event
            if hours_to_event <= 0.5:  # 30 minutes
                threshold_multiplier = 1.5
                size_multiplier = 0.25
            elif hours_to_event <= 1.0:  # 1 hour
                threshold_multiplier = 1.3
                size_multiplier = 0.5
            else:  # 1-2 hours
                threshold_multiplier = 1.2
                size_multiplier = 0.75
            
            return {
                'regime': 'pre_macro_event',
                'threshold_multiplier': threshold_multiplier,
                'size_multiplier': size_multiplier,
                'event': next_event.description,
                'hours_to_event': hours_to_event
            }
        
        return {
            'regime': 'normal',
            'threshold_multiplier': 1.0,
            'size_multiplier': 1.0,
            'event': None,
            'hours_to_event': None
        }
    
    def update_event_calendar(self, external_events: List[Dict]):
        """
        Update event calendar from external source (e.g., economic calendar API)
        
        Args:
            external_events: List of event dictionaries with keys:
                - datetime, event_type, description, importance
        """
        
        new_events = []
        
        for event_data in external_events:
            try:
                # Parse event type
                event_type_str = event_data.get('event_type', 'other').lower()
                event_type = EventType.OTHER
                
                for et in EventType:
                    if et.value in event_type_str:
                        event_type = et
                        break
                
                # Get event configuration
                event_config = self.event_configs.get(event_type, {
                    'blackout_before_min': self.default_blackout_before,
                    'blackout_after_min': self.default_blackout_after,
                    'position_size_multiplier': self.default_size_multiplier
                })
                
                # Create event
                event = MacroEvent(
                    event_type=event_type,
                    scheduled_time=event_data['datetime'],
                    description=event_data['description'],
                    importance=event_data.get('importance', 'medium'),
                    **event_config
                )
                
                new_events.append(event)
                
            except Exception as e:
                logger.warning(f"Failed to parse event: {event_data}, error: {e}")
        
        # Replace calendar with new events
        self.event_calendar = new_events
        self.event_calendar.sort(key=lambda x: x.scheduled_time)
        
        logger.info(f"Updated event calendar with {len(new_events)} events")
    
    def get_event_summary(self) -> Dict:
        """Get summary of macro event status"""
        
        blackout_status = self.check_blackout_status()
        upcoming_events = self.get_upcoming_events(24)
        size_multiplier = self.get_position_size_multiplier()
        
        return {
            'in_blackout': blackout_status['in_blackout'],
            'current_event': blackout_status['event'].description if blackout_status['event'] else None,
            'upcoming_24h': len(upcoming_events),
            'next_event': upcoming_events[0].description if upcoming_events else None,
            'next_event_time': upcoming_events[0].scheduled_time if upcoming_events else None,
            'position_size_multiplier': size_multiplier,
            'total_events_loaded': len(self.event_calendar)
        }
    
    def cleanup_old_events(self, days_back: int = 7):
        """Remove old events from calendar"""
        
        cutoff_time = datetime.now() - timedelta(days=days_back)
        
        old_count = len(self.event_calendar)
        self.event_calendar = [
            event for event in self.event_calendar
            if event.scheduled_time >= cutoff_time
        ]
        
        removed_count = old_count - len(self.event_calendar)
        if removed_count > 0:
            logger.info(f"Cleaned up {removed_count} old events")
