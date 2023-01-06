import re
from datetime import datetime,date

from flask import Flask
from flask import render_template
from dotenv import load_dotenv
import os
import logging
import locale

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

    locale.setlocale(locale.LC_TIME, os.getenv('LOCALE'))
    api = TodoistAPI(os.getenv('TODOIST_API_KEY'))
    filter = os.getenv('TODOIST_FILTER')
    today = datetime.today()
    logging.debug("today: " + str(today))

    try:
        tasks = api.get_tasks(filter=filter)
    except Exception as e:
        try:
            logging.error(e)
            tasks = api.get_tasks(filter=filter)
        except Exception as e:
            logging.error(e)
            tasks = []
    
    logging.info('Recovered ' + str(len(tasks)) + ' task(s)')
    #logging.debug(tasks)

    overdue = []
    today_list = []

    for task in tasks:
        logging.debug('task content: ' + task.content)
        logging.debug('task datetine ' + str(task.due.datetime))
        try:
            if (task.due.datetime is not None):
                parsed_date=datetime.strptime(task.due.datetime,"%Y-%m-%dT%H:%M:%SZ")
            else:
                parsed_date=datetime.strptime(task.due.date,"%Y-%m-%d")
        except Exception as e:
            logging.error("Parsing error,task " + task.content)
        
        logging.debug('task parsed due datetime: ' + str(parsed_date))

        if (parsed_date.day == today.day and parsed_date.month == today.month and parsed_date.year == today.year):
            today_list.append(task.content)
        elif (parsed_date < today):
            overdue.append(task.content)


    logging.debug("overdue tasks: " + str(len(overdue)))
    logging.debug(overdue)

    logging.debug("today tasks: " + str(len(today_list)))
    logging.debug(today_list)

    return render_template(
        "index.html",
        date=today.strftime('%A,%d %B %Y'),
        overdue=overdue,
        today = today_list
    )