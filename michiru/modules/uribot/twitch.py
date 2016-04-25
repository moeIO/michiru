# URI title bot - Twitch module.
import re
import json

from michiru import config, modules


## Module information.

__name__ = 'uribot.twitch'
__author__ = 'Shiz'
__license__ = 'WTFPL'
__desc__ = 'Gives URL information for Twitch links.'
__deps__ = ['uribot']

config.item('uribot.api.twitch', None)
URI_REGEXP = re.compile(r'^https?://(?:www\.)?twitch\.tv/([a-zA-Z0-0_-]+)$')


## Module.

def uri_twitch(contents, matches):
    """ Extract Twitch.tv channel information. """
    channel = json.loads(contents)

    title = channel['status'].replace('\n', ' ')
    title = re.sub(r'\s+', ' ', title).strip()
    game = channel['game'].replace('\n', ' ')
    game = re.sub(r'\s+', ' ', game).strip()

    return 'Twitch: {}'.format(channel['display_name']), title, game

def load():
    from michiru.modules import uribot
    uribot.URI_HANDLERS[URI_REGEXP] = {
        'enabled': lambda: config.get('uribot.api.twitch'),
        'handler': uri_twitch,
        'replacement': r'https://api.twitch.tv/kraken/channels/\1',
        'headers': {
            'Client-ID': config.get('uribot.api.twitch'),
            'Accept': 'application/vnd.twitchtv.v3+json'
        }
    }

def unload():
    from michiru.modules import uribot
    del uribot.URI_HANDLERS[URI_REGEXP]
