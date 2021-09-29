"""

Submission for the RingCentral Small Business Hackathon 2021
The RingCentral Virtual Assistant
Sophia Capello & Curtis Harrison

"""

import threading
from ringcentral import SDK
import urllib
import datetime
from flask import Flask, render_template, request, session
import httplib2
import pickle
from dateutil.parser import isoparse
import oauth2client
from googleapiclient import discovery
from oauth2client import tools
from oauth2client import file
from oauth2client import client

from helper_functions import read_extension_phone_number, send_sms


# This is the API IDs information for both the RC API and the GC API
app = Flask(__name__)
app.secret_key = '###'

RINGCENTRAL_CLIENT_ID = '###'
RINGCENTRAL_CLIENT_SECRET = '###'
RINGCENTRAL_SERVER_URL = 'https://platform.devtest.ringcentral.com'
RINGCENTRAL_REDIRECT_URL = 'http://localhost:5000/oauth2callback'

CLIENT_ID = '###'
CLIENT_SECRET = '###'
SCOPE = 'https://www.googleapis.com/auth/calendar.readonly'
USER_AGENT = 'virtual_assistant'
OAUTH_DISPLAY_NAME = 'RC Virtual Assistant'

rcsdk = SDK(RINGCENTRAL_CLIENT_ID, RINGCENTRAL_CLIENT_SECRET, RINGCENTRAL_SERVER_URL)

#This is the log in flow for the RingCentral API
@app.route('/')
@app.route('/index')
def login():
    base_url = RINGCENTRAL_SERVER_URL + '/restapi/oauth/authorize'
    params = (
        ('response_type', 'code'),
        ('redirect_uri', RINGCENTRAL_REDIRECT_URL),
        ('client_id', RINGCENTRAL_CLIENT_ID),
        ('state', 'initialState')
    )
    auth_url = base_url + '?' + urllib.parse.urlencode(params)
    return render_template('index.html', authorize_uri=auth_url)

# Callback flow for OAuth2 with the RingCentral API
@app.route('/oauth2callback', methods=['GET'])
def oauth2callback():
    platform = rcsdk.platform()
    auth_code = request.values.get('code')
    platform.login('', '', '', auth_code, RINGCENTRAL_REDIRECT_URL)
    tokens = platform.auth().data()
    session['sessionAccessToken'] = tokens
    return render_template('main.html')

# Returns the About page
@app.route('/about', methods=['GET'])
def about():
    return render_template('About.html')

# Returns the Settings page
@app.route('/settings', methods=['GET'])
def settings():
    return render_template('Settings.html')

# Handles main operation of the application
@app.route('/home', methods=['GET'])
def callapi():
    platform = rcsdk.platform() # Connect to the RC API platform
    platform.auth().set_data(session['sessionAccessToken'])
    if platform.logged_in() == False:
        return login()
    api = request.values.get('api')
    # A "go" command means run the demo and send texts for the upcoming meetings
    if api == "go":
        resp = platform.get("/restapi/v1.0/account/~/extension")
        storage = oauth2client.file.Storage('credentials.json')
        credentials = storage.get()
        http = httplib2.Http()
        http = credentials.authorize(http)
        service = discovery.build('calendar', 'v3', http=http)
        now = datetime.datetime.utcnow().isoformat() + 'Z'  # 'Z' indicates UTC time
        events_result = service.events().list(calendarId='primary', timeMin=now,
                                              maxResults=10, singleEvents=True,
                                              orderBy='startTime').execute()
        events = events_result.get('items', [])

        if not events:
            print('No upcoming events found.')
        for event in events:
            if 'description' in event:
                number = event['description'].strip()
                if number.isnumeric():
                    print("Sending a text to", number)
                    send_sms(platform, read_extension_phone_number(platform), number, event['summary'] + " at " + event['location'] + " at " + isoparse(event["start"]["dateTime"]).strftime("%I:%M"))
        return render_template('main.html')
    # A 'google_login' command means trigger the Google Calendar API login in a new thread
    if api == "google_login":
        storage = oauth2client.file.Storage('credentials.json')
        credentials = storage.get()

        if credentials is None or credentials.invalid:
            flow = oauth2client.client.OAuth2WebServerFlow(
                client_id=CLIENT_ID,
                client_secret=CLIENT_SECRET,
                scope=SCOPE,
                user_agent=USER_AGENT,
                oauth_displayname=OAUTH_DISPLAY_NAME)
            flags = pickle.load(open("flags.dat", "rb"))
            x = threading.Thread(target=tools.run_flow, args=(flow, storage, flags), daemon=True)
            x.start()
        return render_template('main.html')
    else:
        return render_template('main.html')

# Run the logout flow
@app.route('/logout', methods=['GET'])
def logout():
    platform = rcsdk.platform()
    platform.auth().set_data(session['sessionAccessToken'])
    if platform.logged_in():
        platform.logout()
    session.pop('sessionAccessToken', None)
    return login()
