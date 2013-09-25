#!/usr/bin/env python3
# URI title bot.
import re
import requests
import bs4
import json

import personalities
from modules import command
_ = personalities.localize

__name__ = 'uribot'
__author__ = 'Shiz'
__license__ = 'WTFPL'

# Thanks Hitler, Obama and Daring Fireball.
URI_REGEXP = re.compile(r"""(?i)\b((?:https?://|www\d{0,3}[.]|[a-z0-9.\-]+[.][a-z]{2,4}/)(?:[^\s()<>]+|\(([^\s()<>]+|(\([^\s()<>]+\)))*\))+(?:\(([^\s()<>]+|(\([^\s()<>]+\)))*\)|[^\s`!()\[\]{};:'".,<>?«»“”‘’]))""")


# URI handlers.

def uri_title(uri, contents):
    """ Extract a regular URL title. """
    html = bs4.BeautifulSoup(contents)

    # Very basic stuff, thanks to BeautifulSoup.
    if not html.title:
        return None
    return 'Title', html.title.string, ''

def uri_youtube(uri, contents):
    """ Extract YouTube video information. """
    xml = bs4.BeautifulSoup(contents)

    # Get video title.
    if not xml.title:
        return
    title = xml.title.string

    # Get video author.
    if xml.author.find('name').string:
        author = xml.author.find('name').string
    else:
        author = None

    # Get video duration.
    if xml.find('yt:duration'):
        duration = int(xml.find('yt:duration')['seconds'])
    else:
        duration = None

    # Put it into a nice format.
    if author:
        type = 'YouTube: {}'.format(author)
    else:
        type = 'YouTube'
    if duration:
        meta = '{}:{:02d}'.format(*divmod(duration, 60))
    else:
        meta = ''

    return type, title, meta

def uri_reddit(uri, contents):
    """ Extract Reddit thread information. """
    pass

def uri_twitter(uri, contents):
    """ Extract Twitter status information. """
    html = bs4.BeautifulSoup(contents)

    # Extract tweet and strip HTML.
    tweet = ''.join(html.find('div', class_='permalink-tweet-container').find('p', class_='tweet-text').find_all(text=True))
    # Extract user.
    user = html.find('div', class_='permalink-tweet-container').find('div', class_='tweet')['data-name']

    # Try to extract metadata.
    try:
        retweets = html.find('ul', class_='stats').find('li', class_='js-stat-retweets').strong.string
    except:
        retweets = None
    try:
        favourites = html.find('ul', class_='stats').find('li', class_='js-stat-favorites').strong.string
    except:
        favourites = None

    # Post-process tweet a bit.
    tweet = re.sub('\s+', ' ', tweet)

    # Build metadata.
    meta = []
    if retweets:
        meta.append('↻ ' + retweets)
    if favourites:
        meta.append('★ ' + favourites)

    return 'Twitter: {}'.format(user), tweet, ', '.join(meta)

def uri_4chan(uri, contents):
    """ Extract 4chan thread information. """
    thread = json.loads(contents)
    wanted = None

    # Check if we want to actually have a linked post instead of the OP.
    uri_parts = uri.split('#', 1)
    if len(uri_parts) > 1:
        uri, segment = uri_parts
        if segment.startswith('p'):
            segment = segment[1:]

        try:
            wanted = int(segment)
        except:
            pass

    title = None
    # We want a given number.
    if wanted:
        for post in thread['posts']:
            if int(post['no']) == wanted:
                # Found the post!
                # Use post contents as URL title, stripped from HTML and cut down.
                # We need to invent our own newlines.
                comment = post['com'].replace('<br>', '\n')
                raw_title = ''.join(bs4.BeautifulSoup(comment).find_all(text=True))

                # Add ... if needed and remove unnecessary whitespace.
                title = raw_title[:300] + '...' * (len(raw_title) > 300)
                title = re.sub('\s+', ' ', title)

    # We want the OP.
    if not title:
        op = thread['posts'][0]
        if 'sub' in op:
            # Use thread title as URL title.
            title = op['sub']
        else:
            # Use thread contents as URL title, stripped from HTML and cut down.
            # We need to invent our own newlines.
            comment = post['com'].replace('<br>', '\n')
            raw_title = ''.join(bs4.BeautifulSoup(comment).find_all(text=True))

            # Add ... if needed and remove unnecessary whitespace.
            title = raw_title[:300] + '...' * (len(raw_title) > 300)
            title = re.sub('\s+', ' ', title)

    # Gather some metadata.
    board = re.match(r'https?://boards\.4chan\.org/([a-z0-9]+)/', uri).group(1)
    num_replies = thread['posts'][0]['replies']
    num_images = thread['posts'][0]['images']

    # And format it nicely.
    type = '4chan: /{}/'.format(board)
    meta = '{} replies'.format(num_replies if num_replies else 'no')
    if num_images:
        meta += ', {} images'.format(num_images)

    return type, title, meta


# All URI handlers.
URI_HANDLERS = {
    # YouTube video.
    r'^https?://(?:www\.)youtube\.com/watch\?(?:\S*)v=([a-zA-Z0-9_-]+)(?:[&#]\S*)?$':
        (uri_youtube, r'https://gdata.youtube.com/feeds/api/videos/\1'),
    # Reddit post/comment.
    r'^(https?://(?:.*?\.){0,1}reddit\.com/r/([a-zA-Z0-9_-]+)/comments/([a-zA-Z0-9_-]+)(/([a-zA-Z0-9_-]*))?/?)(?:[?&#]\S*)?$':
        (uri_reddit, '\1.json'),
    # Twitter status.
    r'^https?://(?:www\.){0,1}twitter\.com/([a-zA-Z0-9_-]+)/status/([0-9]+)(?:[?#&]\S*)?$':
        (uri_twitter, None),
    # 4chan thread/post.
    r'^https?://boards\.4chan\.org/([a-z0-9]+)/res/([0-9]+)(?:[?&#]\S*)?$': 
        (uri_4chan, r'https://api.4chan.org/\1/res/\2.json')
}


# Commands.

@command(r'(?:^|\s)https?://', bare=True)
def uri(bot, server, target, source, message, parsed, private):
    global URI_REGEXP, URI_HANDLERS
    
    # Find all URIs and process them.
    for match in re.findall(URI_REGEXP, message):
        original_uri = uri = match[0]

        # Stock handler: extract the URI.
        handler = uri_title
        # See if we want a custom handler.
        for matcher, (hndlr, replacement) in URI_HANDLERS.items():
            if matcher.match(uri):
                if replacement:
                    uri = matcher.sub(replacement, uri)
                handler = hndlr

        # Do request.
        try:
            response = requests.get(uri)
        except:
            continue
        if not response:
            continue

        # Parse response.
        res = handler(original_uri, response.text)
        if not res:
            continue
        type, title, meta = res

        # Post info.
        if meta:
            bot.privmsg(target, _('[{type}] {b}{title}{/b} ({meta})', type=type, title=title, meta=meta))
        else:
            bot.privmsg(target, _('[{type}] {b}{title}{/b}', type=type, title=title, meta=meta))


# Module stuff.

def load():
    global URI_HANDLERS

    # Precompile all URI handler regexps.
    for match, value in list(URI_HANDLERS.items()):
        URI_HANDLERS[re.compile(match)] = value
        del URI_HANDLERS[match]

    return True

def unload():
    pass
