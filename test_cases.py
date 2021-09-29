import requests
from config import APIConfig

api_url = "http://127.0.0.1:5000/weather?city=Pune&country=in"

def test_API():
    res = requests.get(api_url, auth=(APIConfig.api_username, APIConfig.api_password))
    assert res.status_code == 200
