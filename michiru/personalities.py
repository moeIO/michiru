# IRC bot 'personalities'.
from . import config

config.item('personality', None)

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
    # Colors.
    'white': chr(0x3) + '00',
    'black': chr(0x3) + '01',
    'darkblue': chr(0x3) + '02',
    'darkgreen': chr(0x3) + '03',
    'red': chr(0x3) + '04',
    'darkred': chr(0x3) + '05',
    'darkviolet': chr(0x3) + '06',
    'orange': chr(0x3) + '07',
    'yellow': chr(0x3) + '08',
    'lightgreen': chr(0x3) + '09',
    'cyan': chr(0x3) + '10',
    'lightcyan': chr(0x3) + '11',
    'blue': chr(0x3) + '12',
    'violet': chr(0x3) + '13',
    'darkgray': chr(0x3) + '14',
    'lightgray': chr(0x3) + '15',
    # Misc.
    'spoiler': chr(0x2) + chr(0x3) + '01,01',
    '/spoiler': chr(0x3) + chr(0x2)
}

messages_ = {}
_current_server = None
_current_channel = None

def set_current(server, channel):
    global _current_server, _current_channel
    _current_server = server
    _current_channel = channel

def localize(_msg, *args, _server=None, _channel=None, **kwargs):
    """ Localize message to current personality, if it supports it. """
    global IRC_CODES, messages

    # Find personality and check if personality has an alternative for message.
    personality = config.get('personality', _server or _current_server, _channel or _current_channel)
    if personality and personality in messages_ and _msg in messages_[personality]:
        # Replace message.
        _msg = messages_[personality][_msg]

    kwargs.update(IRC_CODES)
    return _msg.format(*args, **kwargs)

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
