"""
Real-time options dashboard with 5-second updates
"""
import dash
from dash import dcc, html, dash_table, Input, Output, State
import plotly.graph_objs as go
import plotly.express as px
import pandas as pd
from datetime import datetime, timedelta
import threading
import time
import logging

from data.realtime_monitor import RealTimeOptionsMonitor

logger = logging.getLogger(__name__)

class OptionsDashboard:
    """Real-time options dashboard"""
    
    def __init__(self, config: dict):
        self.config = config
        self.app = dash.Dash(__name__)
        self.monitor = None
        self.current_data = {}
        
        # Setup layout
        self._setup_layout()
        self._setup_callbacks()
        
        logger.info("Options dashboard initialized")
        
    def _setup_layout(self):
        """Setup dashboard layout"""
        self.app.layout = html.Div([
            # Header
            html.Div([
                html.H1("SPX/XSP Options Real-Time Monitor", 
                       className="text-center mb-4"),
                html.P(f"Last Updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", 
                      id="last-update", className="text-center text-muted")
            ], className="container-fluid bg-dark text-white p-3"),
            
            # Auto-refresh component
            dcc.Interval(
                id='interval-component',
                interval=5*1000,  # 5 seconds
                n_intervals=0
            ),
            
            # Market Overview
            html.Div([
                html.H3("Market Overview"),
                html.Div(id="market-overview", className="row")
            ], className="container-fluid mt-3"),
            
            # Underlying Assets
            html.Div([
                html.H3("Underlying Assets"),
                html.Div(id="underlying-data", className="row")
            ], className="container-fluid mt-3"),
            
            # Options Table
            html.Div([
                html.H3("Screened Options"),
                html.Div([
                    html.Label("Filter by Symbol:"),
                    dcc.Dropdown(
                        id='symbol-filter',
                        options=[
                            {'label': 'All', 'value': 'ALL'},
                            {'label': 'SPX', 'value': 'SPX'},
                            {'label': 'XSP', 'value': 'XSP'}
                        ],
                        value='ALL',
                        className="mb-2"
                    ),
                    html.Label("Filter by Type:"),
                    dcc.Dropdown(
                        id='type-filter',
                        options=[
                            {'label': 'All', 'value': 'ALL'},
                            {'label': 'Calls', 'value': 'C'},
                            {'label': 'Puts', 'value': 'P'}
                        ],
                        value='ALL',
                        className="mb-2"
                    )
                ], className="col-md-3"),
                
                html.Div([
                    dash_table.DataTable(
                        id='options-table',
                        columns=[
                            {'name': 'Symbol', 'id': 'symbol'},
                            {'name': 'Strike', 'id': 'strike', 'type': 'numeric', 'format': {'specifier': '.2f'}},
                            {'name': 'Type', 'id': 'option_type'},
                            {'name': 'DTE', 'id': 'dte'},
                            {'name': 'Bid', 'id': 'bid', 'type': 'numeric', 'format': {'specifier': '.2f'}},
                            {'name': 'Ask', 'id': 'ask', 'type': 'numeric', 'format': {'specifier': '.2f'}},
                            {'name': 'Mid', 'id': 'midpoint', 'type': 'numeric', 'format': {'specifier': '.2f'}},
                            {'name': 'Last', 'id': 'last_price', 'type': 'numeric', 'format': {'specifier': '.2f'}},
                            {'name': 'Volume', 'id': 'volume', 'type': 'numeric'},
                            {'name': 'OI', 'id': 'open_interest', 'type': 'numeric'},
                            {'name': 'IV', 'id': 'implied_vol', 'type': 'numeric', 'format': {'specifier': '.1%'}},
                            {'name': 'Delta', 'id': 'delta', 'type': 'numeric', 'format': {'specifier': '.3f'}},
                            {'name': 'Gamma', 'id': 'gamma', 'type': 'numeric', 'format': {'specifier': '.4f'}},
                            {'name': 'Theta', 'id': 'theta', 'type': 'numeric', 'format': {'specifier': '.2f'}},
                            {'name': 'Vega', 'id': 'vega', 'type': 'numeric', 'format': {'specifier': '.2f'}},
                        ],
                        data=[],
                        sort_action="native",
                        filter_action="native",
                        page_action="native",
                        page_current=0,
                        page_size=20,
                        style_cell={'textAlign': 'center', 'fontSize': '12px'},
                        style_header={'backgroundColor': 'rgb(230, 230, 230)', 'fontWeight': 'bold'},
                        style_data_conditional=[
                            {
                                'if': {'filter_query': '{option_type} = C'},
                                'backgroundColor': 'rgba(0, 255, 0, 0.1)',
                            },
                            {
                                'if': {'filter_query': '{option_type} = P'},
                                'backgroundColor': 'rgba(255, 0, 0, 0.1)',
                            }
                        ]
                    )
                ], className="col-md-12")
            ], className="container-fluid mt-3"),
            
            # Charts
            html.Div([
                html.H3("Analytics"),
                html.Div([
                    html.Div([
                        dcc.Graph(id='iv-surface-chart')
                    ], className="col-md-6"),
                    html.Div([
                        dcc.Graph(id='volume-chart')
                    ], className="col-md-6")
                ], className="row"),
                html.Div([
                    html.Div([
                        dcc.Graph(id='greeks-chart')
                    ], className="col-md-6"),
                    html.Div([
                        dcc.Graph(id='moneyness-chart')
                    ], className="col-md-6")
                ], className="row")
            ], className="container-fluid mt-3")
        ])
        
    def _setup_callbacks(self):
        """Setup dashboard callbacks"""
        
        @self.app.callback(
            [Output('last-update', 'children'),
             Output('market-overview', 'children'),
             Output('underlying-data', 'children'),
             Output('options-table', 'data')],
            [Input('interval-component', 'n_intervals'),
             Input('symbol-filter', 'value'),
             Input('type-filter', 'value')]
        )
        def update_dashboard(n, symbol_filter, type_filter):
            if self.monitor:
                snapshot = self.monitor.get_current_snapshot()
                if snapshot:
                    self.current_data = snapshot
                    
                    # Update timestamp
                    timestamp = f"Last Updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
                    
                    # Market overview
                    market_overview = self._create_market_overview(snapshot.get('market_overview', {}))
                    
                    # Underlying data
                    underlying_data = self._create_underlying_cards(snapshot.get('underlying_data', {}))
                    
                    # Options table data
                    options_data = self._filter_options_data(
                        snapshot.get('screened_options', []), 
                        symbol_filter, 
                        type_filter
                    )
                    
                    return timestamp, market_overview, underlying_data, options_data
                    
            return "No data available", [], [], []
            
        @self.app.callback(
            Output('iv-surface-chart', 'figure'),
            [Input('interval-component', 'n_intervals')]
        )
        def update_iv_surface(n):
            if not self.current_data:
                return go.Figure()
                
            return self._create_iv_surface_chart()
            
        @self.app.callback(
            Output('volume-chart', 'figure'),
            [Input('interval-component', 'n_intervals')]
        )
        def update_volume_chart(n):
            if not self.current_data:
                return go.Figure()
                
            return self._create_volume_chart()
            
        @self.app.callback(
            Output('greeks-chart', 'figure'),
            [Input('interval-component', 'n_intervals')]
        )
        def update_greeks_chart(n):
            if not self.current_data:
                return go.Figure()
                
            return self._create_greeks_chart()
            
        @self.app.callback(
            Output('moneyness-chart', 'figure'),
            [Input('interval-component', 'n_intervals')]
        )
        def update_moneyness_chart(n):
            if not self.current_data:
                return go.Figure()
                
            return self._create_moneyness_chart()
    
    def _create_market_overview(self, overview: dict) -> list:
        """Create market overview cards"""
        cards = []
        
        # Total options
        total_options = overview.get('total_screened_options', 0)
        cards.append(
            html.Div([
                html.H4(str(total_options), className="text-primary"),
                html.P("Screened Options")
            ], className="col-md-2 text-center border p-3")
        )
        
        # Volatility metrics
        vol_metrics = overview.get('volatility_metrics', {})
        if vol_metrics:
            avg_iv = vol_metrics.get('avg_iv', 0)
            cards.append(
                html.Div([
                    html.H4(f"{avg_iv:.1%}", className="text-info"),
                    html.P("Avg IV")
                ], className="col-md-2 text-center border p-3")
            )
        
        return cards
    
    def _create_underlying_cards(self, underlying_data: dict) -> list:
        """Create underlying asset cards"""
        cards = []
        
        for symbol, data in underlying_data.items():
            last_price = data.get('last', 0)
            midpoint = data.get('midpoint', 0)
            price_to_show = last_price if last_price > 0 else midpoint
            
            cards.append(
                html.Div([
                    html.H5(symbol, className="text-primary"),
                    html.H4(f"${price_to_show:.2f}"),
                    html.P(f"Bid: ${data.get('bid', 0):.2f} | Ask: ${data.get('ask', 0):.2f}")
                ], className="col-md-2 text-center border p-3")
            )
            
        return cards
    
    def _filter_options_data(self, options_data: list, symbol_filter: str, type_filter: str) -> list:
        """Filter options data based on user selections"""
        filtered = options_data.copy()
        
        if symbol_filter != 'ALL':
            filtered = [opt for opt in filtered if opt.get('symbol') == symbol_filter]
            
        if type_filter != 'ALL':
            filtered = [opt for opt in filtered if opt.get('option_type') == type_filter]
            
        return filtered
    
    def _create_iv_surface_chart(self) -> go.Figure:
        """Create implied volatility surface chart"""
        options_data = self.current_data.get('screened_options', [])
        if not options_data:
            return go.Figure()
            
        df = pd.DataFrame(options_data)
        
        # Filter for calls only for cleaner surface
        calls_df = df[df['option_type'] == 'C'].copy()
        
        if calls_df.empty:
            return go.Figure()
            
        fig = px.scatter_3d(
            calls_df, 
            x='strike', 
            y='dte', 
            z='implied_vol',
            color='volume',
            title='Implied Volatility Surface (Calls)',
            labels={'strike': 'Strike', 'dte': 'DTE', 'implied_vol': 'IV'}
        )
        
        fig.update_layout(height=400)
        return fig
    
    def _create_volume_chart(self) -> go.Figure:
        """Create volume distribution chart"""
        options_data = self.current_data.get('screened_options', [])
        if not options_data:
            return go.Figure()
            
        df = pd.DataFrame(options_data)
        
        # Top 20 by volume
        top_volume = df.nlargest(20, 'volume')
        
        fig = px.bar(
            top_volume,
            x='volume',
            y=[f"{row['symbol']} {row['strike']}{row['option_type']}" for _, row in top_volume.iterrows()],
            orientation='h',
            title='Top 20 Options by Volume',
            labels={'volume': 'Volume', 'y': 'Option'}
        )
        
        fig.update_layout(height=400)
        return fig
    
    def _create_greeks_chart(self) -> go.Figure:
        """Create Greeks distribution chart"""
        options_data = self.current_data.get('screened_options', [])
        if not options_data:
            return go.Figure()
            
        df = pd.DataFrame(options_data)
        
        fig = go.Figure()
        
        # Delta distribution
        fig.add_trace(go.Histogram(
            x=df['delta'],
            name='Delta',
            opacity=0.7,
            nbinsx=30
        ))
        
        fig.update_layout(
            title='Delta Distribution',
            xaxis_title='Delta',
            yaxis_title='Count',
            height=400
        )
        
        return fig
    
    def _create_moneyness_chart(self) -> go.Figure:
        """Create moneyness vs IV chart"""
        options_data = self.current_data.get('screened_options', [])
        if not options_data:
            return go.Figure()
            
        df = pd.DataFrame(options_data)
        
        fig = px.scatter(
            df,
            x='moneyness',
            y='implied_vol',
            color='option_type',
            size='volume',
            title='Moneyness vs Implied Volatility',
            labels={'moneyness': 'Moneyness (Strike/Spot)', 'implied_vol': 'Implied Volatility'}
        )
        
        fig.update_layout(height=400)
        return fig
    
    def start_monitor(self):
        """Start the real-time monitor"""
        self.monitor = RealTimeOptionsMonitor(self.config)
        if self.monitor.start():
            logger.info("Real-time monitor started successfully")
        else:
            logger.error("Failed to start real-time monitor")
    
    def run(self, host='127.0.0.1', port=8050, debug=False):
        """Run the dashboard"""
        # Start monitor in background
        monitor_thread = threading.Thread(target=self.start_monitor, daemon=True)
        monitor_thread.start()
        
        # Give monitor time to start
        time.sleep(5)
        
        # Run dashboard
        logger.info(f"Starting dashboard at http://{host}:{port}")
        self.app.run_server(host=host, port=port, debug=debug)
    
    def stop(self):
        """Stop the dashboard and monitor"""
        if self.monitor:
            self.monitor.stop()
