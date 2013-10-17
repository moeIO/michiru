#!/usr/bin/env python3
# sed search/replacement bot.
import re

import config
import personalities
from modules import command, hook
_ = personalities.localize

__name__ = 'sedbot'
__author__ = 'Shiz'
__license__ = 'WTFPL'

config.ensure('sedbot_verbose_errors', False)
config.ensure('sedbot_log_limit', 5)
last_messages = {}


@command(r's(\W{1,2})((?:[^\1]|\\1)+)\1((?:[^\1]|\\1)+)\1([gis]*)', bare=True)
@command(r'(.+)[,;:] s(\W{1,2})((?:[^\2]|\\2)+)\2((?:[^\1]|\\2)+)\2([gis]*)', bare=True)
def sed(bot, server, target, source, message, matched, private):
    global last_messages

    if matched.lastindex >= 5:
        targ = matched.group(1)
        delimiter, pattern, replacement, flags = matched.group(2, 3, 4, 5)
    else:
        targ = source[0]
        delimiter, pattern, replacement, flags = matched.group(1, 2, 3, 4)

    # Do we have anything on the source?
    if not (server, target, targ) in last_messages.keys():
        if config.get('sedbot_verbose_errors', server, target):
            raise EnvironmentError(_('No messages to match.'))
        return

    # Generate flags.
    re_flags = re.UNICODE
    if 'i' in flags:
        re_flags |= re.IGNORECASE
    if 's' in flags:
        re_flags |= re.DOTALL

    # Remove escaped delimiters.
    pattern = pattern.replace('\\' + delimiter, delimiter)
    replacement = replacement.replace('\\' + delimiter, delimiter)

    # Compile regexp.
    try:
        expr = re.compile(pattern, re_flags)
        if not expr:
            if config.get('sedbot_verbose_errors', server, target):
                raise ValueError(_('Invalid regular expression.'))
            return
    except:
        # Not a valid regexp.
        if config.get('sedbot_verbose_errors', server, target):
            raise ValueError(_('Invalid regular expression.'))
        return

    # Start matching.
    matched_message = None
    msg = None
    for message in reversed(last_messages[server, target, targ]):
        msg = expr.sub(_('{b}{repl}{/b}', repl=replacement), message, count=0 if 'g' in flags else 1)
        if msg != message:
            matched_message = message
            break
        else:
            msg = None

    # No message matched?
    if not msg:
        if config.get('sedbot_verbose_errors', server, target):
            raise ValueError(_('Could not find matching message.'))
        return

    bot.privmsg(target, _('<{nick}> {ftfy}', nick=targ, ftfy=msg, diff=len(msg) - len(matched_message)))


# Log messages for later replacement.
@hook('irc.message')
def log(bot, server, target, who, message, private):
    global last_messages

    # Add message to log.
    if not (server, target, who[0]) in last_messages:
        last_messages[server, target, who[0]] = []
    last_messages[server, target, who[0]].append(message)

    # Prune.
    while len(last_messages[server, target, who[0]]) > config.get('sedbot_log_limit', server, target):
        last_messages[server, target, who[0]].pop(0)


# Module stuff.
def load():
    return True

def unload():
    pass
