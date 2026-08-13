import configparser
import logging
import sqlite3
import sys
from datetime import datetime, timezone

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

WEATHER_API_BASE_URL = "https://api.weather.gov"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    stream=sys.stdout,
)
logger = logging.getLogger(__name__)

config = configparser.ConfigParser()
if not config.read("config.ini"):
    logger.error("Missing config.ini")
    sys.exit(1)

try:
    user_agent = config["api"]["user_agent"]
    latitude = config["location"]["latitude"]
    longitude = config["location"]["longitude"]
except KeyError as error:
    logger.error("Missing configuration value: %s", error)
    sys.exit(1)

points_url = f"{WEATHER_API_BASE_URL}/points/{latitude},{longitude}"

session = requests.Session()
session.headers.update({"User-Agent": user_agent})

retry = Retry(total=3, 
              backoff_factor=1, 
              status_forcelist=[429, 500, 502, 503, 504],
              respect_retry_after_header=True,
            )
session.mount("https://", HTTPAdapter(max_retries=retry))

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

try:
    points_response = session.get(points_url, timeout=10)
    points_response.raise_for_status()
    points_data = points_response.json()

    forecast_url = points_data["properties"]["forecast"]

    forecast_response = session.get(forecast_url, timeout=10)
    forecast_response.raise_for_status()
    forecast_data = forecast_response.json()

    periods = forecast_data["properties"]["periods"]
except requests.exceptions.JSONDecodeError as error:
    logger.error("Weather API returned invalid JSON: %s", error)
    sys.exit(1)
except KeyError as error:
    logger.error("Weather API response is missing expected fields: %s", error)
    sys.exit(1)
except requests.RequestException as error:
    logger.error("Weather API request failed: %s", error)
    sys.exit(1)

fetched_at = datetime.now(timezone.utc).isoformat()

periods_cleaned = [
    {
        "period_name": period["name"],
        "start_time": period["startTime"],
        "temperature": period["temperature"],
        "short_forecast": period["shortForecast"],
        "fetched_at": fetched_at,
    } 
    for period in periods
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
logger.info("Processed %d forecast periods", len(periods_cleaned))

conn.close()
session.close()