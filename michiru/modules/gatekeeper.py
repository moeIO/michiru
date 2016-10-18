from michiru import config, personalities
from michiru.modules import hook
_ = personalities.localize


## Module information.

__name__ = 'gatekeeper'
__author__ = 'Shiz'
__license__ = 'WTFPL'
__desc__ = 'Keep people from unwanted channels out.'


## Configuration options.

config.item('gatekeeper.channels', [])
config.item('gatekeeper.whitelist', [])
config.item('gatekeeper.ban.method', 'direct')
config.item('gatekeeper.ban.message', _('Your origins are not conducive to the desired environment.'))
config.item('gatekeeper.ban.proxy', None)
config.item('gatekeeper.ban.proxy_format', None)


## Hooks.

@hook('chat.join')
def join(bot, server, channel, who):
    if who in config.list('gatekeeper.whitelist', server, channel):
        return

    # Get channel list and strip status info.
    info = bot.whois(who)
    channels = [ chan.lstrip('!~@%+') for chan in info['CHANNELS'] ]
    blacklist = config.list('gatekeeper.channels', server, channel)

    # User is in a bad channel?
    if set(channels).intersection(set(blacklist)):
        method = config.get('gatekeeper.ban.method', server, channel)
        message = config.get('gatekeeper.ban.message', server, channel)

        # Direct kick?
        if method == 'direct':
            bot.kickban(channel, who, reason=message)
        # Or kick-by-proxy?
        elif method == 'proxy':
            proxy = config.get('gatekeeper.ban.proxy', server, channel)
            msg = config.get('gatekeeper.ban.proxy_format', server, channel)
            bot.message(proxy, msg.format(nick=who, server=server, channel=channel, message=message))


## Boilerplate.

def load():
    return False

def unload():
    pass
