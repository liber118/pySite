#!/bin/bash

# by Liber 118
# http://liber118.com/
# licensed under a Creative Commons Attribution-ShareAlike 3.0 Unported License
# http://creativecommons.org/licenses/by-sa/3.0/

DIR=`dirname $0`
cd $DIR

/bin/date -u

## crawl the site to report on links, generate feeds, etc.

BASE=/opt/pysite/

TMP1=/tmp/rss_feed
TMP2=/tmp/sitemap

$BASE/bin/crawl.py $BASE/bin/crawl.json $BASE/crawler.log $TMP1 $TMP2 2>&1 > $BASE/update.log
rc=$?

if [ $rc != 0 ]
then
    echo "site crawler failed"
    exit $rc
fi

if [ -s "$TMP1" ]
then
    mv $TMP1 $BASE/www/rss.xml
else
    echo "site crawler failed"
    exit -1
fi

if [ -s "$TMP2" ]
then
    mv $TMP2 $BASE/www/sitemap.xml
else
    echo "site crawler failed"
    exit -1
fi

/bin/date -u
