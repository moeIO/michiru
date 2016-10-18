# Loudbot module.
from datetime import datetime
import random

from michiru import config, db, personalities
from michiru.modules import command
_ = personalities.localize


## Module information.
__name__ = 'loudbot'
__author__ = 'Shiz'
__license__ = 'WTFPL'
__desc__ = 'LOUDER'


## Configuration, database stuff and globals.

config.item('loudbot.cutoff_length', 8)
config.item('loudbot.response_chance', 0.2)

db.table('shouts', {
    'id': db.ID,
    'server': (db.STRING, db.INDEX),
    'channel': (db.STRING, db.INDEX),
    'shouter': db.STRING,
    'shout': db.BINARY,
    'time': db.DATETIME
})

last_shouts = {}


## Personalities.

personalities.messages('fancy', {
    'No last shout for channel {chan} found.':
        'No last shout for channel {b}[{serv}:{chan}]{/b} found.',
    'Unknown shout for channel {chan}.':
        'Unknown shout for channel {b}[{serv}:{chan}]{/b}.',
    'YOU taught me that (don\'t remember? Put down the bong!) on {date}.':
        '{b}YOU{/b} taught me that (don\'t remember? Put down the bong!) on {b}{date}{/b}.',
    '{nick} taught me that on {date}.':
        '{b}{nick}{/b} taught me that on {b}{date}{/b}.'
})

personalities.messages('tsun', {
    'No last shout for channel {chan} found.':
        'I-I don\'t know anything about that channel!',
    'Unknown shout for channel {chan}.':
        'Which shout are you talking about? バカ！',
    'YOU taught me that (don\'t remember? Put down the bong!) on {date}.':
        'YOU taught me that! D-Don\'t tell me you don\'t remember!',
    '{nick} taught me that on {date}.':
        'That no-good {nick} taught me that! ( ¯◡◡¯·)'
})


## Commands.

@command('([^a-z]+)$', case_sensitive=True, bare=True)
def shout(bot, server, target, source, message, parsed, private, admin):
    global last_shouts
    shout = parsed.group(1)

    # Don't record shouts that are too short.
    if len(shout) < config.get('loudbot.cutoff_length'):
        return

    # Respond with another shout.
    if random.random() <= config.get('loudbot.response_chance'):
        # Fetch random shout.
        to_shout = db.from_('shouts').where('server', server).and_('channel', target) \
                                     .random().limit(1).single('id', 'shout')

        if to_shout:
            id, to_shout = to_shout
            to_shout = to_shout.decode('utf-8')

            # Store shout ID in case someone wants info on it.
            last_shouts[server, target] = id

            # Shout it.
            yield from bot.message(target, to_shout)

    # Add shout to database.
    db.to('shouts').add({
        'server': server,
        'channel': target,
        'shouter': source,
        'shout': shout.encode('utf-8'),
        'time': datetime.now()
    })

@command('who (.+)')
def who_shouted(bot, server, target, source, message, parsed, private, admin):
    global last_shouts
    wanted = parsed.group(1)

    # Determine wanted shout.
    query = db.from_('shouts')

    if wanted == 'last':
        if (server, target) not in last_shouts.keys():
            yield from bot.message(target, _(bot, 'No last shout for channel {chan} found.', serv=server, chan=target))
            return
        query.where('id', last_shouts[server, target])
    else:
        query.where('shout', wanted.encode('utf-8'))

    # Look it up.
    shout = query.limit(1).single('shouter', 'time')
    if not shout:
        yield from bot.message(target, _(bot, 'Unknown shout for channel {chan}.', serv=server, chan=target))
        return

    # Give information.
    shouter, time = shout
    if shouter == source:
        yield from bot.message(target, _(bot, 'YOU taught me that (don\'t remember? Put down the bong!) on {date}.', date=time))
    else:
        yield from bot.message(target, _(bot, '{nick} taught me that on {date}.', nick=bot.highlight(shouter), date=time))


## Boilerplate.

def load():
    return True

def unload():
    pass
