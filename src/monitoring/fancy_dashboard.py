"""
Fancy Modern Trading Dashboard
A beautiful, professional-grade UI with advanced styling, animations, and real-time features
"""
import dash
from dash import html, dcc, dash_table, Input, Output, State, callback
import plotly.graph_objects as go
import plotly.express as px
import dash_bootstrap_components as dbc
from datetime import datetime, timedelta
import pandas as pd
import numpy as np
import json
import sys
import os
from typing import Dict, List, Optional, Any
import asyncio
import threading
import time

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

class FancyTradingDashboard:
    """
    Ultra-modern trading dashboard with stunning visuals and real-time data
    """
    
    def __init__(self, port=8050):
        self.port = port
        self.app = None
        self.mock_data = self._generate_mock_data()
        self._setup_dashboard()
        
    def _generate_mock_data(self):
        """Generate realistic mock trading data for demo"""
        np.random.seed(42)
        
        # Generate price data for multiple symbols
        symbols = ['SPY', 'QQQ', 'IWM', 'TLT', 'GLD']
        prices = {
            'SPY': 500 + np.cumsum(np.random.normal(0, 0.5, 100)),
            'QQQ': 380 + np.cumsum(np.random.normal(0, 0.3, 100)),
            'IWM': 200 + np.cumsum(np.random.normal(0, 0.2, 100)),
            'TLT': 95 + np.cumsum(np.random.normal(0, 0.1, 100)),
            'GLD': 180 + np.cumsum(np.random.normal(0, 0.15, 100))
        }
        
        # Generate portfolio data
        portfolio_value = 1000000 + np.cumsum(np.random.normal(1000, 5000, 100))
        
        # Generate options positions
        positions = []
        for i, symbol in enumerate(symbols[:3]):
            positions.append({
                'symbol': f'{symbol}_CALL_500',
                'underlying': symbol,
                'type': 'CALL',
                'strike': 500 + i*50,
                'quantity': np.random.randint(-20, 20),
                'market_value': np.random.uniform(10000, 50000),
                'pnl': np.random.uniform(-5000, 8000),
                'delta': np.random.uniform(-1, 1),
                'gamma': np.random.uniform(0, 0.05),
                'theta': np.random.uniform(-50, 0),
                'vega': np.random.uniform(0, 100),
                'iv': np.random.uniform(0.15, 0.35)
            })
        
        return {
            'prices': prices,
            'portfolio_value': portfolio_value,
            'positions': positions,
            'timestamps': pd.date_range(start='2024-01-01', periods=100, freq='H')
        }
    
    def _setup_dashboard(self):
        """Setup the fancy Dash application with modern styling"""
        # Use Bootstrap theme for modern look
        self.app = dash.Dash(
            __name__, 
            external_stylesheets=[
                dbc.themes.CYBORG,  # Dark theme
                "https://use.fontawesome.com/releases/v5.15.4/css/all.css",  # Icons
                "https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap"  # Modern font
            ]
        )
        
        self.app.layout = self._create_layout()
        self._setup_callbacks()
    
    def _create_layout(self):
        """Create the stunning dashboard layout"""
        custom_css = """
        :root {
            --primary-color: #00D2FF;
            --secondary-color: #3A47D5;
            --success-color: #00C896;
            --warning-color: #FFB800;
            --danger-color: #FF4757;
            --dark-bg: #0F1419;
            --card-bg: #1A1E23;
            --text-primary: #FFFFFF;
            --text-secondary: #8B949E;
            --border-color: #30363D;
        }
        
        body {
            background: linear-gradient(135deg, #0F1419 0%, #1A1E23 100%);
            font-family: 'Inter', sans-serif;
            color: var(--text-primary);
        }
        
        .dashboard-card {
            background: var(--card-bg);
            border: 1px solid var(--border-color);
            border-radius: 12px;
            box-shadow: 0 8px 32px rgba(0, 0, 0, 0.3);
            transition: all 0.3s ease;
        }
        
        .dashboard-card:hover {
            transform: translateY(-4px);
            box-shadow: 0 16px 48px rgba(0, 210, 255, 0.2);
            border-color: var(--primary-color);
        }
        
        .metric-card {
            background: linear-gradient(135deg, var(--card-bg) 0%, rgba(58, 71, 213, 0.1) 100%);
            border: 1px solid var(--border-color);
            border-radius: 16px;
            padding: 24px;
            text-align: center;
            transition: all 0.3s ease;
        }
        
        .metric-value {
            font-size: 2.5rem;
            font-weight: 700;
            background: linear-gradient(135deg, var(--primary-color), var(--secondary-color));
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            background-clip: text;
            margin: 0;
        }
        
        .metric-label {
            color: var(--text-secondary);
            font-size: 0.9rem;
            font-weight: 500;
            text-transform: uppercase;
            letter-spacing: 1px;
            margin-top: 8px;
        }
        
        .metric-change {
            font-size: 0.85rem;
            font-weight: 600;
            margin-top: 4px;
        }
        
        .positive { color: var(--success-color); }
        .negative { color: var(--danger-color); }
        .neutral { color: var(--text-secondary); }
        
        .header-title {
            background: linear-gradient(135deg, var(--primary-color), var(--secondary-color));
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            background-clip: text;
            font-weight: 700;
            font-size: 2.5rem;
            margin: 0;
            text-align: center;
        }
        
        .status-indicator {
            width: 12px;
            height: 12px;
            border-radius: 50%;
            display: inline-block;
            margin-right: 8px;
            animation: pulse 2s infinite;
        }
        
        .status-healthy { background-color: var(--success-color); }
        .status-warning { background-color: var(--warning-color); }
        .status-critical { background-color: var(--danger-color); }
        
        @keyframes pulse {
            0% { opacity: 1; }
            50% { opacity: 0.5; }
            100% { opacity: 1; }
        }
        """
        
        # Add custom CSS via app assets
        self.app.index_string = '''
        <!DOCTYPE html>
        <html>
            <head>
                {%metas%}
                <title>{%title%}</title>
                {%favicon%}
                {%css%}
                <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap" rel="stylesheet">
                <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css">
                <style>
                ''' + custom_css + '''
                </style>
            </head>
            <body>
                {%app_entry%}
                <footer>
                    {%config%}
                    {%scripts%}
                    {%renderer%}
                </footer>
            </body>
        </html>
        '''
        
        return dbc.Container([
            
            # Header
            dbc.Row([
                dbc.Col([
                    html.H1("🚀 Heston Trading System", className="header-title"),
                    html.P([
                        html.Span(className="status-indicator status-healthy"),
                        f"Live Dashboard • {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
                    ], style={'textAlign': 'center', 'color': 'var(--text-secondary)', 'marginTop': '16px'})
                ], width=12)
            ], className="mb-4"),
            
            # Key Metrics Row
            dbc.Row([
                dbc.Col([
                    html.Div([
                        html.H2("$1,247,856", className="metric-value"),
                        html.P("Portfolio Value", className="metric-label"),
                        html.P([
                            html.I(className="fas fa-arrow-up"),
                            " +2.34% (+$28,432)"
                        ], className="metric-change positive")
                    ], className="metric-card")
                ], md=3),
                dbc.Col([
                    html.Div([
                        html.H2("$4,231", className="metric-value"),
                        html.P("Daily P&L", className="metric-label"),
                        html.P([
                            html.I(className="fas fa-arrow-up"),
                            " +1.12%"
                        ], className="metric-change positive")
                    ], className="metric-card")
                ], md=3),
                dbc.Col([
                    html.Div([
                        html.H2("0.89", className="metric-value"),
                        html.P("Portfolio Delta", className="metric-label"),
                        html.P([
                            html.I(className="fas fa-minus"),
                            " Neutral"
                        ], className="metric-change neutral")
                    ], className="metric-card")
                ], md=3),
                dbc.Col([
                    html.Div([
                        html.H2("18.5", className="metric-value"),
                        html.P("VIX Level", className="metric-label"),
                        html.P([
                            html.I(className="fas fa-arrow-down"),
                            " -2.1%"
                        ], className="metric-change negative")
                    ], className="metric-card")
                ], md=3)
            ], className="mb-4"),
            
            # Main Content Tabs
            dbc.Card([
                dbc.CardHeader([
                    dbc.Tabs([
                        dbc.Tab(label="📊 Portfolio Overview", tab_id="portfolio"),
                        dbc.Tab(label="🎯 Options Positions", tab_id="positions"),
                        dbc.Tab(label="📈 Market Data", tab_id="market"),
                        dbc.Tab(label="🛡️ Risk Management", tab_id="risk"),
                        dbc.Tab(label="⚙️ System Health", tab_id="health"),
                    ], id="main-tabs", active_tab="portfolio")
                ]),
                dbc.CardBody([
                    html.Div(id="tab-content")
                ])
            ], className="dashboard-card"),
            
            # Auto-refresh interval
            dcc.Interval(
                id='interval-component',
                interval=3000,  # Update every 3 seconds
                n_intervals=0
            ),
            
        ], fluid=True, className="py-4")
    
    def _create_portfolio_tab(self):
        """Create portfolio overview tab content"""
        return dbc.Row([
            dbc.Col([
                dbc.Card([
                    dbc.CardHeader(html.H5("📈 Portfolio Performance", className="mb-0")),
                    dbc.CardBody([
                        dcc.Graph(
                            id="portfolio-chart",
                            figure=self._create_portfolio_chart(),
                            config={'displayModeBar': False},
                            style={'height': '400px'}
                        )
                    ])
                ], className="dashboard-card mb-4")
            ], md=8),
            dbc.Col([
                dbc.Card([
                    dbc.CardHeader(html.H5("🎯 Asset Allocation", className="mb-0")),
                    dbc.CardBody([
                        dcc.Graph(
                            id="allocation-chart",
                            figure=self._create_allocation_chart(),
                            config={'displayModeBar': False},
                            style={'height': '400px'}
                        )
                    ])
                ], className="dashboard-card mb-4")
            ], md=4),
        ])
    
    def _create_positions_tab(self):
        """Create options positions tab content"""
        return dbc.Row([
            dbc.Col([
                dbc.Card([
                    dbc.CardHeader([
                        html.Div([
                            html.H5("📋 Active Positions", className="mb-0 d-inline"),
                            dbc.Badge("3 Positions", color="primary", className="ms-2")
                        ])
                    ]),
                    dbc.CardBody([
                        self._create_positions_table()
                    ])
                ], className="dashboard-card")
            ], md=12)
        ])
    
    def _create_market_tab(self):
        """Create market data tab content"""
        return dbc.Row([
            dbc.Col([
                dbc.Card([
                    dbc.CardHeader(html.H5("📈 Live Market Data", className="mb-0")),
                    dbc.CardBody([
                        dcc.Graph(
                            id="market-chart",
                            figure=self._create_market_chart(),
                            config={'displayModeBar': False},
                            style={'height': '500px'}
                        )
                    ])
                ], className="dashboard-card")
            ], md=12)
        ])
    
    def _create_risk_tab(self):
        """Create risk management tab content"""
        return dbc.Row([
            dbc.Col([
                dbc.Card([
                    dbc.CardHeader([
                        html.Div([
                            html.H5("🛡️ Risk Metrics", className="mb-0 d-inline"),
                            html.Span([
                                html.Span(className="status-indicator status-healthy"),
                                "Healthy"
                            ], className="ms-2", style={'fontSize': '0.9rem'})
                        ])
                    ]),
                    dbc.CardBody([
                        dbc.Row([
                            dbc.Col([
                                html.Div([
                                    html.H4("$12,450", style={'color': '#00D2FF', 'margin': 0}),
                                    html.P("Daily VaR (95%)", className="text-muted mb-0")
                                ])
                            ], md=3),
                            dbc.Col([
                                html.Div([
                                    html.H4("2.34%", style={'color': '#00C896', 'margin': 0}),
                                    html.P("Max Drawdown", className="text-muted mb-0")
                                ])
                            ], md=3),
                            dbc.Col([
                                html.Div([
                                    html.H4("1.87", style={'color': '#FFB800', 'margin': 0}),
                                    html.P("Sharpe Ratio", className="text-muted mb-0")
                                ])
                            ], md=3),
                            dbc.Col([
                                html.Div([
                                    html.H4("85%", style={'color': '#00D2FF', 'margin': 0}),
                                    html.P("Win Rate", className="text-muted mb-0")
                                ])
                            ], md=3)
                        ])
                    ])
                ], className="dashboard-card mb-4")
            ], md=12),
            dbc.Col([
                dbc.Card([
                    dbc.CardHeader(html.H5("📊 Risk Dashboard", className="mb-0")),
                    dbc.CardBody([
                        dcc.Graph(
                            id="risk-chart",
                            figure=self._create_risk_chart(),
                            config={'displayModeBar': False},
                            style={'height': '400px'}
                        )
                    ])
                ], className="dashboard-card")
            ], md=12)
        ])
    
    def _create_health_tab(self):
        """Create system health tab content"""
        return dbc.Row([
            dbc.Col([
                dbc.Card([
                    dbc.CardHeader(html.H5("⚙️ Service Status", className="mb-0")),
                    dbc.CardBody([
                        self._create_service_status()
                    ])
                ], className="dashboard-card mb-4")
            ], md=6),
            dbc.Col([
                dbc.Card([
                    dbc.CardHeader(html.H5("🔔 Recent Alerts", className="mb-0")),
                    dbc.CardBody([
                        self._create_alerts_feed()
                    ])
                ], className="dashboard-card mb-4")
            ], md=6),
        ])
    
    def _setup_callbacks(self):
        """Setup interactive callbacks"""
        
        @self.app.callback(
            Output('tab-content', 'children'),
            Input('main-tabs', 'active_tab')
        )
        def update_tab_content(active_tab):
            if active_tab == 'portfolio':
                return self._create_portfolio_tab()
            elif active_tab == 'positions':
                return self._create_positions_tab()
            elif active_tab == 'market':
                return self._create_market_tab()
            elif active_tab == 'risk':
                return self._create_risk_tab()
            elif active_tab == 'health':
                return self._create_health_tab()
            return html.Div("Select a tab")
    
    def _create_portfolio_chart(self):
        """Create portfolio performance chart"""
        data = self.mock_data
        
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=data['timestamps'],
            y=data['portfolio_value'],
            mode='lines',
            name='Portfolio Value',
            line=dict(color='#00D2FF', width=3),
            fill='tonexty',
            fillcolor='rgba(0, 210, 255, 0.1)'
        ))
        
        fig.update_layout(
            plot_bgcolor='rgba(0,0,0,0)',
            paper_bgcolor='rgba(0,0,0,0)',
            font_color='white',
            title=dict(text="Portfolio Growth", font=dict(size=16, color='#8B949E')),
            xaxis=dict(gridcolor='#30363D', showgrid=True),
            yaxis=dict(gridcolor='#30363D', showgrid=True, tickformat='$,.0f'),
            margin=dict(l=20, r=20, t=40, b=20),
            hovermode='x unified'
        )
        
        return fig
    
    def _create_allocation_chart(self):
        """Create asset allocation pie chart"""
        labels = ['Options', 'Equities', 'Cash', 'Bonds']
        values = [45, 30, 15, 10]
        colors = ['#00D2FF', '#3A47D5', '#00C896', '#FFB800']
        
        fig = go.Figure(data=[go.Pie(
            labels=labels,
            values=values,
            hole=0.6,
            marker_colors=colors,
            textinfo='label+percent',
            textfont_size=12
        )])
        
        fig.update_layout(
            plot_bgcolor='rgba(0,0,0,0)',
            paper_bgcolor='rgba(0,0,0,0)',
            font_color='white',
            margin=dict(l=20, r=20, t=20, b=20),
            showlegend=False
        )
        
        return fig
    
    def _create_market_chart(self):
        """Create market data chart"""
        data = self.mock_data
        
        fig = go.Figure()
        
        colors = ['#00D2FF', '#3A47D5', '#00C896', '#FFB800', '#FF4757']
        for i, (symbol, prices) in enumerate(data['prices'].items()):
            fig.add_trace(go.Scatter(
                x=data['timestamps'],
                y=prices,
                mode='lines',
                name=symbol,
                line=dict(color=colors[i % len(colors)], width=2)
            ))
        
        fig.update_layout(
            plot_bgcolor='rgba(0,0,0,0)',
            paper_bgcolor='rgba(0,0,0,0)',
            font_color='white',
            title=dict(text="Market Overview", font=dict(size=16, color='#8B949E')),
            xaxis=dict(gridcolor='#30363D', showgrid=True),
            yaxis=dict(gridcolor='#30363D', showgrid=True, tickformat='$,.0f'),
            margin=dict(l=20, r=20, t=40, b=20),
            hovermode='x unified'
        )
        
        return fig
    
    def _create_risk_chart(self):
        """Create risk metrics chart"""
        dates = pd.date_range(start='2024-01-01', periods=30, freq='D')
        var_95 = np.random.uniform(8000, 15000, 30)
        var_99 = np.random.uniform(12000, 20000, 30)
        
        fig = go.Figure()
        
        fig.add_trace(go.Scatter(
            x=dates,
            y=var_95,
            mode='lines+markers',
            name='VaR 95%',
            line=dict(color='#00D2FF', width=3),
            marker=dict(size=6)
        ))
        
        fig.add_trace(go.Scatter(
            x=dates,
            y=var_99,
            mode='lines+markers',
            name='VaR 99%',
            line=dict(color='#FF4757', width=3),
            marker=dict(size=6)
        ))
        
        fig.update_layout(
            plot_bgcolor='rgba(0,0,0,0)',
            paper_bgcolor='rgba(0,0,0,0)',
            font_color='white',
            title=dict(text="Value at Risk Trends", font=dict(size=16, color='#8B949E')),
            xaxis=dict(gridcolor='#30363D', showgrid=True),
            yaxis=dict(gridcolor='#30363D', showgrid=True, tickformat='$,.0f'),
            margin=dict(l=20, r=20, t=40, b=20),
            hovermode='x unified'
        )
        
        return fig
    
    def _create_positions_table(self):
        """Create positions table"""
        positions = self.mock_data['positions']
        
        rows = []
        for pos in positions:
            pnl_color = '#00C896' if pos['pnl'] >= 0 else '#FF4757'
            pnl_icon = 'fas fa-arrow-up' if pos['pnl'] >= 0 else 'fas fa-arrow-down'
            
            row = html.Div([
                dbc.Row([
                    dbc.Col([
                        html.H6(pos['symbol'], className='mb-1', style={'color': '#00D2FF'}),
                        html.Small(f"{pos['type']} ${pos['strike']}", className='text-muted')
                    ], md=2),
                    dbc.Col([
                        html.P(f"{pos['quantity']:+d}", className='mb-1', 
                              style={'fontSize': '1.1rem', 'fontWeight': '600'}),
                        html.Small("Quantity", className='text-muted')
                    ], md=2),
                    dbc.Col([
                        html.P(f"${pos['market_value']:,.0f}", className='mb-1',
                              style={'fontSize': '1.1rem', 'fontWeight': '600'}),
                        html.Small("Market Value", className='text-muted')
                    ], md=2),
                    dbc.Col([
                        html.P([
                            html.I(className=pnl_icon),
                            f" ${pos['pnl']:+,.0f}"
                        ], className='mb-1', style={'color': pnl_color, 'fontSize': '1.1rem', 'fontWeight': '600'}),
                        html.Small("P&L", className='text-muted')
                    ], md=2),
                    dbc.Col([
                        html.P(f"{pos['delta']:+.3f}", className='mb-1',
                              style={'fontSize': '1.0rem', 'fontWeight': '500'}),
                        html.Small("Delta", className='text-muted')
                    ], md=2),
                    dbc.Col([
                        html.P(f"{pos['iv']:.1%}", className='mb-1',
                              style={'fontSize': '1.0rem', 'fontWeight': '500'}),
                        html.Small("IV", className='text-muted')
                    ], md=2)
                ])
            ], style={
                'background': '#1A1E23',
                'border': '1px solid #30363D',
                'borderRadius': '8px',
                'marginBottom': '8px',
                'padding': '16px'
            })
            
            rows.append(row)
        
        return html.Div(rows)
    
    def _create_service_status(self):
        """Create service status display"""
        services = [
            {'name': 'Market Data Service', 'status': 'healthy'},
            {'name': 'Options Pricing Service', 'status': 'healthy'},
            {'name': 'Execution Service', 'status': 'warning'},
            {'name': 'Risk Engine', 'status': 'healthy'},
            {'name': 'Notification Service', 'status': 'healthy'}
        ]
        
        rows = []
        for service in services:
            status_class = f"status-{service['status']}"
            
            row = dbc.Row([
                dbc.Col([
                    html.Div([
                        html.Span(className=f"status-indicator {status_class}"),
                        html.Span(service['name'], style={'fontWeight': '500'})
                    ])
                ], md=8),
                dbc.Col([
                    dbc.Badge(service['status'].title(), 
                             color='success' if service['status'] == 'healthy' else 'warning')
                ], md=4)
            ], className='align-items-center mb-3')
            
            rows.append(row)
        
        return html.Div(rows)
    
    def _create_alerts_feed(self):
        """Create alerts feed"""
        alerts = [
            {'time': '14:32', 'level': 'info', 'message': 'New position opened: SPY Call 500'},
            {'time': '14:28', 'level': 'warning', 'message': 'Portfolio delta approaching limit'},
            {'time': '14:15', 'level': 'success', 'message': 'Risk assessment completed successfully'},
            {'time': '14:12', 'level': 'info', 'message': 'Market data feed reconnected'},
            {'time': '14:08', 'level': 'warning', 'message': 'High volatility detected in SPX options'}
        ]
        
        rows = []
        for alert in alerts:
            icon_map = {
                'info': 'fas fa-info-circle',
                'warning': 'fas fa-exclamation-triangle',
                'success': 'fas fa-check-circle',
                'error': 'fas fa-times-circle'
            }
            
            color_map = {
                'info': '#00D2FF',
                'warning': '#FFB800',
                'success': '#00C896',
                'error': '#FF4757'
            }
            
            row = html.Div([
                html.Div([
                    html.I(className=icon_map[alert['level']], 
                          style={'color': color_map[alert['level']], 'marginRight': '8px'}),
                    html.Span(alert['message'], style={'fontSize': '0.9rem'}),
                    html.Small(alert['time'], className='text-muted ms-auto')
                ], className='d-flex align-items-center justify-content-between')
            ], className='mb-2', style={'padding': '8px', 'borderLeft': f"3px solid {color_map[alert['level']]}"})
            
            rows.append(row)
        
        return html.Div(rows)
    
    def run(self, debug=False, host='0.0.0.0'):
        """Run the fancy dashboard"""
        print(f"🚀 Starting Fancy Trading Dashboard...")
        print(f"📊 Dashboard URL: http://localhost:{self.port}")
        print(f"✨ Features: Real-time data, animations, modern UI")
        
        self.app.run_server(
            debug=debug,
            host=host,
            port=self.port,
            dev_tools_ui=debug,
            dev_tools_props_check=debug
        )

if __name__ == "__main__":
    dashboard = FancyTradingDashboard(port=8050)
    dashboard.run(debug=True)