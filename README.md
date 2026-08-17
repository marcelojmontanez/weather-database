# NWS Forecast Pipeline

Fetches a point forecast from the US National Weather Service (NWS) and stores it in SQLite.

## Setup

Requires Python 3.12, network access to `api.weather.gov`, and coordinates supported by the NWS.

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp config.example.ini config.ini
```

## Configuration

Set the API user agent and location in `config.ini`:

```ini
[api]
user_agent = nws-forecast-pipeline your-email@example.com

[location]
latitude = 38.9072
longitude = -77.0369
```

The user agent should include contact information.

## Usage

```bash
python main.py
```

The pipeline requests the configured point from the NWS, fetches its forecast, and inserts new forecast periods into `weather.db`. It logs the number of periods processed.

Requests have a 10-second timeout and retry up to three times for `429`, `500`, `502`, `503`, and `504` responses.

Missing configuration, failed requests, invalid JSON, and missing API response fields cause the pipeline to exit with an error. SQLite and filesystem errors are reported as Python exceptions.

`start_time` is unique, and inserts use `INSERT OR IGNORE` so that the pipeline doesn't create duplicates or update forecasts.

## Data

| Column | Type | Description |
| --- | --- | --- |
| `period_name` | `TEXT` | Forecast period name |
| `start_time` | `TEXT` | Forecast period start time |
| `temperature` | `INT` | Temperature returned by the NWS |
| `short_forecast` | `TEXT` | Short forecast description |
| `fetched_at` | `TEXT` | Fetch time in UTC |

The temperature unit returned by the NWS is not stored.

`config.ini`, `weather.db`, and `data/` are ignored by Git.

Query the database with:

```bash
sqlite3 weather.db 'SELECT period_name, start_time, temperature, short_forecast FROM forecasts ORDER BY start_time LIMIT 10;'
```

## Docker

The Compose configuration mounts `config.ini` and stores the database in `data/`:

```bash
cp config.example.ini config.ini
docker compose up --build
```

The container runs the pipeline once and exits. Its database is saved as `data/weather.db`.

## Future Work

- Add a forecast archive and observed-weather data to measure forecast accuracy.
- Support environment variables for container-native configuration.
- Add a Kubernetes CronJob for scheduled daily runs.

