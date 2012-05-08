#!/usr/bin/env python
# encoding: utf-8

from BeautifulSoup import BeautifulSoup
from datetime import datetime
from operator import itemgetter
from urlparse import urlparse
from xml.dom.minidom import parse, parseString
import PyRSS2Gen
import dateutil.parser
import httplib
import os.path
import pytz
import re
import urllib2


######################################################################
## static definitions
      
debug = False # True

HTTP_TIMEOUT = 5
TZ_NAME = "America/Los_Angeles"
MIME_HTML = "text/html"
URL_SLUG_REGEX = "http://example.com/(.*)"
FILE_SLUG_FORMAT = "/var/www/%s"

OPENER = urllib2.build_opener()

## global variables

done_urls = set([])
todo_urls = set([])
exit_urls = set([])


######################################################################
## class definitions

class Page:
    """
    representation for an HTML5 page
    """

    def __init__ (self, url, timestamp, soup):
        """
        initialize
        """

        self.url = url
        self.pub_date = timestamp
        self.freq = "weekly"
        self.priority = 0.5
        self.soup = soup
        self.title = soup.title.string
        self.description = soup.findAll(attrs={"name":"description"})[0]["content"]


    def to_feed (self):
        """
        create an RSS feed item based on this URL
        """

        return PyRSS2Gen.RSSItem(
            title = self.title,
            link = self.url,
            description = self.description,
            guid = PyRSS2Gen.Guid(self.url),
            pubDate = self.pub_date
            )


    def to_site (self):
        """
        create an http://sitesmaps.org item based on this URL
        """

        xml = []
        xml.append("<url>")
        xml.append("<loc>")
        xml.append(self.url)
        xml.append("</loc>")
        xml.append("<lastmod>")
        xml.append(self.pub_date.strftime("%Y-%m-%d"))
        xml.append("</lastmod>")
        xml.append("<changefreq>")
        xml.append(self.freq)
        xml.append("</changefreq>")
        xml.append("<priority>")
        xml.append("%0.1f" % self.priority)
        xml.append("</priority>")
        xml.append("</url>")

        return "".join(xml)


######################################################################
## top-level methods

def init_crawler (bot_name="pySite crawler 0.118", http_timeout=5, tz_name="America/Los_Angeles", url_slug_regex="http://example.com/(.*)", file_slug_format="/var/www/%s"):
    """
    initialize the crawler settings
    """

    global HTTP_TIMEOUT, TZ_NAME, URL_SLUG_REGEX, FILE_SLUG_FORMAT, OPENER, done_urls, todo_urls, exit_urls

    HTTP_TIMEOUT = int(http_timeout)
    TZ_NAME = tz_name
    URL_SLUG_REGEX = url_slug_regex
    FILE_SLUG_FORMAT = file_slug_format

    OPENER.addheaders = [('User-agent', bot_name), ('Accept-encoding', 'gzip')]

    done_urls = set([])
    todo_urls = set([])
    exit_urls = set([])


def add_url (url):
    """
    add a URL to the TODO list, if it has not been visited already
    """

    global done_urls, todo_urls

    if url not in done_urls:
        todo_urls.add(url)


def http_get (url):
    """
    attempt to fetch HTML+status for a given URL
    """

    global done_urls, todo_urls, exit_urls

    if debug:
        print url

    response = None
    status = "400"
    norm_url = url
    content_type = MIME_HTML
    page = None

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

                # preserve parsed content+metadata for generating RSS feed, etc.

                timestamp = datetime.utcnow()
                m = re.search(URL_SLUG_REGEX, norm_url)

                if debug:
                    print URL_SLUG_REGEX
                    print norm_url

                if m:
                    file_path = FILE_SLUG_FORMAT % m.group(1)

                    if debug:
                        print file_path

                    if os.path.isfile(file_path):
                        timestamp = datetime.fromtimestamp(os.path.getctime(file_path))
                else:
                    for d in soup.findAll("time"):
                        dt = d[0]["datetime"]
                        local_dt = dateutil.parser.parse(dt).replace(tzinfo=pytz.timezone(TZ_NAME))
                        timestamp = local_dt.astimezone(pytz.utc)

                page = Page(norm_url, timestamp, soup)

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

    log_line = "\t".join(["in", status, norm_url])

    return log_line, page


def http_head (url):
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

    log_line = "\t".join(["ex", status, url])
    return log_line


def crawl_site (seed_urls=[]):
    """
    crawl a web site, starting with the given 'seed' URL list
    """

    global todo_urls

    for url in seed_urls:
        add_url(url);

    while len(todo_urls) > 0:
        yield http_get(todo_urls.pop())


def test_externals ():
    """
    test the status of the external URLs
    """

    global exit_urls

    for url in sorted(exit_urls):
        yield http_head(url)


######################################################################
## validated XML generators

def generate_rss_feed (feed_conf={}, feed_items=[], pretty=False):
    """
    fixes the XML in the RSS feed so that it passes the W3C validator
    """

    rss = PyRSS2Gen.RSS2(
        title = feed_conf["title"],
        link = feed_conf["link"],
        description = feed_conf["description"],
        lastBuildDate = datetime.utcnow(),
        items = feed_items
        )

    dom = parseString(rss.to_xml(encoding="utf-8"))
    dom.documentElement.setAttribute("xmlns:atom", "http://www.w3.org/2005/Atom")

    image_elem = dom.createElement("image")

    url_elem = dom.createElement("url")
    text = dom.createTextNode(feed_conf["image"])
    url_elem.appendChild(text)
    image_elem.appendChild(url_elem)

    title_elem = dom.createElement("title")
    text = dom.createTextNode(feed_conf["title"])
    title_elem.appendChild(text)
    image_elem.appendChild(title_elem)

    link_elem = dom.createElement("link")
    text = dom.createTextNode(feed_conf["link"])
    link_elem.appendChild(text)
    image_elem.appendChild(link_elem)

    link_elem = dom.createElement("atom:link")
    link_elem.setAttribute("href", feed_conf["rss_link"])
    link_elem.setAttribute("rel", "self")
    link_elem.setAttribute("type", "application/rss+xml")

    language_elem = dom.createElement("language")
    text = dom.createTextNode(feed_conf["language"])
    language_elem.appendChild(text)

    copyright_elem = dom.createElement("copyright")
    text = dom.createTextNode(feed_conf["copyright"])
    copyright_elem.appendChild(text)

    ttl_elem = dom.createElement("ttl")
    text = dom.createTextNode(feed_conf["ttl"])
    ttl_elem.appendChild(text)

    channel_elem = dom.getElementsByTagName("channel").item(0)
    title_elem = dom.getElementsByTagName("title").item(0)
    item_elem = dom.getElementsByTagName("item").item(0)

    channel_elem.insertBefore(link_elem, title_elem)
    channel_elem.insertBefore(image_elem, item_elem)
    channel_elem.insertBefore(language_elem, item_elem)
    channel_elem.insertBefore(copyright_elem, item_elem)
    channel_elem.insertBefore(ttl_elem, item_elem)

    if pretty:
        xml = dom.toprettyxml(indent=" ", encoding="utf-8")
    else:
        xml = dom.toxml("utf-8")

    return xml


def generate_site_map (site_items=[], pretty=False):
    """
    generates XML for a Sitemaps definition
    """

    dom = parseString(
        """<?xml version="1.0" encoding="UTF-8"?>
<urlset
xmlns="http://www.sitemaps.org/schemas/sitemap/0.9"
xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
xsi:schemaLocation="http://www.sitemaps.org/schemas/sitemap/0.9
http://www.sitemaps.org/schemas/sitemap/0.9/sitemap.xsd"
>""" + "".join(site_items).strip() + "</urlset>"
        )

    if pretty:
        xml = dom.toprettyxml(indent=" ", encoding="utf-8")
    else:
        xml = dom.toxml("utf-8")

    return xml
