# Configuration settings for the visualization

# Animation settings - UPDATED for maximum stability
ANIMATION_DURATION = 1800  # Total animation duration in seconds - increased to 30 minutes
FPS = 5  # Frames per second - reduced to 5 for extreme stability

# Data settings
DATA_FILE = "data/Sim_Results.csv"
BLOCKS_PER_DAY = 14400  # Number of blocks per day in the simulation

# Block advancement - UPDATED for smoother, more stable animation
MAX_BLOCKS_PER_FRAME = 150  # Reduced for even smoother transitions

# Chart settings - OPTIMIZED for performance
CHART_WINDOW_SIZE = 15000  # Reduced window size for better performance
MAX_DATA_POINTS_PER_CHART = 40  # Reduced max points for better rendering performance

# Visual settings
COLORS = {
    "background": "#f8f9fa",
    "text": "#333333",
    "primary": "#2c3e50",
    "secondary": "#3498db",
    "accent": "#1abc9c",
    "highlight": "#e74c3c",
    "chart_grid": "#ecf0f1",
    "network_rate": "#3498db",
    "generation_rate": "#2ecc71",
    "exchange_rate": "#e74c3c",
    "transaction_cost": "#9b59b6",  # Renamed from token_price to transaction_cost
    "alpha_points_in": "#27ae60",
    "alpha_points_out": "#e67e22",
    "warehouse_level": "#3498db",
    "warehouse_max": "#bdc3c7",
    "warehouse_capacity": {
        "low": "#2ecc71",      # Green for low capacity
        "medium": "#f39c12",   # Yellow for medium capacity
        "high": "#e74c3c"      # Red for high capacity
    }
}

# Layout settings
GRID_COLUMNS = 12
PANEL_HEIGHTS = {
    "main": 400,
    "secondary": 300
}