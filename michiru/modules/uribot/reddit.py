# URI title bot - Reddit module.
import re
import json

from michiru import modules


## Module information.

__name__ = 'uribot.reddit'
__author__ = 'Shiz'
__license__ = 'WTFPL'
__desc__ = 'Gives URL information for Reddit links.'
__deps__ = ['uribot']

URI_REGEXP = re.compile(r'^(https?://(?:.*?\.){0,1}reddit\.com/r/([a-zA-Z0-9_-]+)/comments/([a-zA-Z0-9_-]+)/(?:[a-zA-Z0-9_-]+)(?:/([a-zA-Z0-9_-]+))?/?)(?:[?&#]\S*)?$')


## Module.

def uri_reddit(bot, response, matches):
    """ Extract Reddit thread information. """
    post, comments = json.loads(response.text)
    subreddit = matches.group(2)

    # Do we want the OP or a specific reply?
    if matches.group(4):
        data = comments['data']['children'][0]['data']
        title = data['body']
    else:
        data = post['data']['children'][0]['data']
        title = data['title']

    # Un-markdownify a bit.
    title = re.sub(r'\!?\[(.*)\]\((.+)\)', r'\1: \2', title)
    # Clean up.
    title = title.replace('\n', ' ')
    title = re.sub(r'\s+', ' ', title).strip()
    title = title[:300] + '...' * (len(title) > 300)

    # Get metadata.
    meta = None
    if not data.get('score_hidden'):
        meta = '↑↓{}'.format(data['score'])

    return 'Reddit: /r/{}'.format(subreddit), title, meta

def load():
    from michiru.modules import uribot
    uribot.URI_HANDLERS[URI_REGEXP] = {
        'handler': uri_reddit,
        'replacement': r'\1.json'
    }

def unload():
    from michiru.modules import uribot
    del uribot.URI_HANDLERS[URI_REGEXP]
