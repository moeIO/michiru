#!/usr/bin/env python3
# Loudbot module.
from datetime import datetime
import random

import config
import db
import personalities
from modules import command
_ = personalities.localize

__name__ = 'loudbot'
__author__ = 'Shiz'
__license__ = 'WTFPL'

config.ensure('loudbot_cutoff_length', 8)
config.ensure('loudbot_response_chance', 0.2)

db.ensure('shouts', {
    'id': db.ID,
    'server': (db.STRING, db.INDEX),
    'channel': (db.STRING, db.INDEX),
    'shouter': db.STRING,
    'shout': db.BINARY,
    'time': db.DATETIME
})

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
        'What shout are you talking about? Iiidiot.',
    'YOU taught me that (don\'t remember? Put down the bong!) on {date}.':
        'YOU taught me that! D-Don\'t tell me you don\'t remember!',
    '{nick} taught me that on {date}.':
        '{nick} taught me that, that no-good.'
})


last_shouts = {}

@command('([^a-z]+)$', case_sensitive=True, bare=True)
def shout(bot, server, target, source, message, parsed, private):
    global last_shouts
    shout = parsed.group(1)

    # Don't record shouts that are too short.
    if len(shout) < config.get('loudbot_cutoff_length'):
        return

    # Respond with another shout.
    if random.random() <= config.get('loudbot_response_chance'):
        # Fetch random shout.
        to_shout = db.from_('shouts').where('server', server).and_('channel', target) \
                                     .random().limit(1).single('id', 'shout')

        if to_shout:
            id, to_shout = to_shout
            to_shout = to_shout.decode('utf-8')

            # Store shout ID in case someone wants info on it.
            last_shouts[server, target] = id

            # Shout it.
            bot.privmsg(target, to_shout)

    # Add shout to database.
    db.to('shouts').add({
        'server': server,
        'channel': target,
        'shouter': source[0],
        'shout': shout.encode('utf-8'),
        'time': datetime.now()
    })

@command('who (.+)')
def who_shouted(bot, server, target, source, message, parsed, private):
    global last_shouts
    wanted = parsed.group(1)

    # Determine wanted shout.
    query = db.from_('shouts')

    if wanted == 'last':
        if (server, target) not in last_shouts.keys():
            bot.privmsg(target, _('No last shout for channel {chan} found.', serv=server, chan=target))
            return
        query.where('id', last_shouts[server, target])
    else:
        query.where('shout', wanted.encode('utf-8'))

    # Look it up.
    shout = query.limit(1).single('shouter', 'time')
    if not shout:
        bot.privmsg(target, _('Unknown shout for channel {chan}.', serv=server, chan=target))
        return

    # Give information.
    shouter, time = shout
    if shouter == source[0]:
        bot.privmsg(target, _('YOU taught me that (don\'t remember? Put down the bong!) on {date}.', date=time))
    else:
        bot.privmsg(target, _('{nick} taught me that on {date}.', nick=shouter, date=time))

def load():
    return True

def unload():
    pass
