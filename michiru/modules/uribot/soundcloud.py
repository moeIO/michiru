# URI title bot - SoundCloud module.
import re
import json

from michiru import config, modules


## Module information.

__name__ = 'uribot.soundcloud'
__author__ = 'Shiz'
__license__ = 'WTFPL'
__desc__ = 'Gives URL information for SoundCloud links.'
__deps__ = ['uribot']

config.item('api.soundcloud.client_id', None)
URI_REGEXP = re.compile(r'^https?://(?:www\.)?soundcloud\.com/([a-zA-Z0-9_-]+)/([a-zA-Z0-9_-]+)$')


## Module.

def uri_soundcloud(bot, response, matches):
    """ Extract SoundCloud song information. """
    song = json.loads(response.text)

    title = song['title'].replace('\n', ' ')
    title = re.sub(r'\s+', ' ', title).strip()
    duration = int(round(song['duration'] / 1000))
    meta = '{}:{:02}'.format(*divmod(duration, 60))

    return 'SoundCloud: {}'.format(song['user']['username']), title, meta

def load():
    from michiru.modules import uribot
    uribot.URI_HANDLERS[URI_REGEXP] = {
        'enabled': lambda: config.get('api.soundcloud.client_id'),
        'handler': uri_soundcloud,
        'replacement': r'https://api.soundcloud.com/resolve.json?url=https://soundcloud.com/\1/\2&client_id={}'.format(config.get('api.soundcloud.client_id'))
    }

def unload():
    from michiru.modules import uribot
    del uribot.URI_HANDLERS[URI_REGEXP]
