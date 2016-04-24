#!/usr/bin/env python3
# Global initialization.

from .version import *
from . import version
from . import config
config.load()
from . import db
db.connect()

from . import events, irc, modules, personalities
