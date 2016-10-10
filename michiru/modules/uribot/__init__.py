# URI title bot.
import re
import json
import urllib.parse
import traceback

import requests
import bs4
import aniso8601

from michiru import config, personalities, version
from michiru.modules import command
_ = personalities.localize


## Module information.

__name__ = 'uribot'
__author__ = 'Shiz'
__license__ = 'WTFPL'
__desc__ = 'Gives URL information.'


## Configuration and constants.

config.item('uribot.user_agent', '{}/{}'.format(version.__name__, version.__version__))
config.item('uribot.use_whitelist', False)
config.item('uribot.whitelist', [])
config.item('uribot.verbose_errors', False)


# Thanks Hitler, Obama and Daring Fireball.
URI_REGEXP = re.compile(r"""(?i)\b((?:https?://|www\d{0,3}[.]|[a-z0-9.\-]+[.][a-z]{2,4}/)(?:[^\s()<>]+|\(([^\s()<>]+|(\([^\s()<>]+\)))*\))+(?:\(([^\s()<>]+|(\([^\s()<>]+\)))*\)|[^\s`!()\[\]{};:'".,<>?«»“”‘’]))""")


## URI handlers.

def uri_title(response, matches):
    """ Extract a regular URL title. """
    content_type = response.headers.get('content-type', 'text/html')
    content_type = content_type.split(';')[0].strip().lower()
    if content_type not in ('text/html', 'text/xml', 'text/xhtml', 'application/xml', 'application/xhtml+xml'):
        return None

    html = bs4.BeautifulSoup(response.text)

    # Very basic stuff, thanks to BeautifulSoup.
    if not html.title or not html.title.string:
        return None
    title = html.title.string.strip()
    title = title.replace('\n', ' ')
    title = re.sub(r'\s+', ' ', title)

    return 'Title', title, None



# All URI handlers.
URI_HANDLERS = {}


## Commands.

@command(r'(?:^|.*\s)https?://', bare=True)
def uri(bot, server, target, source, message, parsed, private, admin):
    global URI_REGEXP, URI_HANDLERS

    # Find all URIs and process them.
    for match in re.findall(URI_REGEXP, message):
        uri = match[0]
        matches = None

        # Use whitelist if we have to.
        if config.get('uribot.use_whitelist', server, target):
            components = urllib.parse.urlparse(uri)
            host = components.netloc.split(':', 1)[0]

            # Verify against whitelist.
            for h in config.list('uribot.whitelist', server, target):
                if host.endswith(h):
                    break
            else:
                continue

        # Stock handler: extract the URI.
        handler = uri_title
        headers = {}

        # See if we want a custom handler.
        for matcher, details in URI_HANDLERS.items():
            if not details.get('enabled', lambda: True)():
                continue

            matches = matcher.match(uri)

            if matches:
                if 'replacement' in details:
                    uri = matcher.sub(details['replacement'], uri)
                if 'headers' in details:
                    headers.update(details['headers'])
                handler = details['handler']
                break


        # Do request.
        headers.setdefault('User-Agent', config.get('uribot.user_agent', server, target))
        try:
            response = requests.get(uri, headers=headers, stream=True, timeout=1)
        except:
            traceback.print_exc()
            if config.get('uribot.verbose_errors', server, target):
                raise
            continue
        if response.status_code >= 400:
            if config.get('uribot.verbose_errors', server, target):
                bot.message(target, _('Couldn\'t load URL! Response code: {}'.format(response.status_code)))
            continue

        # Parse response.
        try:
            res = handler(response, matches)
            if not res:
                continue
        except:
            traceback.print_exc()
            if config.get('uribot.verbose_errors', server, target):
                raise
            continue

        type, title, meta = res

        # Post info.
        if meta:
            bot.message(target, _('[{type}] {b}{title}{/b} ({meta})', type=type, title=title, meta=meta))
        else:
            bot.message(target, _('[{type}] {b}{title}{/b}', type=type, title=title, meta=meta))


## Module boilerplate.

def load():
    global URI_HANDLERS

    # Precompile all URI handler regexps.
    for match, value in list(URI_HANDLERS.items()):
        URI_HANDLERS[re.compile(match)] = value
        del URI_HANDLERS[match]

    return True

def unload():
    pass
