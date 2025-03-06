import os
import pandas as pd
import sys

def validate_csv(file_path):
    """Validate a CSV file for the Alpha simulation"""
    print(f"\nValidating CSV file: {file_path}")
    print("=" * 50)
    
    # Check if file exists
    if not os.path.exists(file_path):
        print(f"ERROR: File not found at {file_path}")
        return False
    
    # Get file info
    file_size = os.path.getsize(file_path) / 1024
    print(f"File size: {file_size:.2f} KB")
    
    # Try to read the file
    try:
        df = pd.read_csv(file_path)
        print(f"Successfully read CSV with {len(df)} rows and {len(df.columns)} columns")
        print(f"Column names: {df.columns.tolist()}")
        
        # Check required columns
        required_columns = [
            'block', 'network_rate', 'generation_rate', 'exchange_rate',
            'warehouse_capacity', 'AlphaPoints_per_block_in',
            'AlphaPoints_per_block_out', 'token_price'
        ]
        
        print("\nChecking required columns:")
        missing_columns = []
        for col in required_columns:
            if col in df.columns:
                print(f"✓ {col}")
            else:
                print(f"✗ {col} (MISSING)")
                missing_columns.append(col)
        
        if missing_columns:
            print(f"\nWARNING: Missing {len(missing_columns)} required columns!")
            print("Possible alternatives:")
            for missing in missing_columns:
                possible_matches = [c for c in df.columns if missing.lower() in c.lower()]
                print(f"  For '{missing}', possible matches: {possible_matches}")
        
        # Check data types and null values
        print("\nData types and null counts:")
        for col in df.columns:
            null_count = df[col].isnull().sum()
            print(f"{col}: {df[col].dtype}, {null_count} null values")
        
        # Check data ranges for numerical columns
        print("\nData ranges for key columns:")
        for col in [c for c in required_columns if c in df.columns]:
            if pd.api.types.is_numeric_dtype(df[col]):
                min_val = df[col].min()
                max_val = df[col].max()
                print(f"{col}: min={min_val}, max={max_val}")
                
                # Check for constant values
                if min_val == max_val:
                    print(f"WARNING: {col} has constant value {min_val}")
        
        # Check for duplicate blocks
        if 'block' in df.columns:
            duplicate_blocks = df['block'].duplicated().sum()
            if duplicate_blocks > 0:
                print(f"\nWARNING: Found {duplicate_blocks} duplicate block values!")
            else:
                print("\n✓ No duplicate block values found")
        
        # Sample data
        print("\nSample data (first 3 rows):")
        print(df.head(3).to_string())
        
        return True
    except Exception as e:
        print(f"ERROR reading CSV: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    # Check command line arguments
    if len(sys.argv) > 1:
        file_path = sys.argv[1]
    else:
        # Try common file paths
        possible_paths = [
            "Sim_Results.csv",
            "data/Sim_Results.csv",
            "simulation_results.csv",
            "data/simulation_results.csv"
        ]
        
        print("No file path provided. Searching for CSV files...")
        
        # First check the provided paths
        found_path = None
        for path in possible_paths:
            if os.path.exists(path):
                print(f"Found CSV at: {path}")
                found_path = path
                break
        
        # If not found, look for any CSV in current directory
        if not found_path:
            csv_files = [f for f in os.listdir('.') if f.endswith('.csv')]
            if csv_files:
                print(f"Found CSV files: {csv_files}")
                found_path = csv_files[0]
        
        if found_path:
            file_path = found_path
        else:
            print("No CSV files found. Please provide a file path.")
            print("Usage: python csv_validator.py [path_to_csv]")
            sys.exit(1)
    
    validate_csv(file_path)