"""
Risk Management Types
Common types and enums used across risk management modules
"""
from datetime import datetime
from typing import Dict, Any
from dataclasses import dataclass
from enum import Enum

class RiskLevel(Enum):
    """Overall risk level assessment"""
    HEALTHY = "healthy"
    CAUTION = "caution"
    WARNING = "warning"
    CRITICAL = "critical"
    EMERGENCY = "emergency"

class RiskAction(Enum):
    """Risk actions to be taken"""
    ALLOW_ALL = "allow_all"
    REDUCE_SIZE = "reduce_size"
    BLOCK_NEW = "block_new"
    CLOSE_RISKY = "close_risky"
    CLOSE_ALL = "close_all"
    EMERGENCY_STOP = "emergency_stop"

@dataclass
class RiskAlert:
    """Risk alert/violation"""
    timestamp: datetime
    level: RiskLevel
    component: str
    rule: str
    message: str
    current_value: float
    limit_value: float
    recommended_action: RiskAction
    metadata: Dict[str, Any]