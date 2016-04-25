#!/usr/bin/env python3
# Main code.
import argparse
from . import config

parser = argparse.ArgumentParser(description='Yet another IRC bot', prog='michiru')
parser.add_argument('-c', '--config-dir', help='Configuration directory.')

args = parser.parse_args()

# Load config.
config.load(args.config_dir)
# Connect to database.
from . import db
db.connect()

# Load rest.
from . import events, irc, personalities, modules

# The only hardcoded module.
modules.load('core')
# Load all other modules.
for module in config.current['modules']:
    modules.load(module)

# And do the IRC.
irc.run_forever()

# Clean up.
modules.unload_all()
