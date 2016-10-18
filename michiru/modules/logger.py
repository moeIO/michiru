# Logging module.
import os
from os import path
import datetime

from michiru import config
from michiru.modules import hook


## Module information.

__name__ = 'logger'
__author__ = 'Shiz'
__license__ = 'WTFPL'
__desc__ = 'Log activities.'

config.item('logger.path', path.join('{local}', 'logs', '{server}', '{channel}.log'))
config.item('logger.date_format', '%Y/%m/%d %H:%M:%S')

## Utility functions.

def log(server, channel, message):
    """ Remove earlier entries for `nick` from database and insert new log entry. """
    logfile = config.get('logger.path', server=server, channel=channel).format(
        site=config.SITE_DIR,
        local=config.LOCAL_DIR,
        server=server,
        channel=channel or '<server>'
    )
    logpath = path.dirname(logfile)
    dateformat = config.get('logger.date_format', server=server, channel=channel)

    if not path.exists(logpath):
        os.makedirs(logpath)
    with open(logfile, 'a') as f:
        f.write('[{now}] {message}\n'.format(now=datetime.datetime.utcnow().strftime(dateformat), message=message))


## Commands and hooks.

@hook('chat.join')
def join(bot, server, channel, who):
    log(server, channel, '--> {nick} joined {chan}'.format(nick=who, chan=channel))

@hook('chat.part')
def part(bot, server, channel, who, reason):
    log(server, channel, '<-- {nick} left {chan} ({reason})'.format(nick=who, chan=channel, reason=reason))

@hook('chat.disconnect')
def quit(bot, server, who, reason):
    log(server, None, '<-- {nick} quit ({reason})'.format(nick=who, reason=reason))

@hook('chat.kick')
def kick(bot, server, channel, target, by, reason):
    log(server, channel, '<!- {nick} got kicked from {channel} by {kicker} ({reason})'.format(nick=target, channel=channel, kicker=by, reason=reason))

@hook('chat.nickchange')
def nickchange(bot, server, who, to):
    log(server, None, '-!- {old} changed nickname to {new}'.format(old=who, new=to))

@hook('chat.message')
def message(bot, server, target, who, message, private, admin):
    log(server, who if private else target, '<{nick}> {message}'.format(nick=who, message=message))

@hook('chat.notice')
def notice(bot, server, target, who, message, private, admin):
    log(server, who if private else target, '*{nick}* {message}'.format(nick=who, message=message))

@hook('chat.channelchange')
def channelchange(bot, server, channel, new):
    log(server, channel, '-!- Channel changed to {new}'.format(new=new))

@hook('chat.topicchange')
def topicchange(bot, server, channel, who, topic):
    if who:
        log(server, channel, '-!- {who} changed topic to: {topic}'.format(who=who, topic=topic))
    else:
        log(server, channel, '-!- Topic changed to: {topic}'.format(topic=topic))


## Boilerplate.

def load():
    return True

def unload():
    pass
