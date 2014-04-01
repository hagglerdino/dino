import os
from flask import Flask, request, session, g, redirect, url_for, abort, \
     render_template, flash
from flask import Flask
from flask.ext.login import login_user, logout_user, current_user, login_required, LoginManager
from flask.ext.openid import OpenID
from flask.ext.babel import Babel, lazy_gettext
import pusher
import yaml
from apscheduler.scheduler import Scheduler
from flask.ext.sqlalchemy import SQLAlchemy
from etl import AmazonCrawler

'''Flask Extensions:

1. Flask-WTF - Forms
2. OpenID/Flask-Login - Auth
3. SqlAlchemy

'''

config = yaml.load(open('credentials.yml', "r"))
print config
#Flask app
app = Flask(__name__)

#Flask-WTF settings
CSRF_ENABLED     = config['flask']['csrf']
SECRET_KEY       = config['flask']['secret_key']

#OpenId
lm               = LoginManager()
lm.init_app(app)
lm.login_view    = 'login'
lm.login_message = lazy_gettext('Please log in to access this page.')
oid              = OpenID(app, os.path.join('.', 'tmp'))
OPENID_PROVIDERS = [ { 'name': 'Google', 'url': 'https://www.google.com/accounts/o8/id' },
                   { 'name': 'Yahoo', 'url': 'https://me.yahoo.com' }]

db = SQLAlchemy(app)

#Pusher
pushr = pusher.Pusher(
    app_id       = config['pusher']['appid'],
    key          = config['pusher']['app_key'],
    secret       = config['pusher']['app_secret']
)
CHANNELPFX       = config['pusher']['channelpfx']


#Load default config and override config from an environment variable
app.config.update(dict(
    SQLALCHEMY_DATABASE_URI = config['sqlite']['URI'],
    DEBUG        = config['flask']['DEBUG']),
    SECRET_KEY   = 'some-key-nobody-will-guess'
    )

# Override settings from env variable
app.config.from_envvar('FLASKR_SETTINGS', silent=True)
babel = Babel(app)

#Singleton tracker
sched = Scheduler()
azcrawler = AmazonCrawler(config['amazon'])


def track(tracker):
  #tracker.push_updates()
  job = sched.add_interval_job(tracker.push_updates, seconds=3)
