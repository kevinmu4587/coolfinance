import os
import requests
import urllib.parse

from flask import redirect, render_template, request, session
from functools import wraps
from datetime import datetime

def apology(message, code=400):
    """Render message as an apology to user."""
    def escape(s):
        """
        Escape special characters.

        https://github.com/jacebrowning/memegen#special-characters
        """
        for old, new in [("-", "--"), (" ", "-"), ("_", "__"), ("?", "~q"),
                         ("%", "~p"), ("#", "~h"), ("/", "~s"), ("\"", "''")]:
            s = s.replace(old, new)
        return s
    return render_template("apology.html", top=code, bottom=escape(message)), code


def login_required(f):
    """
    Decorate routes to require login.

    http://flask.pocoo.org/docs/1.0/patterns/viewdecorators/
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if session.get("user_id") is None:
            return redirect("/login")
        return f(*args, **kwargs)
    return decorated_function


def lookup(symbol):
    """Look up quote for symbol."""

    # Contact API
    try:
        api_key = os.environ.get("API_KEY")
        # API KEY IS pk_2bb7cf03d37949a39b284e2c1ca08bc7
        # url = f"https://cloud.iexapis.com/stable/stock/{urllib.parse.quote_plus(symbol)}/quote?token={api_key}"
        url = "https://cloud.iexapis.com/stable/stock/" + symbol + "/quote?token=" + api_key
        # print(url)
        response = requests.get(url)
        # print(response)
        
        response.raise_for_status()
    except requests.RequestException:
        print("Request Exception")
        return None

    # Parse response
    try:
        quote = response.json()
        print(quote)
        return {
            "name": quote["companyName"],
            "price": float(quote["latestPrice"]),
            "symbol": quote["symbol"]
        }
    except (KeyError, TypeError, ValueError):
        print("Other exception")
        return None


def usd(value):
    """Format value as USD."""
    return f"${value:,.2f}"

def usd_to_float(usd):
    # delete all commas and the dollar sign
    for char in usd:
        if char in ",$":
            usd = usd.replace(char, "")

    return float(usd)

def current_time():
    dateTimeObj = datetime.now()
    timestampStr = dateTimeObj.strftime("%d-%b-%Y (%H:%M:%S)")
    return timestampStr;
