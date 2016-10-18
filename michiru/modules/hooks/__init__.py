# Service hooks module.
import traceback
import functools
import threading
import asyncio
import flask

from michiru import config, chat, personalities
_ = personalities.localize


## Module information.

__name__ = 'hooks'
__author__ = 'Shiz'
__license__ = 'WTFPL'
__desc__ = 'Web hook collection.'

config.item('hooks.host', '0.0.0.0')
config.item('hooks.port', 8081)
config.item('hooks.services', {})


## Server stuff.

SERVER = flask.Flask('michiru.modules.hooks')
THREAD = None

@SERVER.route('/<name>', methods=['GET', 'POST', 'PUT', 'DELETE'])
def handle(name):
    if name not in HOOKS:
        flask.abort(404)

    # Get hook information.
    name, handler = HOOKS[name]
    cfg = config.get('hooks.services.' + name)

    # Filter.
    if 'allowed_ips' in cfg and cfg['allowed_ips'] and flask.request.remote_addr not in cfg['allowed_ips']:
        flask.abort(403)

    # Process.
    try:
        ident, messages = handler(cfg, flask.request)
    except:
        traceback.print_exc()
        flask.abort(500)

    # Message.
    for server in cfg['targets'].get(ident, {}):
        if server not in chat.bots:
            continue
        bot = chat.bots[server]

        for channel in cfg['targets'][ident][server]:
            for message in messages:
                asyncio.ensure_future(bot.message(channel, _(bot, message)), loop=bot.loop)

    return ('', 204)



## Boilerplate

HOOKS = {}

def load():
    global THREAD
    THREAD = threading.Thread(target=functools.partial(SERVER.run, host=config.get('hooks.host'), port=config.get('hooks.port')))
    THREAD.start()
    return True

def register(name, endpoint, func):
    HOOKS[endpoint] = (name, func)

def unload():
    pass

def unregister(name, endpoint, func):
    del HOOKS[endpoint]
