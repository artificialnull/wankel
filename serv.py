from peewee import *
from flask import Flask
from flask import request
from flask import g
from flask import session
from flask import render_template, url_for, redirect
from flask import send_from_directory
from flask_bcrypt import Bcrypt
from flask_login import LoginManager
import datetime
import flask_login
import json
import os

app = Flask(__name__)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'welcome'
app.config['SECRET_KEY'] = open('secret').read()
bcrypt = Bcrypt(app)

db = SqliteDatabase('db.db')

class Base(Model):
    class Meta:
        database = db

class User(Base):
    username = CharField(unique=True)
    password = CharField()
    def is_authenticated(self):
        return True
    def is_active(self):
        return True
    def is_anonymous(self):
        return False
    def get_id(self):
        return self.username
    def get_sorted_events(self):
        return list(reversed(sorted(self.events, key = lambda x: x.end_time)))

class Event(Base):
    start_time = DateTimeField()
    end_time = DateTimeField()
    text = CharField()
    user = ForeignKeyField(User, backref='events')

    def get_start_time(self):
        return self.start_time.strftime("%m/%d %H:%M")
    def get_end_time(self):
        return self.end_time.strftime("%m/%d %H:%M")
    def get_duration(self):
        td = self.end_time - self.start_time
        return ':'.join(str(td).split(':')[:2])

    @property
    def duration(self):
        return self.end_time - self.start_time

    @staticmethod
    def get_time_js_form(dt):
        ts = dt.strftime("new Date(%Y, %%s, %d, %H, %M, 0)")
        return (ts % str(dt.month - 1))

    def get_safe_description(self):
        txt = self.text.strip()
        txt = txt.replace('\n', ' ')
        return txt if len(txt) > 0 else '(no description provided)'

    def get_dict_form(self):
        return {
                'username': self.user.username,
                'style': '""',
                'tooltip': True,
                'duration': self.get_duration(),
                'start': self.get_start_time(),
                'end': self.get_end_time(),
                'desc': self.get_safe_description(),
                'start_js': Event.get_time_js_form(self.start_time),
                'end_js':   Event.get_time_js_form(self.end_time)
                }

    @staticmethod
    def get_empty_today_event(user, dt=None):
        return {
                'username': user.username,
                'style': '"opacity: 0;"',
                'start_js': Event.get_time_js_form(
                    (get_start_of_day() + datetime.timedelta(days=1)) if dt==None else dt),
                'end_js': Event.get_time_js_form(
                    (get_start_of_day() + datetime.timedelta(days=1)) if dt==None else dt)
                }

class Group(Base):
    name = CharField()
    description = CharField()
    password = CharField()
    members = ManyToManyField(User, backref='groups')
    admin = ForeignKeyField(User, backref='administrating')
    start_date = DateTimeField(default=datetime.datetime.now)

    def get_time_js_form(self):
        ts = self.start_date.strftime("new Date(%Y, %%s, %d, %H, %M, 0)")
        return (ts % str(self.start_date.month - 1))


@app.before_request
def before_request():
    g.db = db
    g.db.connect()

@app.after_request
def after_request(response):
    g.db.close()
    return response

def get_start_of_day():
    return datetime.datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)

def permission_error():
    return render_template('error.html', message="you can't see that")

@app.route('/')
@flask_login.login_required
def main():
    ev = Event.select().where(
            (Event.user == flask_login.current_user._get_current_object()) &
            (Event.end_time > get_start_of_day())
            )

    return render_template('index.html',
            events = flask_login.current_user.get_sorted_events()[:5],
            show_remove = True,
            show_more = True,
            ev_js = list([e.get_dict_form() for e in ev]) +
                [Event.get_empty_today_event(flask_login.current_user)],
            groups = flask_login.current_user.groups,
            sel = 'day'
            )

@app.route('/welcome')
def welcome():
    return render_template('welcome.html')

@app.route('/user/<username>')
@flask_login.login_required
def render_events(username):
    user = load_user(username)
    show_remove = False
    try:
        show_remove = (user.username == flask_login.current_user.username)
    except:
        pass
    intersect = [ group for group in user.groups if group in flask_login.current_user.groups ]
    if len(intersect) > 0 or show_remove:
        return render_template('user.html',
                username = user.username,
                events = user.get_sorted_events(),
                ev_js = [e.get_dict_form() for e in user.get_sorted_events()] +
                    [Event.get_empty_today_event(user)],
                show_remove = show_remove)
    return permission_error()

@app.route('/groups')
def render_groups():
    is_a_user = flask_login.current_user.is_authenticated
    all_groups = list(Group.select())
    groups = all_groups if not is_a_user else list(filter(
            lambda x: flask_login.current_user._get_current_object() not in x.members,
            all_groups))
    print([x.name for x in groups])
    return render_template('groups.html',
            groups = groups,
            is_a_user = is_a_user
            )

@app.route('/group/<int:group_id>')
@flask_login.login_required
def render_specific_group_without_hist_length(group_id):
    return render_specific_group(group_id, 'all')

@app.route('/group/<int:group_id>/<hist_length>')
@flask_login.login_required
def render_specific_group(group_id, hist_length):
    group = Group.get(Group.id == group_id)

    offset = int(request.args.get('offset', 0))

    hist_map = {
            'all': [
                group.start_date,
                get_start_of_day() + datetime.timedelta(days=1)
                ],
            'day': [
                get_start_of_day() + datetime.timedelta(days=offset),
                get_start_of_day() + datetime.timedelta(days=offset + 1)
                ],
            'week': [
                get_start_of_day() + datetime.timedelta(days=offset * 7 - 6),
                get_start_of_day() + datetime.timedelta(days=offset * 7 + 1)
                ],
            'month': [
                get_start_of_day() + datetime.timedelta(days=offset * 30 - 29),
                get_start_of_day() + datetime.timedelta(days=offset * 30 + 1),
                ]
            }
    if flask_login.current_user._get_current_object() not in group.members:
        return permission_error()
    all_js_events = []
    event_stats = {}
    totals = {
            'count': 0,
            'total_duration': datetime.timedelta(days=0)
            }
    for user in group.members:
        ev = Event.select().where(
                (Event.user == user) &
                (Event.end_time > hist_map.get(hist_length, hist_map.get('all'))[0]) &
                (Event.end_time < hist_map.get(hist_length, hist_map.get('all'))[1]) &
                (Event.start_time > group.start_date)
                )
        ue = [e.get_dict_form() for e in list(ev)]
        all_js_events += ue
        all_js_events.append(Event.get_empty_today_event(user,
            hist_map.get(hist_length, hist_map.get('all'))[1]))
        event_stats[user.id] = {
                'count': len(ev),
                'total_duration': sum([e.duration for e in ev], datetime.timedelta(seconds=0)),
                'avg_duration': str(
                    sum([e.duration for e in ev], datetime.timedelta(seconds=0)) / max(1, len(ev))
                    ).split('.')[0]
                }
        totals['count'] += event_stats[user.id]['count']
        totals['total_duration'] += event_stats[user.id]['total_duration']
    totals['avg_duration'] = str(totals['total_duration'] / max(1, totals['count'])).split('.')[0]
    event_stats[-1] = totals

    return render_template('group.html', group=group, ev_js=all_js_events, event_stats=event_stats,
            sel = (hist_length if hist_length in hist_map.keys() else 'all'),
            sorted_members = list(reversed(sorted(list(group.members), key = lambda x: (
                event_stats[x.id]['count'],
                event_stats[x.id]['total_duration'])
                ))),
            time_range = {
                'start_js': Event.get_time_js_form(hist_map.get(hist_length, hist_map.get('all'))[0]),
                'end_js': Event.get_time_js_form(hist_map.get(hist_length, hist_map.get('all'))[1])
                }
            )

@login_manager.user_loader
def load_user(user_id):
    return User.get(User.username == user_id)

@app.route('/signup', methods=['POST'])
def signup():
    print(request.get_json())
    signup_json = request.get_json()

    return json.dumps({'success': create_user(signup_json.get('name'), signup_json.get('pass'))})

def create_user(uname, pword):
    try:
        pw_hash = bcrypt.generate_password_hash(pword).decode('utf-8')
        user = User(username = uname, password = pw_hash)
        user.save()
        return authenticate_user(uname, pword)
    except:
        return False

@app.route('/logout')
@flask_login.login_required
def logout():
    flask_login.logout_user()
    return redirect('/')

@app.route('/login', methods=['POST'])
def login():
    login_json = request.get_json()
    print(request.args.get('next'))
    return json.dumps({'success': authenticate_user(login_json.get('name'), login_json.get('pass'))})

def authenticate_user(uname, pword):
    try:
        user = load_user(uname)
        if bcrypt.check_password_hash(user.password, pword):
            flask_login.login_user(user)
            return True
        return False
    except:
        return False

@app.route('/create-event', methods=['POST'])
@flask_login.login_required
def create_event():
    create_json = request.get_json()
    return json.dumps({'success': make_new_event(
        create_json.get('start'),
        create_json.get('end'),
        create_json.get('description', '')
        )})

@app.route('/remove-event', methods=['POST'])
@flask_login.login_required
def remove_event():
    remove_json = request.get_json()
    return json.dumps({'success': delete_existing_event(remove_json.get('id'))})

def timestr_to_datetime(time_str):
    current_time = datetime.datetime.now()
    return datetime.datetime.combine(current_time.date(), datetime.datetime.strptime(time_str, "%H:%M").time())

def make_new_event(start_str, end_str, description):
    if not start_str or not end_str:
        return False

    try:
        s_time = timestr_to_datetime(start_str)
        e_time = timestr_to_datetime(end_str)

        if s_time > datetime.datetime.now():
            s_time -= datetime.timedelta(days=1)

        if e_time > datetime.datetime.now():
            e_time -= datetime.timedelta(days=1)

        user = flask_login.current_user._get_current_object()
        for event in user.events:
            if event.start_time < e_time and s_time < event.end_time:
                return False
        event = Event(
                start_time = s_time,
                end_time = e_time,
                text = description,
                user = user)
        event.save()

        return True
    except KeyboardInterrupt:
        return False

def delete_existing_event(event_id):
    try:
        event_id = int(event_id)
        event = Event.get(Event.id == event_id)
        if event.user.id == flask_login.current_user.id:
            event.delete_instance()
            return True
    except:
        pass
    return False

@app.route('/create-group', methods=['POST'])
@flask_login.login_required
def create_group():
    create_json = request.get_json()
    succeeded = False
    try:
        if create_json.get('name') and create_json.get('pass'):
            print(create_json)
            group = Group(
                    name = create_json.get('name'),
                    description = create_json.get('description', ''),
                    password = bcrypt.generate_password_hash(create_json.get('pass')).decode('utf-8'),
                    admin = flask_login.current_user._get_current_object()
                    )
            group.save()
            succeeded = True
    except:
        pass
    return json.dumps({'success': succeeded})

@app.route('/join-group', methods=['POST'])
@flask_login.login_required
def join_group():
    join_json = request.get_json()
    succeeded = False
    try:
        if len(flask_login.current_user.administrating) >= 5:
            pass
        elif join_json.get('group_name') and join_json.get('group_pass'):
            group = Group.get(Group.name == join_json.get('group_name'))
            if flask_login.current_user._get_current_object() in group.members:
                pass
            elif bcrypt.check_password_hash(group.password, join_json.get('group_pass')):
                group.members.add(flask_login.current_user._get_current_object())
                succeeded = True
    except:
        pass
    return json.dumps({'success': succeeded})

@app.route('/leave-group', methods=['POST'])
@flask_login.login_required
def leave_group():
    leave_json = request.get_json()
    succeeded = False
    try:
        group = Group.get(Group.name == leave_json.get('name'))
        if flask_login.current_user._get_current_object() in group.members:
            group.members.remove(flask_login.current_user._get_current_object())
            succeeded = True
    except KeyboardInterrupt:
        pass
    return json.dumps({'success': succeeded})


@app.errorhandler(500)
def five_hundred(e):
    return render_template('error.html', message="internal server error"), 500
@app.errorhandler(404)
def four_oh_four(e):
    return render_template('error.html', message="page not found"), 404

@app.route('/favicon.ico')
def favicon():
    return send_from_directory(os.path.join(app.root_path, 'static'),
                               'favicon.ico', mimetype='image/vnd.microsoft.icon')

if __name__ == '__main__':
    with db:
        db.create_tables([User, Event, Group, Group.members.get_through_model()])
