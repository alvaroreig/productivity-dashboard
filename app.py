import re
from datetime import datetime

from flask import Flask
from flask import render_template
from dotenv import load_dotenv
import os
import logging

from todoist_api_python.api import TodoistAPI

load_dotenv()
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s -  %(levelname)s-  %(message)s')

app = Flask(__name__)

# tutorial
# https://code.visualstudio.com/docs/python/tutorial-flask
# https://medium.com/@jtpaasch/the-right-way-to-use-virtual-environments-1bc255a0cba7

# Instalar dependencias
# pip install -r requirements.txt


@app.route("/")
def home():

    api = TodoistAPI(os.getenv('TODOIST_API_KEY'))
    filter = os.getenv('TODOIST_FILTER')
    tasks = api.get_tasks(filter=filter)
    logging.debug(api)

    
    #tasks = api.get_tasks()
    logging.debug('Recovered ' + str(len(tasks)) + ' task(s)')

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