#!/usr/bin/env python

import argparse


def _login(args):
    """Log in to Hacker News and return the cookies."""

    r = requests.get('http://news.ycombinator.com/newslogin')

    return ''

def _get_saved_stories(args):
    """Returns a sorted list of the user's saved stories."""
    user = _login(args)
    return []

def saved(args):
    """Returns a formatted list of the logged-in user's saved stories."""
    stories = _get_saved_stories(args)
    return ''

# Parser
parser = argparse.ArgumentParser(prog='Hacker News')
parser.add_argument('--version', action='version', version='%(prog)s 0.1')
subparsers = parser.add_subparsers()

# Subparsers
saved_parser = subparsers.add_parser('saved')
saved_parser.add_argument('--username', help='HN Username', required=True)
saved_parser.add_argument('--password', help='HN Password', required=True)
saved_parser.set_defaults(func=saved)

# Args
args = parser.parse_args()
args.func(args)
