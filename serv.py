from peewee import *
from flask import Flask
from flask import request
from flask import g
from flask import session
from flask import render_template, url_for
from flask_bcrypt import Bcrypt
from flask_login import LoginManager
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

class Event(Base):
    time = IntegerField()
    duration = IntegerField()
    text = CharField()
    user = ForeignKeyField(User, backref='events')

@app.before_request
def before_request():
    g.db = db
    g.db.connect()

@app.after_request
def after_request(response):
    g.db.close()
    return response

@app.route('/')
@flask_login.login_required
def main():
    return render_template('index.html')

@app.route('/welcome')
def welcome():
    return render_template('welcome.html')

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
        return True
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

@app.route('/what-the-heck')
@flask_login.login_required
def wth():
    return "yep its you, " + flask_login.current_user.username


if __name__ == '__main__':
    with db:
        db.create_tables([User, Event])
