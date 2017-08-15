import os
basedir = os.path.abspath(os.path.dirname(__file__))

ENV = os.getenv('OH_QUEUE_ENV', 'dev')

if ENV in ('dev', 'staging'):
    DEBUG = True
elif ENV == 'prod':
    DEBUG = False

if ENV == 'dev':
    SECRET_KEY = 'dev'
    SQLALCHEMY_DATABASE_URI = 'sqlite:///' + os.path.join(basedir, 'app.db')
else:
    SECRET_KEY = os.getenv('SECRET_KEY')
    SQLALCHEMY_DATABASE_URI = os.getenv('DATABASE_URL').replace('mysql://', 'mysql+pymysql://')

SQLALCHEMY_TRACK_MODIFICATIONS = False
DATABASE_CONNECT_OPTIONS = {}

LOCAL_TIMEZONE = os.getenv('TIMEZONE', 'US/Pacific')

OK_KEY = os.getenv('OK_KEY', 'oh-queue')
OK_SECRET = os.getenv('OK_SECRET', 'M05dGkt1xe1a1OJvG06YRITzAqQQvEa')

OK_SERVER_URL = os.getenv('OK_DEPLOYMENT', 'https://okpy.org')

COURSE_OFFERING = os.getenv('COURSE_OFFERING', 'ok/test/su16')
COURSE_NAME = os.getenv('COURSE_NAME', 'OK')


GOOGLE_CALENDAR_ID = 'berkeley.edu_nkbhm5av5g714be1tgpg0t6bes@group.calendar.google.com'
# This account should have write access to the calendar.
with open('service-account.json', 'r') as f:
    GAPI_SERVICE_ACCOUNT_JSON = json.loads(f.read())
