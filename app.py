from flask import Flask, render_template
from redis import Redis
import requests
import json

app = Flask(__name__)
redis = Redis(host='redis', port=6379)

API_URL = "https://api.open-meteo.com/v1/forecast"
PARAMS = {
    "latitude": -22.2758,
    "longitude": 166.4579,
    # use current_weather to get temperature, windspeed, winddirection and weathercode
    "current_weather": True,
    "timezone": "Pacific/Noumea"
}

@app.route('/')
def meteo():
    cached_data = redis.get('meteo_data')

    if cached_data:
        data = json.loads(cached_data)
    else:
        response = requests.get(API_URL, params=PARAMS, timeout=10)
        response.raise_for_status()
        raw = response.json()
        # Open-Meteo returns a `current_weather` object when asked
        current = raw.get("current_weather", {})
        temperature = current.get("temperature")
        code = current.get("weathercode")
        wind_speed = current.get("windspeed")
        wind_dir = current.get("winddirection")

        # Convert wind speed to km/h for nicer display when available
        wind_kmh = round(wind_speed * 3.6, 1) if wind_speed is not None else None

        data = {
            "temperature": temperature,
            "weather_code": code,
            "wind_speed": wind_speed,
                "wind_kmh": wind_kmh,
                "wind_dir": wind_dir
        }
        redis.setex('meteo_data', 600, json.dumps(data))  # expire dans 10 minutes

    icon_url = get_icon_url(data["weather_code"]) if data.get("weather_code") is not None else None

    # Determine human-readable wind direction (N, NE, E, ...)
    wind_dir_name = None
    if data.get("wind_dir") is not None:
        wind_dir_name = deg_to_compass(data["wind_dir"])

    # Determine Beaufort scale and name from km/h
    wind_beaufort = None
    wind_beaufort_name = None
    if data.get("wind_kmh") is not None:
        try:
            wind_beaufort = kmh_to_beaufort(data.get("wind_kmh"))
            wind_beaufort_name = beaufort_name(wind_beaufort)
        except Exception:
            wind_beaufort = None
            wind_beaufort_name = None

    return render_template(
        "index.html",
        temperature=data.get("temperature"),
        icon_url=icon_url,
        wind_speed=data.get("wind_speed"),
        wind_kmh=data.get("wind_kmh"),
        wind_dir_deg=data.get("wind_dir"),
    wind_dir_name=wind_dir_name,
    wind_beaufort=wind_beaufort,
    wind_beaufort_name=wind_beaufort_name
    )

def get_icon_url(code):
    # Correspondance météo (Open-Meteo code → icône de chez https://openweathermap.org/weather-conditions)
    mapping = {
        0: "01d",  # clair
        1: "02d", 2: "03d", 3: "04d",  # nuageux
        45: "50d", 48: "50d",  # brouillard
        51: "09d", 53: "09d", 55: "09d",  # bruine
        61: "10d", 63: "10d", 65: "10d",  # pluie
        71: "13d", 73: "13d", 75: "13d",  # neige
        80: "09d", 81: "09d", 82: "09d",  # averses
        95: "11d", 96: "11d", 99: "11d"   # orage
    }
    code_str = mapping.get(code, "01d")
    return f"https://openweathermap.org/img/wn/{code_str}@2x.png"


def deg_to_compass(deg: float) -> str:
    # Convert degrees to compass direction
    try:
        val = int((deg / 22.5) + 0.5)
        directions = [
            "N", "NNE", "NE", "ENE", "E", "ESE", "SE", "SSE",
            "S", "SSW", "SW", "WSW", "W", "WNW", "NW", "NNW"
        ]
        return directions[(val % 16)]
    except Exception:
        return ""


def kmh_to_beaufort(kmh: float) -> int:
    """Convertit km/h en force de Beaufort (0..12)."""
    try:
        k = float(kmh)
    except Exception:
        return None
    thresholds = [1, 5, 11, 19, 28, 38, 49, 61, 74, 88, 102, 117]
    for i, t in enumerate(thresholds):
        if k <= t:
            return i
    return 12


def beaufort_name(b: int) -> str:
    names = [
        "Calme", "Très légère brise", "Légère brise", "Petite brise",
        "Jolie brise", "Vent frais", "Grand vent", "Coup de vent",
        "Fort coup de vent", "Violent", "Tempête", "Violente tempête", "Ouragan"
    ]
    try:
        return names[int(b)]
    except Exception:
        return ""

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)

