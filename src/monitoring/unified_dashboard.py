"""
Unified Professional Trading Dashboard
Consolidates all dashboard functionality into a single, comprehensive interface
"""
import logging
import threading
import dash
from dash import html, dcc, dash_table, Input, Output, State
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime, timedelta
import pandas as pd
import sys
import os
from typing import Dict, List, Optional, Any

# Import components
sys.path.append(os.path.dirname(os.path.dirname(__file__)))
from strategy.monitoring_system import MonitoringSystem, AlertLevel

logger = logging.getLogger(__name__)

class UnifiedDashboard:
    """
    Professional unified dashboard combining real-time monitoring,
    options data, strategy performance, and system health
    """
    
    def __init__(self, strategy=None, feed_manager=None, monitoring_system=None, port=8050):
        self.strategy = strategy
        self.feed_manager = feed_manager
        self.monitoring_system = monitoring_system
        self.port = port
        self.app = None
        self.current_data = {}
        
        self._setup_dashboard()
        logger.info(f"Unified Dashboard initialized on port {port}")
    
    def _setup_dashboard(self):
        """Setup the unified Dash application"""
        self.app = dash.Dash(__name__)
        
        # Custom CSS styles
        self.app.layout = html.Div([
            # Header Section
            html.Div([
                html.H1('🎯 Heston Trading Strategy - Professional Dashboard', 
                       style={'textAlign': 'center', 'color': 'white', 'margin': '0'}),
                html.P(f'Real-time Options Trading • Last Updated: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}',
                      id='header-timestamp',
                      style={'textAlign': 'center', 'color': '#bdc3c7', 'margin': '5px 0 0 0'})
            ], style={
                'background': 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
                'padding': '20px',
                'marginBottom': '20px'
            }),
            
            # System Status Cards
            html.Div([
                self._create_status_card('system-status', 'System Status', 'Loading...', '#3498db'),
                self._create_status_card('market-status', 'Market Data', 'Loading...', '#2ecc71'),
                self._create_status_card('performance-status', 'Performance', 'Loading...', '#f39c12'),
                self._create_status_card('risk-status', 'Risk Level', 'Loading...', '#e74c3c')
            ], style={'display': 'flex', 'justifyContent': 'space-between', 'marginBottom': '20px'}),
            
            # Main Content Tabs
            dcc.Tabs(id="main-tabs", value='overview', children=[
                dcc.Tab(label='📊 Strategy Overview', value='overview'),
                dcc.Tab(label='📈 Live Markets', value='markets'),
                dcc.Tab(label='💼 Positions', value='positions'),
                dcc.Tab(label='⚡ Signals', value='signals'),
                dcc.Tab(label='⚖️ Risk Management', value='risk'),
                dcc.Tab(label='📋 System Health', value='health')
            ], style={'marginBottom': '20px'}),
            
            # Tab Content
            html.Div(id='tab-content'),
            
            # Auto-refresh interval
            dcc.Interval(
                id='interval-component',
                interval=2000,  # Update every 2 seconds
                n_intervals=0
            )
        ], style={'fontFamily': 'Arial, sans-serif', 'margin': '0', 'padding': '0'})
        
        self._setup_callbacks()
    
    def _create_status_card(self, id_name: str, title: str, content: str, color: str):
        """Create a status card component"""
        return html.Div([
            html.H4(title, style={'color': color, 'margin': '0 0 10px 0', 'fontSize': '14px'}),
            html.P(content, id=id_name, style={'margin': '0', 'fontSize': '16px', 'fontWeight': 'bold'})
        ], style={
            'backgroundColor': 'white',
            'padding': '15px',
            'borderRadius': '8px',
            'boxShadow': '0 2px 4px rgba(0,0,0,0.1)',
            'border': f'3px solid {color}',
            'width': '23%',
            'textAlign': 'center'
        })
    
    def _setup_callbacks(self):
        """Setup all dashboard callbacks"""
        
        # Main tab content callback
        @self.app.callback(
            Output('tab-content', 'children'),
            [Input('main-tabs', 'value')]
        )
        def render_tab_content(active_tab):
            if active_tab == 'overview':
                return self._render_overview_tab()
            elif active_tab == 'markets':
                return self._render_markets_tab()
            elif active_tab == 'positions':
                return self._render_positions_tab()
            elif active_tab == 'signals':
                return self._render_signals_tab()
            elif active_tab == 'risk':
                return self._render_risk_tab()
            elif active_tab == 'health':
                return self._render_health_tab()
            return html.Div("Select a tab")
        
        # Status updates callback
        @self.app.callback(
            [
                Output('system-status', 'children'),
                Output('market-status', 'children'),
                Output('performance-status', 'children'),
                Output('risk-status', 'children'),
                Output('header-timestamp', 'children')
            ],
            [Input('interval-component', 'n_intervals')]
        )
        def update_status_cards(n):
            try:
                # Get current data
                data = self._get_current_data()
                
                # System status
                system_status = "🟢 Running" if data.get('system_running', False) else "🔴 Stopped"
                
                # Market status
                market_count = data.get('market_data_count', 0)
                market_status = f"📊 {market_count} contracts" if market_count > 0 else "⚠️ No data"
                
                # Performance
                pnl = data.get('total_pnl', 0)
                pnl_status = f"${pnl:,.2f}" if pnl != 0 else "$0.00"
                
                # Risk level
                risk_level = data.get('risk_level', 'Unknown')
                risk_emoji = {'LOW': '🟢', 'NORMAL': '🟡', 'HIGH': '🟠', 'CRITICAL': '🔴'}.get(risk_level, '⚪')
                risk_status = f"{risk_emoji} {risk_level}"
                
                # Timestamp
                timestamp = f'Real-time Options Trading • Last Updated: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}'
                
                return system_status, market_status, pnl_status, risk_status, timestamp
                
            except Exception as e:
                logger.error(f"Error updating status cards: {e}")
                return "Error", "Error", "Error", "Error", "Error"
    
    def _render_overview_tab(self):
        """Render strategy overview tab"""
        return html.Div([
            # Key Metrics Row
            html.Div([
                html.Div([
                    html.H3("📊 Strategy Performance", style={'color': '#2c3e50'}),
                    dcc.Graph(id='pnl-chart', style={'height': '350px'})
                ], style={'width': '50%', 'display': 'inline-block', 'padding': '10px'}),
                
                html.Div([
                    html.H3("🎯 Trading Activity", style={'color': '#2c3e50'}),
                    dcc.Graph(id='activity-chart', style={'height': '350px'})
                ], style={'width': '50%', 'display': 'inline-block', 'padding': '10px'})
            ]),
            
            # Summary Statistics
            html.Div([
                html.H3("📈 Today's Summary", style={'color': '#2c3e50', 'textAlign': 'center'}),
                html.Div(id='summary-stats', style={'textAlign': 'center', 'fontSize': '18px'})
            ], style={'marginTop': '20px', 'padding': '20px', 'backgroundColor': '#f8f9fa', 'borderRadius': '8px'})
        ])
    
    def _render_markets_tab(self):
        """Render live markets tab"""
        return html.Div([
            # Underlying Assets
            html.Div([
                html.H3("🏛️ Underlying Assets", style={'color': '#2c3e50'}),
                html.Div(id='underlying-assets', style={'marginBottom': '20px'})
            ]),
            
            # Options Chain with Filters
            html.Div([
                html.H3("📋 Live Options Chain", style={'color': '#2c3e50'}),
                html.Div([
                    html.Div([
                        html.Label("Symbol:"),
                        dcc.Dropdown(
                            id='symbol-filter',
                            options=[
                                {'label': 'All', 'value': 'ALL'},
                                {'label': 'SPX', 'value': 'SPX'},
                                {'label': 'SPY', 'value': 'SPY'},
                                {'label': 'XSP', 'value': 'XSP'}
                            ],
                            value='ALL'
                        )
                    ], style={'width': '20%', 'display': 'inline-block', 'marginRight': '2%'}),
                    
                    html.Div([
                        html.Label("Option Type:"),
                        dcc.Dropdown(
                            id='type-filter',
                            options=[
                                {'label': 'All', 'value': 'ALL'},
                                {'label': 'Calls', 'value': 'C'},
                                {'label': 'Puts', 'value': 'P'}
                            ],
                            value='ALL'
                        )
                    ], style={'width': '20%', 'display': 'inline-block', 'marginRight': '2%'}),
                    
                    html.Div([
                        html.Label("Min Volume:"),
                        dcc.Input(
                            id='volume-filter',
                            type='number',
                            value=0,
                            min=0
                        )
                    ], style={'width': '15%', 'display': 'inline-block'})
                ], style={'marginBottom': '15px'}),
                
                dash_table.DataTable(
                    id='options-table',
                    columns=[
                        {'name': 'Symbol', 'id': 'symbol'},
                        {'name': 'Strike', 'id': 'strike', 'type': 'numeric', 'format': {'specifier': '.2f'}},
                        {'name': 'Type', 'id': 'type'},
                        {'name': 'DTE', 'id': 'dte'},
                        {'name': 'Bid', 'id': 'bid', 'type': 'numeric', 'format': {'specifier': '.2f'}},
                        {'name': 'Ask', 'id': 'ask', 'type': 'numeric', 'format': {'specifier': '.2f'}},
                        {'name': 'Last', 'id': 'last', 'type': 'numeric', 'format': {'specifier': '.2f'}},
                        {'name': 'Volume', 'id': 'volume'},
                        {'name': 'IV', 'id': 'implied_vol', 'type': 'numeric', 'format': {'specifier': '.1%'}},
                        {'name': 'Delta', 'id': 'delta', 'type': 'numeric', 'format': {'specifier': '.3f'}},
                        {'name': 'Gamma', 'id': 'gamma', 'type': 'numeric', 'format': {'specifier': '.4f'}},
                        {'name': 'Theta', 'id': 'theta', 'type': 'numeric', 'format': {'specifier': '.3f'}},
                        {'name': 'Vega', 'id': 'vega', 'type': 'numeric', 'format': {'specifier': '.3f'}}
                    ],
                    page_size=20,
                    sort_action='native',
                    filter_action='native',
                    style_cell={'textAlign': 'center', 'fontSize': '12px'},
                    style_header={'backgroundColor': '#3498db', 'color': 'white', 'fontWeight': 'bold'}
                )
            ])
        ])
    
    def _render_positions_tab(self):
        """Render positions tab"""
        return html.Div([
            html.H3("💼 Current Positions", style={'color': '#2c3e50'}),
            html.Div(id='positions-content')
        ])
    
    def _render_signals_tab(self):
        """Render signals tab"""
        return html.Div([
            html.H3("⚡ Trading Signals", style={'color': '#2c3e50'}),
            html.Div(id='signals-content')
        ])
    
    def _render_risk_tab(self):
        """Render risk management tab"""
        return html.Div([
            html.H3("⚖️ Risk Management", style={'color': '#2c3e50'}),
            html.Div(id='risk-content')
        ])
    
    def _render_health_tab(self):
        """Render system health tab"""
        return html.Div([
            html.H3("📋 System Health", style={'color': '#2c3e50'}),
            html.Div(id='health-content')
        ])
    
    def _get_current_data(self) -> Dict[str, Any]:
        """Get current system data"""
        try:
            data = {}
            
            # Get data from feed manager
            if self.feed_manager:
                snapshot = self.feed_manager.get_latest_snapshot()
                if snapshot:
                    data['market_data_count'] = len(snapshot.get('options', []))
                    data['underlying_data'] = snapshot.get('underlying', {})
                    data['options_data'] = snapshot.get('options', [])
            
            # Get data from strategy
            if self.strategy:
                data['system_running'] = getattr(self.strategy, 'is_running', False)
                if hasattr(self.strategy, 'get_performance_summary'):
                    perf = self.strategy.get_performance_summary()
                    data['total_pnl'] = perf.get('total_pnl', 0)
                    data['daily_pnl'] = perf.get('daily_pnl', 0)
                    data['active_positions'] = perf.get('active_positions', 0)
            
            # Get data from monitoring system
            if self.monitoring_system:
                health = self.monitoring_system.get_system_health()
                data['risk_level'] = health.get('risk_level', 'UNKNOWN')
                data['alerts'] = self.monitoring_system.get_recent_alerts()
            
            self.current_data = data
            return data
            
        except Exception as e:
            logger.error(f"Error getting current data: {e}")
            return {}
    
    def run(self, debug=False, host='127.0.0.1'):
        """Run the dashboard"""
        try:
            logger.info(f"Starting Unified Dashboard on http://{host}:{self.port}")
            self.app.run(
                host=host,
                port=self.port,
                debug=debug,
                use_reloader=False  # Prevent double startup in debug mode
            )
        except Exception as e:
            logger.error(f"Error running dashboard: {e}")
            raise
    
    def stop(self):
        """Stop the dashboard"""
        logger.info("Stopping Unified Dashboard")
        # Note: Dash doesn't have a built-in stop method
        # This is handled by the calling process