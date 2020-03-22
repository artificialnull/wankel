from peewee import *
from flask import Flask
from flask import request
from flask import g
from flask import session
from flask import render_template, url_for
from flask_bcrypt import Bcrypt
from flask_login import LoginManager
import datetime
import flask_login
import json

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

    def get_time_js_form(dt):
        ts = dt.strftime("new Date(%Y, %%s, %d, %H, %M, 0)")
        return (ts % str(dt.month - 1))

    def create_tooltip(self):
        return ('''
            "<div class=\\"tooltip\\"><p><b>duration: %s</b></p><p>%s - %s</p><p>%s</p></div>"
        ''' % (self.get_duration(), self.get_start_time(), self.get_end_time(), self.text))

    def get_js_form(self):
        return ','.join(['"' + self.user.username + '"', '""', '', self.create_tooltip(),
            Event.get_time_js_form(self.start_time),
            Event.get_time_js_form(self.end_time)])

    @staticmethod
    def get_empty_today_event(user):
        return ','.join(['"' + user.username + '"', '""', '"opacity: 0;"', '""',
            Event.get_time_js_form(get_start_of_day()),
            Event.get_time_js_form(get_start_of_day())])

class Group(Base):
    name = CharField()
    description = CharField()
    password = CharField()
    members = ManyToManyField(User, backref='groups')
    admin = ForeignKeyField(User, backref='administrating')
    start_date = DateTimeField(default=datetime.datetime.now)


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

@app.route('/')
@flask_login.login_required
def main():
    ev = Event.select().where(
            (Event.user == flask_login.current_user._get_current_object()) &
            (Event.end_time > get_start_of_day())
            )

    return render_template('index.html',
            events = flask_login.current_user.get_sorted_events()[:5],
            log_events = [e.get_js_form() for e in ev],
            groups = flask_login.current_user.groups
            )

@app.route('/welcome')
def welcome():
    return render_template('welcome.html')

@app.route('/events/<username>')
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
        return render_template('more-events.html',
                username = user.username,
                events = user.get_sorted_events(),
                show_remove = show_remove)
    return render_template('perm-error.html')

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
    hist_map = {
            'all': group.start_date,
            'day': get_start_of_day(),
            'week': get_start_of_day() - datetime.timedelta(days=6),
            'month': get_start_of_day() - datetime.timedelta(days=29)
            }

    if flask_login.current_user._get_current_object() not in group.members:
        return render_template('perm-error.html')
    all_events = []
    for user in group.members:
        ev = Event.select().where(
                (Event.user == user) &
                (Event.end_time > hist_map.get(hist_length, hist_map.get('all'))) &
                (Event.start_time > group.start_date)
                )
        all_events += list([e.get_js_form() for e in ev])
        all_events.append(Event.get_empty_today_event(user))
    return render_template('specific-group.html', group=group, events=all_events,
            sel = (hist_length if hist_length in hist_map.keys() else 'all')
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
        create_json.get('description')
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

        if s_time > e_time:
            s_time -= datetime.timedelta(days=1)

        user = flask_login.current_user._get_current_object()
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
    create_json = request.get_json()
    succeeded = False
    try:
        if create_json.get('group_name') and create_json.get('group_pass'):
            group = Group.get(Group.name == create_json.get('group_name'))
            if bcrypt.check_password_hash(group.password, create_json.get('group_pass')):
                group.members.add(flask_login.current_user._get_current_object())
                succeeded = True
    except:
        pass
    return json.dumps({'success': succeeded})

if __name__ == '__main__':
    with db:
        db.create_tables([User, Event, Group, Group.members.get_through_model()])
