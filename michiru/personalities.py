#!/usr/bin/env python3
# IRC bot 'personalities'.
import config

config.ensure('personality', None)

IRC_CODES = {
    # Bold.
    'b': chr(0x2),
    '/b': chr(0x2),
    # Italic.
    'i': chr(0x9),
    '/i': chr(0x9),
    # Underline.
    'u': chr(0x15),
    '/u': chr(0x15),
    # Reset.
    '_': chr(0xF),
    ## Colors.
    'white': chr(0x3) + chr(0x0),
    'black': chr(0x3) + chr(0x1),
    'darkblue': chr(0x3) + chr(0x2),
    'darkgreen': chr(0x3) + chr(0x3),
    'red': chr(0x3) + chr(0x4),
    'darkred': chr(0x3) + chr(0x5),
    'darkviolet': chr(0x3) + chr(0x6),
    'orange': chr(0x3) + chr(0x7),
    'yellow': chr(0x3) + chr(0x8),
    'lightgreen': chr(0x3) + chr(0x9),
    'cyan': chr(0x3) + chr(0xA),
    'lightcyan': chr(0x3) + chr(0xB),
    'blue': chr(0x3) + chr(0xC),
    'violet': chr(0x3) + chr(0xD),
    'darkgray': chr(0x3) + chr(0xE),
    'lightgray': chr(0x3) + chr(0xF)
}

messages_ = {}

def localize(msg, *args, **kwargs):
    """ Localize message to current personality, if it supports it. """
    global IRC_CODES, messages

    # Find personality and check if personality has an alternative for message.
    personality = config.current['personality']
    if personality and personality in messages_ and msg in messages_[personality]:
        # Replace message.
        msg = messages_[personality][msg]

    kwargs.update(IRC_CODES)
    return msg.format(*args, **kwargs)

def message(personality, original, tl):
    """ Register alternative message for `personality` for message `original`. """
    global messages_
    if not personality in messages_:
        messages_[personality] = {}
    messages_[personality][original] = tl

def messages(personality, map):
    """ Register multiple alternative messages for `personality` through an `original` -> `tl` dict. """
    for original, tl in map.items():
        message(personality, original, tl)
