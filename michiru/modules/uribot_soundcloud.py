# URI title bot - SoundCloud module.
import re
import json

from michiru import config, modules


## Module information.

__name__ = 'uribot_soundcloud'
__author__ = 'Shiz'
__license__ = 'WTFPL'
__desc__ = 'Gives URL information for SoundCloud links.'
__deps__ = ['uribot']

config.item('uribot.api.soundcloud', None)
URI_REGEXP = re.compile(r'^https?://(?:www\.)?soundcloud\.com/([a-zA-Z0-9_-]+)/([a-zA-Z0-9_-]+)$')


## Module.

def uri_soundcloud(contents, matches):
    """ Extract SoundCloud song information. """
    song = json.loads(contents)

    title = song['title'].replace('\n', ' ')
    title = re.sub(r'\s+', ' ', title).strip()
    duration = int(round(song['duration'] / 1000))
    meta = '{}:{:02}'.format(*divmod(duration, 60))

    return 'SoundCloud: {}'.format(song['user']['username']), title, meta

def load():
    uribot = modules.get('uribot')
    uribot.URI_HANDLERS[URI_REGEXP] = {
        'enabled': lambda: config.get('uribot.api.soundcloud'),
        'handler': uri_soundcloud,
        'replacement': r'https://api.soundcloud.com/resolve.json?url=https://soundcloud.com/\1/\2&client_id={}'.format(config.get('uribot.api.soundcloud'))
    }

def unload():
    uribot = modules.get('uribot')
    del uribot.URI_HANDLERS[URI_REGEXP]
