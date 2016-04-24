#!/usr/bin/env python3
from michiru import config, personalities
from michiru.modules import hook
_ = personalities.localize


## Module information.

__name__ = 'waitopiggu'
__author__ = 'Shiz'
__license__ = 'WTFPL'


## Configuration options.

config.item('waitopiggu_channels', [])
config.item('waitopiggu_whitelist', [])
config.item('waitopiggu_ban_method', 'direct')
config.item('waitopiggu_ban_message', _('Your origins are not conducive to the desired environment.'))
config.item('waitopiggu_ban_proxy', None)
config.item('waitopiggu_ban_proxy_format', None)


## Hooks.

@hook('irc.join')
def join(bot, server, channel, who):
    if who in config.list('waitopiggu_whitelist', server, channel):
        return

    # Get channel list and strip status info.
    info = bot.whois(who)
    channels = [ chan.lstrip('!~@%+') for chan in info['CHANNELS'] ]
    blacklist = config.list('waitopiggu_channels', server, channel)

    # User is in a bad channel?
    if set(channels).intersection(set(blacklist)):
        method = config.get('waitopiggu_ban_method', server, channel)
        message = config.get('waitopiggu_ban_message', server, channel)

        # Direct kick?
        if method == 'direct':
            mask = yield bot.whois(who)
            bot.set_mode(channel, '+b *!*@{mask}'.format(mask=mask['hostname']))
            bot.kick(channel, who, message)
        # Or kick-by-proxy?
        elif method == 'proxy':
            proxy = config.get('waitopiggu_ban_proxy', server, channel)
            msg = config.get('waitopiggu_ban_proxy_format', server, channel)
            bot.message(proxy, msg.format(nick=who, server=server, channel=channel, message=message))


## Boilerplate.

def load():
    return False

def unload():
    pass
