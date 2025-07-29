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
    "current": "temperature_2m,weather_code",
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
        current = raw.get("current", {})
        temperature = current.get("temperature_2m")
        code = current.get("weather_code")

        data = {
            "temperature": temperature,
            "weather_code": code
        }
        redis.setex('meteo_data', 600, json.dumps(data))  # expire dans 10 minutes

    icon_url = get_icon_url(data["weather_code"])
    return render_template("index.html", temperature=data["temperature"], icon_url=icon_url)

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

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)

