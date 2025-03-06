import pandas as pd
import numpy as np
import os
from config import BLOCKS_PER_DAY

# Enable debugging output
DEBUG = True

def debug_print(*args, **kwargs):
    """Print debug messages if debugging is enabled"""
    if DEBUG:
        print("[DEBUG]", *args, **kwargs)

def load_data(file_path):
    """Load and preprocess the simulation data"""
    debug_print(f"Attempting to load data from: {file_path}")
    
    # Check if file exists
    if not os.path.exists(file_path):
        debug_print(f"ERROR: File not found at {file_path}")
        # Try to find file in current directory
        base_name = os.path.basename(file_path)
        if os.path.exists(base_name):
            debug_print(f"Found file in current directory: {base_name}")
            file_path = base_name
        else:
            debug_print(f"ERROR: File not found as {base_name} either")
            # Return empty DataFrame with required columns to prevent crashes
            return pd.DataFrame(columns=[
                'block', 'network_rate', 'generation_rate', 'exchange_rate',
                'warehouse_capacity', 'AlphaPoints_per_block_in',
                'AlphaPoints_per_block_out', 'token_price'
            ])
    
    # Load data
    try:
        data = pd.read_csv(file_path)
        debug_print(f"Successfully loaded data with {len(data)} rows and {len(data.columns)} columns")
        debug_print(f"Columns: {data.columns.tolist()}")
        
        # Check for required columns
        required_columns = [
            'block', 'network_rate', 'generation_rate', 'exchange_rate',
            'warehouse_capacity', 'AlphaPoints_per_block_in',
            'AlphaPoints_per_block_out', 'token_price'
        ]
        
        missing_columns = [col for col in required_columns if col not in data.columns]
        if missing_columns:
            debug_print(f"WARNING: Missing required columns: {missing_columns}")
        
        # Add day column
        data['day'] = data['block'] // BLOCKS_PER_DAY
        debug_print(f"Added 'day' column based on BLOCKS_PER_DAY={BLOCKS_PER_DAY}")
        
        # Calculate additional metrics if needed
        data['net_alpha_points_flow'] = data['AlphaPoints_per_block_in'] - data['AlphaPoints_per_block_out']
        debug_print("Added 'net_alpha_points_flow' calculated column")
        
        # Check data ranges for key columns
        for col in required_columns:
            if col in data.columns:
                min_val = data[col].min() if not data[col].empty else None
                max_val = data[col].max() if not data[col].empty else None
                null_count = data[col].isnull().sum()
                debug_print(f"Column '{col}': Range [{min_val} to {max_val}], Null values: {null_count}")
                
                if min_val == max_val:
                    debug_print(f"WARNING: Column '{col}' has constant value: {min_val}")
        
        # Precompute the block interval for optimization
        if len(data) > 1:
            data = data.sort_values('block')
            block_intervals = data['block'].diff().dropna()
            if len(block_intervals) > 0:
                most_common_interval = block_intervals.mode().iloc[0]
                data.attrs['block_interval'] = most_common_interval
                debug_print(f"Detected block interval: {most_common_interval}")
            else:
                data.attrs['block_interval'] = 1000  # Default assumption
        else:
            data.attrs['block_interval'] = 1000  # Default assumption
            
        return data
    except Exception as e:
        debug_print(f"ERROR during data loading: {e}")
        import traceback
        traceback.print_exc()
        # Return empty DataFrame with required columns to prevent crashes
        return pd.DataFrame(columns=[
            'block', 'network_rate', 'generation_rate', 'exchange_rate',
            'warehouse_capacity', 'AlphaPoints_per_block_in',
            'AlphaPoints_per_block_out', 'token_price'
        ])

def get_frame_data(data, current_block):
    """Get data for a specific block/frame - optimized version"""
    debug_print(f"Getting frame data for block: {current_block}")
    
    try:
        # Find the closest block to the current_block
        if len(data) == 0:
            debug_print("WARNING: Empty dataframe, can't get frame data")
            return pd.Series()
        
        # Optimization: Calculate approximate index based on block interval
        block_interval = data.attrs.get('block_interval', 1000)
        approx_idx = int(current_block / block_interval)
        
        # Ensure index is within bounds
        approx_idx = max(0, min(approx_idx, len(data) - 1))
        
        # Check if we got close enough, otherwise fallback to full search
        if abs(data.iloc[approx_idx]['block'] - current_block) > block_interval * 2:
            # Fallback to standard search if our approximation was off
            idx = (data['block'] - current_block).abs().idxmin()
        else:
            # Fine-tune by checking a few neighbors
            start_idx = max(0, approx_idx - 2)
            end_idx = min(len(data), approx_idx + 3)
            idx = start_idx + (data.iloc[start_idx:end_idx]['block'] - current_block).abs().idxmin()
        
        debug_print(f"Found closest block at index {idx}: block={data.loc[idx, 'block']}")
        
        return data.loc[idx]
    except Exception as e:
        debug_print(f"ERROR in get_frame_data: {e}")
        import traceback
        traceback.print_exc()
        return pd.Series()

def interpolate_data(data, current_block):
    """Interpolate data between blocks for smoother animation - optimized version"""
    debug_print(f"Interpolating data for block: {current_block}")
    
    try:
        if len(data) <= 1:
            debug_print("WARNING: Not enough data for interpolation")
            return pd.Series() if len(data) == 0 else data.iloc[0]
        
        # OPTIMIZATION: Use binary search directly instead of searching the entire dataset
        # This is more efficient for our evenly spaced data
        block_interval = data.attrs.get('block_interval', 1000)
        
        # Optimization: Calculate approximate indices based on block interval
        approx_idx_before = int(current_block / block_interval)
        
        # Ensure indices are within bounds
        if approx_idx_before >= len(data):
            approx_idx_before = len(data) - 1
        approx_idx_before = max(0, approx_idx_before)
        
        # Check if our approximation is good, otherwise search nearby
        actual_before_block = data.iloc[approx_idx_before]['block']
        
        # If approximation is off, search a small window
        if actual_before_block > current_block:
            # Need to look earlier
            search_start = max(0, approx_idx_before - 5)
            search_end = approx_idx_before
            search_subset = data.iloc[search_start:search_end]
            if len(search_subset) > 0:
                idx_before = search_start + (search_subset['block'] <= current_block)[::-1].idxmax()
            else:
                idx_before = 0
        elif actual_before_block < current_block:
            # See if the next block is after current_block
            if approx_idx_before + 1 < len(data) and data.iloc[approx_idx_before + 1]['block'] > current_block:
                # We found the right pair of blocks
                idx_before = approx_idx_before
            else:
                # Need to look further ahead
                search_start = approx_idx_before
                search_end = min(len(data), approx_idx_before + 5)
                search_subset = data.iloc[search_start:search_end]
                matches = search_subset['block'] <= current_block
                if matches.any():
                    idx_before = search_start + matches[::-1].idxmax()
                else:
                    idx_before = min(len(data) - 2, search_start)
        else:
            # Exact match
            idx_before = approx_idx_before
        
        # Now get the after index
        idx_after = min(len(data) - 1, idx_before + 1)
        
        # Handle edge cases
        if idx_before < 0:
            debug_print("Using first block (no earlier block available)")
            return data.iloc[0]
        if idx_after >= len(data):
            debug_print("Using last block (no later block available)")
            return data.iloc[-1]
        
        # Get the block values
        block_before = data.iloc[idx_before]['block']
        block_after = data.iloc[idx_after]['block']
        
        debug_print(f"Interpolating between blocks {block_before} and {block_after}")
        
        # Calculate interpolation factor
        if block_after == block_before:
            factor = 0
            debug_print("Same blocks, factor=0")
        else:
            factor = (current_block - block_before) / (block_after - block_before)
            debug_print(f"Interpolation factor: {factor:.4f}")
        
        # Get the rows
        before_row = data.iloc[idx_before]
        after_row = data.iloc[idx_after]
        
        # Create a new row with interpolated values
        interp_row = {}
        for col in data.columns:
            if col != 'block' and col != 'day':
                interp_row[col] = before_row[col] + factor * (after_row[col] - before_row[col])
        
        interp_row['block'] = current_block
        interp_row['day'] = current_block // BLOCKS_PER_DAY
        
        return pd.Series(interp_row)
    except Exception as e:
        debug_print(f"ERROR in interpolate_data: {e}")
        import traceback
        traceback.print_exc()
        # Try a simpler method - just find the closest block
        return get_frame_data(data, current_block)