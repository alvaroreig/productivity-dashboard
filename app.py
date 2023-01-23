from __future__ import print_function

import re
import datetime

from flask import Flask
from flask import render_template
from dotenv import load_dotenv
import os
import logging
import locale
from pprint import pformat

from todoist_api_python.api import TodoistAPI
from operator import itemgetter


import datetime
import os.path

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

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

 # Dependencias
 #  pip3.10 install flask python-dotenv

@app.route("/")
def home():

    if os.getenv('LOCALE') is not None:
        locale.setlocale(locale.LC_TIME, os.getenv('LOCALE'))
    
    api = TodoistAPI(os.getenv('TODOIST_API_KEY'))
    filter = os.getenv('TODOIST_FILTER')
    today = datetime.datetime.today()
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

    global_elements = {}
    # Dic with dictionaries that contains title, elements
    # -1 => overdue elements
    # 0 => today elements
    # 1 => tomorrow elements
    # 2...n other days elements
    #
    # Each key contains an array with dictionaries with two elements: datetime and title
    # Example
    #[{}]


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
                parsed_date=datetime.datetime.strptime(task.due.datetime,"%Y-%m-%dT%H:%M:%SZ")
                #TODO Dirty hack: todoist returns UTC, I need to convert it to my zonetime more elegantly.
                parsed_date = parsed_date.replace(hour=parsed_date.hour + 1)
                hour = "0" + str(parsed_date.hour) if parsed_date.hour < 10 else str(parsed_date.hour )
                minute = "0" + str(parsed_date.minute) if parsed_date.minute < 10 else str(parsed_date.minute)
                task_clean_title = "[T] " + "[" + hour + ":" + minute + "] " + task_content
            else:
                parsed_date=datetime.datetime.strptime(task.due.date,"%Y-%m-%d")
                task_clean_title = "[T] " + task_content
        except Exception as e:
            logging.error("Parsing error,task " + task_content)
            task_clean_title = "[T] " + task_content
        
        logging.debug('task parsed due datetime: ' + str(parsed_date))

        days_between_dates = parsed_date.date() - today.date()
        add_element(days_between_dates.days,global_elements,task_clean_title,parsed_date)

        if (days_between_dates.days < 0):
            overdue.append(task_clean_title)
        elif (days_between_dates.days == 0):
            today_list.append(task_clean_title)
        elif (days_between_dates.days == 1):
            tomorrow.append(task_clean_title)
        else:
            task_date_clean = str(parsed_date.date())
            if (task_date_clean in after):
                tasks_in_date = after[task_date_clean]
            else:
                tasks_in_date = []
            tasks_in_date.append(task_clean_title)
            after[task_date_clean] = tasks_in_date




    gcal_events = get_gcal_events();
    for event in gcal_events:
        logging.debug(event['summary'])
        event_datetime= event['start'].get('dateTime')
        logging.debug(event_datetime)
        # TODO. This is a dirty hack. I need to remove the datezone offset in a more elegant manner.
        truncated_due = event_datetime[0:19]
        logging.debug(truncated_due)
        truncared_parsed_date=datetime.datetime.strptime(truncated_due,"%Y-%m-%dT%H:%M:%S")
        logging.debug(truncared_parsed_date)
        
        
        days_between_dates = truncared_parsed_date.date() - today.date()
        logging.debug(days_between_dates.days)


        if (truncared_parsed_date.hour != 0):
            hour = "0" + str(truncared_parsed_date.hour) if truncared_parsed_date.hour < 10 else str(truncared_parsed_date.hour)
            minute = "0" + str(truncared_parsed_date.minute) if truncared_parsed_date.minute < 10 else str(truncared_parsed_date.minute)
            event_clean_title = "[C] " + "[" + hour + ":" + minute + "] " + event['summary']
        else:
            event_clean_title = "[C] " + event['summary']
        
        if (days_between_dates.days == 0):
            today_list.append(event_clean_title)
        elif (days_between_dates.days == 1):
            tomorrow.append(event_clean_title)
        else:
            task_date_clean = str(truncared_parsed_date.date())
            if (task_date_clean in after):
                elements_in_date = after[task_date_clean]
            else:
                elements_in_date = []
            elements_in_date.append(event_clean_title)
            after[task_date_clean] = elements_in_date

        add_element(days_between_dates.days,global_elements,event_clean_title,truncared_parsed_date)

    after = sorted(after.items())

    logging.debug("overdue tasks: " + str(len(overdue)))
    logging.debug(overdue)

    logging.debug("today tasks: " + str(len(today_list)))
    logging.debug(today_list)

    logging.debug("tomorrow tasks: " + str(len(tomorrow)))
    logging.debug(tomorrow)

    logging.debug("after tasks: " + str(len(after)))
    logging.debug(after)

    logging.debug("global")
    logging.debug(pformat(global_elements))

    for key in global_elements:
        logging.debug(key)
        section = global_elements[key]
        logging.debug(pformat(section))
        elements = section['elements'];
        logging.debug(pformat(elements))
        elements = sorted(elements, key=itemgetter('datetime')) 
        logging.debug(elements)
        section['elements'] = elements
        global_elements[key] = section

    global_elements = sorted(global_elements.items())

    return render_template(
        "index.html",
        date=today.strftime('%A,%d %B %Y'),
        overdue=overdue,
        today = today_list,
        tomorrow = tomorrow,
        after = after,
        global_elements = global_elements
    )

def get_gcal_events():
    # If modifying these scopes, delete the file token.json.
    SCOPES = ['https://www.googleapis.com/auth/calendar.readonly']

    # Tutorial seguido
    # https://developers.google.com/calendar/api/quickstart/python?hl=en

    """Shows basic usage of the Google Calendar API.
    Prints the start and name of the next 10 events on the user's calendar.
    """
    creds = None
    # The file token.json stores the user's access and refresh tokens, and is
    # created automatically when the authorization flow completes for the first
    # time.
    if os.path.exists('token.json'):
        creds = Credentials.from_authorized_user_file('token.json', SCOPES)
    # If there are no (valid) credentials available, let the user log in.
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                'credentials.json', SCOPES)
            creds = flow.run_local_server(port=0)
        # Save the credentials for the next run
        with open('token.json', 'w') as token:
            token.write(creds.to_json())

    try:
        service = build('calendar', 'v3', credentials=creds)

        # Call the Calendar API
        now = datetime.datetime.utcnow().isoformat() + 'Z'  # 'Z' indicates UTC time
        print('Getting the upcoming 10 events')

        events_result = service.events().list(calendarId='771b9ig6pbv1vkv07kia1jt28g@group.calendar.google.com', timeMin=now,
                                              maxResults=20, singleEvents=True,
                                              orderBy='startTime',timeZone='Europe/Madrid').execute()
        events = events_result.get('items', [])

        if not events:
            print('No upcoming events found.')
            return

        # Prints the start and name of the next 10 events
        return events
        # for event in events:
        #     start = event['start'].get('dateTime', event['start'].get('date'))
        #     print(start, event['summary'])
        #     print(event)

    except HttpError as error:
        print('An error occurred: %s' % error)

    return 3
    
def add_element(section_index,list,element_title,element_datetime):
    if section_index in list:
        section = list[section_index]
        section_header = section['header']
        section_elements = section['elements']
    else:
        section = {}
        
        match section_index:
            case -1:
                section_header = "Overdue"
            case 0:
                section_header = "Today"
            case 1:
                section_header = "Tomorrow"
            case _:
                today = datetime.datetime.now()
                next = today + datetime.timedelta(days = section_index)
                if section_index < 7:
                    section_header = next.strftime('%A')
                else:
                    section_header = element_datetime.strftime('%A,%d %B')

        section_elements = []
        section = {"header" : section_header}
      
    section_elements.append({"title":element_title,"datetime":element_datetime})
    section['elements'] = section_elements
    list[section_index] = section