"""
Dashboard for real-time monitoring
"""
import logging
import threading
import dash
from dash import html, dcc
import plotly.graph_objects as go
from datetime import datetime

logger = logging.getLogger(__name__)

class Dashboard:
    """Real-time monitoring dashboard"""
    
    def __init__(self, strategy=None, feed_manager=None, port=8050):
        self.strategy = strategy
        self.feed_manager = feed_manager
        self.port = port
        self.app = None
        
        self._setup_dashboard()
        logger.info(f"Dashboard initialized on port {port}")
    
    def _setup_dashboard(self):
        """Setup the Dash application"""
        self.app = dash.Dash(__name__)
        
        self.app.layout = html.Div([
            html.H1('Heston Trading System Dashboard', 
                   style={'textAlign': 'center'}),
            
            html.Div([
                html.Div([
                    html.H3('System Status'),
                    html.P(id='status', children='Running'),
                ], style={'width': '48%', 'display': 'inline-block'}),
                
                html.Div([
                    html.H3('Market Data'),
                    html.P(id='market-data', children='Loading...'),
                ], style={'width': '48%', 'float': 'right', 'display': 'inline-block'})
            ]),
            
            dcc.Graph(id='live-graph'),
            
            dcc.Interval(
                id='interval-component',
                interval=5000,  # Update every 5 seconds
                n_intervals=0
            )
        ])
        
        # Setup callbacks
        @self.app.callback(
            [dash.dependencies.Output('market-data', 'children'),
             dash.dependencies.Output('live-graph', 'figure')],
            [dash.dependencies.Input('interval-component', 'n_intervals')]
        )
        def update_dashboard(n):
            # Get market data
            if self.feed_manager:
                snapshot = self.feed_manager.get_snapshot()
                if snapshot and 'SPX' in snapshot:
                    spx = snapshot['SPX']
                    market_text = f"SPX: {spx['last']:.2f} | VIX: {snapshot.get('VIX', {}).get('last', 0):.2f}"
                else:
                    market_text = "No data"
            else:
                market_text = "Feed not connected"
            
            # Create simple chart
            fig = go.Figure()
            fig.add_trace(go.Scatter(
                x=[datetime.now()],
                y=[5000],
                mode='lines+markers',
                name='SPX'
            ))
            fig.update_layout(
                title='SPX Price',
                xaxis_title='Time',
                yaxis_title='Price'
            )
            
            return market_text, fig
    
    def start(self):
        """Start the dashboard in a separate thread"""
        def run_dash():
            self.app.run_server(host='0.0.0.0', port=self.port, debug=False)
        
        thread = threading.Thread(target=run_dash, daemon=True)
        thread.start()
        logger.info(f"Dashboard started at http://localhost:{self.port}")
