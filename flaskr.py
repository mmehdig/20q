# -*- coding: utf-8 -*-
# all the imports
import sqlite3
from flask import Flask, request, session, g, redirect, url_for, \
    abort, render_template, flash, json, jsonify
from contextlib import closing
from pprint import pprint


class Question:
    """

    """

    def __init__(self, question, param, validator=None, source=None, answer=None, value_type=None):
        """
        """
        self.question = question
        self.param = param
        # grammar
        self.validator = validator
        # an address to data source to choose a guess from it.
        self.source = source
        # default answer (none)
        self.answer = answer

        if value_type is None:
            self.value_type = 'string'
        else:
            self.value_type = value_type

    def perception(self, guess):
        """
        :param tuple guess: tuple of (param, value), usually retrieved from session['guessed_param']
        """
        answer = self.answer
        param, value = guess

        if value is None:
            session['params'][param] = answer

    def is_valid(self, answer):
        """
        """
        if type(self.validator) == list:
            if answer not in self.validator:
                return False
            else:
                self.answer = answer
                return True
        elif type(self.validator) == dict:
            if answer not in self.validator:
                return False
            else:
                self.answer = self.validator[answer]
                return True
        elif callable(self.validator):
            if not self.validator(answer):
                return False
            else:
                self.answer = answer
                return True

        self.answer = answer
        return True

    def format_syntax(self, guess=None):
        """

        """
        if guess is None:
            guess = ""

        # definite syntax (a/an)
        guess_key = guess.replace('.', '_').replace('\'', '_').replace('"', '_')

        if self.question.find("%s") > -1 and guess is not None:
            if guess[0].lower() in ['a', 'e', 'i', 'o', 'u']:
                question = self.question.replace('/Def', 'an ')
            else:
                question = self.question.replace('/Def', 'a ')

            question = question % guess_key
        else:
            question = self.question

        # gender syntax
        is_female = True
        if session.get('params') and session.get('params').get('is_female', None) is not None:
            is_female = session['params']['is_female']

        # {male: female} dictionary
        mapping = {
            'actor': 'actress',
            'Actor': 'Actress',
            'he': 'she',
            'He': 'She',
            'him': 'her',
            'Him': 'Her',
        }

        # reverse the mapping dictionary if it's male:
        if not is_female:
            mapping = {v: k for k, v in mapping.items()}

        # dictionary which has every thing:
        dictionary = dict({v: v for k, v in mapping.items()}.items() + mapping.items())

        # new?
        if guess not in dictionary:
            dictionary[guess_key] = guess

        result = question.format(**dictionary)

        return result
    
    def dict_rep(self, guess=None):
        """
        """
        d = {
            "ask": self.format_syntax(guess),
            "param": self.param,
        }

        if type(self.validator) == list or type(self.validator) == dict:
            d['simple-grammar'] = self.validator

        return d


class YesNoQuestion(Question):
    """

    """

    def __init__(self, question, param, validator=None, source=None, answer=None, value_type=None):
        """

        """
        Question.__init__(self, question, param, validator, source, answer, value_type)

        self.validator = {
            "yes": "yes",
            "yes yes": "yes",
            "yes she is": "yes",
            "yes he is": "yes",
            "no": "no",
            "no no": "no",
            "no she is not": "no",
            "no he is not": "no",
            "no she's not": "no",
            "no he's not": "no",
            "no she isn't": "no",
            "no he isn't": "no",
            "I don't think so": "no",
        }

        if validator is not None:
            self.validator.update(validator)

    def perception(self, guess):
        """
        :param tuple guess: tuple of (param, value), usually retrieved from session['guessed_param']
        """
        answer = self.answer
        param, value = guess

        if answer == 'yes':
            if self.value_type == 'list':
                if session['params'].get(param, None) is None:
                    session['params'][param] = []

                session['params'][param].append(value)
            else:
                session['params'][param] = value
        elif answer == 'no':
            if param not in session['rejected_params']:
                session['rejected_params'][param] = []

            session['rejected_params'][param].append(value)
        else:
            if param not in session['unknown_params']:
                session['unknown_params'][param] = []

            session['unknown_params'][param].append(value)


# list of all questions with their parameters
list_of_questions = [
    YesNoQuestion(
        param="/people/person/profession",
        question="Is {she} /Def{%s}?",
        validator={"I don't know": "I don't know", "I do not know": "I don't know"},
        source=['output', '/people/person/profession', '/people/person/profession', 'name'],
        value_type='list'),
    YesNoQuestion(
        param="/people/person/nationality",
        question="Is {she} from {%s}?",
        validator={"I don't know": "I don't know", "I do not know": "I don't know"},
        source=['output', '/people/person/nationality', '/people/person/nationality', 'name']),
    YesNoQuestion(
        param="notable",
        question="Is {she} a notable {%s}?",
        validator={"I don't know": "I don't know"},
        source=['notable', 'name']),
    YesNoQuestion(
        param="/people/place_lived/location",
        question="Has {she} ever lived in {%s}?",
        validator={"I don't know": "I don't know", "I do not know": "I don't know"},
        source=['output', '/people/place_lived/location', '/people/place_lived/location', 'name'],
        value_type='list'),
]
dict_of_questions = {q.param: q for q in list_of_questions}
dict_of_questions['hint'] = Question(question="Please give me a hint, in one word!", param="hint")
dict_of_questions['name'] = YesNoQuestion(question="Is {she} '%s'?", param="name", source=['name'])


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


def kb_feature(topic_id, property_key):
    """
    topic_id:
        /en/barack_obama or /m/02mjmr

    property_key:
        /people/person/profession
        /people/person/nationality
    """
    import urllib
    service_url = 'https://www.googleapis.com/freebase/v1/topic'

    # person property
    # property_key = '/people/person/' + property_key

    params = {
        'key': free_base_api_key,
        'filter': property_key
    }

    url = service_url + topic_id + '?' + urllib.urlencode(params)
    response = urllib.urlopen(url).read()
    topic = json.loads(response)

    results = []
    if 'property' in topic and property_key in topic['property'] and 'values' in topic['property'][property_key]:
        results = [
            value['text']
            for value in topic['property'][property_key]['values']
            if topic['property'][property_key]['valuetype'] != "compound"
        ]

    return results


def kb_query(params, rejected_params):
    """
    """
    import urllib

    service_url = 'https://www.googleapis.com/freebase/v1/search'

    query = params.get('hint', '')

    is_female = params.get('is_female', '')
    name = params.get('name', '')
    notable = params.get('notable', '')
    origin = params.get('/people/person/nationality', '')
    location = params.get('/people/place_lived/location', '')
    profession = params.get('/people/person/profession', '')

    the_filter = None

    if profession:
        if type(profession) == list:
            for pro in profession:
                if not the_filter:
                    the_filter = 'type:"%s"' % pro
                else:
                    the_filter += ' /people/person/profession:"%s"' % pro
        else:
            the_filter = 'type:"%s"' % profession
    else:
        the_filter = 'type:/people/person'

    if origin:
        if type(origin) == list:
            for loc in origin:
                the_filter += ' /people/person/nationality:"%s"' % loc
        else:
            the_filter += ' /people/person/nationality:"%s"' % origin

    if location:
        if type(location) == list:
            for loc in location:
                the_filter += ' /people/place_lived/location:"%s"' % loc
        else:
            the_filter += ' /people/place_lived/location:"%s"' % location

    if notable:
        the_filter += ' notable:"%s"' % notable

    if name:
        the_filter += ' name:"%s"' % name

    if type(is_female) == bool:
        the_filter += ' /people/person/gender:"%s"' % ('female' if is_female else 'male')

    for key in rejected_params:
        for value in rejected_params[key]:
            the_filter += ' (not %s:"%s")' % (key, value)

    params = {
        'query': unicode(query).encode('utf-8'),
        'filter': unicode('(all ' + the_filter + ')').encode('utf-8'),
        'output': '(/people/person/nationality /people/person/profession /people/place_lived/location)',
        'key': unicode(free_base_api_key).encode('utf-8'),
        # 'limit': '5',
        'indent': 'true'
    }

    url = service_url + '?' + urllib.urlencode(params)
    response = urllib.urlopen(url).read()
    response = json.loads(response)
    print "#" * 10, 'parameters', "#" * 10
    pprint(params)
    print "#" * 10, 'query', "#" * 10
    pprint(url)
    print "#" * 10, 'response', "#" * 10
    pprint(response)
    print "#" * 30

    if "status" in response and response["status"] == "200 OK" and "result" in response and "hits" in response:
        if response['hits'] == 0 and len(response['result']) > 0:
            return response['result'], -1

        return response['result'], response['hits']
    else:
        # error
        return None, -1


# feature extraction
def feature_path_search(compound, path):
    """
    :param compound: a complex and nested data structure
    :type compound: dict, list, str
    :param path: a list which shows path to desire data placed in compound structure
    :type path: list
    """
    path = path[:]
    if type(compound) == dict:
        if path:
            next_key = path.pop(0)
            if next_key in compound:
                return feature_path_search(compound[next_key], path)
            else:
                # return empty:
                return None
        else:
            return compound
    elif type(compound) == list:
        feature_list = []
        for f in compound:
            item = feature_path_search(f, path)
            if type(item) == list:
                feature_list.extend(item)
            elif type(item) == str or type(item) == unicode:
                feature_list.append(item)

        return feature_list
    elif type(compound) == str or type(compound) == unicode:
        return compound


@app.route('/game', methods=['GET', 'POST'])
def game():
    """

    """

    return render_template('game.html')

@app.route('/dm', methods=['GET', 'POST'])
def dm():
    """

    """
    if not session.get('progress'):
        session['progress'] = -1

    if session['progress'] <= 0:
        session['params'] = {}
        session['rejected_params'] = {}
        session['unknown_params'] = {}

    if not session.get('params'):
        session['params'] = {}

    if not session.get('rejected_params'):
        session['rejected_params'] = {}

    if not session.get('unknown_params'):
        session['unknown_params'] = {}

    if request.method == 'POST':
        # update the param and progress:
        if len(request.form) > 0 and session['progress'] > 0:
            session['progress'] += 1
        elif session['progress'] <= 0:
            session['progress'] += 1

        if request.form.get('ready'):
            if request.form.get('ready') != "yes":
                # end the game
                session['progress'] == -1
                session.pop('params')
                return jsonify({
                    "progress": session['progress'],
                    "end": "Please come back whenever you are ready!"
                })
            elif session['progress'] == 0:
                session['progress'] = 1

        if request.form.get('is_female') in ['yes', 'no']:
            session['params']['is_female'] = True if request.form.get('is_female') == 'yes' else False

        for p in request.form:
            if p in ['is_female', 'ready']:
                continue

            if p in dict_of_questions:
                if dict_of_questions[p].is_valid(request.form.get(p)):
                    if session.get('guessed_param', None) is not None:
                        if session['guessed_param'][0] == p:
                            guess = session.get('guessed_param')
                            session.pop('guessed_param')
                            dict_of_questions[p].perception(guess)

            # wining scenario:
            if p == 'name' and session['params'].get(p, None) is not None:
                session.pop('progress')
                return jsonify({
                    "progress": 20,
                    "end": "Yooohooo! I won! I knew the answer was %s!" % session['params'].get(p)
                })

    if session['progress'] > 20:
        session.pop('progress')
        return jsonify({
            "progress": 20,
            "end": "The game is over! I guess you won!"
        })
    return next_command()


def next_command():
    """
    - end:
        if the progress was -1
    - ask:
        * ready?
            if the progress was 0
        * gender
            if the gender was not defined
        * ask next unanswered question which you can guess an answer for it.

        * if there was no question or guess announce that user won the game.

    """
    import random

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
            "simple-grammar": {"yes": "yes",
                               "yes I am": "yes",
                               "yes I'm ready": "yes",
                               "yes I am ready": "yes",
                               "yes yes": "yes",
                               "no": "no",
                               "no no": "no",
                               }
        })
    else:
        # gender
        if session['params'].get('is_female', None) is None:
            return jsonify({
                "progress": session['progress'],
                "ask": "Is this person a woman?",
                "param": "is_female",
                "simple-grammar": {
                    "yes": "yes",
                    "no": "no",
                    "yes yes": "yes",
                    "no no": "no",
                    "no he is not": "no",
                    "yes she is": "yes",
                }
            })
        else:
            if session.get('rejected_params', None) is None:
                session['rejected_params'] = {}

            if session.get('unknown_params', None) is None:
                session['unknown_params'] = {}

            # ask kb
            results, count = kb_query(session['params'], session['rejected_params'])
            results_count = len(results)

            if results is None:
                # error handling with dead end situation:
                session.pop("progress")
                return jsonify({
                    "progress": 20,
                    "end": "I'm totally lost!"
                })

            # if the estimate
            if count < 0 < results_count:
                count = 21

            # if you cannot guess in remaining steps skip this part
            if count > 17 - session['progress']:
                questions = list_of_questions[:]
                random.shuffle(questions)
                for question in questions:
                    param_key = question.param
                    feature_key = question.source

                    # if the parameter was set before and this question should only be asked once,
                    # then go to next question
                    if question.value_type != 'list':
                        if session['params'].get(param_key, None) is not None:
                            continue

                    if feature_key is None:
                        # no feature = no guessing = this question doesn't need any guessing
                        next_response = question.dict_rep()
                        next_response["progress"] = session["progress"]
                        return jsonify(next_response)

                    # find available features to guess on this question
                    features = []
                    guess = None
                    for result in results:
                        if type(feature_key) == str:
                            result_features = kb_feature(result['id'], feature_key)
                        elif type(feature_key) == list:
                            # path to the key ['notable', 'name']
                            result_features = feature_path_search(result, feature_key)

                        if type(result_features) == list:
                            features.extend(result_features)
                        elif type(result_features) == str or type(result_features) == unicode:
                            features.append(result_features)

                    # unique values?
                    # features = set(features)
                    # features = list(features)

                    # exclude those possible guesses which have been rejected before:
                    if session['rejected_params'].get(param_key):
                        for exclude_value in session['rejected_params'][param_key]:
                            try:
                                while True:
                                    features.remove(exclude_value)
                            except ValueError:
                                continue

                    # exclude those possible guesses which have been didn't know before:
                    if session['unknown_params'].get(param_key):
                        for exclude_value in session['unknown_params'][param_key]:
                            try:
                                while True:
                                    features.remove(exclude_value)
                            except ValueError:
                                continue

                    # exclude those guesses which have been asked and you know it's a correct answer:
                    if question.value_type == 'list':
                        if session['params'].get(param_key):
                            for exclude_value in session['params'][param_key]:
                                try:
                                    while True:
                                        features.remove(exclude_value)
                                except ValueError:
                                    continue

                    n_possibilities = len(features)

                    # if there is opportunity to guess, choose one randomly as guess:
                    if n_possibilities:
                        guess = features[random.randint(0, n_possibilities-1)]
                    else:
                        # if you have no clue what to ask, then pass this question:
                        continue

                    # if you reach here it means you have a guess and you know what to ask:
                    session['guessed_param'] = (param_key, guess)
                    next_response = question.dict_rep(guess)
                    next_response["progress"] = session["progress"]
                    return jsonify(next_response)

                # if you reach this point with out any questions, you should ask for a hint:
                if session['params'].get('hint', None) is None:
                    session['guessed_param'] = ('hint', None)
                    next_response = dict_of_questions['hint'].dict_rep()
                    next_response["progress"] = session["progress"]
                    return jsonify(next_response)

            if results_count > 0:
                # if you can guess the answer don't waste the time!
                session['guessed_param'] = ("name", results[random.randint(0, results_count - 1)]["name"])
                next_response = dict_of_questions['name'].dict_rep(session['guessed_param'][1])
                next_response["progress"] = session["progress"]
                return jsonify(next_response)
            else:
                session.pop("progress")
                return jsonify({
                    "progress": 20,
                    "end": "I have no idea! You won!"
                })

    # impossible error:
    return jsonify({
        "error": "unknown error?",
    })

if __name__ == '__main__':
    app.run('0.0.0.0', debug=True, port=8100, ssl_context='adhoc')