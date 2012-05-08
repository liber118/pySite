pySite
======
Python libraries (tested on 2.6.5) for web site admin.

This was written to crawl a moderately-sized HTML5 web site, then
generate Sitemaps, RSS 2.0 feeds, etc.

Code provided by Google for generating Sitemaps seemed unwieldy.

Code for generating RSS, such as "PyRSS2Gen", would not pass W3C
validation, which seems like a bad thing for testability.

usage
=====
See `example.sh`

dependencies
============
[PyRSS2Gen](http://www.dalkescientific.com/Python/PyRSS2Gen.html)
[BeautifulSoup](http://www.crummy.com/software/BeautifulSoup/)
[python-dateutil](http://labix.org/python-dateutil)

license
=======
created by [Liber 118](http://liber118.com)
licensed under a [Creative Commons Attribution-ShareAlike 3.0 Unported License](http://creativecommons.org/licenses/by-sa/3.0/)
