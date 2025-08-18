"""
Enhanced Dashboard for real-time monitoring with comprehensive strategy integration
"""
import logging
import threading
import dash
from dash import html, dcc, dash_table
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime, timedelta
import pandas as pd

# Import comprehensive monitoring system
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(__file__)))
from strategy.monitoring_system import MonitoringSystem, AlertLevel

logger = logging.getLogger(__name__)

class Dashboard:
    """Enhanced real-time monitoring dashboard with comprehensive strategy integration"""
    
    def __init__(self, strategy=None, feed_manager=None, monitoring_system=None, port=8050):
        self.strategy = strategy
        self.feed_manager = feed_manager
        self.monitoring_system = monitoring_system
        self.port = port
        self.app = None
        
        self._setup_dashboard()
        logger.info(f"Enhanced Dashboard initialized on port {port}")
    
    def _setup_dashboard(self):
        """Setup the enhanced Dash application"""
        self.app = dash.Dash(__name__)
        
        self.app.layout = html.Div([
            html.H1('SPX/XSP Options Mispricing Strategy Dashboard', 
                   style={'textAlign': 'center', 'color': '#2c3e50'}),
            
            # Status Row
            html.Div([
                html.Div([
                    html.H4('System Status', style={'color': '#34495e'}),
                    html.P(id='system-status', children='Loading...'),
                ], className='status-card', style={'width': '24%', 'display': 'inline-block', 'margin': '1%'}),
                
                html.Div([
                    html.H4('Market Data', style={'color': '#34495e'}),
                    html.P(id='market-data', children='Loading...'),
                ], className='status-card', style={'width': '24%', 'display': 'inline-block', 'margin': '1%'}),
                
                html.Div([
                    html.H4('Performance', style={'color': '#34495e'}),
                    html.P(id='performance-data', children='Loading...'),
                ], className='status-card', style={'width': '24%', 'display': 'inline-block', 'margin': '1%'}),
                
                html.Div([
                    html.H4('Risk Status', style={'color': '#34495e'}),
                    html.P(id='risk-status', children='Loading...'),
                ], className='status-card', style={'width': '24%', 'display': 'inline-block', 'margin': '1%'})
            ], style={'margin-bottom': '20px'}),
            
            # Charts Row
            html.Div([
                html.Div([
                    dcc.Graph(id='pnl-chart'),
                ], style={'width': '50%', 'display': 'inline-block'}),
                
                html.Div([
                    dcc.Graph(id='positions-chart'),
                ], style={'width': '50%', 'display': 'inline-block'})
            ]),
            
            # Alerts and Positions Row
            html.Div([
                html.Div([
                    html.H4('Recent Alerts', style={'color': '#e74c3c'}),
                    html.Div(id='alerts-table'),
                ], style={'width': '50%', 'display': 'inline-block', 'vertical-align': 'top'}),
                
                html.Div([
                    html.H4('Current Positions', style={'color': '#27ae60'}),
                    html.Div(id='positions-table'),
                ], style={'width': '50%', 'display': 'inline-block', 'vertical-align': 'top'})
            ]),
            
            dcc.Interval(
                id='interval-component',
                interval=5000,  # Update every 5 seconds
                n_intervals=0
            )
        ])
        
        # Setup callbacks
        @self.app.callback(
            [
                dash.dependencies.Output('system-status', 'children'),
                dash.dependencies.Output('market-data', 'children'),
                dash.dependencies.Output('performance-data', 'children'),
                dash.dependencies.Output('risk-status', 'children'),
                dash.dependencies.Output('pnl-chart', 'figure'),
                dash.dependencies.Output('positions-chart', 'figure'),
                dash.dependencies.Output('alerts-table', 'children'),
                dash.dependencies.Output('positions-table', 'children')
            ],
            [dash.dependencies.Input('interval-component', 'n_intervals')]
        )
        def update_dashboard(n):
            return self._update_all_components()
    
    def _update_all_components(self):
        """Update all dashboard components"""
        
        # System Status
        if self.strategy:
            status = self.strategy.get_strategy_status()
            system_text = f"Status: {'🟢 Running' if status['is_running'] else '🔴 Stopped'}\nPositions: {status['position_count']}\nRisk: {status['risk_level']}"
        else:
            system_text = "Strategy not connected"
        
        # Market Data
        if self.feed_manager:
            try:
                snapshot = self.feed_manager.get_snapshot()
                if snapshot and 'SPX' in snapshot:
                    spx = snapshot['SPX']
                    vix = snapshot.get('VIX', {}).get('last', 0)
                    market_text = f"SPX: ${spx['last']:.2f}\nVIX: {vix:.2f}\nLast Update: {datetime.now().strftime('%H:%M:%S')}"
                else:
                    market_text = "No market data"
            except:
                market_text = "Feed error"
        else:
            market_text = "Feed not connected"
        
        # Performance Data
        if self.monitoring_system:
            dashboard_data = self.monitoring_system.get_dashboard_data()
            perf = dashboard_data['performance']
            performance_text = f"Daily P&L: ${perf['daily_pnl']:,.0f} ({perf['daily_pnl_pct']:.2%})\nSharpe: {perf['sharpe_ratio']:.2f}\nHit Rate: {perf['hit_rate']:.1%}"
        else:
            performance_text = "Monitoring not connected"
        
        # Risk Status
        if self.monitoring_system:
            dashboard_data = self.monitoring_system.get_dashboard_data()
            alerts = dashboard_data['alerts']
            risk_color = '🔴' if alerts['critical_count'] > 0 else '🟡' if alerts['high_count'] > 0 else '🟢'
            risk_text = f"{risk_color} Alerts: {alerts['critical_count']} Critical, {alerts['high_count']} High\nDrawdown: {dashboard_data['performance']['current_drawdown']:.2%}"
        else:
            risk_text = "Risk monitoring not connected"
        
        # P&L Chart
        pnl_fig = self._create_pnl_chart()
        
        # Positions Chart
        positions_fig = self._create_positions_chart()
        
        # Alerts Table
        alerts_table = self._create_alerts_table()
        
        # Positions Table
        positions_table = self._create_positions_table()
        
        return (
            system_text, market_text, performance_text, risk_text,
            pnl_fig, positions_fig, alerts_table, positions_table
        )
    
    def _create_pnl_chart(self):
        """Create P&L chart"""
        fig = go.Figure()
        
        if self.monitoring_system and len(self.monitoring_system.pnl_history) > 0:
            pnl_data = list(self.monitoring_system.pnl_history)
            timestamps = [p['timestamp'] for p in pnl_data]
            pnls = [p['pnl'] for p in pnl_data]
            
            fig.add_trace(go.Scatter(
                x=timestamps,
                y=pnls,
                mode='lines',
                name='Daily P&L',
                line=dict(color='#3498db', width=2)
            ))
        else:
            # Placeholder data
            fig.add_trace(go.Scatter(
                x=[datetime.now()],
                y=[0],
                mode='lines',
                name='Daily P&L'
            ))
        
        fig.update_layout(
            title='Daily P&L',
            xaxis_title='Time',
            yaxis_title='P&L ($)',
            height=300
        )
        
        return fig
    
    def _create_positions_chart(self):
        """Create positions risk chart"""
        fig = go.Figure()
        
        if self.strategy and hasattr(self.strategy, 'state') and self.strategy.state.positions:
            positions = self.strategy.state.positions
            
            # Create risk breakdown
            vegas = [abs(p.get('vega_exposure', 0)) for p in positions]
            gammas = [abs(p.get('gamma_exposure_1pct', 0)) for p in positions]
            
            if vegas and gammas:
                fig.add_trace(go.Bar(
                    x=['Vega', 'Gamma'],
                    y=[sum(vegas), sum(gammas)],
                    name='Risk Exposure',
                    marker_color=['#e74c3c', '#f39c12']
                ))
        
        fig.update_layout(
            title='Portfolio Risk Exposure',
            yaxis_title='Exposure ($)',
            height=300
        )
        
        return fig
    
    def _create_alerts_table(self):
        """Create alerts table"""
        if not self.monitoring_system:
            return html.P("No alerts data")
        
        dashboard_data = self.monitoring_system.get_dashboard_data()
        recent_alerts = dashboard_data['alerts']['recent_alerts']
        
        if not recent_alerts:
            return html.P("No recent alerts", style={'color': '#27ae60'})
        
        # Create table data
        table_data = []
        for alert in recent_alerts[-5:]:  # Show last 5 alerts
            color = {
                'critical': '#e74c3c',
                'high': '#f39c12', 
                'medium': '#f1c40f',
                'low': '#95a5a6'
            }.get(alert['level'], '#95a5a6')
            
            table_data.append({
                'Level': alert['level'].upper(),
                'Type': alert['type'],
                'Message': alert['message'][:50] + '...' if len(alert['message']) > 50 else alert['message'],
                'Time': datetime.fromisoformat(alert['timestamp']).strftime('%H:%M:%S')
            })
        
        return dash_table.DataTable(
            data=table_data,
            columns=[
                {'name': 'Level', 'id': 'Level'},
                {'name': 'Type', 'id': 'Type'},
                {'name': 'Message', 'id': 'Message'},
                {'name': 'Time', 'id': 'Time'}
            ],
            style_cell={'textAlign': 'left', 'fontSize': '12px'},
            style_data_conditional=[
                {
                    'if': {'filter_query': '{Level} = CRITICAL'},
                    'backgroundColor': '#fadbd8',
                    'color': 'black',
                },
                {
                    'if': {'filter_query': '{Level} = HIGH'},
                    'backgroundColor': '#fdeaa7',
                    'color': 'black',
                }
            ]
        )
    
    def _create_positions_table(self):
        """Create positions table"""
        if not self.strategy or not hasattr(self.strategy, 'state'):
            return html.P("No positions data")
        
        positions = self.strategy.state.positions
        
        if not positions:
            return html.P("No open positions", style={'color': '#95a5a6'})
        
        # Create table data
        table_data = []
        for pos in positions[-10:]:  # Show last 10 positions
            table_data.append({
                'Symbol': pos.get('symbol', 'N/A'),
                'Side': pos.get('side', 'N/A'),
                'Qty': pos.get('quantity', 0),
                'Entry': f"${pos.get('entry_price', 0):.2f}",
                'P&L': f"${pos.get('pnl', 0):.0f}",
                'Z-Score': f"{pos.get('z_score', 0):.2f}"
            })
        
        return dash_table.DataTable(
            data=table_data,
            columns=[
                {'name': 'Symbol', 'id': 'Symbol'},
                {'name': 'Side', 'id': 'Side'},
                {'name': 'Qty', 'id': 'Qty'},
                {'name': 'Entry', 'id': 'Entry'},
                {'name': 'P&L', 'id': 'P&L'},
                {'name': 'Z-Score', 'id': 'Z-Score'}
            ],
            style_cell={'textAlign': 'left', 'fontSize': '12px'}
        )
    
    def start(self):
        """Start the enhanced dashboard in a separate thread"""
        def run_dash():
            self.app.run_server(host='0.0.0.0', port=self.port, debug=False)
        
        thread = threading.Thread(target=run_dash, daemon=True)
        thread.start()
        logger.info(f"Enhanced Dashboard started at http://localhost:{self.port}")
    
    def set_monitoring_system(self, monitoring_system: MonitoringSystem):
        """Set the monitoring system for enhanced features"""
        self.monitoring_system = monitoring_system
        logger.info("Monitoring system connected to dashboard")
