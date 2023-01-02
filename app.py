import re
from datetime import datetime

from flask import Flask
from flask import render_template
from dotenv import load_dotenv
import os
import logging


load_dotenv()
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s -  %(levelname)s-  %(message)s')

app = Flask(__name__)

# tutorial
# https://code.visualstudio.com/docs/python/tutorial-flask
# https://medium.com/@jtpaasch/the-right-way-to-use-virtual-environments-1bc255a0cba7

# Instalar dependencias
# pip install -r requirements.txt

example = os.environ.get('TODOIST_API_KEY');
logging.debug(example)
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