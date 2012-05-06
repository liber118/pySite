#!/usr/bin/env python
# encoding: utf-8

from BeautifulSoup import BeautifulSoup
from datetime import datetime, date
from urlparse import urlparse
import dateutil.parser
import httplib
import pytz
import urllib2


## static definitions
      
HTTP_TIMEOUT = 5
TZ_NAME = "America/Los_Angeles"
MIME_HTML = "text/html"
OPENER = urllib2.build_opener()


## global variables

done_urls = set([])
todo_urls = set([])
exit_urls = set([])


## class definitions

class Page:
    """
    representation for an HTML5 page
    """

    def __init__ (self, url, soup, is_news_item=False):
        """
        initialize
        """

        self.url = url
        self.title = soup.title.string
        self.description = soup.findAll(attrs={"name":"description"})[0]["content"]
        self.is_news_item = is_news_item

        if is_news_item:
            self.datetime = soup.findAll("time")[0]["datetime"]
            local_dt = dateutil.parser.parse(self.datetime).replace(tzinfo=pytz.timezone(TZ_NAME))
            self.pub_date = local_dt.astimezone(pytz.utc)
        else:
            self.pub_date = datetime.utcnow()
            self.datetime = self.pub_date.isoformat()


    def to_rss (self):
        """
        create an RSS item based on this URL
        """

        return PyRSS2Gen.RSSItem(
            title = self.title,
            link = self.url,
            description = self.description,
            guid = PyRSS2Gen.Guid(self.url),
            pubDate = self.pub_date
            )


    def to_sitemap (self, freq="weekly"):
        """
        create an http://sitesmaps.org item based on this URL
        """

        xml = []
        xml.append("<url>")
        xml.append("<loc>")
        xml.append(self.url)
        xml.append("</loc>")
        xml.append("<lastmod>")
        xml.append(datetime.utcnow().strftime("%Y-%m-%d"))
        xml.append("</lastmod>")
        xml.append("<changefreq>")
        xml.append(freq)
        xml.append("</changefreq>")
        xml.append("</url>")

        return "".join(xml)


######################################################################
## top-level methods

def init_crawler (bot_name="pySite crawler 0.118", http_timeout=5, tz_name="America/Los_Angeles"):
    """
    initialize the crawler settings
    """

    HTTP_TIMEOUT = int(http_timeout)
    OPENER.addheaders = [('User-agent', bot_name), ('Accept-encoding', 'gzip')]
    TZ_NAME = tz_name

    done_urls = set([])
    todo_urls = set([])
    exit_urls = set([])


def add_url (url):
    """
    add a URL to the TODO list, if it has not been visited already
    """

    if url not in done_urls:
        todo_urls.add(url)


def http_get (url, log=[], pages={}):
    """
    attempt to fetch HTML+status for a given URL
    """

    response = None
    status = "400"
    norm_url = url
    content_type = MIME_HTML

    try:
        response = urllib2.urlopen(url, None, HTTP_TIMEOUT)
        todo_urls.discard(url)

        if response:
            status = str(response.getcode())
            norm_url = response.geturl()

            done_urls.add(url)
            done_urls.add(norm_url)
            todo_urls.discard(norm_url)

            # determine the content type

            headers = response.info()

            if "content-type" in headers:
                content_type = headers["content-type"].split(";", 1)[0].strip()

            if content_type == MIME_HTML:
                # find all the URLs embedded in the page content

                url_parse = urlparse(norm_url)
                base_url = "://".join([url_parse.scheme, url_parse.netloc])

                soup = BeautifulSoup(response)

                for link in soup.findAll('a'):
                    href = link.get('href')

                    if href.startswith("/"):
                        # relative internal link
                        add_url(base_url + href)
                    elif href.startswith(base_url):
                        # fully qualified internal link
                        add_url(href)
                    elif href not in ["#"]:
                        # external link
                        exit_urls.add(href)

                # preserve metadata for generating RSS

                a = Page(norm_url, soup)
                pages[a] = a.datetime

    except httplib.InvalidURL:
        status = "400"
    except httplib.BadStatusLine:
        status = "400"
    except httplib.IncompleteRead:
        status = "400"
    except IOError:
        status = "400"
    except ValueError:
        # unknown url type: http
        status = "400"

    log.append("\t".join(["in", status, norm_url]))


def http_head (url, log=[]):
    """
    test the HTTP status for an external URL
    """

    status = "400"
    norm_url = url

    try:
        request = urllib2.Request(url)
        request.get_method = lambda : 'HEAD'

        response = urllib2.urlopen(request, None, HTTP_TIMEOUT)
        status = str(response.getcode())
        norm_url = response.geturl()
        headers = response.info()

    except httplib.InvalidURL:
        status = "400"
    except httplib.BadStatusLine:
        status = "400"
    except httplib.IncompleteRead:
        status = "400"
    except IOError:
        status = "400"
    except ValueError:
        # unknown url type: http
        status = "400"

    log.append("\t".join(["ex", status, url]))


def crawl_site (seed_urls=[], log=[], pages={}):
    """
    crawl a web site, starting with the given 'seed' URL list
    """

    for url in seed_urls:
        add_url(url);

    while len(todo_urls) > 0:
        url = todo_urls.pop()
        http_get(url, log, pages)


def test_externals (log=[]):
    """
    test external URLs
    """

    for url in sorted(exit_urls):
        http_head(url, log)
