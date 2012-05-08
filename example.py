#!/usr/bin/env python
# encoding: utf-8

from datetime import datetime
from operator import itemgetter
import json
import pysite
import sys
          

if __name__ == "__main__":
    ## command line arguments

    file_bot_conf = sys.argv[1]
    file_crawl_log = sys.argv[2]
    file_rss_feed = sys.argv[3]
    file_site_map = sys.argv[4]

    ## dependency injection

    with open(file_bot_conf, "r") as f:
        bot_conf = json.load(f)

    log = open(file_crawl_log, "w")
    pysite.init_crawler(bot_conf["bot_name"], bot_conf["http_timeout"], bot_conf["tz_name"], bot_conf["url_slug_regex"], bot_conf["file_slug_format"])

    feed_dict = {}
    site_dict = {}

    ## crawl site (internal URLs only)

    for log_line, page in pysite.crawl_site(bot_conf["seed_urls"]):
        log.write(log_line)
        log.write("\n")

        ## append RSS feed and Sitemap XML items

        if page:
            site_dict[page.to_site()] = page.url

            if len(page.soup.findAll("article")) > 0:
                feed_dict[page.to_feed()] = page.url

    ## generate RSS feed

    feed_items = [feed for feed, date in sorted(feed_dict.items(), key=itemgetter(1), reverse=True)]
    feed_xml = pysite.generate_rss_feed(bot_conf["rss_feed"], feed_items, pretty=True)

    with open(file_rss_feed, "w") as f:
        f.write(feed_xml)

    ## generate Sitemaps XML

    site_items = [site for site, date in sorted(site_dict.items(), key=itemgetter(1), reverse=True)]
    site_xml = pysite.generate_site_map(site_items, pretty=True)

    with open(file_site_map, "w") as f:
        f.write(site_xml)

    ## test external URLs

    for log_line in pysite.test_externals():
        log.write(log_line)
        log.write("\n")

    log.close()
