# Know-it-all Wolfram|Alpha module.
import re
import wolframalpha
from michiru import config, personalities
from michiru.modules import command
_ = personalities.localize


## Module information.

__name__ = 'knowitall.wolframalpha.appid'
__author__ = 'Shiz'
__license__ = 'WTFPL'
__desc__ = 'Get knowledge from Wolfram|Alpha.'


## Configuration.

config.item('api.wolframalpha', None)


## Module.

@command('calculate (.+)')
def calculate(bot, server, target, source, message, parsed, private, admin):
    from michiru.modules import knowitall

    wanted = parsed.group(1).strip()
    definition = knowitall.get_definition(bot, wanted, sources=['Wolfram|Alpha'], source=source, server=server, channel=target)
    bot.message(target, _('{factoid}: {definition}', source=source, factoid=wanted, definition=definition))

def define_wolframalpha(definition, bot, source, server, channel):
    client = wolframalpha.Client(config.get('api.wolframalpha.appid', server, channel))
    res = client.query(definition)

    defs = []
    for pod in res.pods:
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
            defs.append(text)

    if defs:
        return ' | '.join(defs)

def load():
    from michiru.modules import knowitall
    knowitall.register(10, 'Wolfram|Alpha', define_wolframalpha)
    return True

def unload():
    from michiru.modules import knowitall
    knowitall.deregister(10, 'Wolfram|Alpha', define_wolframalpha)
