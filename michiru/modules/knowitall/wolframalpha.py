# Know-it-all Wolfram|Alpha module.
import re
import asyncio
import wolframalpha

from michiru import config, personalities
from michiru.modules import command
_ = personalities.localize


## Module information.

__name__ = 'knowitall.wolframalpha.appid'
__author__ = 'Shiz'
__license__ = 'WTFPL'
__desc__ = 'Get knowledge from Wolfram|Alpha.'
__deps__ = ['knowitall']


## Configuration.

config.item('api.wolframalpha', None)


## Module.

@command('calculate (.+)')
def calculate(bot, server, target, source, message, parsed, private, admin):
    from michiru.modules import knowitall

    wanted = parsed.group(1).strip()
    definition = yield from knowitall.get_definition(bot, wanted, sources=['Wolfram|Alpha'], source=source, server=server, channel=target)
    yield from bot.message(target, _(bot, '{factoid}: {definition}', source=source, factoid=wanted, definition=definition))

@asyncio.coroutine
def define_wolframalpha(definition, bot, source, server, channel):
    client = wolframalpha.Client(config.get('api.wolframalpha.appid', server, channel))
    res = yield from bot.loop.run_in_executor(None, client.query, definition)

    defs = []
    for pod in res.pods:
        if pod.title in ('Input', 'Input interpretation'):
            continue

        text = pod.text
        if text:
            if pod.title and pod.title not in ('Result', 'Response', 'Answer') and 'approximation' not in pod.title:
                text = '{b}[{title}]{/b} '.format(title=pod.title, **bot.FORMAT_CODES) + text
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
            if not pod.title or pod.title in ('Result', 'Response', 'Answer') or 'approximation' in pod.title:
                break

    if defs:
        return ' | '.join(defs)

def load():
    from michiru.modules import knowitall
    knowitall.register(10, 'Wolfram|Alpha', define_wolframalpha)
    return True

def unload():
    from michiru.modules import knowitall
    knowitall.unregister(10, 'Wolfram|Alpha', define_wolframalpha)
