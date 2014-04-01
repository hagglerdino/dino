import json
import time
from etl import utils
from model import User, Subscription, Product, DinoUpdate
from flask import current_app as app
from init import db
from init import config

class Singleton(type):
    _instances = {}
    def __call__(cls, *args, **kwargs):
        if cls not in cls._instances:
            cls._instances[cls] = super(Singleton, cls).__call__(*args, **kwargs)
        return cls._instances[cls]

class Tracker(object):
    __metaclass__= Singleton

    VERYLOWPER = -30

    def __init__(self):
        self.updated_prods = {}

    @classmethod
    def _per_change(cls, c, n):
        return ((n-c) * 100)/c


    def getupdate(self, pid):
        prod = Product.query.filter(Product.id == pid).first()
        if prod.curr_price < prod.prev_price:
            if prod.curr_price == prod.lowest_price:
                return (prod, -5)
            elif self._per_change(prod.prev_price, prod.curr_price) < Tracker.VERYLOWPER:
                return (prod, -2)
            else:
                return (prod, -1)

        elif prod.curr_price > prod.prev_price:
            return (prod, 1)
        return None

    def push_updates(self):

        print "Updating..."
        from init import pushr
        subs = Subscription.query.all()
        print "updating 1"
        print "updating 2"
        for s in subs:
            up = None
            if s.prod_id in self.updated_prods:
              up = self.getupdate(s.prod_id)

            if up:
              #Push to Updates db
              m = utils.get_merchant_name(up[0].url)
              if up[1] > 0:
                  msg = "Price increase! - $%.2f"%up[0].curr_price
              elif up[1] < 0:
                  msg = 'Price decrease alert! - $%.2f'%up[0].curr_price

              print "Pushing update with msg ", msg
              try:
                update = { 'title': up[0].title, 'message': msg, 
                           'url': up[0].url, 
                           'img': up[0].img_url, 
                           'merchant': m, 
                           'mag': up[1], 
                           'userid': s.user_id }

                exist_up = DinoUpdate.query.filter(DinoUpdate.update==json.dumps(update), 
                                                 DinoUpdate.prod_id==s.prod_id).first()
              except Exception, e:
                print str(e)

              if exist_up:
                  continue

              try:
                      u = DinoUpdate(json.dumps(update), s.user_id, up[0].id)
                      db.session.add(u)
                      db.session.commit()
              except Exception, e:
                      print "Db TX failed", str(e)
                      return
              
              print "Update ", update
              usernickname = User.query.filter(User.id == s.user_id).first().nickname
              channel = config['pusher']['channelpfx'] + usernickname
              pushr[channel].trigger('priceup', update)

        self.updated_prods = {}

    def updates(self, updated_prods={}):
        self.updated_prods = updated_prods
        print self.updated_prods



