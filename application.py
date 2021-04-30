import os

import sqlite3
# from cs50 import SQL
from flask import Flask, flash, jsonify, redirect, render_template, request, session
from flask_session import Session
from tempfile import mkdtemp
from werkzeug.exceptions import default_exceptions, HTTPException, InternalServerError
from werkzeug.security import check_password_hash, generate_password_hash

from helpers import apology, login_required, lookup, usd, usd_to_float, current_time

# Configure application
app = Flask(__name__)

# Ensure templates are auto-reloaded
app.config["TEMPLATES_AUTO_RELOAD"] = True

# Ensure responses aren't cached
@app.after_request
def after_request(response):
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Expires"] = 0
    response.headers["Pragma"] = "no-cache"
    return response


# Custom filter
app.jinja_env.filters["usd"] = usd

# Configure session to use filesystem (instead of signed cookies)
app.config["SESSION_FILE_DIR"] = mkdtemp()
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# Configure CS50 Library to use SQLite database
# db = SQL("sqlite:///finance.db")

connection = sqlite3.connect('finance.db', check_same_thread=False) 
users = connection.cursor()

# CREATE TABLE IF NOT EXISTS 'users' ('id' INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL, 'username' TEXT NOT NULL, 'hash' TEXT NOT NULL, 
# 'cash' NUMERIC NOT NULL DEFAULT 10000.00 );
# CREATE UNIQUE INDEX 'username' ON "users" ("username");

# sqlite database to store transactions
connect = sqlite3.connect("transactions.db", check_same_thread=False)
trsc = connect.cursor()
trsc.execute("DROP TABLE transactions")
create = """CREATE TABLE IF NOT EXISTS 'transactions' ('user_id' INTEGER, symbol TEXT, 
count INTEGER, price NUMERIC, timestamp TEXT);"""
trsc.execute(create)

# here we store the active transactions
create = """CREATE TABLE IF NOT EXISTS 'active' ('user_id' INTEGER, name TEXT, 
symbol TEXT, price NUMERIC, count INTEGER, total NUMERIC);"""
trsc.execute(create)

# Make sure API key is set
if not os.environ.get("API_KEY"):
    raise RuntimeError("API_KEY not set")

@app.route("/")
@login_required
def index():
    """Show portfolio of stocks"""
    trsc.execute("SELECT * FROM active")
    data = trsc.fetchall()

    net_worth = 0
    # update price and total for each purchased item
    for row in data:
        symbol = row[2]
        count = row[4]
        result = lookup(symbol)
        price = result["price"]
        total = price * int(count)
        net_worth += total
        trsc.execute("UPDATE active SET price=?, total=? WHERE symbol=?", (usd(price), usd(total), symbol))

    users.execute("SELECT * FROM users WHERE id=?", (session["user_id"],))
    user_info = users.fetchall()
    balance = user_info[0][3]
    net_worth += balance

    # display alerts
    alert = session["alert"]
    session["alert"] = None

    return render_template("index.html", data=data, balance=usd(balance), net_worth=usd(net_worth), alert=alert)

@app.route("/buy", methods=["GET", "POST"])
@login_required
def buy():
    """Buy shares of stock"""

    if request.method == "GET":
        return render_template("buy.html")
    else:
        symbol = request.form.get("buy")
        result = lookup(symbol)
        if result is None:
            return apology("Invalid symbol")
        else:
            # calcuclate the purchase total
            price = result["price"]
            count = (int) (request.form.get("count"))
            total = price * count
            
            # get the balance of the current user
            users.execute("SELECT * FROM users WHERE id=1")
            data = users.fetchall()
            balance = data[0][3]

            if total > balance:
                return apology("Insufficient funds!")

            # now we can purchase it
            user_id = session["user_id"]
            name = result["name"]

            # first insert it into the transaction history
            trsc.execute("INSERT INTO transactions VALUES (?, ?, ?, ?, ?)", 
            (user_id, symbol, count, usd(price), current_time(),))
            users.execute("UPDATE users SET cash=? WHERE id=?", (balance - total, session["user_id"],))

            # check if we already own this company's stocks
            trsc.execute("SELECT * FROM active WHERE symbol=?", (symbol,))
            stocks = trsc.fetchall()
            if len(stocks) == 1:
                # update the existing stock
                existing = stocks[0][4]
                old_total = stocks[0][5]
                
                count += int(existing)
                dollar_old_total = usd_to_float(old_total) + total
                trsc.execute("UPDATE active SET count=?, price=?, total=? WHERE symbol=?", 
                (count, usd(price), usd(dollar_old_total), symbol))
            else: 
                # add a new entry
                trsc.execute("INSERT INTO active VALUES (?, ?, ?, ?, ?, ?)", 
                (user_id, name, symbol, usd(price), count, usd(total),))
            session["alert"] = "Bought successfully!"
            return redirect("/")

@app.route("/history")
@login_required
def history():
    """Show history of transactions"""
    trsc.execute("SELECT * FROM transactions WHERE user_id=?", (session["user_id"],))
    data = trsc.fetchall()
    return render_template("history.html", data=data)

@app.route("/login", methods=["GET", "POST"])
def login():
    """Log user in"""

    # Forget any user_id
    session.clear()

    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":

        # Ensure username was submitted
        if not request.form.get("username"):
            return apology("must provide username", 403)

        # Ensure password was submitted
        elif not request.form.get("password"):
            return apology("must provide password", 403)

        # Query database for username
        username = request.form.get("username")
        users.execute("SELECT * FROM users WHERE username = ?", (username,))
        rows = users.fetchall()
        # rows = users.execute("SELECT * FROM users WHERE username = :username",
        #                  username=request.form.get("username"))

        # Ensure username exists and password is correct
        if len(rows) != 1 or not check_password_hash(rows[0][2], request.form.get("password")):
            return apology("invalid username and/or password", 403)

        # Remember which user has logged in
        session["user_id"] = rows[0][0] 

        # Redirect user to home page
        session["alert"] = "Welcome!"
        return redirect("/")

    # User reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("login.html")


@app.route("/logout")
def logout():
    """Log user out"""

    # Forget any user_id
    session.clear()

    # Redirect user to login form
    return redirect("/")


@app.route("/quote", methods=["GET", "POST"])
@login_required
def quote():
    """Get stock quote."""

    if request.method == "GET":
        return render_template("quote.html")
    else:
        symbol = request.form.get("quote")
        result = lookup(symbol)
        if result is None:
            return apology("Invalid symbol")
        else:
            name = result["name"]
            symbol = result["symbol"]
            price = result["price"]
            return render_template("stock.html", name=name, symbol=symbol, price=usd(price))


@app.route("/register", methods=["GET", "POST"])
def register():
    """Register user"""

    if request.method == "GET":
        return render_template("register.html")
    else:
        username = request.form.get("username")
        password = request.form.get("password")
        confirm = request.form.get("confirm password")
        
        # check if the username already exists
        users.execute("SELECT * FROM users WHERE username = ?", (username,))
        rows = users.fetchall()
        if len(rows) != 0:
            # username already exists
            return apology("Username already exists!")

        # check if the password and its confirmation matches
        if not password == confirm:
            # passwords to do match
            return apology("Password and confirmation do not match!")

        # by now we should be okay to add it to the users table
        # id, username, hash, cash
        users.execute("INSERT INTO users (username, hash, cash) values (?, ?, ?)", 
        (username, generate_password_hash(password), 10000.00,))
        users.execute("SELECT * FROM users WHERE username=?", (username,))
        rows = users.fetchall()
        session["user_id"] = rows[0][0] 
        session["alert"] = "Welcome!"
        return redirect("/")


@app.route("/sell", methods=["GET", "POST"])
@login_required
def sell():
    """Sell shares of stock"""
    if request.method == "GET":
        return render_template("sell.html")
    else:
        symbol = request.form.get("sell")

        # first check if the symbol is valid
        result = lookup(symbol)
        if not result:
            return apology("Invalid stock symbol.")

        count = int(request.form.get("num_sold"))
        
        # check if the user owns the share
        trsc.execute("SELECT * FROM active WHERE symbol=?", (symbol,))
        data = trsc.fetchall()
        if len(data) == 0:
            return apology("You do not own that stock.")
        
        # check if the user has enough shares to sell
        total_owned = int(data[0][4])
        if count > total_owned:
            return apology("You don't have that many shares.")

        # now we can sell
        # first add the transaction to the transactions table
        user_id = session["user_id"]
        price = result["price"]
        trsc.execute("INSERT INTO transactions VALUES (?, ?, ?, ?, ?)", 
            (user_id, symbol, -count, usd(price), current_time(),))

        # now update the active table
        revenue = int(count) * price

        # update the user's balance
        users.execute("SELECT * FROM users WHERE id=?", (user_id,))
        user = users.fetchall()
        old_cash = user[0][3]
        users.execute("UPDATE users SET cash=? WHERE id=?", (old_cash + revenue, user_id,))

        # update the active table
        if count == total_owned:
            trsc.execute("DELETE FROM active WHERE symbol=?", (symbol,))
        else:
            old_count = data[0][4]
            trsc.execute("UPDATE active SET count=? WHERE user_id=?", (old_count - count, user_id,))
        session["alert"] = "Sold successfully!"
        return redirect("/")


def errorhandler(e):
    """Handle error"""
    if not isinstance(e, HTTPException):
        e = InternalServerError()
    return apology(e.name, e.code)


# Listen for errors
for code in default_exceptions:
    app.errorhandler(code)(errorhandler)
