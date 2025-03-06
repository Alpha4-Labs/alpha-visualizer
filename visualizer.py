import plotly.graph_objects as go
from plotly.subplots import make_subplots
import dash_bootstrap_components as dbc
from dash import html, dcc
import numpy as np
import pandas as pd
from config import COLORS, GRID_COLUMNS, PANEL_HEIGHTS, CHART_WINDOW_SIZE, MAX_DATA_POINTS_PER_CHART, FPS

# Enable debugging
DEBUG = True

def debug_print(*args, **kwargs):
    """Print debug messages if debugging is enabled"""
    if DEBUG:
        print("[VIZ-DEBUG]", *args, **kwargs)

def create_layout():
    """Create the dashboard layout"""
    debug_print("Creating dashboard layout")
    
    layout = dbc.Container([
        dbc.Row([
            dbc.Col([
                html.H2("Alpha Economic Simulation", className="text-center mb-4")
            ], width=GRID_COLUMNS)
        ]),
        
        # Animation controls
        dbc.Row([
            dbc.Col([
                dbc.ButtonGroup([
                    dbc.Button("Play", id="play-button", color="primary", className="me-1"),
                    dbc.Button("Pause", id="pause-button", color="secondary", className="me-1"),
                    dbc.Button("Reset", id="reset-button", color="warning", className="me-1"),
                ], className="me-2"),
                html.Span("Playback Speed: ", className="ms-2 me-1"),
                html.Div([
                    dcc.Slider(
                        id='speed-slider',
                        min=0.5,
                        max=2,
                        step=0.1,
                        value=1,
                        marks={i: f'{i}x' for i in [0.5, 1, 1.5, 2]},
                        className="ms-1 me-2"
                    )
                ], style={"width": "200px", "display": "inline-block"}),
                dbc.Button("Record Video", id="record-button", color="success", className="ms-2"),
                html.Div(id="simulation-day", className="ms-4", style={"display": "inline-block"}),
            ], width=GRID_COLUMNS, className="d-flex align-items-center")
        ], className="mb-4"),
        
        # Main charts row
        dbc.Row([
            # Exchange Rate Chart
            dbc.Col([
                dbc.Card([
                    dbc.CardHeader("Exchange Rate"),
                    dbc.CardBody([
                        dcc.Graph(id="exchange-rate-chart", figure={}, style={"height": f"{PANEL_HEIGHTS['main']}px"})
                    ])
                ])
            ], width=GRID_COLUMNS // 2),
            
            # Transaction Cost Chart (Changed from Token Price)
            dbc.Col([
                dbc.Card([
                    dbc.CardHeader("Transaction Cost (USD)"),  # Updated title
                    dbc.CardBody([
                        dcc.Graph(id="transaction-cost-chart", figure={}, style={"height": f"{PANEL_HEIGHTS['main']}px"})  # Updated ID
                    ])
                ])
            ], width=GRID_COLUMNS // 2)
        ], className="mb-4"),
        
        # Secondary charts row
        dbc.Row([
            # Network & Generation Rate Chart
            dbc.Col([
                dbc.Card([
                    dbc.CardHeader("Network & Generation Rates"),
                    dbc.CardBody([
                        dcc.Graph(id="network-gen-chart", figure={}, style={"height": f"{PANEL_HEIGHTS['secondary']}px"})
                    ])
                ])
            ], width=GRID_COLUMNS // 3),
            
            # Warehouse Capacity & AlphaPoints Level Chart
            dbc.Col([
                dbc.Card([
                    dbc.CardHeader("Warehouse Metrics"),
                    dbc.CardBody([
                        dcc.Graph(id="warehouse-chart", figure={}, style={"height": f"{PANEL_HEIGHTS['secondary']}px"})
                    ])
                ])
            ], width=GRID_COLUMNS // 3),
            
            # AlphaPoints Flow Chart
            dbc.Col([
                dbc.Card([
                    dbc.CardHeader("AlphaPoints Flow"),
                    dbc.CardBody([
                        dcc.Graph(id="alpha-flow-chart", figure={}, style={"height": f"{PANEL_HEIGHTS['secondary']}px"})
                    ])
                ])
            ], width=GRID_COLUMNS // 3)
        ]),
        
        # Hidden components for animation state
        dcc.Store(id="animation-state", data={"playing": False, "current_block": 0, "speed": 1.0}),
        dcc.Interval(id="animation-interval", interval=1000 / FPS, n_intervals=0, disabled=True),
        
        # Hidden download component
        dcc.Download(id="download-video")
    ], fluid=True)
    
    return layout

def optimize_chart_data(data_slice, current_block, max_block, chart_column):
    """Optimize data for chart creation - common function to avoid duplicate code"""
    debug_print(f"Optimizing chart data for column: {chart_column}")
    
    # Use a smaller window size to reduce filtering overhead
    window_size = CHART_WINDOW_SIZE
    start_block = max(0, current_block - window_size // 2)
    end_block = min(max_block, current_block + window_size // 2)
    
    debug_print(f"Window range: {start_block} to {end_block}")
    
    # OPTIMIZATION: Calculate approximate indices based on block interval
    block_interval = data_slice.attrs.get('block_interval', 1000)
    start_idx = max(0, int(start_block / block_interval) - 1)
    end_idx = min(len(data_slice), int(end_block / block_interval) + 2)
    
    # Get a slice of the data first (much faster than filtering the whole dataset)
    data_subset = data_slice.iloc[start_idx:end_idx]
    
    # Now filter the smaller subset
    window_data = data_subset[(data_subset['block'] >= start_block) & (data_subset['block'] <= end_block)]
    
    # If we have too many points, downsample for performance
    if len(window_data) > MAX_DATA_POINTS_PER_CHART:
        debug_print(f"Downsampling from {len(window_data)} to {MAX_DATA_POINTS_PER_CHART} points")
        # Systematic sampling - take every nth point
        n = len(window_data) // MAX_DATA_POINTS_PER_CHART
        window_data = window_data.iloc[::n].copy()
    
    debug_print(f"Window contains {len(window_data)} data points")
    
    return {
        'window_data': window_data,
        'start_block': start_block,
        'end_block': end_block,
        'current_value': find_current_value(data_slice, current_block, chart_column)
    }
    
def find_current_value(data_slice, current_block, column):
    """Find the current value for a column at the specified block - optimized"""
    try:
        # OPTIMIZATION: Calculate index directly based on block interval
        block_interval = data_slice.attrs.get('block_interval', 1000)
        closest_idx = min(len(data_slice) - 1, max(0, int(round(current_block / block_interval))))
        
        # Check if our guess is close enough
        if abs(data_slice.iloc[closest_idx]['block'] - current_block) > block_interval * 2:
            # If not close enough, use a more thorough search
            closest_idx = (data_slice['block'] - current_block).abs().idxmin()
            
        closest_block = data_slice.iloc[closest_idx]['block']
        current_value = data_slice.iloc[closest_idx][column]
        
        debug_print(f"Current marker at block {closest_block} with {column}={current_value}")
        return {
            'block': closest_block,
            'value': current_value
        }
    except Exception as e:
        debug_print(f"ERROR finding current value: {e}")
        return None

def create_exchange_rate_chart(data_slice, current_block, max_block):
    """Create the exchange rate chart with debug info - optimized version"""
    debug_print(f"Creating exchange rate chart for block {current_block}, max_block {max_block}")
    
    try:
        # Validate inputs
        if data_slice is None or len(data_slice) == 0:
            debug_print("ERROR: Empty data provided to exchange_rate_chart")
            # Return an empty chart rather than failing
            fig = go.Figure()
            fig.update_layout(
                title="No Data Available",
                xaxis_title="Block",
                yaxis_title="Exchange Rate"
            )
            return fig
        
        if 'exchange_rate' not in data_slice.columns:
            debug_print(f"ERROR: 'exchange_rate' column not found in data")
            debug_print(f"Available columns: {data_slice.columns.tolist()}")
            # Return an empty chart rather than failing
            fig = go.Figure()
            fig.update_layout(
                title="Missing Data Column: exchange_rate",
                xaxis_title="Block",
                yaxis_title="Exchange Rate"
            )
            return fig
        
        # Get optimized data for the chart
        chart_data = optimize_chart_data(data_slice, current_block, max_block, 'exchange_rate')
        window_data = chart_data['window_data']
        start_block = chart_data['start_block']
        end_block = chart_data['end_block']
        current_marker = chart_data['current_value']
        
        if len(window_data) == 0:
            debug_print("WARNING: No data points in the window range")
            # Create a simple empty chart rather than failing
            fig = go.Figure()
            fig.update_layout(
                title="No Data in Current Window",
                xaxis_title="Block",
                yaxis_title="Exchange Rate"
            )
            return fig
        
        # Create figure
        fig = go.Figure()
        
        # Add exchange rate line
        fig.add_trace(
            go.Scatter(
                x=window_data['block'],
                y=window_data['exchange_rate'],
                mode='lines',
                line=dict(color=COLORS['exchange_rate'], width=3),
                name='Exchange Rate'
            )
        )
        
        # Add marker for current position
        if current_marker:
            fig.add_trace(
                go.Scatter(
                    x=[current_marker['block']],
                    y=[current_marker['value']],
                    mode='markers',
                    marker=dict(color=COLORS['highlight'], size=12, symbol='circle'),
                    showlegend=False
                )
            )
        
        # Update layout
        fig.update_layout(
            margin=dict(l=20, r=20, t=20, b=20),
            plot_bgcolor=COLORS['background'],
            paper_bgcolor=COLORS['background'],
            font=dict(color=COLORS['text']),
            xaxis=dict(
                title='Block',
                gridcolor=COLORS['chart_grid'],
                range=[start_block, end_block]
            ),
            yaxis=dict(
                title='Exchange Rate',
                gridcolor=COLORS['chart_grid']
            ),
            hovermode='x unified'
        )
        
        return fig
        
    except Exception as e:
        debug_print(f"ERROR in create_exchange_rate_chart: {e}")
        import traceback
        traceback.print_exc()
        # Return a minimal chart rather than failing
        fig = go.Figure()
        fig.update_layout(
            title=f"Error: {str(e)}",
            xaxis_title="Block",
            yaxis_title="Exchange Rate"
        )
        return fig

def create_transaction_cost_chart(data_slice, current_block, max_block):
    """Create the transaction cost chart with debug info - optimized version"""
    debug_print(f"Creating transaction cost chart for block {current_block}, max_block {max_block}")
    
    try:
        # Validate inputs
        if data_slice is None or len(data_slice) == 0:
            debug_print("ERROR: Empty data provided to transaction_cost_chart")
            # Return an empty chart rather than failing
            fig = go.Figure()
            fig.update_layout(
                title="No Data Available",
                xaxis_title="Block",
                yaxis_title="Transaction Cost (USD)"
            )
            return fig
        
        if 'average_transaction_cost_usd' not in data_slice.columns:
            debug_print(f"ERROR: 'average_transaction_cost_usd' column not found in data")
            debug_print(f"Available columns: {data_slice.columns.tolist()}")
            # Return an empty chart rather than failing
            fig = go.Figure()
            fig.update_layout(
                title="Missing Data Column: average_transaction_cost_usd",
                xaxis_title="Block",
                yaxis_title="Transaction Cost (USD)"
            )
            return fig
        
        # Get optimized data for the chart
        chart_data = optimize_chart_data(data_slice, current_block, max_block, 'average_transaction_cost_usd')
        window_data = chart_data['window_data']
        start_block = chart_data['start_block']
        end_block = chart_data['end_block']
        current_marker = chart_data['current_value']
        
        if len(window_data) == 0:
            debug_print("WARNING: No data points in the window range")
            # Create a simple empty chart rather than failing
            fig = go.Figure()
            fig.update_layout(
                title="No Data in Current Window",
                xaxis_title="Block",
                yaxis_title="Transaction Cost (USD)"
            )
            return fig
        
        # Create figure
        fig = go.Figure()
        
        # Add transaction cost line
        fig.add_trace(
            go.Scatter(
                x=window_data['block'],
                y=window_data['average_transaction_cost_usd'],
                mode='lines',
                line=dict(color=COLORS['transaction_cost'], width=3),
                fill='tozeroy',
                fillcolor=f"rgba({int(COLORS['transaction_cost'][1:3], 16)}, {int(COLORS['transaction_cost'][3:5], 16)}, {int(COLORS['transaction_cost'][5:7], 16)}, 0.2)",
                name='Transaction Cost'
            )
        )
        
        # Add marker for current position
        if current_marker:
            fig.add_trace(
                go.Scatter(
                    x=[current_marker['block']],
                    y=[current_marker['value']],
                    mode='markers',
                    marker=dict(color=COLORS['highlight'], size=12, symbol='circle'),
                    showlegend=False
                )
            )
        
        # Update layout
        fig.update_layout(
            margin=dict(l=20, r=20, t=20, b=20),
            plot_bgcolor=COLORS['background'],
            paper_bgcolor=COLORS['background'],
            font=dict(color=COLORS['text']),
            xaxis=dict(
                title='Block',
                gridcolor=COLORS['chart_grid'],
                range=[start_block, end_block]
            ),
            yaxis=dict(
                title='Cost (USD)',
                gridcolor=COLORS['chart_grid'],
                tickprefix='$'
            ),
            hovermode='x unified'
        )
        
        return fig
        
    except Exception as e:
        debug_print(f"ERROR in create_transaction_cost_chart: {e}")
        import traceback
        traceback.print_exc()
        # Return a minimal chart rather than failing
        fig = go.Figure()
        fig.update_layout(
            title=f"Error: {str(e)}",
            xaxis_title="Block",
            yaxis_title="Transaction Cost (USD)"
        )
        return fig

def create_network_gen_chart(data_slice, current_block, max_block):
    """Create the network and generation rates chart with debug info - optimized version"""
    debug_print(f"Creating network/generation chart for block {current_block}")
    
    try:
        # Validate inputs
        if data_slice is None or len(data_slice) == 0:
            debug_print("ERROR: Empty data provided to network_gen_chart")
            # Return an empty chart rather than failing
            fig = go.Figure()
            fig.update_layout(
                title="No Data Available",
                xaxis_title="Block",
                yaxis_title="Rates"
            )
            return fig
        
        for required_col in ['network_rate', 'generation_rate']:
            if required_col not in data_slice.columns:
                debug_print(f"ERROR: '{required_col}' column not found in data")
                debug_print(f"Available columns: {data_slice.columns.tolist()}")
                # Return an empty chart rather than failing
                fig = go.Figure()
                fig.update_layout(
                    title=f"Missing Data Column: {required_col}",
                    xaxis_title="Block",
                    yaxis_title="Rates"
                )
                return fig
            
        # Get optimized data for network rate chart
        network_data = optimize_chart_data(data_slice, current_block, max_block, 'network_rate')
        window_data = network_data['window_data']
        start_block = network_data['start_block']
        end_block = network_data['end_block']
        network_marker = network_data['current_value']
        
        # Get current generation rate value
        generation_marker = find_current_value(data_slice, current_block, 'generation_rate')
        
        if len(window_data) == 0:
            debug_print("WARNING: No data points in the window range")
            # Create a simple empty chart rather than failing
            fig = go.Figure()
            fig.update_layout(
                title="No Data in Current Window",
                xaxis_title="Block",
                yaxis_title="Rates"
            )
            return fig
        
        # Create figure with secondary Y axis
        fig = make_subplots(specs=[[{"secondary_y": True}]])
        
        # Add network rate line
        fig.add_trace(
            go.Scatter(
                x=window_data['block'],
                y=window_data['network_rate'],
                mode='lines',
                line=dict(color=COLORS['network_rate'], width=3),
                name='Network Rate'
            ),
            secondary_y=False
        )
        
        # Add generation rate line
        fig.add_trace(
            go.Scatter(
                x=window_data['block'],
                y=window_data['generation_rate'],
                mode='lines',
                line=dict(color=COLORS['generation_rate'], width=3),
                name='Generation Rate'
            ),
            secondary_y=True
        )
        
        # Add markers for current position
        if network_marker:
            fig.add_trace(
                go.Scatter(
                    x=[network_marker['block']],
                    y=[network_marker['value']],
                    mode='markers',
                    marker=dict(color=COLORS['highlight'], size=12, symbol='circle'),
                    showlegend=False
                ),
                secondary_y=False
            )
        
        if generation_marker:
            fig.add_trace(
                go.Scatter(
                    x=[generation_marker['block']],
                    y=[generation_marker['value']],
                    mode='markers',
                    marker=dict(color=COLORS['highlight'], size=12, symbol='circle'),
                    showlegend=False
                ),
                secondary_y=True
            )
        
        # Update layout
        fig.update_layout(
            margin=dict(l=20, r=20, t=20, b=20),
            plot_bgcolor=COLORS['background'],
            paper_bgcolor=COLORS['background'],
            font=dict(color=COLORS['text']),
            xaxis=dict(
                title='Block',
                gridcolor=COLORS['chart_grid'],
                range=[start_block, end_block]
            ),
            hovermode='x unified',
            legend=dict(
                orientation="h",
                yanchor="bottom",
                y=1.02,
                xanchor="right",
                x=1
            )
        )
        
        fig.update_yaxes(
            title_text="Network Rate",
            gridcolor=COLORS['chart_grid'],
            secondary_y=False
        )
        
        fig.update_yaxes(
            title_text="Generation Rate",
            gridcolor=COLORS['chart_grid'],
            secondary_y=True
        )
        
        return fig
        
    except Exception as e:
        debug_print(f"ERROR in create_network_gen_chart: {e}")
        import traceback
        traceback.print_exc()
        # Return a minimal chart rather than failing
        fig = go.Figure()
        fig.update_layout(
            title=f"Error: {str(e)}",
            xaxis_title="Block",
            yaxis_title="Rates"
        )
        return fig

def create_warehouse_chart(data_slice, current_block, max_block):
    """Create the warehouse metrics chart with capacity gauge - optimized version"""
    debug_print(f"Creating warehouse chart for block {current_block}")
    
    try:
        # Validate inputs
        if data_slice is None or len(data_slice) == 0:
            debug_print("ERROR: Empty data provided to warehouse_chart")
            # Return an empty chart rather than failing
            fig = go.Figure()
            fig.update_layout(
                title="No Data Available",
                xaxis_title="Block",
                yaxis_title="Warehouse Capacity"
            )
            return fig
        
        if 'warehouse_capacity' not in data_slice.columns:
            debug_print(f"ERROR: 'warehouse_capacity' column not found in data")
            debug_print(f"Available columns: {data_slice.columns.tolist()}")
            # Return an empty chart rather than failing
            fig = go.Figure()
            fig.update_layout(
                title="Missing Data Column: warehouse_capacity",
                xaxis_title="Block",
                yaxis_title="Warehouse Capacity"
            )
            return fig
        
        # Get the capacity value at current block - optimized    
        capacity_data = find_current_value(data_slice, current_block, 'warehouse_capacity')
        capacity = capacity_data['value'] if capacity_data else 50  # Default to middle value if error
        
        debug_print(f"Warehouse capacity at current block: {capacity}%")
        
        # Determine color based on capacity level
        if capacity < 33:
            color = COLORS['warehouse_capacity']['low']
        elif capacity < 66:
            color = COLORS['warehouse_capacity']['medium']
        else:
            color = COLORS['warehouse_capacity']['high']
        
        # Create figure
        fig = go.Figure()
        
        # Add gauge for warehouse capacity
        fig.add_trace(
            go.Indicator(
                mode="gauge+number",
                value=capacity,
                title={"text": "Warehouse Capacity (%)"},
                gauge={
                    'axis': {'range': [0, 100], 'tickwidth': 1},
                    'bar': {'color': color},
                    'steps': [
                        {'range': [0, 33], 'color': 'rgba(46, 204, 113, 0.3)'},
                        {'range': [33, 66], 'color': 'rgba(243, 156, 18, 0.3)'},
                        {'range': [66, 100], 'color': 'rgba(231, 76, 60, 0.3)'}
                    ],
                    'threshold': {
                        'line': {'color': "red", 'width': 4},
                        'thickness': 0.75,
                        'value': 95
                    }
                }
            )
        )
        
        # Update layout
        fig.update_layout(
            margin=dict(l=20, r=20, t=20, b=20),
            plot_bgcolor=COLORS['background'],
            paper_bgcolor=COLORS['background'],
            font=dict(color=COLORS['text'])
        )
        
        return fig
    
    except Exception as e:
        debug_print(f"ERROR in create_warehouse_chart: {e}")
        import traceback
        traceback.print_exc()
        # Return a minimal chart rather than failing
        fig = go.Figure()
        fig.update_layout(
            title=f"Error: {str(e)}",
            xaxis_title="Block",
            yaxis_title="Warehouse Capacity"
        )
        return fig

def create_alpha_flow_chart(data_slice, current_block, max_block):
    """Create the AlphaPoints flow chart with debug info - optimized version"""
    debug_print(f"Creating AlphaPoints flow chart for block {current_block}")
    
    try:
        # Validate inputs
        if data_slice is None or len(data_slice) == 0:
            debug_print("ERROR: Empty data provided to alpha_flow_chart")
            # Return an empty chart rather than failing
            fig = go.Figure()
            fig.update_layout(
                title="No Data Available",
                xaxis_title="Block",
                yaxis_title="AlphaPoints Flow"
            )
            return fig
        
        for required_col in ['AlphaPoints_per_block_in', 'AlphaPoints_per_block_out']:
            if required_col not in data_slice.columns:
                debug_print(f"ERROR: '{required_col}' column not found in data")
                debug_print(f"Available columns: {data_slice.columns.tolist()}")
                # Return an empty chart rather than failing
                fig = go.Figure()
                fig.update_layout(
                    title=f"Missing Data Column: {required_col}",
                    xaxis_title="Block",
                    yaxis_title="AlphaPoints Flow"
                )
                return fig
        
        # Get optimized data for alpha points in chart
        in_data = optimize_chart_data(data_slice, current_block, max_block, 'AlphaPoints_per_block_in')
        window_data = in_data['window_data']
        start_block = in_data['start_block']
        end_block = in_data['end_block']
        in_marker = in_data['current_value']
        
        # Get current out value
        out_marker = find_current_value(data_slice, current_block, 'AlphaPoints_per_block_out')
        
        if len(window_data) == 0:
            debug_print("WARNING: No data points in the window range")
            # Create a simple empty chart rather than failing
            fig = go.Figure()
            fig.update_layout(
                title="No Data in Current Window",
                xaxis_title="Block",
                yaxis_title="AlphaPoints Flow"
            )
            return fig
        
        # Create figure
        fig = go.Figure()
        
        # Add AlphaPoints in
        fig.add_trace(
            go.Scatter(
                x=window_data['block'],
                y=window_data['AlphaPoints_per_block_in'],
                mode='lines',
                line=dict(color=COLORS['alpha_points_in'], width=3),
                name='AlphaPoints In'
            )
        )
        
        # Add AlphaPoints out
        fig.add_trace(
            go.Scatter(
                x=window_data['block'],
                y=window_data['AlphaPoints_per_block_out'],
                mode='lines',
                line=dict(color=COLORS['alpha_points_out'], width=3),
                name='AlphaPoints Out'
            )
        )
        
        # Add markers for current position
        if in_marker:
            fig.add_trace(
                go.Scatter(
                    x=[in_marker['block']],
                    y=[in_marker['value']],
                    mode='markers',
                    marker=dict(color=COLORS['highlight'], size=12, symbol='circle'),
                    showlegend=False
                )
            )
        
        if out_marker:
            fig.add_trace(
                go.Scatter(
                    x=[out_marker['block']],
                    y=[out_marker['value']],
                    mode='markers',
                    marker=dict(color=COLORS['highlight'], size=12, symbol='circle'),
                    showlegend=False
                )
            )
        
        # Update layout
        fig.update_layout(
            margin=dict(l=20, r=20, t=20, b=20),
            plot_bgcolor=COLORS['background'],
            paper_bgcolor=COLORS['background'],
            font=dict(color=COLORS['text']),
            xaxis=dict(
                title='Block',
                gridcolor=COLORS['chart_grid'],
                range=[start_block, end_block]
            ),
            yaxis=dict(
                title='AlphaPoints Flow',
                gridcolor=COLORS['chart_grid']
            ),
            hovermode='x unified'
        )
        
        return fig
    
    except Exception as e:
        debug_print(f"ERROR in create_alpha_flow_chart: {e}")
        import traceback
        traceback.print_exc()
        # Return a minimal chart rather than failing
        fig = go.Figure()
        fig.update_layout(
            title=f"Error: {str(e)}",
            xaxis_title="Block",
            yaxis_title="AlphaPoints Flow"
        )
        return fig