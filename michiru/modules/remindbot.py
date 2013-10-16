#!/usr/bin/env python3
# Reminder bot.
from datetime import datetime, timedelta
import re
import threading

import db
from modules import command, hook
import personalities
_ = personalities.localize

__name__ = 'remindbot'
__author__ = 'Shiz'
__license__ = 'WTFPL'

db.ensure('reminders', {
    'id': db.ID,
    'server': (db.STRING, db.INDEX),
    'channel': (db.STRING, db.INDEX),
    'from': db.STRING,
    'to': (db.STRING, db.INDEX),
    'message': db.STRING,
    'time': db.DATETIME
})


@command(r'remind (\S+)(?: in (.*?))? (?:that|to) (.*)$')
def remind(bot, server, target, source, message, parsed, private):
    targ = parsed.group(1)
    msg = parsed.group(3)
    if parsed.group(2):
        when = parse_timespan(parsed.group(2))
    else:
        when = None

    # Adjust egoisms.
    if targ == 'me':
        targ = source[0]

    # If we're told to remind someone in a PM, just remind them anywhere. Because we're assholes.
    if private:
        channel = None
    else:
        channel = target

    id = db.to('reminders').add({
        'server': server,
        'channel': channel,
        'from': source[0],
        'to': targ,
        'message':  msg,
        'time': when
    })

    # If this is a timed reminder, set a timer.
    if when:
        timeout = (when - datetime.now()).total_seconds()
        timer = threading.Timer(timeout, do_remind, [bot, id])
        timer.start()

    bot.privmsg(target, _('Reminder added.', to=targ, when=when))

@hook('irc.join')
def join(bot, server, channel, who):
    check_reminders(bot, server, channel, who[0])

@hook('irc.message')
def message(bot, server, target, who, message, private):
    if not private:
        check_reminders(bot, server, target, who[0])


## Callback/utility functions.

def parse_timespan(message):
    chunks = [ x.strip() for x in re.split('(,|and)', message, flags=re.IGNORECASE) ]
    regexp = re.compile(r'([0-9]+) (\S+)$')

    timespans = {
        'millennium':  60*60*24*365*1000,
        'millennia':   60*60*24*365*1000,
        'century':     60*60*24*365*100,
        'centuries':   60*60*24*365*100,
        'decennium':   60*60*24*365*10,
        'decennia':    60*60*24*365*10,
        'year':        60*60*24*365,
        'years':       60*60*24*365,
        'month':       60*60*24*30,
        'months':      60*60*24*30,
        'week':        60*60*24*7,
        'weeks':       60*60*24*7,
        'day':         60*60*24,
        'days':        60*60*24,
        'hour':        60*60,
        'hours':       60*60,
        'minute':      60,
        'minutes':     60,
        'second':      1,
        'seconds':     1
    }

    offset = 0
    for chunk in chunks:
        matches = regexp.match(chunk)
        if not matches:
            raise ValueError(_("I don't know what a '{chunk}' is.", chunk=chunk))

        try:
            amount = int(matches.group(1))
            weight = timespans[matches.group(2)]
        except:
            raise ValueError(_("I don't know what a '{chunk}' is.", chunk=chunk))

        offset += amount * weight

    return datetime.now() + timedelta(seconds=offset)

def check_reminders(bot, server, channel, who):
    # See if there are untimed reminders for this user.
    reminders = db.from_('reminders').where('server', server).and_('channel', channel) \
                                     .and_('to', who).and_('time', None).get('id', 'from', 'message')
    reminders.extend(db.from_('reminders').where('server', server).and_('channel', None) \
                                          .and_('to', who).and_('time', None).get('id', 'from', 'message'))

    for reminder in reminders:
        # Tell user...
        bot.privmsg(channel, _('{targ}: <{src}> {msg}', targ=who, src=reminder['from'], msg=reminder['message']))
        # ... and remove reminder.
        db.from_('reminders').where('id', reminder['id']).delete()

def do_remind(bot, id):
    # Get reminder.
    reminder = db.from_('reminders').where('id', id).single('channel', 'from', 'to', 'message')
    if not reminder:
        # Already reminded?
        return

    # Tell user.
    bot.privmsg(reminder['channel'], _('{targ}: <{src}> {msg}', targ=reminder['to'], src=reminder['from'], msg=reminder['message']))
    # Remove reminder.
    db.from_('reminders').where('id', id).delete()


## Module stuff.

def load():
    return True

def unload():
    pass
