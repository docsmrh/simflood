# simflood

This repository contains a Python script for automated flood-level prediction.
The script downloads recent weather data and river gauge updates, then feeds
the data into a simple machine‑learning model to estimate water level at a
specified location in Pakistan.

## Usage

1. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
2. Generate an interactive map to pick coordinates:
   ```bash
   python flood_simulator.py --map
   ```
   Open `flood_map.html` in a browser and choose a location.
3. Run a prediction for the chosen latitude/longitude:
   ```bash
   python flood_simulator.py --lat 31.5204 --lon 74.3587
   ```

The script will scrape weather and river data, load or train a model, and print
an estimated flood water level for the selected point.
