from init import app
db = SQLAlchemy(app)

'''
Represents a User with the LoginManager.User interface
'''
#Database
class User(db.Model):
    id = db.Column(db.Integer, primary_key = True)
    nickname = db.Column(db.String(64), unique = True)
    email = db.Column(db.String(120), unique = True)
    watches = db.relationship('Subscription', backref = 'watcher', lazy = 'dynamic')

    def __init__(self, nickname, email):
      self.nickname = nickname
      self.email = email

    def is_authenticated(self):
        return True

    def get_nickname(self):
        return self.nickname

    def is_active(self):
        return True

    def is_anonymous(self):
        return False

    def get_id(self):
        return unicode(self.id)

    def __repr__(self):
        return '<User %r>' % (self.nickname)


'''
Represents a Product. The product ids may not be in URL as expected - 
hence the id is auto-increment key than an amazon ISBN like entity
'''
class Product(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(80))
    url = db.Column(db.String(200), unique=True)
    img_url = db.Column(db.String(200))
    curr_price = db.Column(db.Float)
    prev_price = db.Column(db.Float)
    lowest_price = db.Column(db.Float)

    def __init__(self, title, url, img_url, curr_price):
      self.title = title
      self.url = url
      self.img_url = img_url
      self.curr_price = curr_price
      self.lowest_price = curr_price

    def __repr__(self):
        return '<Product %r %r at %r>' % (self.id, self.title, self.curr_price)



'''
Represents a stream update for a user
'''
class DinoUpdate(db.Model):
  id = db.Column(db.Integer, primary_key = True)
  update = db.Column(db.String(100), unique = True)
  user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
  prod_id = db.Column(db.Integer, db.ForeignKey('product.id'))
  timestamp = db.Column(db.DateTime, default=datetime.now)


  def __init__(self, update, uid, pid):
    self.update = update
    self.user_id = uid
    self.prod_id = pid

  def __repr__(self):
    return '<Update for pid %r for user id %r>'%(self.prod_id, self.user_id)


'''
Represents a user subscription to a product
'''
class Subscription(db.Model):
  id = db.Column(db.Integer, primary_key=True)
  prod_id = db.Column(db.Integer)
  user_id = db.Column(db.Integer, db.ForeignKey('user.id'))


  def __init__(self, pid, uid):
      self.prod_id = pid
      self.user_id = uid

  def __repr__(self):
      return '<Subscription for pid %r for user id %r>' % (self.prod_id, self.user_id)



def init_db():
    """Creates the database tables."""
    with app.app_context():
      db = get_db()
      db.create_all()


def connect_db():
    """Connects to the specific database."""
    return db


def get_db():
    """Opens a new database connection if there is none yet for the
    current application context.
    """
    with app.app_context():
      if not hasattr(g, 'sqlite_db'):
          g.sqlite_db = connect_db()
      return g.sqlite_db

