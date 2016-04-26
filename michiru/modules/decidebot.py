# Decide the important stuff.
import re
import random
import itertools
import bisect

from michiru import personalities
from michiru.modules import command
_ = personalities.localize


## Module information.
__name__ = 'decidebot'
__author__ = 'Shiz'
__license__ = 'WTFPL'
__desc__ = 'Decide on the important stuff.'

personalities.messages('tsun', {
    'Yes.':
        'Sure~!',
    'No.':
        'Michiru thinks that\'s a bad idea...',
    'Maybe.':
        'えとね。。。 maybe?',
    'Ask again later.':
        'Michiru\'s way~ too busy, another time!',
    'Why are you asking me?':
        'H-How would I know? BAKA! ┐（　｀ー´）┌',
    'Outlook hazy.':
        'M-Michiru doesn\'t even know what that means...'
})


## Module.

def weighed_choice(options):
    options, weights = list(options.keys()), list(options.values())

    total = sum(weights)
    distribution = itertools.accumulate(weights)

    r = random.random() * total
    i = bisect.bisect(distribution, r)
    return options[i]

@command(r'decide (.+)$')
def decide(bot, server, target, source, message, parsed, private, admin):
    options = re.split(r'\s*(\sor\s|,)\s*', parsed.group(1), re.IGNORECASE)
    if len(options) == 1:
        options = {
            _('Yes.'): 0.4,
            _('No.'): 0.4,
            _('Maybe.'): 0.05,
            _('Ask again later.'): 0.05,
            _('Why are you asking me?'): 0.05,
            _('Outlook hazy.'): 0.05
        }
    else:
        options = {option: 1 for option in options}

    option = weighed_choice(options)
    bot.message(target, _('{targ}: {decision}', targ=source, decision=option))


def load():
    return True

def unload():
    pass
