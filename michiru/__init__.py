#!/usr/bin/env python3
# Global initialization.

from version import *
import version

import config
config.load()
import db
db.connect()

import irc
import modules
import personalities
