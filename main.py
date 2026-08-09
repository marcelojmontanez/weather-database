import requests
import sqlite3
from datetime import datetime, timezone

conn = sqlite3.connect("weather.db")
cur = conn.cursor()
cur.execute("""
    CREATE TABLE IF NOT EXISTS forecasts (
        period_name TEXT,
        start_time TEXT,
        temperature INT,
        short_forecast TEXT,
        fetched_at TEXT,
        UNIQUE(start_time)
    )
""")
conn.commit()

session = requests.Session()
session.headers.update({"User-Agent": "marcelojmontanez@gmail.com"})

fairfax_url = "https://api.weather.gov/points/38.8462,-77.3064"

points_response = session.get(fairfax_url) 
points_data = points_response.json()
forecast_url = points_data["properties"]["forecast"]
forecast_response = session.get(forecast_url)
fetched_at = datetime.now(timezone.utc).isoformat()
forecast_data = forecast_response.json()
periods = forecast_data["properties"]["periods"]

periods_cleaned = [
    {
        "period_name": period["name"],
        "start_time": period["startTime"],
        "temperature": period["temperature"],
        "short_forecast": period["shortForecast"],
        "fetched_at": fetched_at
    } for period in periods
]

cur.executemany(
    """
    INSERT OR IGNORE INTO forecasts 
        (period_name, start_time, temperature, short_forecast, fetched_at)
    VALUES
        (:period_name, :start_time, :temperature, :short_forecast, :fetched_at)
    """,
    periods_cleaned
)
conn.commit()