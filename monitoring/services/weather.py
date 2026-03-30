import os
import requests
from django.core.cache import cache

def get_current_weather(lat, lon):
    cache_key = f"weather_{lat}_{lon}"
    cached = cache.get(cache_key)

    if cached:
        return cached

    api_key = os.getenv("WEATHER_API_KEY")

    if not api_key:
        return {
            "error": True,
            "message": "API Key Not Configured",
            "temp": "--",
            "humidity": "--",
            "description": "N/A",
            "icon": ""
        }

    url = f"http://api.weatherapi.com/v1/forecast.json?key={api_key}&q={lat},{lon}&days=2"

    try:
        response = requests.get(url, timeout=5)
        response.raise_for_status()
        data = response.json()
        
        # Flatten hourly forecasts across the 2 possible days
        all_hours = []
        for d in data.get("forecast", {}).get("forecastday", []):
            all_hours.extend(d.get("hour", []))
            
        current_local_epoch = data.get("location", {}).get("localtime_epoch", 0)
        
        forecast_hours = []
        slots_found = 0
        for hr in all_hours:
            # Find the closest immediate next slots
            if hr["time_epoch"] >= current_local_epoch:
                time_str = hr["time"].split(" ")[1]
                forecast_hours.append({
                    "time": time_str,
                    "temp": hr["temp_c"],
                    "icon": hr["condition"]["icon"]
                })
                slots_found += 1
                if slots_found >= 4:
                    break

        weather = {
            "error": False,
            "location_name": data["location"]["name"],
            "country": data["location"]["country"],
            "temp": data["current"]["temp_c"],
            "humidity": data["current"]["humidity"],
            "description": data["current"]["condition"]["text"],
            "icon": data["current"]["condition"]["icon"],
            "wind_kph": data["current"]["wind_kph"],
            "wind_dir": data["current"]["wind_dir"],
            "gust_kph": data["current"]["gust_kph"],
            "forecast": forecast_hours
        }

        cache.set(cache_key, weather, 900)  # 15 min cache
        return weather

    except requests.exceptions.RequestException:
        return {
            "error": True,
            "message": "Weather service unavailable",
            "temp": "--",
            "humidity": "--",
            "description": "Error",
            "icon": ""
        }