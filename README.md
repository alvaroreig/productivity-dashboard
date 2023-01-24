# productivity-dashboard

Just a simple Python/Flask app that retrieves tasks (from Todoist) and events (from Google Calendar) and displays them in a simple view designed for a Kindle Touch.

Settings are configured in the .env file (check .env-sample).

![](resources/img/kindle.jpg)

![](resources/img/index.png)

The elements will show a [C] or a [T] prefix to indicate if the element is a task or a calendar event

## Todoist settings

* Enable the integration with TODOIST_ENABLED and TODOIST_API_KEY
* Customize the filter (TODOIST_FILTER) used in the API call.
* Remove links to avoid clutter with TODOIST_REMOVE_LINKS

## Google Calendar settings

* Enable the integration with GCAL_ENABLED and specify your calendars in GCAL_CALENDARS_IDS, GCAL_DEFAULT_CALENDAR_ID
* The integration works with GOOGLE_CALENDAR_AUTH_PROFILE=service_account
* Follow the instrucctions in https://github.com/spatie/laravel-google-calendar#how-to-obtain-the-credentials-to-communicate-with-google-calendar
* Store your JSON credentials file in storage/app/google-calendar/service-account-credentials.json

## Group by date

The elements (events and/or taks)  are grouped in for type of elements:

- Overdue elements.
- Elements due today.
- Elements due tomorrow
- The rest

You can customize (localize) the keywords applied to every category of elements:

* APP_OVERDUE_LABEL=Retrasado
* APP_TODAY_LABEL=Hoy
* APP_TOMORROW_LABEL=Mañana

### Other

* Clicking on the header will refresh the view.

## Tested Devices

I use this app with a jailbroken Kindle Touch + KUAL + Weblaunch.

## Troubleshooting / Tips

- In previous versions the page auto refreshed every X seconds. It no longers does so because it froze after some days and, anyway, I didn't want to leave the backend on 24x7. I refresh it manually clicking the header


## TODO

- Make the elements clickable so todoist tasks can be completed.
- Prettier UI
- Propper localization
