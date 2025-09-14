"""Flood simulation script.

This script automates data collection and water level prediction for a given
location in Pakistan. It retrieves recent weather data from the Open-Meteo API
and attempts to download Federal Flood Commission (FFC) river update images to
extract gauge readings via OCR. The collected data is fed into a lightweight
machine-learning model to estimate local flood water level.

Usage:
    python flood_simulator.py --lat 31.5204 --lon 74.3587

Optional:
    python flood_simulator.py --map
        Generates an interactive map (flood_map.html) for selecting a
        location. The user can then run the script again with the chosen
        coordinates.
"""

from __future__ import annotations

import argparse
import io
import os
import re
import statistics
from pathlib import Path
from typing import Dict, List, Tuple

import joblib
import numpy as np
import pandas as pd
import requests
from bs4 import BeautifulSoup
from PIL import Image
import pytesseract
from sklearn.ensemble import RandomForestRegressor

MODEL_FILE = Path("flood_model.pkl")
FFC_BASE_URL = "https://ffc.gov.pk"
SAVE_DIR = Path("ffc_river_updates")
SAVE_DIR.mkdir(exist_ok=True)


def fetch_weather(lat: float, lon: float) -> pd.DataFrame:
    """Fetch recent precipitation and temperature for a coordinate."""
    url = (
        "https://api.open-meteo.com/v1/forecast"
        f"?latitude={lat}&longitude={lon}"
        "&hourly=precipitation,temperature_2m"
        "&past_days=7"
    )
    resp = requests.get(url, timeout=30)
    resp.raise_for_status()
    data = resp.json()
    df = pd.DataFrame(
        {
            "time": data["hourly"]["time"],
            "precip_mm": data["hourly"]["precipitation"],
            "temp_c": data["hourly"]["temperature_2m"],
        }
    )
    df["time"] = pd.to_datetime(df["time"])
    return df


def fetch_ffc_river_update_images() -> List[Path]:
    """Download image links labeled 'River ... Updates' from FFC homepage."""
    paths: List[Path] = []
    try:
        resp = requests.get(FFC_BASE_URL, timeout=30)
        resp.raise_for_status()
    except Exception:
        return paths

    soup = BeautifulSoup(resp.text, "html.parser")
    pattern = re.compile(r"River\s+\w+\s+Updates", re.I)
    for anchor in soup.find_all("a", string=pattern):
        img_url = anchor.get("href")
        if not img_url:
            continue
        if not img_url.lower().endswith((".jpg", ".png")):
            continue
        try:
            img_resp = requests.get(img_url, timeout=30)
            img_resp.raise_for_status()
        except Exception:
            continue
        fname = SAVE_DIR / os.path.basename(img_url)
        with open(fname, "wb") as f:
            f.write(img_resp.content)
        paths.append(fname)
    return paths


def ocr_river_levels(image_path: Path) -> str:
    """Run OCR on a downloaded FFC image and return raw text."""
    try:
        img = Image.open(image_path)
        return pytesseract.image_to_string(img)
    except Exception:
        return ""


def fetch_river_levels() -> Dict[str, float]:
    """Attempt to extract river gauge levels from FFC images.

    Returns a dictionary mapping station names to water levels. If no data is
    available, an empty dict is returned.
    """
    levels: Dict[str, float] = {}
    for path in fetch_ffc_river_update_images():
        text = ocr_river_levels(path)
        for line in text.splitlines():
            match = re.search(r"(\w+)\s+(\d+\.\d+)\s*m", line)
            if match:
                name, level = match.group(1), float(match.group(2))
                levels[name] = level
    return levels


def train_flood_model() -> RandomForestRegressor:
    """Train a simple model on synthetic data and persist it."""
    rng = np.random.default_rng(42)
    X = rng.normal(size=(200, 3))
    y = 0.5 * X[:, 0] + 0.3 * X[:, 1] + 0.2 * X[:, 2] + rng.normal(0, 0.05, 200)
    model = RandomForestRegressor(n_estimators=100, random_state=42)
    model.fit(X, y)
    joblib.dump(model, MODEL_FILE)
    return model


def load_model() -> RandomForestRegressor:
    if MODEL_FILE.exists():
        return joblib.load(MODEL_FILE)
    return train_flood_model()


def predict_flood_level(lat: float, lon: float) -> float:
    """Fetch data for a location and predict flood water level."""
    weather_df = fetch_weather(lat, lon)
    recent = weather_df.tail(24)  # use last 24 hours
    precip = recent["precip_mm"].mean()
    temp = recent["temp_c"].mean()

    levels = fetch_river_levels()
    flow = statistics.mean(levels.values()) if levels else 0.0

    model = load_model()
    features = np.array([flow, precip, temp]).reshape(1, -1)
    predicted_level = model.predict(features)[0]
    return predicted_level


def create_interactive_map() -> None:
    import folium
    from folium.plugins import MousePosition

    m = folium.Map(location=[30.3753, 69.3451], zoom_start=5)
    formatter = "function(num) {return L.Util.formatNum(num, 5);};"
    MousePosition(
        position="topright",
        separator=" | ",
        empty_string="NaN",
        lng_first=True,
        num_digits=5,
        prefix="Coordinates:",
        lat_formatter=formatter,
        lng_formatter=formatter,
    ).add_to(m)
    m.add_child(folium.ClickForMarker(popup="Selected Location"))
    m.save("flood_map.html")
    print("Map saved to flood_map.html")


def main(argv: List[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Predict flood level for a location.")
    parser.add_argument("--lat", type=float, help="Latitude", default=None)
    parser.add_argument("--lon", type=float, help="Longitude", default=None)
    parser.add_argument("--map", action="store_true", help="Generate interactive map")
    args = parser.parse_args(argv)

    if args.map:
        create_interactive_map()
        return

    if args.lat is None or args.lon is None:
        parser.error("--lat and --lon are required unless --map is specified")

    level = predict_flood_level(args.lat, args.lon)
    print(f"Predicted water level at ({args.lat:.4f}, {args.lon:.4f}): {level:.2f} m")


if __name__ == "__main__":
    main()
