#!/usr/bin/env python3
# Know-it-all module.
import re
import json
import random
import urbandict
import wolframalpha

import config
import personalities
from modules import command
_ = personalities.localize

__name__ = 'know-it-all'
__author__ = 'Shiz'
__license__ = 'WTFPL'

config.ensure('knowitall_wolfram_api_key', None)


@command('(?:what|who|where|how|why)(?: am| is|\'s|are|\'re) (?:an? |the )?(.+)\??$')
@command('(tell .+)\.?')
@command('define (.+)\.?')
def whatis(bot, server, target, source, message, parsed, private):
    wanted = parsed.group(1).strip()

    # Obvious edge cases.
    if wanted == bot.current_nick:
        bot.privmsg(target, _('Me.'))
        return
    elif wanted == source[0]:
        bot.privmsg(target, _('You.'))
        return
    
    definition = get_definition(wanted)
    bot.privmsg(target, definition)

@command('calculate (.+)')
def calculate(bot, server, target, source, message, parsed, private):
    wanted = parsed.group(1).strip()
    definition = get_definition(wanted, sources=['wolframalpha'])
    bot.privmsg(target, definition)


def get_definition(wanted, sources=['urbandictionary', 'wolframalpha']):
    """ Try to define something through several sources. """
    definition = None

    # See if urbandictionary knows something.
    if 'urbandictionary' in sources:
        udres = urbandict.define(wanted)
        if udres:
            definition = udres[0]['def']
            # Remove annoying formatting we can't do anything with.
            definition = re.sub(r'\[(.+?)\](.+?)\[\/\1\]', r'\2', definition)
            definition = re.sub(r'\[(.+?)\]', r'\1', definition)
            definition = re.sub(r'\\n', '\n', definition)
            definition = re.sub(r'\s+', ' ', definition)

    # WolframAlpha for scientific inquiries and the like.
    if not definition and 'wolframalpha' in sources:
        client = wolframalpha.Client(config.current['knowitall_wolfram_api_key'])
        wares = client.query(wanted)

        wadef = []
        for pod in wares.pods:
            text = pod.text
            if text:
                if pod.title and pod.title != 'Result' and pod.title != 'Input interpretation':
                    text = '{b}[{title}]{/b} '.format(title=pod.title, **personalities.IRC_CODES) + text
                text = text.strip()
                # Reorder formatting a bit.
                text = text.replace('\n', ' - ')
                text = text.replace(' | ', ': ')
                text = re.sub(r' - \(as seen by .+?\)', '', text)
                text = re.sub(r' - \(according to .+?\)', '', text)
                text = re.sub(r' - \(', ' (', text)
                text = re.sub(r'\s+', ' ', text)
                wadef.append(text)

        if wadef:
            definition = ' | '.join(wadef)

    # Dummy texts.
    if not definition:
        dunnolol = [
            _('I have no idea what you\'re talking about.', wanted=wanted),
            _('What is this you are speaking of?', wanted=wanted),
            _('I\'ll keep it in mind for next time.', wanted=wanted)
        ]
        definition = random.choice(dunnolol)

    return definition


# Module stuff.
def load():
    return True

def unload():
    pass
