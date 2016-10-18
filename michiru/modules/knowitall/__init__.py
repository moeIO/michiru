# Know-it-all module.
import random
import heapq
import asyncio

from michiru import personalities
from michiru.modules import command
_ = personalities.localize


## Module information.

__name__ = 'knowitall'
__author__ = 'Shiz'
__license__ = 'WTFPL'
__desc__ = 'Knows things better than you.'


## Configuration.

personalities.messages('tsun', {
    'Me.':
        'Michiru でーす！',
    'You.':
        'It\'s you! ( ´・‿-) ~ ♥',
    'I have no idea what you\'re talking about.':
        'I-I don\'t know what you\'re talking about, but you made the right choice by asking ME anyway! ( ´・‿-) ~ ♥',
    'What is this you are speaking of?':
        'I-It\'s not like I\'d tell someone like YOU, even if I knew!',
    'I\'ll keep it in mind for next time.':
        'S-stop bothering me with these weird things!',
    '{factoid}: {definition}':
        '{definition}'
})


## Commands.

@command('(.+)$', fallback=True)
def raw_whatis(bot, server, target, source, message, parsed, private, admin):
    wanted = parsed.group(1).strip()

    definition = yield from get_definition(bot, wanted, source=source, server=server, channel=target)
    yield from bot.message(target, _(bot, '{factoid}: {definition}', source=source, factoid=wanted, definition=definition))

@command('(?:what|who|where|how|why)(?: am| is|\'s|are|\'re) (?:an? |the )?(.+)\??$')
@command('(tell .+)\.?')
@command('define (.+)\.?')
def whatis(bot, server, target, source, message, parsed, private, admin):
    wanted = parsed.group(1).strip()
    definition = yield from get_definition(bot, wanted, source=source, server=server, channel=target)
    yield from bot.message(target, _(bot, '{factoid}: {definition}', source=source, factoid=wanted, definition=definition))


## Utility functions.

@asyncio.coroutine
def define_builtin(definition, bot, source, server, channel):
    if definition == bot.nickname:
        return _(bot, 'Me.')
    elif wanted == source:
        return _(bot, 'You.')

@asyncio.coroutine
def get_definition(bot, wanted, sources=None, source=None, server=None, channel=None):
    """ Try to define something through several sources. """
    definition = None

    for prio, name, f in SOURCES:
        if sources and name not in sources:
            continue
        try:
            definition = yield from f(wanted, bot, source, server, channel)
        except:
            continue
        if definition:
            break

    # Dummy texts.
    if not definition:
        dunnolol = [
            _(bot, 'I have no idea what you\'re talking about.', wanted=wanted),
            _(bot, 'What is this you are speaking of?', wanted=wanted),
            _(bot, 'I\'ll keep it in mind for next time.', wanted=wanted)
        ]
        definition = random.choice(dunnolol)

    return definition


## Boilerplate.

SOURCES = [
    (0, 'builtin', define_builtin)
]

def load():
    return True

def register(prio, name, func):
    heapq.heappush(SOURCES, (prio, name, func))

def unload():
    pass

def unregister(prio, name, func):
    SOURCES.remove((prio, name, func))
