from apiclient import discovery
from httplib2 import Http
from oauth2client.service_account import ServiceAccountCredentials
from oh_queue import app

DEFAULT_MESSAGE = "Office hours appointments start at the exact time and " + \
"last for no more than 10 minutes. If you want to meet for more time, please "+\
"schedule two appointments back-to-back.\n\nAppointments will always be with "+\
"a TA or tutor. If you wish to meet with a particular staff member, make " + \
"sure that their office hours overlap with this appointment and then invite " +\
"them directly to this event. Please do not use this system to schedule " + \
"appointments with course instructors."

def make_description(cost):
    return DEFAULT_MESSAGE + '\n\nCOST=' + str(cost)

def find_cost(description, fallback=50):
    for line in description.split('\n'):
        try:
            if line.startswith('COST='):
                return int(line.split('=')[1])
        except:
            pass
    return fallback

def event_json(event):
    return {
        'eventId': event['id'],
        'startTime': event['start']['dateTime'],
        'endTime': event['end']['dateTime'],
        'location': event['location'],
        'cost': find_cost(event['description']),
    }

def get_calendar_service():
    credentials = ServiceAccountCredentials.from_json_keyfile_dict(
        app.config.get('GAPI_SERVICE_ACCOUNT_JSON'),
        ['https://www.googleapis.com/auth/calendar']
    )
    http_auth = credentials.authorize(Http())
    return discovery.build('calendar', 'v3', http=http_auth)

service = get_calendar_service()
