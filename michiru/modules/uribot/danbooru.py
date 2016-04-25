# URI title bot - Danbooru module.
import re
import json

from michiru import modules


## Module information.

__name__ = 'uribot.danbooru'
__author__ = 'Shiz'
__license__ = 'WTFPL'
__desc__ = 'Gives URL information for Danbooru links.'
__deps__ = ['uribot']

URI_REGEXP = re.compile(r'^https?://danbooru.donmai.us/posts/([0-9]+)(?:\?.*)?$')


## Module.

def uri_danbooru(contents, matches):
    """ Extract Danbooru post information. """
    post = json.loads(contents)

    url = 'http://danbooru.donmai.us{}'.format(post['file_url'])
    artists = [tag.replace('_', ' ').title() for tag in post['tag_string_artist'].split()]
    tags = [tag.replace('_', ' ').title() for tag in post['tag_string_character'].split()]

    return 'Danbooru: {}'.format(', '.join(artists)), url, ', '.join(tags)

def load():
    from michiru.modules import uribot
    uribot.URI_HANDLERS[URI_REGEXP] = {
        'handler': uri_danbooru,
        'replacement': r'https://danbooru.donmai.us/posts/\1.json'
    }

def unload():
    from michiru.modules import uribot
    del uribot.URI_HANDLERS[URI_REGEXP]
