Hacker News
===========

A Python-based CLI for working with [Hacker News](https://news.ycombinator.com).

Requirements
------------

* [Requests](http://docs.python-requests.org/en/latest/index.html)
* [pystache](https://github.com/defunkt/pystache)
* [pyquery](http://packages.python.org/pyquery/)

Requirements can be installed directly by using:

    pip install -r requirements.txt

Using hackernews
----------------

### Help

    hackernews.py -h

### Cookies

By default, `hackernews` uses a built-in cookie system. It saves the file `hackernews.cookie` to the base directory. To disable the use of cookies:

    hackernews.py <command> --no-cookies

When cookies are turned off, two additional requests are needed per-command to retrieve proper login info.

### Saved items

Retrieve a user's latest saved items, and print the output as JSON (default):

    hackernews.py saved -u 'username' -p 'password'

Retrieve all saved items, and print the output as XML (this might take a while):

    hackernews.py saved -all -e xml -u 'username' -p 'password'

Help for the `saved` subcommand:

    hackernews.py saved -h

### Comments

Retrieve a user's comment threads, and print the output as JSON (default):

    hackernews.py comments -u 'username' -p 'password'

Retrieve all comments, and print the output as XML (this might take a while):

    hackernews.py comments -all -e xml -u 'username' -p 'password'

Help for the `comments` subcommand:

    hackernews.py comments -h
