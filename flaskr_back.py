# -*- coding: utf-8 -*-
# all the imports
import sqlite3
from flask import Flask, request, session, g, redirect, url_for, \
    abort, render_template, flash, json, jsonify
from contextlib import closing
from pprint import pprint

# configuration
DATABASE = 'flaskr.db'
DEBUG = True
SECRET_KEY = '4056000'
USERNAME = 'admin'
PASSWORD = 'default'
free_base_api_key = 'AIzaSyCNi0NvH5964WWfS80XrRmn9LzJCpTpWdg'

# create our little application :)
app = Flask(__name__)
app.config.from_object(__name__)
#app.config.from_envvar('FLASKR_SETTINGS', silent=True)


def connect_db():
    return sqlite3.connect(app.config['DATABASE'])


def init_db():
    with closing(connect_db()) as db:
        with app.open_resource('schema.sql', mode='r') as f:
            db.cursor().executescript(f.read())
        db.commit()


@app.before_request
def before_request():
    g.db = connect_db()


@app.teardown_request
def teardown_request(exception):
    db = getattr(g, 'db', None)
    if db is not None:
        db.close()


@app.route('/entries')
def show_entries():
    cur = g.db.execute('SELECT id, title, text FROM entries ORDER BY id desc')
    entries = [dict(id=row[0], title=row[1], text=row[2]) for row in cur.fetchall()]
    return render_template('show_entries.html', entries=entries)


@app.route('/entries/add', methods=['POST'])
def add_entry():
    if not session.get('logged_in'):
        abort(401)
    if len(request.form['title']) < 128 and len(request.form['text']) < 255:
        g.db.execute('insert into entries (title, text) values (?, ?)',
                     [request.form['title'], request.form['text']])
        g.db.commit()
        flash('New entry was successfully posted')
    else:
        flash('Failed: Only small texts and titles are acceptable')
    return redirect(url_for('show_entries'))


@app.route('/login', methods=['GET', 'POST'])
def login():
    error = None
    if request.method == 'POST':
        if request.form['username'] != app.config['USERNAME']:
            error = 'Invalid username'
        elif request.form['password'] != app.config['PASSWORD']:
            error = 'Invalid password'
        else:
            session['logged_in'] = True
            flash('You were logged in')
            return redirect(url_for('show_entries'))
    return render_template('login.html', error=error)


@app.route('/logout')
def logout():
    session.pop('logged_in', None)
    flash('You were logged out')
    return redirect(url_for('show_entries'))


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/listener')
def listener():
    return render_template('listener.html')


@app.route('/about')
def about():
    return render_template('about.html')


@app.route('/fb-question', methods=['GET', 'POST'])
def fb_question():
    import urllib
    service_url = 'https://www.googleapis.com/freebase/v1/search'

    api_key = 'AIzaSyCNi0NvH5964WWfS80XrRmn9LzJCpTpWdg'
    # query = request.args.get('query', '')

    notable = request.args.get('notable', '')

    the_filter = 'type:/people/person'

    if notable:
        the_filter += ' notable:' + notable

    params = {
        'query': '',
        'filter': '(all ' + the_filter + ')',
        'key': api_key
    }

    pprint(params)
    url = service_url + '?' + urllib.urlencode(params)
    response = urllib.urlopen(url).read()

    try:
        response = json.loads(response)
        if 'result' in response:
            notables_1 = [result['notable']['name'] for result in response['result']]
            notables_0 = [notable.split(' ')[-1] for notable in notables_1]
            if notable and notable in notables_0:
                pass
        return jsonify(response)
    except:
        return jsonify({'error': 'invalid response'})


@app.route('/fb-search', methods=['GET', 'POST'])
def fb_search():
    """
    $.getJSON('http://localhost:5000/fb-search',{"notable":"football player", "is_from":"sweden", "is_female":"yes"}, function(data){console.log(data)})
    """
    import urllib
    service_url = 'https://www.googleapis.com/freebase/v1/search'

    api_key = 'AIzaSyCNi0NvH5964WWfS80XrRmn9LzJCpTpWdg'
    query = request.args.get('query', '')

    name = request.args.get('name', '')
    is_from = request.args.get('is_from', '')
    member_of = request.args.get('member_of', '')
    # child_of = request.args.get('child_of', '')
    practitioner_of = request.args.get('practitioner_of', '')
    notable = request.args.get('notable', '')
    is_female = request.args.get('is_female', '')

    the_filter = 'type:/people/person'

    if is_from:
        the_filter += ' origin:"%s"' % is_from

    if member_of:
        the_filter += ' member_of:"%s"' % member_of

    # if child_of:
    #     the_filter += ' parent:"%s"' % child_of

    if practitioner_of:
        the_filter += ' practitioner_of:"%s"' % practitioner_of

    if notable:
        the_filter += ' notable:"%s"' % notable

    if name:
        the_filter += ' name:"%s"' % name

    if is_female:
        the_filter += ' category:"%s"' % ('female' if is_female == 'yes' else 'male')


    params = {
        'query': query,
        'filter': '(all ' + the_filter + ')',
        'key': api_key
    }

    pprint(params)
    url = service_url + '?' + urllib.urlencode(params)
    response = urllib.urlopen(url).read()

    try:
        response = json.loads(response)
        return jsonify(response)
    except:
        return jsonify({'error': 'invalid response'})


@app.route('/fb-topic', methods=['GET', 'POST'])
def fb_topic():
    import urllib
    service_url = 'https://www.googleapis.com/freebase/v1/topic'

    api_key = 'AIzaSyCNi0NvH5964WWfS80XrRmn9LzJCpTpWdg'
    topic_id = request.args.get('topic', '')

    params = {
        'key': api_key,
        # 'filter': '/people/person'
    }

    url = service_url + topic_id + '?' + urllib.urlencode(params)
    response = urllib.urlopen(url).read()

    try:
        topic = json.loads(response)
        pprint(topic)
        return jsonify(topic)
    except:
        return jsonify({'error': 'invalid response'})


def get_person_feature(topic_id, property_key):
    """
    topic_id:
        /en/barack_obama or /m/02mjmr

    property_key:
        profession
        children
        sibling_s
        spouse_s
        date_of_birth
        places_lived
        height_meters
    """
    import urllib
    service_url = 'https://www.googleapis.com/freebase/v1/topic'
    property_key = '/people/person/' + property_key

    params = {
        'key': free_base_api_key,
        'filter': property_key
    }

    url = service_url + topic_id + '?' + urllib.urlencode(params)
    response = urllib.urlopen(url).read()
    topic = json.loads(response)

    results = []
    if 'property' in topic and property_key in topic['property'] and 'values' in topic['property'][property_key]:
        results = [value['text'] for value in topic['property'][property_key]['values']]

    return results


@app.route('/drive/auth')
def drive_auth():
    import httplib2
    import pprint

    from apiclient.discovery import build
    from apiclient.http import MediaFileUpload
    from oauth2client.client import OAuth2WebServerFlow

    # Copy your credentials from the console
    client_id = '1014912252116-7ld479oqr9h2fv7chho4g6f2utpa8n1l.apps.googleusercontent.com'
    client_secret = '_M9T9th-0pO1Xwm7ZHlkUSZZ'

    # Check https://developers.google.com/drive/scopes for all available scopes
    oauth_scope = 'https://www.googleapis.com/auth/drive'

    # Redirect URI for installed apps
    redirect_uri = 'http://localhost:5000/drive/auth'

    # Run through the OAuth flow and retrieve credentials
    flow = OAuth2WebServerFlow(client_id, client_secret, oauth_scope, redirect_uri)
    authorize_url = flow.step1_get_authorize_url()

    code = request.args.get('code', '')
    if not code:
        return redirect(authorize_url)

    # Path to the file to upload
    file_name = 'document1.txt'

    credentials = flow.step2_exchange(code)

    # Create an httplib2.Http object and authorize it with our credentials
    http = httplib2.Http()
    http = credentials.authorize(http)

    drive_service = build('drive', 'v2', http=http)

    # Insert a file
    media_body = MediaFileUpload(file_name, mimetype='text/plain', resumable=True)
    body = {
        'title': 'test 2',
        'description': 'A test document',
        'mimeType': 'text/plain'
    }

    f = drive_service.files().insert(body=body, media_body=media_body).execute()
    pprint.pprint(f)

    return "text"

@app.route('/game')
def game():
    """

    """
    return render_template('game.html')

@app.route('/dm', methods=['GET', 'POST'])
def dm():
    """


    """
    if not session.get('progress'):
        session['progress'] = 0
    if not session.get('params'):
        session['params'] = {}

    if request.method == 'POST':
        # update the param and progress:
        if request.form.get('ready'):
            print 'ready', request.form['ready']

            if request.form.get('ready') != "yes":
                # end the game
                session.pop('progress')
                session.pop('params')

        if request.form.get('is_female') and request.form.get('is_female') in ['yes', 'no']:
            print 'is_female', request.form['is_female']
            session['params']['is_female'] = True if request.form.get('is_female') == 'yes' else False

    return next_command()


def next_command():
    """
    - end:

    - ask:
        # initial
        /ready?

        # gender
        /is_female

        # notability
        /is_actor
            /film
            /character
        /is_politician
            /member_of
        /is_musician
            /album
            /track
        /is_athlete
            /sport
        /notable_for

        # alive?
        /is_alive
        #country
        /nationality

        1. gender
        2. alive
        3.
    """
    if session['progress'] == -1:
        return jsonify({
            "progress": session['progress'],
            "end": "Please come back whenever you are ready!"
        })
    elif session['progress'] == 0:
        # initial question
        return jsonify({
            "progress": 0,
            "ask": "Are you ready for this game?",
            "param": "ready",
            "simple-grammar": ["yes", "no"]
        })
    elif session['params']:

        # gender
        if session['params'].get('is_female', None) is  None:
            return jsonify({
                "progress": session['progress'],
                "ask": "Is this person a woman?",
                "param": "is_female",
                "simple-grammar": ["yes", "no"]
            })
        else:
            # notability
            if session['params']['is_female']:
                is_female = True
            else:
                is_female = False

            if session['params'].get('notable', None) is None:
                # is_actor

                return jsonify({
                    "progress": session['progress'],
                    "ask": "Is he an actor?",
                    "param": "is_actor",
                    "simple-grammar": ["yes", "no"]
                })
                return jsonify({
                    "progress": session['progress'],
                    "ask": "Is she an actress?",
                    "param": "is_actor",
                    "simple-grammar": ["yes", "no"]
                })

    return jsonify({
        "error": "unknown",
    })



if __name__ == '__main__':
    app.run('0.0.0.0', debug=True, port=8100, ssl_context='adhoc')