# Know-it-all module.
import re
import json
import random
import urbandict
import wolframalpha

from michiru import config, db, personalities
from michiru.modules import command
_ = personalities.localize


## Module information.

__name__ = 'know-it-all'
__author__ = 'Shiz'
__license__ = 'WTFPL'
__desc__ = 'Knows things better than you.'


## Configuration.

config.item('knowitall.wolfram_api_key', None)

db.table('factoids', {
    'id': db.INT,
    'factoid': (db.STRING, db.INDEX),
    'definition': db.STRING
})

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
    '{factoid} defined.':
        'gotcha!',
    '{factoid} deleted.':
        'gotcha!',
    'Unknown definition: {factoid}':
        'I-I didn\'t know much about {factoid} in the first place... (´･ω･`)',
    '{factoid}: {definition}':
        '{definition}'
})


## Commands.

@command('(\S+)[:,] (.+)$', fallback=True, bare=True)
def raw_whatis(bot, server, target, source, message, parsed, private, admin):
    addressed = parsed.group(1)
    wanted = parsed.group(2).strip()

    if addressed.lower() != bot.nickname.lower():
        return

    definition = get_definition(bot, wanted, source=source, server=server, channel=target)
    bot.message(target, _('{factoid}: {definition}', source=source, factoid=wanted, definition=definition))

@command('(?:what|who|where|how|why)(?: am| is|\'s|are|\'re) (?:an? |the )?(.+)\??$')
@command('(tell .+)\.?')
@command('define (.+)\.?')
def whatis(bot, server, target, source, message, parsed, private, admin):
    wanted = parsed.group(1).strip()
    definition = get_definition(bot, wanted, source=source, server=server, channel=target)
    bot.message(target, _('{factoid}: {definition}', source=source, factoid=wanted, definition=definition))

@command('calculate (.+)')
def calculate(bot, server, target, source, message, parsed, private, admin):
    wanted = parsed.group(1).strip()
    definition = get_definition(bot, wanted, sources=['wolframalpha'], source=source, server=server, channel=target)
    bot.message(target, _('{factoid}: {definition}', source=source, factoid=wanted, definition=definition))

@command(r'(\S+) is (.*[^\?])$')
def define(bot, server, target, source, message, parsed, private, admin):
    factoid = parsed.group(1)
    definition = parsed.group(2).strip()

    if factoid in ('what', 'who', 'where', 'how', 'why'):
        return

    db.from_('factoids').where('factoid', factoid).delete()
    db.to('factoids').add({
        'factoid': factoid,
        'definition': definition
    })

    bot.message(target, _('{factoid} defined.', source=source, factoid=factoid, definition=definition))

@command(r'forget about (\S+)$')
def undefine(bot, server, target, source, message, parsed, private, admin):
    factoid = parsed.group(1)

    if db.from_('factoids').where('factoid', factoid).delete():
        bot.message(target, _('{factoid} deleted.', source=source, factoid=factoid))
    else:
        bot.message(target, _('Unknown definition: {factoid}', source=source, factoid=factoid))

## Utility functions.

def get_definition(bot, wanted, sources=['builtin', 'factoids', 'urbandictionary', 'wolframalpha'], source=None, server=None, channel=None):
    """ Try to define something through several sources. """
    definition = None

    # Builtin stuff.
    if not definition and 'builtin' in sources:
        if wanted == bot.nickname:
            definition = _('Me.')
        elif wanted == source:
            definition = _('You.')

    # User-defined factoids.
    if not definition and 'factoids' in sources:
        query = db.from_('factoids').where('factoid', wanted).single('definition')
        if query:
            definition = query['definition']

    # See if urbandictionary knows something.
    if not definition and 'urbandictionary' in sources:
        udres = urbandict.define(wanted)
        if udres:
            definition = udres['definitions'][0]['definition']
            # Remove annoying formatting we can't do anything with.
            definition = re.sub(r'\[(.+?)\](.+?)\[\/\1\]', r'\2', definition)
            definition = re.sub(r'\[(.+?)\]', r'\1', definition)
            definition = re.sub(r'\\n', '\n', definition)
            definition = re.sub(r'\s+', ' ', definition)

    # WolframAlpha for scientific inquiries and the like.
    if not definition and 'wolframalpha' in sources:
        client = wolframalpha.Client(config.get('knowitall.wolfram_api_key', server, channel))
        wares = client.query(wanted)

        wadefs = []
        for pod in wares.pods:
            if pod.title == 'Input interpretation':
                continue

            text = pod.text
            if text:
                if pod.title and pod.title != 'Result' and pod.title != 'Input interpretation':
                    text = '{b}[{title}]{/b} '.format(title=pod.title, **personalities.IRC_CODES) + text
                text = text.strip()
                # Reorder formatting a bit. WolframAlpha uses \:<unicode code> to represent unicode characters.
                text = text.replace('\n', ' - ')
                text = text.replace(' | ', ': ')
                text = re.sub('(\\:[a-z0-9]+)', lambda x: chr(int(x.group(1)[2:])), text)
                text = re.sub(r' - \(as seen by .+?\)', '', text)
                text = re.sub(r' - \(according to .+?\)', '', text)
                text = re.sub(r' - \(', ' (', text)
                text = re.sub(r'\s+', ' ', text)
                wadefs.append(text)

        if wadefs:
            definition = ' | '.join(wadefs)

    # Dummy texts.
    if not definition:
        dunnolol = [
            _('I have no idea what you\'re talking about.', wanted=wanted),
            _('What is this you are speaking of?', wanted=wanted),
            _('I\'ll keep it in mind for next time.', wanted=wanted)
        ]
        definition = random.choice(dunnolol)

    return definition


## Boilerplate.

def load():
    return True

def unload():
    pass
