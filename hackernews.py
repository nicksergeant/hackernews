#!/usr/bin/env python

import argparse, os, pickle, re, requests
from pyquery import PyQuery as pq
import pystache

BASE_PATH = os.path.dirname(__file__)
COOKIE = os.path.join(BASE_PATH, 'hackernews.cookie')
EXPORT_TYPES = ( 'json', 'xml', )

tries = 0


def _login(**kwargs):
    """Log in to Hacker News and return the cookies."""

    if 'r' not in kwargs:
        # We haven't established a login request.

        # If we're using cookies, try to return those instead.
        if not kwargs['args'].no_cookies:

            # If the cookie doesn't exist, create it.
            try:
                cookie = open(COOKIE, 'r')
            except IOError:
                cookie = open(COOKIE, 'w')

            # If there's something in the cookie, return that.
            if os.stat(COOKIE).st_size:
                cookies = pickle.load(cookie)
                cookie.close()
                return cookies
            else:
                cookie.close()

        # Request a blank login page to harvest the fnid (a CSRF-type key).
        r = requests.get('https://news.ycombinator.com/newslogin')
        J = pq(r.content)
        fnid = J('input[name="fnid"]').val()

        # Build the login POST data and make the login request.
        payload = {
            'fnid': fnid,
            'u': kwargs['args'].username,
            'p': kwargs['args'].password,
        }
        r = requests.post('https://news.ycombinator.com/y', data=payload)

        if 'set-cookie' not in r.headers:
            raise BaseException('It looks like you might have an incorrect username/password (got a bad response when logging you in).')

        cookies = r.cookies

    else:
        # Set the cookies to the cached login request's cookies.
        cookies = kwargs['r'].cookies

    # Set the cookie
    if not kwargs['args'].no_cookies:
        cookie = open(COOKIE, 'w+')
        pickle.dump(cookies, cookie)
        cookie.close()

    return cookies

def _reset_cookie(tries):

    # Reset the cookie and mark this as a try.
    # If we try 5 times, kill the script.
    if tries < 5:
        cookie = open(COOKIE, 'r+')
        cookie.truncate(0)
        cookie.close()
        tries = tries + 1
    else:
        raise BaseException('Too many tries with bad responses (Hacker News may be down).')

def _good_response(**kwargs):

    # Handle an invalid cookie / login.
    if kwargs['r'].content == "Can't display that.":
        _reset_cookie(tries)
        return False

    return True

def _sanitize_comment(J, c):
    user = J('span.comhead a:eq(0)', c).text()
    link = 'https://news.ycombinator.com/%s' % J('span.comhead a:eq(1)', c).attr('href')
    points = J('span.comhead span', c).text()

    # 'Parent' and 'Story' don't exist for non-owned comments.
    parent = J('span.comhead a:eq(2)', c).attr('href')
    if parent is None:
        parent = 'N/A'
        story  = 'N/A'
    else:
        parent = 'https://news.ycombinator.com/%s' % parent
        story  = 'https://news.ycombinator.com/%s' % J('span.comhead a:eq(3)', c).attr('href')

    # Reply link doesn't always exist, for some reason.
    reply = J('u a', c).attr('href')
    if reply is None:
        reply = 'N/A'
    else:
        reply = 'https://news.ycombinator.com/%s' % J('u a', c).attr('href')

    # Sanitize the comment.
    comment = J('span.comment', c).html()
    comment = re.sub('</p>', '\n\n', comment)
    comment = re.sub('<[^<]+?>', '', comment).rstrip('\n\n')

    # Grab the points, if possible.
    if points != None:
        points = re.sub('points?', '', points).strip()
    else:
        points = 'N/A'

    # Strip the comhead and harvest the date.
    J('span.comhead a, span.comhead span', c).remove()
    date = J('span.comhead', c).text()
    date = re.sub('on:|by|\||', '', date).strip()

    return {
        'user': user,
        'comment': comment,
        'reply': reply,
        'points': points,
        'link': link,
        'parent': parent,
        'story': story,
        'date': date,
    }


def _get_saved_stories(**kwargs):
    """Returns a sorted list of the user's saved stories."""

    # Log in to get cookies.
    cookies = _login(**kwargs)

    if 'r' not in kwargs:
        # This is the first saved items request.
        # Make the saved items request and set an empty list.
        kwargs['r'] = requests.get('https://news.ycombinator.com/saved?id=%s' % kwargs['args'].username,
                                   cookies=cookies)

        # Check to make sure we have a good response.
        if not _good_response(**kwargs):
            kwargs.pop('r')
            return _get_saved_stories(**kwargs)

        kwargs['saved'] = []

    # Grab the stories.
    J = pq(kwargs['r'].content)
    stories = J('table table td.title')

    for story in stories:
        title = J(story).text()
        url = J('a', story).attr('href')

        # Skip digit-only <td>s and the 'More' link.        
        if not re.match('\d+|\/x\?', title):

            # Skip HN dead links
            if url is not None:

                # For HN links, make absolute URL.
                if not url.startswith('http'):
                    url = 'https://news.ycombinator.com/' + url

                # Add the story to the saved list.
                kwargs['saved'].append({
                    'title': title,
                    'url': url,
                })

    # If we're getting all saved stories.
    if kwargs['args'].all:

        # Find the 'More' link and load it.
        last = J('a', J('table table tr td.title:last'))
        if last.text() == 'More':
            kwargs['r'] = requests.get('https://news.ycombinator.com%s' % last.attr('href'),
                                       cookies=cookies)

            # Check to make sure we have a good response.
            if not _good_response(**kwargs):
                kwargs.pop('r')
                return _get_saved_stories(**kwargs)

            # Call this function again, this time with the new list.
            return _get_saved_stories(**kwargs)

    return kwargs['saved']

def _get_comments(**kwargs):
    """Returns a sorted list of the user's comments."""

    # Log in to get cookies.
    cookies = _login(**kwargs)

    if 'r' not in kwargs:
        # This is the first comments request.
        # Make the comments request and set an empty list.
        kwargs['r'] = requests.get('https://news.ycombinator.com/threads?id=%s' % kwargs['args'].username,
                                   cookies=cookies)

        # Check to make sure we have a good response.
        if not _good_response(**kwargs):
            kwargs.pop('r')
            return _get_comments(**kwargs)

        kwargs['comments'] = []

    # Grab the comments.
    J = pq(kwargs['r'].content)
    comments = J('table table td.default')

    for c in comments:

        comment = _sanitize_comment(J, c)

        if kwargs['args'].no_owner and comment['user'] == kwargs['args'].username:
            continue

        # Add the comment to the saved list.
        kwargs['comments'].append({
            'user': comment['user'],
            'comment': comment['comment'],
            'reply': comment['reply'],
            'points': comment['points'],
            'link': comment['link'],
            'parent': comment['parent'],
            'story': comment['story'],
            'date': comment['date'],
        })

    # If we're getting all comments.
    if kwargs['args'].all:

        # Find the 'More' link and load it.
        last = J('a', J('table table tr td.title:last'))
        if last.text() == 'More':
            kwargs['r'] = requests.get('https://news.ycombinator.com%s' % last.attr('href'),
                                       cookies=cookies)

            # Check to make sure we have a good response.
            if not _good_response(**kwargs):
                kwargs.pop('r')
                return _get_comments(**kwargs)

            # Call this function again, this time with the new list.
            return _get_comments(**kwargs)

    return kwargs['comments']


def saved(args):
    """Returns a formatted list of the logged-in user's saved stories."""

    stories = _get_saved_stories(args=args)

    if args.export == 'json':
        return stories
    elif args.export == 'xml':
        return pystache.render("""<?xml version="1.0" encoding="utf-8"?>
            <feed xmlns="http://www.w3.org/2005/Atom">
                <title>Saved stories on Hacker News</title>
                {{#stories}}
                <entry>
                    <title>{{title}}</title>
                    <link href="{{url}}" />
                </entry>
                {{/stories}}
            </feed>""", {'stories': stories})

def comments(args):
    """Returns a formatted list of the logged-in user's comments."""

    comments = _get_comments(args=args)

    if args.export == 'json':
        return comments
    elif args.export == 'xml':
        return pystache.render("""<?xml version="1.0" encoding="utf-8"?>
            <feed xmlns="http://www.w3.org/2005/Atom">
                <title>Comments on Hacker News</title>
                {{#comments}}
                <entry>
                    <title>{{comment}}</title>
                    <author>
                        <name>{{user}}</name>
                    </author>
                    <reply>{{reply}}</reply>
                    <points>{{points}}</points>
                    <link href="{{link}}" />
                    <parent>{{parent}}</parent>
                    <story>{{story}}</story>
                    <date>{{date}}</date>
                </entry>
                {{/comments}}
            </feed>""", {'comments': comments})


if __name__ == '__main__':

    # Parser
    parser = argparse.ArgumentParser(prog='Hacker News')
    parser.add_argument('--version', action='version', version='%(prog)s 0.1')
    subparsers = parser.add_subparsers()

    # TODO: --username, --password, --all, --no-cookies should probably be stored
    # at the parser level, not subparser.

    # Saved stories
    saved_parser = subparsers.add_parser('saved')
    saved_parser.add_argument('-u', '--username', dest='username', help='HN Username',
                              required=True)
    saved_parser.add_argument('-p', '--password', dest='password', help='HN Password',
                              required=True)
    saved_parser.add_argument('-e', '--export', dest='export', help='Export type',
                              required=False, default='json', choices=EXPORT_TYPES)
    saved_parser.add_argument('--all', dest='all', help='Get all saved stories',
                              action='store_true')
    saved_parser.add_argument('--no-cookies', dest='no_cookies', help="Don't use cookies",
                              action='store_true', default=False)
    saved_parser.set_defaults(func=saved)

    # Comments
    comments_parser = subparsers.add_parser('comments')
    comments_parser.add_argument('-u', '--username', dest='username', help='HN Username',
                              required=True)
    comments_parser.add_argument('-p', '--password', dest='password', help='HN Password',
                              required=True)
    comments_parser.add_argument('-e', '--export', dest='export', help='Export type',
                              required=False, default='json', choices=EXPORT_TYPES)
    comments_parser.add_argument('--all', dest='all', help='Get all comments',
                              action='store_true')
    comments_parser.add_argument('--no-cookies', dest='no_cookies', help="Don't use cookies",
                              action='store_true', default=False)
    comments_parser.add_argument('--no-owner', dest='no_owner', help="Don't show owner's comments",
                              action='store_true', default=False)
    comments_parser.set_defaults(func=comments)

    # Args
    args = parser.parse_args()
    print args.func(args)
