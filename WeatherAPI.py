import os
import datetime
import requests
import logging
from flask import Flask, g, request, jsonify
from functools import wraps
from flask_cache import Cache
from config import APIConfig

app = Flask(__name__)

app.config['CACHE_TYPE'] = 'simple'
# Register the cache instance and binds it on to the app.
app.cache = Cache(app) 

"""
Logger function.
"""
def get_logger():
    root = os.path.dirname(os.path.abspath(__file__))
    logdir = os.path.join(root, 'logs')
    log_level = logging.INFO
    if not os.path.exists(logdir):
        os.mkdir(logdir)
    log_file = os.path.join(logdir, 'WeatherAPI_' + datetime.datetime.now().strftime('%Y_%m_%d') + '.log')
    handler = logging.FileHandler(log_file)
    handler.setLevel(log_level)
    app.logger.addHandler(handler)


"""
Decorator for Authentication.
"""
def protected(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        auth = request.authorization
        if auth and auth.username == APIConfig.api_username and auth.password == APIConfig.api_password:
            return f(*args, **kwargs)
        else:
            return jsonify({"message" : "Authentication Failed!"}), 401
    return decorated


"""
Function to format dates from Epoch to human readable format.
Input params : Epoch date, Expected date format
Returns : Date in given format
"""
def format_date(dt, date_type):
    try:
        if date_type == "HM":
            return datetime.datetime.fromtimestamp(dt).strftime('%H:%M')
        elif date_type == "All":
            return datetime.datetime.fromtimestamp(dt).strftime('%Y-%m-%d %H:%M:%S')
    except Exception as err:
        print("format_date() Exception - {}".format(err))


"""
Endpoint '/weather' to return weather data.
Params : City, Country
Return : Weather data in json format.
Keeping data cache for 2mins(120 seconds)
"""
get_logger()
@app.route("/weather", methods=["GET"])
@protected
## Keeping data in Cache for 2 mins.
@app.cache.cached(timeout=120)
def get_weather():
    app.logger.info("GET /weather")
    try:
        city = request.args.get("city")
        country = request.args.get("country")
        if city and country:            
            new_app_url = APIConfig.app_url.format(city, country)
            app.logger.info("City- {}, Country - {}, URL - {}".format(city, country, new_app_url))
            res_data = requests.get(new_app_url)
            sc = res_data.status_code
            if sc == 200:
                j_data = res_data.json()
                if j_data:
                    # Formatting dates from Epoch to human readable format
                    requested_time = format_date(j_data["dt"], "All")
                    sunrise = format_date(j_data["sys"]["sunrise"], "HM")
                    sunset = format_date(j_data["sys"]["sunset"], "HM")
                    # Kelvin to Celcius conversion.
                    temperature_dc = j_data["main"]["temp"] - 273.15
                    temperature_fh = (j_data["main"]["temp"] - 273.15) * 9/5 + 32
                    lat = j_data["coord"]["lat"]
                    lon = j_data["coord"]["lon"]
                    pressure = j_data["main"]["pressure"]
                    weather = {
                        'city' : j_data["name"],
                        'country' : j_data["sys"]["country"],
                        "location_name" : "{}, {}".format(j_data["name"], j_data["sys"]["country"]),
                        'humidity' : "{}%".format(j_data["main"]["humidity"]),
                        'pressure' : "{} hpa".format(pressure),
                        'geo_coordinates' : "[{}, {}]".format(lat, lon),
                        'requested_time' : requested_time,
                        'sunrise' : sunrise,
                        'sunset' : sunset,
                        'temperature' : "{} °C, {} °F".format(round(temperature_dc, 2), round(temperature_fh ,2)),
                        'wforcast' : j_data["weather"][0]["description"],
                        'wcloudiness' : j_data["clouds"]["all"],
                        'wind' : j_data["wind"]["speed"]
                    }
            else:
                app.logger.error("ERROR, Status Code # %d " % sc)
            # returns response with the content-type header (application/json)
            return jsonify({"weather_data":weather})
        else:
            return jsonify({"Message" : "City/Country name is missing.."})
    except Exception as err:
        app.logger.error("get_weather() Exception -- {}".format(err))
