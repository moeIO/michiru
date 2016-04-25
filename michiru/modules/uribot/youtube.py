# URI title bot - YouTube module.
import re
import json
import aniso8601

from michiru import config, modules


## Module information.

__name__ = 'uribot.youtube'
__author__ = 'Shiz'
__license__ = 'WTFPL'
__desc__ = 'Gives URL information for YouTube links.'
__deps__ = ['uribot']

config.item('uribot.api.youtube', None)
URI_REGEXP = re.compile(r'^https?://(?:www\.)youtube\.com/watch\?(?:\S*)v=([a-zA-Z0-9_-]+)(?:[&#]\S*)?$')


## Module.

def uri_youtube(contents, matches):
    """ Extract YouTube video information. """
    video = json.loads(contents)
    info = video['items'][0]['snippet']
    details = video['items'][0]['contentDetails']

    duration = int(aniso8601.parse_duration(details['duration']).total_seconds())
    meta = '{}:{:02}'.format(*divmod(duration, 60))

    return 'YouTube: {}'.format(info['channelTitle']), info['title'], meta

def load():
    from michiru.modules import uribot
    uribot.URI_HANDLERS[URI_REGEXP] = {
        'enabled': lambda: config.get('uribot.api.youtube'),
        'handler': uri_youtube,
        'replacement': r'https://www.googleapis.com/youtube/v3/videos?id=\1&key={}&part=snippet,contentDetails&fields=items(id,snippet(title,channelTitle),contentDetails(duration))'.format(config.get('uribot.api.youtube'))
    }

def unload():
    from michiru.modules import uribot
    del uribot.URI_HANDLERS[URI_REGEXP]
