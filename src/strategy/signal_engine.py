"""
Signal Generation Engine with Kalman Filtering
"""
import numpy as np
import pandas as pd
from typing import Dict, List, Tuple, Optional
from collections import deque
import logging
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

class SignalEngine:
    """
    Generates trading signals based on Heston model mispricing
    """
    
    def __init__(self, config: dict):
        self.config = config
        self.signal_config = config.get('signals', {})
        
        # Signal parameters
        self.exit_z = self.signal_config.get('exit_abs_z', 1.0)
        self.percentile = self.signal_config.get('percentile', 0.98)
        self.window_hours = self.signal_config.get('window_hours', 3)
        
        # Kalman filter parameters
        self.kalman_q = self.signal_config.get('kalman_q', 0.02)
        self.kalman_r = self.signal_config.get('kalman_r', 1.0)
        
        # Neighborhood parameters
        self.nbhd_k = self.signal_config.get('nbhd_k_abs', 0.02)
        self.nbhd_days = self.signal_config.get('nbhd_days_abs', 5)
        self.min_samples = self.signal_config.get('min_samples', 100)
        
        # History storage
        self.z_history = deque(maxlen=10000)
        self.kalman_states = {}
        self.threshold_cache = {}
        
    def compute_signals(self, market_iv: pd.DataFrame, model_surface: pd.DataFrame,
                       spot: float) -> List[Dict]:
        """
        Compute trading signals from market vs model IVs
        
        Args:
            market_iv: Market implied volatilities
            model_surface: Model implied volatilities
            spot: Current spot price
            
        Returns:
            List of trading signals
        """
        signals = []
        
        # Compute z-scores
        z_scores = self._compute_z_scores(market_iv, model_surface)
        
        # Apply Kalman filtering
        smoothed_z = self._apply_kalman_filter(z_scores)
        
        # Compute entry thresholds
        thresholds = self._compute_thresholds(z_scores)
        
        # Generate signals
        for idx, row in smoothed_z.iterrows():
            node_key = (row['strike'], row['expiry'])
            
            # Check entry condition
            if abs(row['smoothed_z']) >= thresholds.get(node_key, 2.5):
                if self._check_gates(row):
                    signal = {
                        'strike': row['strike'],
                        'expiry': row['expiry'],
                        'type': row['option_type'],
                        'z_score': row['z_score'],
                        'smoothed_z': row['smoothed_z'],
                        'direction': 'BUY' if row['z_score'] < 0 else 'SELL',
                        'timestamp': datetime.now()
                    }
                    signals.append(signal)
        
        return signals
    
    def check_exits(self, positions: List[Dict], current_z: pd.DataFrame) -> List[Dict]:
        """
        Check for exit signals on existing positions
        
        Args:
            positions: Current positions
            current_z: Current z-scores
            
        Returns:
            List of exit signals
        """
        exits = []
        
        for position in positions:
            # Find current z-score for position
            pos_z = current_z[
                (current_z['strike'] == position['strike']) &
                (current_z['expiry'] == position['expiry']) &
                (current_z['option_type'] == position['type'])
            ]
            
            if not pos_z.empty:
                z = abs(pos_z.iloc[0]['z_score'])
                
                # Exit if z-score below threshold
                if z < self.exit_z:
                    exits.append({
                        'position': position,
                        'z_score': z,
                        'reason': 'z_threshold'
                    })
        
        return exits
    
    def _compute_z_scores(self, market_iv: pd.DataFrame, 
                         model_surface: pd.DataFrame) -> pd.DataFrame:
        """Compute normalized pricing errors (z-scores)"""
        
        # Merge market and model data
        merged = pd.merge(
            market_iv,
            model_surface,
            on=['strike', 'expiry'],
            suffixes=('_market', '_model')
        )
        
        # Compute residuals
        merged['residual'] = merged['iv_market'] - merged['iv_model']
        
        # Compute local standard deviation
        merged['local_std'] = merged.apply(
            lambda row: self._get_local_std(row['moneyness'], row['expiry']),
            axis=1
        )
        
        # Compute z-score
        merged['z_score'] = merged['residual'] / merged['local_std']
        
        # Store in history
        for _, row in merged.iterrows():
            self.z_history.append({
                'timestamp': datetime.now(),
                'strike': row['strike'],
                'expiry': row['expiry'],
                'moneyness': row['moneyness'],
                'z_score': row['z_score']
            })
        
        return merged
    
    def _get_local_std(self, moneyness: float, expiry: int) -> float:
        """Get local residual standard deviation"""
        
        # Find historical samples in neighborhood
        recent_samples = []
        cutoff_time = datetime.now() - timedelta(hours=self.window_hours)
        
        for sample in self.z_history:
            if sample['timestamp'] < cutoff_time:
                continue
            
            # Check if in neighborhood
            if (abs(sample['moneyness'] - moneyness) <= self.nbhd_k and
                abs(sample['expiry'] - expiry) <= self.nbhd_days):
                recent_samples.append(sample['z_score'])
        
        # Calculate standard deviation
        if len(recent_samples) >= 10:
            return np.std(recent_samples)
        else:
            return 1.0  # Default
    
    def _apply_kalman_filter(self, z_scores: pd.DataFrame) -> pd.DataFrame:
        """Apply Kalman filter to smooth |z| scores"""
        
        result = z_scores.copy()
        result['smoothed_z'] = 0.0
        
        for idx, row in z_scores.iterrows():
            key = (row['strike'], row['expiry'])
            
            # Initialize Kalman state if needed
            if key not in self.kalman_states:
                self.kalman_states[key] = {
                    'x': 0.0,  # State estimate
                    'P': 1.0   # Error covariance
                }
            
            state = self.kalman_states[key]
            
            # Kalman filter update
            # Prediction
            x_pred = state['x']
            P_pred = state['P'] + self.kalman_q
            
            # Update
            y = abs(row['z_score'])  # Observation
            K = P_pred / (P_pred + self.kalman_r)  # Kalman gain
            
            state['x'] = x_pred + K * (y - x_pred)
            state['P'] = (1 - K) * P_pred
            
            # Store smoothed value
            result.at[idx, 'smoothed_z'] = state['x']
        
        return result
    
    def _compute_thresholds(self, z_scores: pd.DataFrame) -> Dict[Tuple, float]:
        """Compute dynamic entry thresholds"""
        
        thresholds = {}
        cutoff_time = datetime.now() - timedelta(hours=self.window_hours)
        
        # Group by strike/expiry neighborhoods
        for _, row in z_scores.iterrows():
            key = (row['strike'], row['expiry'])
            
            # Find samples in neighborhood
            nbhd_samples = []
            
            for sample in self.z_history:
                if sample['timestamp'] < cutoff_time:
                    continue
                
                if (abs(sample['moneyness'] - row['moneyness']) <= self.nbhd_k and
                    abs(sample['expiry'] - row['expiry']) <= self.nbhd_days):
                    nbhd_samples.append(abs(sample['z_score']))
            
            # Compute percentile threshold
            if len(nbhd_samples) >= self.min_samples:
                threshold = np.percentile(nbhd_samples, self.percentile * 100)
            else:
                # Expand neighborhood or use default
                threshold = 2.5
            
            thresholds[key] = threshold
        
        return thresholds
    
    def _check_gates(self, signal_row: pd.Series) -> bool:
        """Check if signal passes entry gates"""
        
        # Time of day filter
        now = datetime.now()
        market_open = now.replace(hour=9, minute=30)
        market_close = now.replace(hour=16, minute=0)
        
        tod_block = self.signal_config.get('tod_block_min', 15)
        
        if (now - market_open).seconds < tod_block * 60:
            return False
        
        if (market_close - now).seconds < tod_block * 60:
            return False
        
        # Other gates would go here
        
        return True
