from xml.dom import minidom
import hashlib
import requests
import time
import json
from bs4 import BeautifulSoup
import configparser

INVALID_SID = "0000000000000000"
CONFIG_FILE = "./default.conf"
BASE_URL    = "http://fritz.box"
LOGIN_URL   = BASE_URL + "/login_sid.lua"
NETWORK_URL = BASE_URL + "/net/network.lua"
SID         = ""
PASSWORD    = ""

DEVICE_QUERY_PARAMS = {
    "no_check":"",
    "no_siderenew":"",
    "updatecheck":"",
    "t"+str(round(time.time())):"nocache",
    "xhr":"1"
}

def read_config(path):
    """read configuration file"""
    global BASE_URL, LOGIN_URL, NETWORK_URL, PASSWORD
    config = configparser.RawConfigParser()
    config.read(path)
    BASE_URL = config.get("default", "url")
    LOGIN_URL = BASE_URL + config.get("default", "login")
    NETWORK_URL = BASE_URL + config.get("default", "network")
    PASSWORD = config.get("default", "password")

def get_xml_element(xml_response, element):
    """helper function to extract value from xml element"""
    elems = minidom.parseString(xml_response).getElementsByTagName(element)
    if len(elems) == 1:
        return elems[0].firstChild.nodeValue
    else:
        return ""

def md5_response(challenge, password):
    """helper function to create md5 response string"""
    return hashlib.md5((challenge + "-" + password).encode("utf-16le")).hexdigest()

def login(password=""):
    """log in using password (set session id)"""

    global SID

    if password == "":
        read_config(CONFIG_FILE)
        password = PASSWORD

    print("Requesting challenge...")

    r = requests.get(LOGIN_URL)
    if r.status_code != 200:
        print(LOGIN_URL + " returned status code " + r.status_code)
        return False

    challenge = get_xml_element(r.text, "Challenge")
    if challenge == "":
        print("Could not extract Challenge. XML:\n" + r.text)
        return False

    res = challenge + "-" + md5_response(challenge, password)

    print("Requesting Session-ID (logging in)")
    r = requests.get(LOGIN_URL + "?username=&response=" + res)

    if r.status_code != 200:
        print(LOGIN_URL + "?username=&response=" + res + " returned status code " + r.status_code)
        return False

    SID = get_xml_element(r.text, "SID")
    if SID == "":
        print("Could not extract SID. XML:\n" + r.text)
        return False

    if SID == INVALID_SID:
        print("Login failed. Retry in " + get_xml_element(r.text, "BlockTime") + " seconds")
        return False

    print("Logged in. Session-ID: " + SID)

    return True

def logout():
    """Log current session id out"""
    global SID
    print("Logging out. Session-ID: " + SID)

    r = requests.get(LOGIN_URL + "?logout=1&sid=" + SID)

    if r.status_code != 200:
        print(LOGIN_URL + " returned status code " + r.status_code)
        return False

    return True


def get(url, parameters = {}, headers = {}):
    """Send GET request to url with parameters (session id will be added automatically)"""
    global SID

    if SID == "":
        print("No Session-ID (login first).")
        return None

    params = "?sid=" + SID

    for key in parameters:
        params += "&" + key + "=" + parameters.get(key)

    print("GET\t" + url + params)

    return requests.get(url + params, headers=headers)

def post(url, parameters = {}, headers = {}):
    """Send POST request to url with parameters"""
    global SID

    if SID == "":
        print("No Session-ID (login first).")
        return None

    parameters["sid"] = SID

    print("POST\t" + url)

    return requests.post(url, parameters, headers)

def get_devices():
    """Get currently connected device names in list"""

    r = get(NETWORK_URL, DEVICE_QUERY_PARAMS)

    res = json.loads(r.text)
    parsed = BeautifulSoup(res["devices"], "lxml")
    devs = parsed.find_all('td', class_="name")

    devices = []

    for dev in devs:
        devices.append(dev["title"])

    return devices
