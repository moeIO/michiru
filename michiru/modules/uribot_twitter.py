# URI title bot - Twitter module.
import re
import bs4

from michiru import config, modules


## Module information.

__name__ = 'uribot_twitter'
__author__ = 'Shiz'
__license__ = 'WTFPL'
__desc__ = 'Gives URL information for Twitter links.'
__deps__ = ['uribot']

URI_REGEXP = re.compile(r'^https?://(?:www\.){0,1}twitter\.com/([a-zA-Z0-9_-]+)/status/([0-9]+)(?:[?#&]\S*)?$')


## Module.

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
        if re.search(r'(?:https?://)?pic\.twitter\.com/[a-zA-Z0-9_-]+', tweet):
            tweet = re.sub(r'(?:https?://)?pic\.twitter\.com/[a-zA-Z0-9_-]+', url, tweet)
        elif re.search(r'(?:https?://)t\.co/[a-zA-Z0-9_-]+', tweet):
            tweet = re.sub(r'(?:https?://)t\.co/[a-zA-Z0-9_-]+', url, tweet)
        else:
            tweet += ' ' + url
    # Un-cramp URLs.
    tweet = re.sub(r'(?!\s+)http(s?):', r' http\1:', tweet)
    # Post-process tweet a bit.
    tweet = re.sub(r'\s+', ' ', tweet).strip()

    # Build metadata.
    meta = []
    if retweets:
        meta.append('↻ ' + retweets)
    if likes:
        meta.append('♥ ' + likes)

    return 'Twitter: {}'.format(user), tweet, ', '.join(meta)

def load():
    uribot = modules.get('uribot')
    uribot.URI_HANDLERS[URI_REGEXP] = {
        'handler': uri_twitter,
    }

def unload():
    uribot = modules.get('uribot')
    del uribot.URI_HANDLERS[URI_REGEXP]
