# URI title bot - 4chan module.
import re
import json
import bs4

from michiru import modules, personalities


## Module information.

__name__ = 'uribot.fourchan'
__author__ = 'Shiz'
__license__ = 'WTFPL'
__desc__ = 'Gives URL information for 4chan links.'
__deps__ = ['uribot']

URI_REGEXP = re.compile(r'^https?://boards\.4chan\.org/([a-z0-9]+)/thread/([0-9]+)(?:/[a-z0-9_-]+/?)?(?:#p?([0-9]+))?$')


## Module.

def uri_4chan(response, matches):
    """ Extract 4chan thread information. """
    thread = json.loads(response.text)

    # Check if we want to actually have a linked post instead of the OP.
    wanted = None
    if matches.group(3):
        try:
            wanted = int(matches.group(3))
        except:
            pass

    title = None
    comment = None
    # We want a given post: get its contents.
    if wanted:
        for post in thread['posts']:
            if post['no'] == wanted:
                # Found the post!
                comment = post['com']
    # We want just the thread: try to use thread title or OP contents.
    if not comment:
        op = thread['posts'][0]
        if 'sub' in op:
            # Use thread title as URL title.
            title = op['sub']
        else:
            comment = op['com']

    # Build title from comment.
    if not title and comment:
        # Use post contents as URL title, stripped from HTML and cut down.
        # We need to invent our own newlines.
        comment = comment.replace('<br>', '\n')
        comment = comment.replace('<s>', personalities.IRC_CODES['spoiler'])
        comment = comment.replace('</s>', personalities.IRC_CODES['/spoiler'])
        comment = comment.replace('\n', ' ')
        raw_title = ''.join(bs4.BeautifulSoup(comment).find_all(text=True))

        # Add ... if needed and remove unnecessary whitespace.
        title = raw_title[:300] + '...' * (len(raw_title) > 300)
        title = re.sub(r'\s+', ' ', title)

    # Gather some metadata.
    board = matches.group(1)
    num_replies = thread['posts'][0]['replies']
    num_images = thread['posts'][0]['images']

    # And format it nicely.
    type = '4chan: /{}/'.format(board)
    meta = '{} replies'.format(num_replies if num_replies else 'no')
    if num_images:
        meta += ', {} images'.format(num_images)

    return type, title, meta

def load():
    from michiru.modules import uribot
    uribot.URI_HANDLERS[URI_REGEXP] = {
        'handler': uri_4chan,
        'replacement': r'https://api.4chan.org/\1/res/\2.json'
    }

def unload():
    from michiru.modules import uribot
    del uribot.URI_HANDLERS[URI_REGEXP]
