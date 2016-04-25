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
config.item('uribot.api.youtube', None)
config.item('uribot.api.soundcloud', None)
config.item('uribot.api.twitch', None)


# Thanks Hitler, Obama and Daring Fireball.
URI_REGEXP = re.compile(r"""(?i)\b((?:https?://|www\d{0,3}[.]|[a-z0-9.\-]+[.][a-z]{2,4}/)(?:[^\s()<>]+|\(([^\s()<>]+|(\([^\s()<>]+\)))*\))+(?:\(([^\s()<>]+|(\([^\s()<>]+\)))*\)|[^\s`!()\[\]{};:'".,<>?«»“”‘’]))""")


## URI handlers.

def uri_title(contents, matches):
    """ Extract a regular URL title. """
    html = bs4.BeautifulSoup(contents)

    # Very basic stuff, thanks to BeautifulSoup.
    if not html.title:
        return None
    return 'Title', html.title.string.strip(), ''

def uri_youtube(contents, matches):
    """ Extract YouTube video information. """
    video = json.loads(contents)
    info = video['items'][0]['snippet']
    details = video['items'][0]['contentDetails']

    duration = int(aniso8601.parse_duration(details['duration']).total_seconds())
    meta = '{}:{:02}'.format(*divmod(duration, 60))

    return 'YouTube: {}'.format(info['channelTitle']), info['title'], meta

def uri_soundcloud(contents, matches):
    """ Extract SoundCloud song information. """
    song = json.loads(contents)

    title = song['title'].replace('\n', ' ')
    title = re.sub(r'\s+', ' ', title).strip()
    duration = int(round(song['duration'] / 1000))
    meta = '{}:{:02}'.format(*divmod(duration, 60))

    return 'SoundCloud: {}'.format(song['user']['username']), title, meta

def uri_twitch(contents, matches):
    """ Extract Twitch.tv channel information. """
    channel = json.loads(contents)

    title = channel['status'].replace('\n', ' ')
    title = re.sub(r'\s+', ' ', title).strip()
    game = channel['game'].replace('\n', ' ')
    game = re.sub(r'\s+', ' ', game).strip()

    return 'Twitch: {}'.format(channel['display_name']), title, game

def uri_reddit(contents, matches):
    """ Extract Reddit thread information. """
    post, comments = json.loads(contents)
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

    # Get metadata.
    meta = None
    if not data.get('score_hidden'):
        meta = '↑↓{}'.format(data['score'])

    return 'Reddit: /r/{}'.format(subreddit), title, meta


def uri_twitter(contents, matches):
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
        likes = html.find('ul', class_='stats').find('li', class_='js-stat-favorites').strong.string
    except:
        likes = None

    # Extract images.
    images = html.find_all('meta', property='og:image')
    for image in images:
        url = image['content'].rsplit(':', maxsplit=1)[0]
        if re.match(r'(?:https?://)?pic\.twitter\.com/[a-zA-Z0-9_-]+', tweet):
            tweet = re.sub(r'(?:https?://)?pic\.twitter\.com/[a-zA-Z0-9_-]+', url, tweet)
        elif re.match(r'(?:https?://)t\.co/[a-zA-Z0-9_-]+', tweet):
            tweet = re.sub(r'(?:https?://)t\.co/[a-zA-Z0-9_-]+', url, tweet)
        else:
            tweet += ' ' + url
    # Un-cramp URLs.
    tweet = re.sub(r'(?!\s+)http(s)?:', r' http\1:', tweet)
    # Post-process tweet a bit.
    tweet = re.sub(r'\s+', ' ', tweet).strip()

    # Build metadata.
    meta = []
    if retweets:
        meta.append('↻ ' + retweets)
    if likes:
        meta.append('♥ ' + likes)

    return 'Twitter: {}'.format(user), tweet, ', '.join(meta)

def uri_4chan(contents, matches):
    """ Extract 4chan thread information. """
    thread = json.loads(contents)
    wanted = None

    # Check if we want to actually have a linked post instead of the OP.
    if matches.group(3):
        try:
            wanted = int(matches.group(3))
        except:
            pass

    title = None
    comment = None
    # We want a given number.
    if wanted:
        for post in thread['posts']:
            if post['no'] == wanted:
                # Found the post!
                comment = post['com']

    # We want the OP.
    if not comment:
        op = thread['posts'][0]
        if 'sub' in op:
            # Use thread title as URL title.
            title = op['sub']
        else:
            comment = post['com']

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

def uri_danbooru(contents, matches):
    """ Extract Danbooru post information. """
    post = json.loads(contents)

    url = 'http://danbooru.donmai.us{}'.format(post['file_url'])
    artists = [tag.replace('_', ' ').title() for tag in post['tag_string_artist'].split()]
    tags = [tag.replace('_', ' ').title() for tag in post['tag_string_character'].split()]

    return 'Danbooru: {}'.format(', '.join(artists)), url, ', '.join(tags)


# All URI handlers.
URI_HANDLERS = {
    # YouTube video.
    r'^https?://(?:www\.)youtube\.com/watch\?(?:\S*)v=([a-zA-Z0-9_-]+)(?:[&#]\S*)?$': {
        'enabled': lambda: config.get('uribot.api.youtube'),
        'handler': uri_youtube,
        'replacement': r'https://www.googleapis.com/youtube/v3/videos?id=\1&key={}&part=snippet,contentDetails&fields=items(id,snippet(title,channelTitle),contentDetails(duration))'.format(config.get('uribot.api.youtube'))
    },
    # Soundcloud song.
    r'^https?://(?:www\.)?soundcloud\.com/([a-zA-Z0-9_-]+)/([a-zA-Z0-9_-]+)$': {
        'enabled': lambda: config.get('uribot.api.soundcloud'),
        'handler': uri_soundcloud,
        'replacement': r'https://api.soundcloud.com/resolve.json?url=https://soundcloud.com/\1/\2&client_id={}'.format(config.get('uribot.api.soundcloud'))
    },
    # Twitch channel.
    r'^https?://(?:www\.)?twitch\.tv/([a-zA-Z0-0_-]+)$': {
        'enabled': lambda: config.get('uribot.api.twitch'),
        'handler': uri_twitch,
        'replacement': r'https://api.twitch.tv/kraken/channels/\1',
        'headers': {
            'Client-ID': config.get('uribot.api.twitch'),
            'Accept': 'application/vnd.twitchtv.v3+json'
        }
    },
    # Reddit post/comment.
    r'^(https?://(?:.*?\.){0,1}reddit\.com/r/([a-zA-Z0-9_-]+)/comments/([a-zA-Z0-9_-]+)/(?:[a-zA-Z0-9_-]+)(?:/([a-zA-Z0-9_-]+))?/?)(?:[?&#]\S*)?$': {
        'handler': uri_reddit,
        'replacement': r'\1.json'
    },
    # Twitter status.
    r'^https?://(?:www\.){0,1}twitter\.com/([a-zA-Z0-9_-]+)/status/([0-9]+)(?:[?#&]\S*)?$': {
        'handler': uri_twitter,
    },
    # 4chan thread/post.
    r'^https?://boards\.4chan\.org/([a-z0-9]+)/thread/([0-9]+)(?:/[a-z0-9_-]+/?)?(?:#p?([0-9]+))?$': {
        'handler': uri_4chan,
        'replacement': r'https://api.4chan.org/\1/res/\2.json'
    },
    # Danbooru post.
    r'^https?://danbooru.donmai.us/posts/([0-9]+)(?:\?.*)?$': {
        'handler': uri_danbooru,
        'replacement': r'https://danbooru.donmai.us/posts/\1.json'
    }
}


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
            response = requests.get(uri, headers=headers)
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
            res = handler(response.text, matches)
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
