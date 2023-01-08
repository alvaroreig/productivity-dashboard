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

app = Flask(__name__)

if os.getenv('GUNICORN') == 'True':
    gunicorn_error_logger = logging.getLogger('gunicorn.error')
    app.logger.handlers.extend(gunicorn_error_logger.handlers)
    app.logger.setLevel(logging.DEBUG)
else:
    logging.basicConfig(level=logging.DEBUG, format='%(asctime)s -  %(levelname)s-  %(message)s')

# tutorial
# https://code.visualstudio.com/docs/python/tutorial-flask
# https://medium.com/@jtpaasch/the-right-way-to-use-virtual-environments-1bc255a0cba7
# https://testdriven.io/blog/flask-render-deployment/

# Guardar dependencias
# pip freeze > requirements.txt

# Instalar dependencias
# pip install -r requirements.txt

# Arracar server local con binding a todo
# flask run --host 0.0.0.0

@app.route("/")
def home():

    if os.getenv('LOCALE') is not None:
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
    tomorrow = []
    after = {}

    for task in tasks:
        logging.debug('task content: ' + task.content)
        logging.debug('task datetine ' + str(task.due.datetime))

        if 'http' in task.content:
            task_content = re.sub(r"http\S+", "", task.content)
        else:
            task_content = task.content
        try:
            if (task.due.datetime is not None):
                parsed_date=datetime.strptime(task.due.datetime,"%Y-%m-%dT%H:%M:%SZ")
            else:
                parsed_date=datetime.strptime(task.due.date,"%Y-%m-%d")
        except Exception as e:
            logging.error("Parsing error,task " + task_content)
        
        logging.debug('task parsed due datetime: ' + str(parsed_date))

        days_between_dates = parsed_date.date() - today.date()
        
        if (days_between_dates.days < 0):
            overdue.append(task_content)
        elif (days_between_dates.days == 0):
            today_list.append(task_content)
        elif (days_between_dates.days == 1):
            tomorrow.append(task_content)
        else:
            task_date_clean = str(parsed_date.date())
            if (task_date_clean in after):
                tasks_in_date = after[task_date_clean]
            else:
                tasks_in_date = []
            tasks_in_date.append(task_content)
            after[task_date_clean] = tasks_in_date

    after = sorted(after.items())

    logging.debug("overdue tasks: " + str(len(overdue)))
    logging.debug(overdue)

    logging.debug("today tasks: " + str(len(today_list)))
    logging.debug(today_list)

    logging.debug("tomorrow tasks: " + str(len(tomorrow)))
    logging.debug(tomorrow)

    logging.debug("after tasks: " + str(len(after)))
    logging.debug(after)

    return render_template(
        "index.html",
        date=today.strftime('%A,%d %B %Y'),
        overdue=overdue,
        today = today_list,
        tomorrow = tomorrow,
        after = after
    )