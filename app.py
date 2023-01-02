import re
from datetime import datetime

from flask import Flask
from flask import render_template

app = Flask(__name__)

# tutorial
# https://code.visualstudio.com/docs/python/tutorial-flask
# https://medium.com/@jtpaasch/the-right-way-to-use-virtual-environments-1bc255a0cba7

# Instalar dependencias
# pip install -r requirements.txt

@app.route("/")
def home():
    return render_template(
        "index.html",
        date=datetime.now()
    )

@app.route("/hello/<name>")
def hello_there(name = None):
    return render_template(
        "index.html",
        date=datetime.now()
    )