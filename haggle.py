#from flask import current_app as app
from init import app, lm, oid, pushr, OPENID_PROVIDERS, azcrawler
from model import  get_db, Product, User, DinoUpdate, Subscription
from flask.ext.login import login_user, logout_user, current_user, login_required, LoginManager
from flask.ext import  babel
from flask import request, session, g, redirect, url_for, abort, render_template, flash
from forms import LoginForm
from datetime import datetime
import json
from flask.ext.babel import Babel, lazy_gettext, to_user_timezone
import pytz
import humanize
from etl import utils


@app.template_filter()
def timesince(dt, default="just now"):
    """
    Returns string representing "time since" e.g.
    3 days ago, 5 hours ago etc.
    """

    now = to_user_timezone(datetime.now())
    diff = now - dt
    periods = (
        (diff.days / 365, "year", "years"),
        (diff.days / 30, "month", "months"),
        (diff.days / 7, "week", "weeks"),
        (diff.days, "day", "days"),
        (diff.seconds / 3600, "hour", "hours"),
        (diff.seconds / 60, "minute", "minutes"),
    )

    for period, singular, plural in periods:
        if period:
            return "%d %s ago" % (period, singular if period == 1 else plural)

    return default


#Needs to get out from here into an API module
@app.route('/hack/<int:pid>/<float:newprice>')
def hack(pid, newprice):
    print "Updating prod id %s to price %s"%(pid, newprice)
    db = get_db()
    existing = Product.query.filter(Product.id == pid).first()
    if existing:
       existing.prev_price = existing.curr_price
       existing.curr_price = newprice
       if existing.lowest_price > newprice:
            existing.lowest_price = newprice
       db.session.add(existing)
       db.session.commit()
       t.updates(updated_prods={pid: datetime.now()})  
       return json.dumps({'result': 'success', 'prod': pid})
    return json.dumps({'result': 'Nothing to update'})


#API
#Needs to get out from here into an blueprint module
@app.route('/prods')
def prods():
    pids = request.args.get("pids",'').split(",")
    if pids:
        pids = [int(x) for x in pids]
    allprods = Product.query.all()
    if pids:
        return json.dumps(dict((p.id, p.title) for p in allprods if p.id in pids))
    return json.dumps(dict((p.id, p.title) for p in allprods))


#API
#Needs to get out from here into a blueprint module
@app.route('/subs')
def subs():
    uids = request.args.get("uids",'').split(",")
    users = request.args.get("users", '').split(",")

    if (not uids or not uids[0]) and (not users or not users[0]):
        return json.dumps({"result": "No updates for you"})

    if users:
        uids = [User.query.filter(User.nickname == username).first().id for username in users]

    if uids:
        uids = [int(x) for x in uids]
    allsubs = Subscription.query.all()
    if uids:
        return json.dumps([(s.prod_id, s.user_id) for s in allsubs if s.user_id in uids])
    return json.dumps([s.prod_id for s in allsubs])


#API/test
#Needs to get out from here into a blueprint module
@app.route('/fakecrawl')
def fakecrawl():
    pids =      request.args.get("pids",'').split(",")
    prices =    request.args.get("prices",'').split(",")
    goup =      request.args.get("goup")
    godown =    request.args.get("godown")
    gotoodown = request.args.get("gotoodown")

    GOUP, GODOWN, GOTOODOWN = 1.1, 0.9, 0.6

    if not pids or not pids[0]:
        return json.dumps({"result": "No updates for you"})

    if prices and prices[0]:
        for pid, price in zip(pids, prices):
            hack(int(pid), float(price))
        return json.dumps(dict((pid,price) for pid, price in zip(pids, prices)))

    db = get_db()
    mul = 1
    if godown:
        mul = GODOWN
    elif gotoodown:
        mul = GOTOODOWN
    elif goup:
        mul = GOUP

    if godown or goup or gotoodown:
        updates = {}
        for p in pids:
            existing = Product.query.filter(Product.id == int(p)).first()
            print "Product found ", existing
            if existing:
                newprice = existing.curr_price * mul
                existing.prev_price = existing.curr_price
                existing.curr_price = newprice
                if existing.lowest_price is None or existing.lowest_price == 0.0:
                    existing.lowest_price = min(existing.prev_price, existing.curr_price)
                if existing.lowest_price > newprice:
                    existing.lowest_price = newprice
                print "updated price ", newprice
                try:
                        db.session.add(existing)
                except Exception, e:
                        print str(e)
                updates[int(p)] = newprice
                print "updated price fpr prod"
        print "Committing changes ", updates
        db.session.commit()
        t.updates(updated_prods=updates)
        return json.dumps(updates)

    return json.dumps({"result": "Nothing to update"})


@app.route('/')
@app.route('/show')
@login_required
def show_entries():
    db = get_db()
    entries = DinoUpdate.query.filter(DinoUpdate.user_id==session['userid']).order_by(DinoUpdate.timestamp.desc())
    entries = [(json.loads(x.update), timesince(to_user_timezone(x.timestamp))) for x in entries]
    return render_template('show_entries.html', entries=entries)


@app.route('/add', methods = ['POST'])
@login_required
def add_entry():

    if not session.get('logged_in'):
        abort(401)

    url = request.form['url']

    # Add product to DB
    existing = Product.query.filter(Product.url == url).first()
    e = None
    product = None
    if not existing:
        #Query Amazon
        try:
            product = azcrawler.crawl_url(url)
            if product is None:
                flash("Amazon doesn't sell this product today!")
                return redirect(url_for('show_entries'))
            e  = Product(product[0], url , product[2], float(product[1][0]))
            e.prev_price = 0
            db = get_db()
            db.session.add(e)
            db.session.commit()
        except:
            flash("Error fetching product...")
            return redirect(url_for('show_entries'))

    existing =  existing or e
    # Add Subscription
    s = Subscription.query.filter(Subscription.user_id == session['userid'],
                                 Subscription.prod_id == existing.id).first()
    if not s:
      try:
          print "Adding subscription"
          sub = Subscription(existing.id, session['userid'])
          db = get_db()
          db.session.add(sub)
          updt = DinoUpdate(json.dumps(
                                {"title": existing.title, 
                                "message": "Watching currently at $%s"%(existing.curr_price),
                                "url": existing.url,
                                "img": existing.img_url,
                                "merchant": utils.get_merchant_name(existing.url),
                                "mag" : 0, 
                                "userid": session['userid']}),
                                session['userid'], 
                                existing.id)
          print "Adding subscription %s"% updt
          db.session.add(updt)
          db.session.commit()
      except Exception, e:
          print "DB Tx failed: %s"%str(e)

    flash('Watching %s now!'%existing.title)
    return redirect(url_for('show_entries'))


#Name says it all
@app.before_request
def before_request():
    g.user = current_user
    db = get_db()
    if g.user.is_authenticated():
        session.logged_in = True
        g.user.last_seen = datetime.utcnow()
        g.user.username = session['username']
        db.session.add(g.user)
        db.session.commit()


@lm.user_loader
def load_user(id):
    return User.query.get(int(id))


@app.route('/login', methods = ['GET', 'POST'])
@oid.loginhandler
def login():
    if g.user is not None and g.user.is_authenticated():
        return redirect(url_for('show_entries'))
    form = LoginForm()
    if form.validate_on_submit():
        session['remember'] = form.remember.data
        session['logged_in'] = True
        return oid.try_login(form.openid.data, ask_for = ['nickname', 'email'])

    return render_template('login.html',next=oid.get_next_url(),error=oid.fetch_error(),
                            title = 'Sign In',
                            form = form,
                            providers=OPENID_PROVIDERS)


@oid.after_login
def create_login(resp):
    if resp.email is None or resp.email == "":
        print resp
        flash('Invalid login. Please try again.')
        return redirect(url_for('login'))
    nickname = resp.nickname
    if nickname is None or nickname == "":
        nickname = resp.email.split('@')[0]

    db = get_db()
    user = User.query.filter_by(email = resp.email).first()
    if user is None:
        user = User(nickname = nickname, email = resp.email)
        db.session.add(user)
        db.session.commit()
    remember = False
    session['username'] = user.nickname
    session['user_id'] = user.id
    session['userid'] = user.id
    if 'remember' in session:
        remember = session['remember']
        session.pop('remember', None)
    login_user(user, remember=remember)
    flash('You were logged in')
    return redirect(url_for('show_entries'))


@app.route('/pusher/auth', methods=['POST'])
def pusher_auth():
    channel_name = request.form.get('channel_name')
    # Auth user based on channel name
    socket_id = request.form.get('socket_id')
    if session['user_id']:
        auth = pushr[channel_name].authenticate(socket_id)
        json_data = json.dumps(auth)
        return json_data
    return None


@app.route('/logout')
def logout():
    session.pop('logged_in', None)
    logout_user()
    flash('You were logged out')
    return redirect(url_for('show_entries'))


if __name__ == '__main__':
    import os
    from init import sched, track
    from tracker import Tracker
    sched.start() #start the scheduler
    t = Tracker()
    track(t)
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
