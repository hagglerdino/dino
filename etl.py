from urlparse import urlparse
from amazon.api import AmazonAPI
import re

class ETLManager(object):

    # Fetch product updates
    def fetchall(self):
        pass

    # Add mechant 
    def add_merchant(self):
        pass

    # Fetch a merchants update
    def fetch_merchant(self, merchant_crawler):
        pass

    def fetch_pids(self, pids=[]):
        pass


class MerchantCrawler(object):

    def __init__(self):
        pass

    def crawlall(self):
        pass

    def crawl_url(self):
        pass

    def crawl_pids(self, pids):
        pass


class AmazonCrawler(MerchantCrawler):

    def __init__(self, creds):
      super(AmazonCrawler, self).__init__()
      self.ep = AmazonAPI(creds.get("AWS_ACCESS"),
                          creds.get("AWS_SEC_KEY"),
                          creds.get("AMAZON_ASSOC_TAG"))

      regex = "http://www.amazon.com/([\\w-]+/)?(dp|gp/product)/(\\w+/)?(\\w{10})"
      self.rc = re.compile(regex)

    def crawl_url(self, url):
        urlgrps = self.rc.match(url).groups()
        amazonid = urlgrps[3] #url.split("/")[-2]
        print "Getting ", amazonid
        try:
            p = self.ep.lookup(ItemId=amazonid)
        except:
            p = None
        if p is None:
            return None
        return (p.title, p.price_and_currency, p.medium_image_url)


class utils(object):

    #parse merchant name from URL
    @classmethod
    def get_merchant_name(cls, url):
        p = urlparse(url)
        host = p.netloc.split(".")
        return host[1]

