from __future__ import print_function

import re
import datetime
from dateutil import parser

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

from google.oauth2 import service_account
from googleapiclient.errors import HttpError
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

load_dotenv()
APP_GUNICORN = os.getenv('APP_GUNICORN')
APP_LOCALE = os.getenv('APP_LOCALE')

TODOIST_ENABLED = os.getenv('TODOIST_ENABLED','True')
TODOIST_REMOVE_LINKS = os.getenv('TODOIST_REMOVE_LINKS','True')
TODOIST_API_KEY = os.getenv('TODOIST_API_KEY')
TODOIST_FILTER = os.getenv('TODOIST_FILTER')


GCAL_ENABLED = os.getenv('GCAL_ENABLED','False')
GCAL_CALENDAR_IDS = os.getenv('GCAL_CALENDAR_IDS','')

app = Flask(__name__)

if APP_GUNICORN == 'True':
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

    if APP_LOCALE is not None:
        locale.setlocale(locale.LC_TIME, os.getenv('APP_LOCALE'))
    today = datetime.datetime.today()

    global_elements = {}
    # Dic with sections for each day 
    # -1 => overdue section
    # 0 => today section
    # 1 => tomorrow section
    # 2...n other days section
    #
    # Each section contains two elements: A header withe the label (Overdue, Today, Tomorrow, Monday..) and
    # an array with elements, defined by two elements: datetime (for ordering purposes) and title
    # Example
    # {-1: {'elements': [{'datetime': datetime.datetime(2023, 1, 23, 13, 0),
    #                 'title': '[T] [13:00] Weekly review'},
    #                {'datetime': datetime.datetime(2023, 1, 23, 0, 0),
    #                 'title': '[T] Kefir'}],
    #     'header': 'Retrasado'},
    # 0: {'elements': [{'datetime': datetime.datetime(2023, 1, 24, 16, 20),
    #                 'title': '[C] [16:20] Cita centro salud'},
    #                 {'datetime': datetime.datetime(2023, 1, 24, 18, 0),
    #                 'title': '[C] [18:00] Gym'}],
    #     'header': 'Hoy'},
    # 1: {'elements': [{'datetime': datetime.datetime(2023, 1, 25, 9, 0),
    #                 'title': '[C] [09:00] Álvaro trabaja hasta tarde'},
    #                 {'datetime': datetime.datetime(2023, 1, 25, 17, 45),
    #                 'title': '[C] [17:45] Natación'}
    #     'header': 'Mañana'},
    # 2: {'elements': [{'datetime': datetime.datetime(2023, 1, 26, 0, 0),
    #                 'title': '[T] Seguro coche'},
    #                 {'datetime': datetime.datetime(2023, 1, 26, 18, 0),
    #                 'title': '[C] [18:00] Psicomotricidad'}
    #     'header': 'Jueves'}
    # }

    ######################################################################################################
    #################            TODOIST EVENTS PROCESSING      ##########################################
    ######################################################################################################

    if TODOIST_ENABLED == "True":
        tasks = get_todoist_events()
        logging.info('Recovered ' + str(len(tasks)) + ' task(s)')
        #logging.debug(tasks)

        for task in tasks:
            logging.debug('task content: ' + task.content)
            logging.debug('task datetine ' + str(task.due.datetime))

            if TODOIST_REMOVE_LINKS == "True" and 'http' in task.content:
                task_content = re.sub(r"http\S+", "", task.content)
            else:
                task_content = task.content
            try:
                if (task.due.datetime is not None):
                    #parsed_date=datetime.datetime.strptime(task.due.datetime,"%Y-%m-%dT%H:%M:%SZ")
                    parsed_date = parser.parse(task.due.datetime)
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


    ######################################################################################################
    #################            GOOGLE CALENDAR EVENTS PROCESSING      ##################################
    ######################################################################################################

    if GCAL_ENABLED == "True":
        gcal_calendar_ids = GCAL_CALENDAR_IDS.split(',')
        logging.debug(pformat(gcal_calendar_ids))

        for calendar in gcal_calendar_ids:
            gcal_events = get_gcal_events(calendar)
            for event in gcal_events:
                # TODO auto generated events from restaurant reservations are not available for some reason
                if ('summary' in event.keys()):
                    summary = event['summary']
                else:
                    summary = 'Private event'
                logging.debug(summary)
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
                    event_clean_title = "[C] " + "[" + hour + ":" + minute + "] " + summary
                else:
                    event_clean_title = "[C] " + summary

                add_element(days_between_dates.days,global_elements,event_clean_title,truncared_parsed_date)

    ######################################################################################################
    #################            ORDERING ELEMENTS      ##################################################
    ######################################################################################################

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
        date=today.strftime('%A,%d %B %Y').capitalize(),
        global_elements = global_elements
    )

######################################################################################################
#################            AUX FUNCTIONS       #####################################################
######################################################################################################

# Get tasks from Todoist 
def get_todoist_events():

    api = TodoistAPI(TODOIST_API_KEY)
    filter = TODOIST_FILTER
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
    
    return tasks

# Get events from Google Calendar
def get_gcal_events(calendar):
    # If modifying these scopes, delete the file token.json.
    SCOPES = ['https://www.googleapis.com/auth/calendar.readonly']

    # Tutorial seguido
    # https://developers.google.com/calendar/api/quickstart/python?hl=en

    creds = service_account.Credentials.from_service_account_file(
        'credentials.json',
        scopes=['https://www.googleapis.com/auth/calendar']
    )

    try:
        service = build('calendar', 'v3', credentials=creds)

        # Call the Calendar API
        now = datetime.datetime.utcnow().isoformat() + 'Z'  # 'Z' indicates UTC time
        print('Getting the upcoming 10 events')

        events_result = service.events().list(calendarId=calendar, timeMin=now,
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
        return []  # Devuelve una lista vacía en caso de error

    
# Add an element {title,datetime} to its section, that will be created if necessary
def add_element(section_index,list,element_title,element_datetime):

    # Every overdue element inside the same section
    if section_index < -1:
        section_index = -1
    
    # Only manage sections within the specied max days
    if section_index <= int(os.getenv('MAX_DAYS',7)):
    
        # If section already existed, recover elements
        if section_index in list:
            section = list[section_index]
            section_header = section['header']
            section_elements = section['elements']
        # Else, create section with the relevant header and the empty elements list
        else:
            section = {}
            
            match section_index:
                case -1:
                    section_header = os.getenv('APP_OVERDUE_LABEL',"Overdue")
                case 0:
                    section_header = os.getenv('APP_TODAY_LABEL',"Today")
                case 1:
                    section_header = os.getenv('APP_TOMORROW_LABEL',"Tomorrow")
                case _:
                    today = datetime.datetime.now()
                    next = today + datetime.timedelta(days = section_index)
                    if section_index < 7:
                        section_header = next.strftime('%A').capitalize()
                    else:
                        section_header = element_datetime.strftime('%A,%d %B').capitalize()

            section_elements = []
            section = {"header" : section_header}
        
        # Finally, add the item to the elements list, and update the section with them
        section_elements.append({"title":element_title,"datetime":element_datetime})
        section['elements'] = section_elements
        list[section_index] = section