# Alpha Economic Simulation Visualizer

## Overview

This application provides a dynamic visualization of economic simulation data for the Alpha ecosystem. It renders real-time charts and metrics as the simulation progresses through block data.

## Features

The visualizer creates an interactive dashboard with five key metrics:

- **Exchange Rate** - Shows the fluctuation of exchange rates over time.
- **Transaction Cost (USD)** - Displays the average transaction costs in USD.
- **Network & Generation Rates** - Compares network and generation rates on a dual-axis chart.
- **Warehouse Metrics** - Presents current warehouse capacity with color-coded gauges.
- **AlphaPoints Flow** - Shows the flow of AlphaPoints in and out of the system.

Users can control playback with play/pause/reset buttons, adjust animation speed, and record videos of the simulation for later analysis.

## Installation

### Prerequisites

- Python 3.8 or higher
- pip (Python package installer)

### Setup

1. Clone the repository:

   ```bash
   git clone https://github.com/Alpha4-Labs/alpha-visualizer.git
   cd alpha-economic-visualizer
   ```

2. Create a virtual environment:

   ```bash
   # Windows
   python -m venv venv

   # macOS/Linux
   python3 -m venv venv
   ```

3. Activate the virtual environment:

   ```bash
   # Windows PowerShell
   .\venv\Scripts\Activate.ps1

   # Windows Command Prompt
   .\venv\Scripts\activate.bat

   # macOS/Linux
   source venv/bin/activate
   ```

4. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

## Running the Application

1. Ensure your data file is in the correct location:

   - By default, the application looks for `data/Sim_Results.csv`
   - You can modify the path in `config.py` if needed

2. Run the application:

   ```bash
   python main.py
   ```

3. Open your web browser and navigate to:
   - [http://127.0.0.1:8050/](http://127.0.0.1:8050/)

## Usage

- Click **Play** to start the animation.
- Use **Pause** to halt at the current point.
- Click **Reset** to return to the beginning.
- Adjust the **Playback Speed** slider to speed up or slow down the animation.
- Click **Record Video** to create an MP4 file of the current visualization.

## File Structure

- `main.py` - Main application entry point.
- `config.py` - Configuration settings.
- `data_processor.py` - Data loading and interpolation functions.
- `visualizer.py` - Chart creation and layout functions.
- `recorder.py` - Video recording functionality.
- `data/` - Directory for simulation data CSV files.

## Troubleshooting

- If you encounter a **"String literal is unterminated"** error related to `tickprefix`, ensure that the `tickprefix='$'` parameter in `visualizer.py` has proper closing quotes.
- If the application crashes at higher block counts, try adjusting the following in `config.py`:
  - Increase `ANIMATION_DURATION` to extend the animation time.
  - Decrease `FPS` to reduce the frame rate.
  - Reduce `MAX_BLOCKS_PER_FRAME` to slow down block advancement.

## Requirements

The application requires the following dependencies:

- `dash`
- `dash-bootstrap-components`
- `plotly`
- `pandas`
- `numpy`
- `opencv-python`
- `moviepy`

See `requirements.txt` for specific versions.
