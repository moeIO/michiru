# Seenbot module.
from datetime import datetime
import json

from michiru import db, personalities
from michiru.modules import command, hook
_ = personalities.localize


## Module information.
__name__ = 'seenbot'
__author__ = 'Shiz'
__license__ = 'WTFPL'
__desc__ = 'Tells when someone was last seen.'


## Database stuff and constants.

db.table('seen', {
    'id': db.ID,
    'server': (db.STRING, db.INDEX),
    'nickname': (db.STRING, db.INDEX),
    'action': db.INT,
    'data': db.STRING,
    'time': db.DATETIME
})

# The action values. Fake enum.
class Actions:
    JOIN = 0x1
    PART = 0x2
    QUIT = 0x3
    KICK = 0x4
    KICKED = 0x5
    NICKCHANGE = 0x6
    NICKCHANGED = 0x7
    MESSAGE = 0x8
    NOTICE = 0x9
    TOPICCHANGE = 0x10
    CTCP = 0x11


## Utility functions.

def timespan(date, current=None, reach=2):
    """ Calculate human readable timespan. """
    if current is None:
        current = datetime.now()

    timespans = [
        ('millennium', 'millennia',    60*60*24*365*1000),
        ('century', 'centuries',       60*60*24*365*100),
        ('decennium', 'decennia',      60*60*24*365*10),
        ('year', 'years',              60*60*24*365),
        ('month', 'months',            60*60*24*30),
        ('week', 'weeks',              60*60*24*7),
        ('day', 'days',                60*60*24),
        ('hour', 'hours',              60*60),
        ('minute', 'minutes',          60),
        ('second', 'seconds',          1)
    ]

    message = None
    reachstart = None
    delta = int((current - date).total_seconds())

    for i, (singular, plural, seconds) in enumerate(timespans):
        # Is our time at least one 'unit' worth of this span?
        if delta >= seconds:
            # Get the number of units it's worth, and the remainder.
            n, delta = divmod(delta, seconds)

            # Append to message.
            if message is not None:
                message += ', '
            else:
                reachstart = i
                message = ''
            message += '{n} {noun}'.format(n=n, noun=plural if n >= 2 else singular)

        # Stop if we reached our precision limit.
        if reachstart is not None and reach is not None and i - reachstart + 1 >= reach:
            break

    if message is None:
        message = 'just now'
    else:
        message += ' ago'
    return message

def log(server, nick, what, **data):
    """ Remove earlier entries for `nick` from database and insert new log entry. """
    db.from_('seen').where('nickname', nick.lower()).and_('server', server).delete()

    db.to('seen').add({
        'server': server,
        'nickname': nick.lower(),
        'action': what,
        'data': json.dumps(data),
        'time': datetime.now()
    })

def meify(bot, nick):
    if bot.nickname == nick:
        return 'me'
    return bot.highlight(nick)


## Commands and hooks.

@command(r'seen (\S+)$')
@command(r'have you seen (\S+)(?: lately)?\??$')
def seen(bot, server, target, source, message, parsed, private, admin):
    nick = parsed.group(1)

    # Weed out the odd cases.
    if nick == source:
        yield from bot.message(target, _(bot, 'Asking for yourself?', serv=server, nick=nick))
        return
    elif nick == bot.nickname:
        yield from bot.message(target, _(bot, "I'm right here.", serv=server, nick=nick))
        return

    # Do we have an entry for this nick?
    entry = db.from_('seen').where('nickname', nick.lower()).and_('server', server).single('action', 'data', 'time')
    if not entry:
        yield from bot.message(target, _(bot, "I don't know who {nick} is.", serv=server, nick=meify(bot, nick)))
        return

    message = 'I saw {nick} {timeago}, {action}'
    submessage = None

    action, raw_data, raw_time = entry
    data = json.loads(raw_data)
    time = datetime.strptime(raw_time, db.DATETIME_FORMAT)

    # Huge if/else chain incoming.
    if action == Actions.JOIN:
        submessage = _(bot, 'joining {chan}.', serv=server, **data)
    elif action == Actions.PART:
        submessage = _(bot, 'leaving {chan}, with reason "{reason}".', serv=server, **data)
    elif action == Actions.QUIT:
        submessage = _(bot, 'disconnecting with reason "{reason}".', serv=server, **data)
    elif action == Actions.KICK:
        submessage = _(bot, 'kicking {target} from {chan} with reason "{reason}".', serv=server, **data)
    elif action == Actions.KICKED:
        submessage = _(bot, 'getting kicked from {chan} by {kicker} with reason "{reason}".', serv=server, **data)
    elif action == Actions.NICKCHANGE:
        submessage = _(bot, 'changing nickname to {newnick}.', serv=server, **data)
    elif action == Actions.NICKCHANGED:
        submessage = _(bot, 'changing nickname from {oldnick}.', serv=server, **data)
    elif action == Actions.MESSAGE:
        submessage = _(bot, 'telling {chan} "<{nick}> {message}".', serv=server, nick=nick, **data)
    elif action == Actions.NOTICE:
        submessage = _(bot, 'noticing {chan} "*{nick}* {message}".', serv=server, nick=nick **data)
    elif action == Actions.TOPICCHANGE:
        submessage = _(bot, 'changing topic for {chan} to "{topic}".', serv=server, **data)
    elif action == Actions.CTCP:
        submessage = _(bot, 'CTCPing {target} ({message}).', serv=server, **data)
    else:
        submessage = _(bot, 'doing something.', serv=server, **data)

    message = _(bot, message, action=submessage, nick=meify(bot, nick), serv=server, rawtime=time, timeago=timespan(time))
    yield from bot.message(target, message)

@hook('chat.join')
def join(bot, server, channel, who):
    log(server, who, Actions.JOIN, chan=channel)

@hook('chat.part')
def part(bot, server, channel, who, reason):
    log(server, who, Actions.PART, chan=channel, reason=reason)

@hook('chat.disconnect')
def quit(bot, server, who, reason):
    log(server, who, Actions.QUIT, reason=reason)

@hook('chat.kick')
def kick(bot, server, channel, target, by, reason):
    log(server, by, Actions.KICK, chan=channel, target=meify(bot, target), reason=reason)
    log(server, target, Actions.KICKED, chan=channel, kicker=meify(bot, by), reason=reason)

@hook('chat.nickchange')
def nickchange(bot, server, who, to):
    log(server, who, Actions.NICKCHANGE, newnick=to)
    log(server, to, Actions.NICKCHANGED, oldnick=who)

@hook('chat.message')
def message(bot, server, target, who, message, private, admin):
    if not private:
        log(server, who, Actions.MESSAGE, chan=target, message=message)

@hook('chat.notice')
def notice(bot, server, target, who, message, private, admin):
    if not private:
        log(server, who, Actions.NOTICE, chan=target, message=message)

@hook('chat.topicchange')
def topicchange(bot, server, channel, who, topic):
    log(server, who, Actions.TOPICCHANGE, chan=channel, topic=topic)

@hook('irc.ctcp')
def ctcp(bot, server, target, who, message):
    log(server, who, Actions.CTCP, target=meify(bot, target), message=message)


## Boilerplate.

def load():
    return True

def unload():
    pass
