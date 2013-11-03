#!/usr/bin/env python3
import config
import personalities
from modules import hook
_ = personalities.localize


## Module information.

__name__ = 'waitopiggu'
__author__ = 'Shiz'
__license__ = 'WTFPL'


## Configuration options.

config.ensure('waitopiggu_channels', [])
config.ensure('waitopiggu_whitelist', [])
config.ensure('waitopiggu_ban_method', 'direct')
config.ensure('waitopiggu_ban_message', _('Your origins are not conducive to the desired environment.'))
config.ensure('waitopiggu_ban_proxy', None)
config.ensure('waitopiggu_ban_proxy_format', None)


## Hooks.

@hook('irc.join')
def join(bot, server, channel, who):
    if who[0] in config.list('waitopiggu_whitelist', server, channel):
        return

    # Get channel list and strip status info.
    info = bot.whois(who[0])
    channels = [ chan.lstrip('!~@%+') for chan in info['CHANNELS'] ]
    blacklist = config.list('waitopiggu_channels', server, channel)

    # User is in a bad channel?
    if set(channels).intersection(set(blacklist)):
        method = config.get('waitopiggu_ban_method', server, channel)
        message = config.get('waitopiggu_ban_message', server, channel)

        # Direct kick?
        if method == 'direct':
            bot.cmode(channel, '+b *!*@{mask}'.format(mask=who[2]))
            bot.kick(channel, who[0], message)
        # Or kick-by-proxy?
        elif method == 'proxy':
            proxy = config.get('waitopiggu_ban_proxy', server, channel)
            msg = config.get('waitopiggu_ban_proxy_format', server, channel)
            bot.privmsg(proxy, msg.format(nick=who[0], server=server, channel=channel, message=message))


## Boilerplate.

def load():
    return False

def unload():
    pass
