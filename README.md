# productivity-dashboard

Just a simple PHP/Laravel app that retrieves tasks (from Todoist) and events (from Google Calendar) and displays them in a simple view designed for a Kindle Touch.

All the settings are configured in the .env file (check .env-sample).

![](resources/img/kindle.jpg)

![](resources/img/index.png)

The elements will show a [C] or a [T] prefix to indicate if the element is a task or a calendar event

## Todoist settings

* Enable the integration with TODOIST_ENABLED and TODOIST_API_KEY
* Customize the filter (TODOIST_FILTER) used in the API call.
* Add the hour to taks with hour (TODOIST_ADD_HOUR_TO_TASK)
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

You can customize (localize) the header mask (APP_DATE_HEADER_MASK) and the keywords applied to every category of elements:

* APP_LOCALE_OVERDUE
* APP_LOCALE_TODAY
* APP_LOCALE_TOMORROW
* APP_LOCALE_OTHERS_MASK

### Other

* The view will autorefresh every 1800 seconds. You can change that setting in REFRESH_RATE_IN_SECONDS.
* Every element will be truncated if the string is longer than ELEMENT_MAX_LENGHT.
* Clicking on the header will refresh the view.

## Tested Devices

I use this app with a jailbroken Kindle Touch + KUAL + Weblaunch.

## Troubleshooting / Tips

* In my experience, when REFRESH_RATE_IN_SECONDS the WebLaunch browser crashes pretty often. I use REFRESH_RATE_IN_SECONDS=3600 and I have to manually relaunch the dashbord every couple of days or so.


## TODO

- Make the elements clickable so todoist tasks can be completed.
- Prettier UI
- Propper localization
