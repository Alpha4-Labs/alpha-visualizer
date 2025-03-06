import dash
from dash import html, dcc
from dash.dependencies import Input, Output, State
import pandas as pd
import time
import base64
from datetime import datetime
import os

from config import DATA_FILE, BLOCKS_PER_DAY, ANIMATION_DURATION, FPS, MAX_BLOCKS_PER_FRAME, CHART_WINDOW_SIZE, MAX_DATA_POINTS_PER_CHART
from data_processor import load_data, get_frame_data, interpolate_data
from visualizer import (
    create_layout,
    create_exchange_rate_chart,
    create_transaction_cost_chart,  # Changed from token_price_chart
    create_network_gen_chart,
    create_warehouse_chart,
    create_alpha_flow_chart
)
from recorder import VideoRecorder

# Enable debugging
DEBUG = True

# Global variable to track last update time
last_animation_update = 0
minimum_update_interval = 0.2  # Minimum seconds between updates
block_interval = 1000  # Default block interval

def debug_print(*args, **kwargs):
    """Print debug messages if debugging is enabled"""
    if DEBUG:
        print("[MAIN-DEBUG]", *args, **kwargs)

debug_print("Alpha Economic Simulation Visualizer - Debug Mode")
debug_print(f"Looking for data file at: {DATA_FILE}")
    
# Check if the file exists
if os.path.exists(DATA_FILE):
    debug_print(f"Data file found!")
    file_size = os.path.getsize(DATA_FILE) / 1024
    debug_print(f"File size: {file_size:.2f} KB")
else:
    debug_print(f"WARNING: Data file not found at {DATA_FILE}")
    debug_print(f"Current working directory: {os.getcwd()}")
    
    data_dir = os.path.dirname(DATA_FILE)
    if data_dir and os.path.exists(data_dir):
        debug_print(f"Directory {data_dir} exists. Files in directory:")
        for file in os.listdir(data_dir):
            debug_print(f"  - {file}")
    
    # Try to find the file in the current directory
    base_name = os.path.basename(DATA_FILE)
    if os.path.exists(base_name):
        debug_print(f"File found in current directory: {base_name}")
        debug_print(f"Will attempt to use this file instead.")
        DATA_FILE = base_name

# Load the data
try:
    debug_print("Loading data...")
    data = load_data(DATA_FILE)
    
    # Debug information about the data
    if data is not None and len(data) > 0:
        debug_print(f"Data loaded successfully with {len(data)} rows and {len(data.columns)} columns")
        debug_print(f"Columns in dataset: {data.columns.tolist()}")
        
        max_block = data['block'].max()
        blocks_per_second = max_block / ANIMATION_DURATION
        
        debug_print(f"Simulation covers {max_block} blocks ({max_block / BLOCKS_PER_DAY:.1f} days)")
        debug_print(f"Animation speed: {blocks_per_second:.1f} blocks per second")
        
        # Check key columns
        key_columns = ['exchange_rate', 'average_transaction_cost_usd', 'network_rate', 'generation_rate',
                      'warehouse_capacity', 'AlphaPoints_per_block_in', 'AlphaPoints_per_block_out']
        
        debug_print("Checking key data columns:")
        for col in key_columns:
            if col in data.columns:
                debug_print(f"  ✓ '{col}' present with {data[col].count()} values")
                # Show range
                min_val = data[col].min()
                max_val = data[col].max()
                debug_print(f"    Range: {min_val} to {max_val}")
                
                # Check for constant values
                if min_val == max_val:
                    debug_print(f"    WARNING: '{col}' has constant value {min_val}")
            else:
                debug_print(f"  ✗ '{col}' MISSING")
        
        # Test chart creation
        debug_print("\nTesting chart creation with the first block...")
        first_block = data['block'].min()
        try:
            test_chart = create_exchange_rate_chart(data, first_block, max_block)
            debug_print("  ✓ Successfully created test chart")
        except Exception as e:
            debug_print(f"  ✗ Error creating test chart: {e}")
            import traceback
            traceback.print_exc()
    else:
        debug_print("ERROR: Failed to load data or empty dataset")
        # Create empty dataframe to prevent further errors
        data = pd.DataFrame(columns=['block', 'exchange_rate', 'average_transaction_cost_usd', 'network_rate',
                                    'generation_rate', 'warehouse_capacity',
                                    'AlphaPoints_per_block_in', 'AlphaPoints_per_block_out'])
        max_block = 1
        blocks_per_second = 1
    
except Exception as e:
    debug_print(f"ERROR during data loading: {e}")
    import traceback
    traceback.print_exc()
    # Create empty dataframe to prevent further errors
    data = pd.DataFrame(columns=['block', 'exchange_rate', 'average_transaction_cost_usd', 'network_rate',
                                'generation_rate', 'warehouse_capacity',
                                'AlphaPoints_per_block_in', 'AlphaPoints_per_block_out'])
    max_block = 1
    blocks_per_second = 1

# Preprocess and sort data for faster interpolation
if len(data) > 0:
    debug_print("Preprocessing data for faster interpolation...")
    data = data.sort_values('block').reset_index(drop=True)
    
    # Determine block interval for optimization
    if len(data) > 1:
        block_diff = data['block'].diff().dropna()
        if len(block_diff) > 0:
            most_common_interval = block_diff.mode().iloc[0]
            debug_print(f"Most common block interval: {most_common_interval}")
            block_interval = most_common_interval  # Set global block interval
            if 'attrs' not in dir(data):
                data.attrs = {}
            data.attrs['block_interval'] = most_common_interval

# Create the app
app = dash.Dash(
    __name__,
    external_stylesheets=['https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/css/bootstrap.min.css']
)
app.layout = create_layout()

@app.callback(
    [
        Output("animation-state", "data"),
        Output("animation-interval", "disabled"),
        Output("animation-interval", "interval")
    ],
    [
        Input("play-button", "n_clicks"),
        Input("pause-button", "n_clicks"),
        Input("reset-button", "n_clicks"),
        Input("speed-slider", "value")
    ],
    [
        State("animation-state", "data")
    ],
    prevent_initial_call=True
)
def control_animation(play_clicks, pause_clicks, reset_clicks, speed, current_state):
    """Control the animation state based on button clicks"""
    ctx = dash.callback_context
    if not ctx.triggered:
        return current_state, not current_state["playing"], 1000 / FPS
    
    button_id = ctx.triggered[0]["prop_id"].split(".")[0]
    
    if button_id == "play-button":
        debug_print("Animation PLAY pressed")
        current_state["playing"] = True
    elif button_id == "pause-button":
        debug_print("Animation PAUSE pressed")
        current_state["playing"] = False
    elif button_id == "reset-button":
        debug_print("Animation RESET pressed")
        current_state["playing"] = False
        current_state["current_block"] = 0
        # Clear any stuck detection
        if hasattr(update_animation, 'last_block'):
            delattr(update_animation, 'last_block')
    elif button_id == "speed-slider":
        debug_print(f"Animation speed changed to {speed}x")
        current_state["speed"] = speed
    
    # Calculate interval based on speed with a minimum to prevent too-rapid updates
    interval = max(100, (1000 / FPS) / current_state["speed"])  # At least 100ms between frames
    
    return current_state, not current_state["playing"], interval

@app.callback(
    [
        Output("animation-state", "data", allow_duplicate=True),
        Output("simulation-day", "children"),
        Output("exchange-rate-chart", "figure"),
        Output("transaction-cost-chart", "figure"),  # Changed from token-price-chart
        Output("network-gen-chart", "figure"),
        Output("warehouse-chart", "figure"),
        Output("alpha-flow-chart", "figure")
    ],
    [
        Input("animation-interval", "n_intervals")
    ],
    [
        State("animation-state", "data")
    ],
    prevent_initial_call=True
)
def update_animation(n_intervals, animation_state):
    """Update the animation state and charts with throttling to prevent overwhelming the system"""
    global last_animation_update
    
    # Throttling to prevent excessive updates
    current_time = time.time()
    if current_time - last_animation_update < minimum_update_interval:
        raise dash.exceptions.PreventUpdate
    
    last_animation_update = current_time
    
    if not animation_state["playing"]:
        raise dash.exceptions.PreventUpdate
    
    # Calculate new block position
    current_block = animation_state["current_block"]
    
    # IMPORTANT: Limit blocks_to_advance to prevent skipping too much data
    blocks_to_advance = min(
        MAX_BLOCKS_PER_FRAME,  # Hard max from config
        blocks_per_second * (1 / FPS) * animation_state["speed"]
    )
    new_block = current_block + blocks_to_advance
    
    # Check if we're stuck on the same block (protection against loops)
    if hasattr(update_animation, 'last_block') and update_animation.last_block == new_block:
        debug_print(f"Warning: Animation appears stuck at block {new_block}, forcing advancement")
        new_block += block_interval  # Force advancement by one data point
    
    update_animation.last_block = new_block
    
    # Log animation progress periodically (less frequently for performance)
    if n_intervals % (FPS * 5) == 0:  # Log every ~5 seconds
        debug_print(f"Animation frame {n_intervals}, block {new_block:.1f} / {max_block}")
    
    # Check if animation is complete
    if new_block >= max_block:
        debug_print("Animation complete")
        animation_state["playing"] = False
        animation_state["current_block"] = 0
        if hasattr(update_animation, 'last_block'):
            delattr(update_animation, 'last_block')
        return animation_state, "Simulation Complete", dash.no_update, dash.no_update, dash.no_update, dash.no_update, dash.no_update
    
    # Update animation state
    animation_state["current_block"] = new_block
    
    # Get the data for the current block (interpolated for smoothness)
    try:
        current_data = interpolate_data(data, new_block)
    except Exception as e:
        debug_print(f"Error interpolating data at block {new_block}: {e}")
        # Use a simpler approach if interpolation fails
        current_data = get_frame_data(data, new_block)
    
    # Update day indicator
    day_text = f"Day: {int(new_block // BLOCKS_PER_DAY)} / Block: {int(new_block)}"
    
    try:
        # Create charts with optimized implementations
        exchange_chart = create_exchange_rate_chart(data, new_block, max_block)
        transaction_chart = create_transaction_cost_chart(data, new_block, max_block)  # Changed from token_price_chart
        network_chart = create_network_gen_chart(data, new_block, max_block)
        warehouse_chart = create_warehouse_chart(data, new_block, max_block)
        alpha_flow_chart = create_alpha_flow_chart(data, new_block, max_block)
        
        return animation_state, day_text, exchange_chart, transaction_chart, network_chart, warehouse_chart, alpha_flow_chart
    except Exception as e:
        debug_print(f"ERROR in update_animation at block {new_block}: {e}")
        import traceback
        traceback.print_exc()
        # Return no updates if there's an error
        return animation_state, f"Error at block {new_block}", dash.no_update, dash.no_update, dash.no_update, dash.no_update, dash.no_update

@app.callback(
    Output("download-video", "data"),
    Input("record-button", "n_clicks"),
    prevent_initial_call=True
)
def record_video(n_clicks):
    """Record the animation as a video - ultra optimized"""
    if not n_clicks:
        raise dash.exceptions.PreventUpdate
    
    debug_print("Recording video started")
    
    # Create a recorder with reduced FPS for stability
    recorder = VideoRecorder(fps=FPS)
    
    # Set recording parameters - further adjusted for extreme stability
    record_speed = 2.0  # Reduced from 3.0 for more stable recording
    frames_to_record = int(ANIMATION_DURATION * FPS / record_speed)
    
    # Calculate block increment per frame - with limit for smooth recording
    block_increment = min(MAX_BLOCKS_PER_FRAME, max_block / frames_to_record)
    
    # Record frames
    try:
        for frame_idx in range(frames_to_record):
            current_block = frame_idx * block_increment
            
            # Get data for this frame - with error handling
            try:
                current_data = interpolate_data(data, current_block)
            
                # Create charts
                exchange_chart = create_exchange_rate_chart(data, current_block, max_block)
                transaction_chart = create_transaction_cost_chart(data, current_block, max_block)  # Changed from token_price
                network_chart = create_network_gen_chart(data, current_block, max_block)
                warehouse_chart = create_warehouse_chart(data, current_block, max_block)
                alpha_flow_chart = create_alpha_flow_chart(data, current_block, max_block)
                
                # Add frame to recorder
                recorder.add_frame([exchange_chart, transaction_chart, network_chart, warehouse_chart, alpha_flow_chart])
                
                # Add delay to prevent overloading
                if frame_idx % 5 == 0:
                    time.sleep(0.05)  # Small delay every 5 frames
            except Exception as frame_error:
                debug_print(f"Error creating frame {frame_idx}: {frame_error}")
                # Continue with next frame if one fails
                continue
            
            # Print progress less frequently
            if frame_idx % 20 == 0:
                debug_print(f"Recording progress: {frame_idx}/{frames_to_record} frames ({frame_idx/frames_to_record*100:.1f}%)")
    except Exception as e:
        debug_print(f"ERROR during video recording: {e}")
        import traceback
        traceback.print_exc()
    
    # Save video and prepare for download
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"alpha_simulation_{timestamp}.mp4"
    
    try:
        video_path = recorder.save_video()
        debug_print(f"Recording complete: {video_path}")
        return dcc.send_file(video_path)
    except Exception as e:
        debug_print(f"ERROR saving video: {e}")
        import traceback
        traceback.print_exc()
        # Return nothing if video saving fails
        raise dash.exceptions.PreventUpdate

if __name__ == "__main__":
    debug_print("Starting visualization server...")
    app.run_server(debug=True, dev_tools_hot_reload=False)  # Disable hot reload for stability