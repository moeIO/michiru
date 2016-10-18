# Chat bot 'personalities'.
from . import config

config.item('personality', None)

messages_ = {}
_current_server = None
_current_channel = None

def set_current(server, channel):
    global _current_server, _current_channel
    _current_server = server
    _current_channel = channel

def localize(_bot, _msg, *args, _server=None, _channel=None, **kwargs):
    """ Localize message to current personality, if it supports it. """
    global messages

    # Find personality and check if personality has an alternative for message.
    personality = config.get('personality', _server or _current_server, _channel or _current_channel)
    if personality and personality in messages_ and _msg in messages_[personality]:
        # Replace message.
        _msg = messages_[personality][_msg]

    kw = _bot.FORMAT_CODES.copy()
    kw.update(kwargs)

    return _msg.format(*args, **kw)

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
