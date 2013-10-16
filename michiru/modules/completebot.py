#!/usr/bin/env python3
# completebot - complete missing }, ] and ).
import config
import personalities
from modules import hook
_ = personalities.localize

__name__ = 'completebot'
__author__ = 'Shiz'
__license__ = 'WTFPL'

@hook('irc.message')
def message(bot, server, target, source, message, private):

