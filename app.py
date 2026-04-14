from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS
import requests
import json
import os
from datetime import datetime, timezone

app = Flask(__name__)
CORS(app)  # Allow frontend to call this backend

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# ─── API KEYS ─────────────────────────────────────────────────────────────────
OPENWEATHER_API_KEY = os.getenv("OPENWEATHER_API_KEY", "")
FIRMS_MAP_KEY       = os.getenv("FIRMS_MAP_KEY", "")

# ─── BASE URLS ────────────────────────────────────────────────────────────────
OW_BASE    = "https://api.openweathermap.org/data/2.5"
FIRMS_BASE = "https://firms.modaps.eosdis.nasa.gov/api/area/csv"

# ─── HELPER ───────────────────────────────────────────────────────────────────
def ok(data):
    return jsonify({"status": "ok", "data": data})

def err(msg, code=500):
    return jsonify({"status": "error", "message": msg}), code


@app.route("/", methods=["GET"])
def index():
    return send_from_directory(BASE_DIR, "index.html")


def require_env(var_name):
    value = os.getenv(var_name, "").strip()
    if not value:
        raise RuntimeError(f"Missing required environment variable: {var_name}")
    return value

# ══════════════════════════════════════════════════════════════════════════════
#  WEATHER ROUTES
# ══════════════════════════════════════════════════════════════════════════════

@app.route("/api/weather/current", methods=["GET"])
def weather_current():
    """
    Live weather for a city.
    Query params: city (default: New Delhi)
    """
    city = request.args.get("city", "New Delhi")
    try:
        api_key = require_env("OPENWEATHER_API_KEY")
        r = requests.get(
            f"{OW_BASE}/weather",
            params={"q": city, "appid": api_key, "units": "metric"},
            timeout=8
        )
        r.raise_for_status()
        d = r.json()
        return ok({
            "city":        d["name"],
            "country":     d["sys"]["country"],
            "temp":        round(d["main"]["temp"], 1),
            "feels_like":  round(d["main"]["feels_like"], 1),
            "humidity":    d["main"]["humidity"],
            "pressure":    d["main"]["pressure"],
            "wind_speed":  d["wind"]["speed"],
            "wind_deg":    d["wind"].get("deg", 0),
            "visibility":  d.get("visibility", 0),
            "description": d["weather"][0]["description"].upper(),
            "icon":        d["weather"][0]["icon"],
            "clouds":      d["clouds"]["all"],
            "lat":         d["coord"]["lat"],
            "lon":         d["coord"]["lon"],
            "sunrise":     datetime.fromtimestamp(d["sys"]["sunrise"], tz=timezone.utc).strftime("%H:%M UTC"),
            "sunset":      datetime.fromtimestamp(d["sys"]["sunset"],  tz=timezone.utc).strftime("%H:%M UTC"),
        })
    except requests.exceptions.HTTPError as e:
        return err(f"OpenWeather API error: {str(e)}", r.status_code)
    except Exception as e:
        return err(str(e))


@app.route("/api/weather/multi", methods=["GET"])
def weather_multi():
    """
    Live weather for multiple Indian cities at once.
    Used by the mission control map.
    """
    cities = [
        "New Delhi", "Mumbai", "Chennai", "Kolkata",
        "Bengaluru", "Hyderabad", "Ahmedabad", "Pune",
        "Bhubaneswar", "Guwahati"
    ]
    results = []
    for city in cities:
        try:
            api_key = require_env("OPENWEATHER_API_KEY")
            r = requests.get(
                f"{OW_BASE}/weather",
                params={"q": city + ",IN", "appid": api_key, "units": "metric"},
                timeout=6
            )
            if r.status_code == 200:
                d = r.json()
                results.append({
                    "city":        d["name"],
                    "temp":        round(d["main"]["temp"], 1),
                    "humidity":    d["main"]["humidity"],
                    "wind_speed":  round(d["wind"]["speed"] * 3.6, 1),  # m/s → km/h
                    "description": d["weather"][0]["description"].upper(),
                    "icon":        d["weather"][0]["icon"],
                    "lat":         d["coord"]["lat"],
                    "lon":         d["coord"]["lon"],
                    "clouds":      d["clouds"]["all"],
                    "pressure":    d["main"]["pressure"],
                })
        except Exception:
            pass
    return ok(results)


@app.route("/api/weather/forecast", methods=["GET"])
def weather_forecast():
    """
    5-day / 3-hour forecast for a city.
    Query params: city
    """
    city = request.args.get("city", "New Delhi")
    try:
        api_key = require_env("OPENWEATHER_API_KEY")
        r = requests.get(
            f"{OW_BASE}/forecast",
            params={"q": city, "appid": api_key, "units": "metric", "cnt": 40},
            timeout=8
        )
        r.raise_for_status()
        d = r.json()
        items = []
        for item in d["list"]:
            items.append({
                "dt":          item["dt"],
                "dt_txt":      item["dt_txt"],
                "temp":        round(item["main"]["temp"], 1),
                "temp_min":    round(item["main"]["temp_min"], 1),
                "temp_max":    round(item["main"]["temp_max"], 1),
                "humidity":    item["main"]["humidity"],
                "description": item["weather"][0]["description"].upper(),
                "icon":        item["weather"][0]["icon"],
                "wind_speed":  round(item["wind"]["speed"] * 3.6, 1),
                "pop":         round(item.get("pop", 0) * 100),  # probability of precipitation %
                "clouds":      item["clouds"]["all"],
            })
        return ok({"city": d["city"]["name"], "forecast": items})
    except Exception as e:
        return err(str(e))


# ══════════════════════════════════════════════════════════════════════════════
#  FIRMS FIRE / DISASTER ROUTES
# ══════════════════════════════════════════════════════════════════════════════

@app.route("/api/fires/india", methods=["GET"])
def fires_india():
    """
    Active fire hotspots over India from NASA FIRMS (VIIRS SNPP, last 24h).
    Bounding box: India roughly  lon 68-97, lat 8-37
    """
    days  = request.args.get("days", "1")
    # FIRMS CSV endpoint: /api/area/csv/{MAP_KEY}/{source}/{area}/{day_range}
    area  = "68,8,97,37"   # W,S,E,N  (India bounding box)
    src   = "VIIRS_SNPP_NRT"
    map_key = require_env("FIRMS_MAP_KEY")
    url   = f"{FIRMS_BASE}/{map_key}/{src}/{area}/{days}"
    try:
        r = requests.get(url, timeout=15)
        r.raise_for_status()
        lines = r.text.strip().split("\n")
        if len(lines) < 2:
            return ok([])
        headers = [h.strip() for h in lines[0].split(",")]
        fires = []
        for line in lines[1:]:
            cols = line.split(",")
            if len(cols) < len(headers):
                continue
            row = dict(zip(headers, cols))
            try:
                fires.append({
                    "lat":        float(row.get("latitude",  row.get("lat",  0))),
                    "lon":        float(row.get("longitude", row.get("lon",  0))),
                    "brightness": float(row.get("bright_ti4", row.get("brightness", 300))),
                    "frp":        float(row.get("frp", 0)),
                    "confidence": row.get("confidence", "n").strip().upper(),
                    "acq_date":   row.get("acq_date", "").strip(),
                    "acq_time":   row.get("acq_time", "").strip(),
                    "satellite":  row.get("satellite", "N").strip(),
                    "instrument": row.get("instrument", "VIIRS").strip(),
                })
            except (ValueError, KeyError):
                pass
        # Sort by fire radiative power descending
        fires.sort(key=lambda x: x["frp"], reverse=True)
        return ok(fires[:200])   # Cap at 200 hotspots
    except Exception as e:
        return err(str(e))


@app.route("/api/fires/summary", methods=["GET"])
def fires_summary():
    """
    Aggregated fire summary stats for India.
    """
    days = request.args.get("days", "1")
    area = "68,8,97,37"
    src  = "VIIRS_SNPP_NRT"
    map_key = require_env("FIRMS_MAP_KEY")
    url  = f"{FIRMS_BASE}/{map_key}/{src}/{area}/{days}"
    try:
        r = requests.get(url, timeout=15)
        r.raise_for_status()
        lines = r.text.strip().split("\n")
        if len(lines) < 2:
            return ok({"total": 0, "high_confidence": 0, "states": []})
        headers = [h.strip() for h in lines[0].split(",")]
        total = 0
        high  = 0
        frp_total = 0.0
        for line in lines[1:]:
            cols = line.split(",")
            if len(cols) < len(headers):
                continue
            row = dict(zip(headers, cols))
            total += 1
            conf = row.get("confidence", "").strip().upper()
            if conf in ("H", "HIGH", "100", "99", "98", "97", "96", "95"):
                high += 1
            try:
                frp_total += float(row.get("frp", 0))
            except ValueError:
                pass
        return ok({
            "total":           total,
            "high_confidence": high,
            "total_frp_mw":    round(frp_total, 1),
            "days":            days,
            "source":          "VIIRS SNPP · NASA FIRMS",
            "updated":         datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
        })
    except Exception as e:
        return err(str(e))


# ══════════════════════════════════════════════════════════════════════════════
#  CYCLONE / ALERTS  (OpenWeather Air Quality + Weather Alerts)
# ══════════════════════════════════════════════════════════════════════════════

@app.route("/api/aqi/<lat>/<lon>", methods=["GET"])
def aqi(lat, lon):
    """Air Quality Index for a location."""
    try:
        api_key = require_env("OPENWEATHER_API_KEY")
        r = requests.get(
            "https://api.openweathermap.org/data/2.5/air_pollution",
            params={"lat": lat, "lon": lon, "appid": api_key},
            timeout=8
        )
        r.raise_for_status()
        d = r.json()
        comp = d["list"][0]["components"]
        aqi_val = d["list"][0]["main"]["aqi"]
        labels = {1:"GOOD", 2:"FAIR", 3:"MODERATE", 4:"POOR", 5:"VERY POOR"}
        return ok({
            "aqi":       aqi_val,
            "label":     labels.get(aqi_val, "UNKNOWN"),
            "co":        comp.get("co"),
            "no2":       comp.get("no2"),
            "o3":        comp.get("o3"),
            "pm2_5":     comp.get("pm2_5"),
            "pm10":      comp.get("pm10"),
            "so2":       comp.get("so2"),
        })
    except Exception as e:
        return err(str(e))


@app.route("/api/weather/alerts", methods=["GET"])
def weather_alerts():
    """
    One-call weather alerts for a lat/lon.
    Query params: lat, lon
    """
    lat = request.args.get("lat", "20.59")   # Default: roughly central India
    lon = request.args.get("lon", "78.96")
    try:
        api_key = require_env("OPENWEATHER_API_KEY")
        r = requests.get(
            "https://api.openweathermap.org/data/3.0/onecall",
            params={
                "lat": lat, "lon": lon,
                "exclude": "minutely,hourly,daily",
                "appid": api_key,
                "units": "metric"
            },
            timeout=8
        )
        r.raise_for_status()
        d = r.json()
        alerts = d.get("alerts", [])
        return ok([{
            "event":       a.get("event"),
            "sender":      a.get("sender_name"),
            "start":       datetime.fromtimestamp(a["start"], tz=timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
            "end":         datetime.fromtimestamp(a["end"],   tz=timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
            "description": a.get("description", "")[:300],
        } for a in alerts])
    except Exception as e:
        return err(str(e))


# ══════════════════════════════════════════════════════════════════════════════
#  HEALTH CHECK
# ══════════════════════════════════════════════════════════════════════════════

@app.route("/api/health", methods=["GET"])
def health():
    return ok({
        "server":  "ISRO Mission Control — Flask API",
        "time_utc": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC"),
        "apis":    ["OpenWeather", "NASA FIRMS"],
        "version": "2.0.0",
    })


if __name__ == "__main__":
    print("🛰  ISRO Mission Control Backend — Starting on http://localhost:5000")
    app.run(debug=True, host="0.0.0.0", port=5000)
