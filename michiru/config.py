#!/usr/bin/env python3
# Load and parse configuration.
import builtins
import sys
import os
import os.path as path
import stat
import pprint
import shutil

import version as michiru

# Current configuration.
current = None

# Configuration file name.
CONFIG_FILE = 'config'

# Decide on local and site directories.
# I WOULD use appdirs.py for this, but it has opinions and they suck.
# Nobody should have to comply to the XDG specification.

if sys.platform.startswith('win'):
    # Windows has no global configuration directory. Everybody point and laugh.
    SITE_DIR = path.join(os.getenv('APPDATA'), michiru.__author__, michiru.__name__)
    LOCAL_DIR = SITE_DIR
elif sys.platform.startswith('darwin'):
    SITE_DIR = path.join('/Library', 'Application Support', michiru.__name__)

    # Try getting the local directory from AppKit first.
    try:
        import AppKit
    except:
        # No AppKit available for this install, use a sensible fallback.
        LOCAL_DIR = path.join(path.expanduser('~'), 'Library', 'Application Support', michiru.__name__)
    else:
        # Get the directory from AppKit.
        NS_APPLICATION_SUPPORT_DIRECTORY = 14
        NS_USER_DOMAIN = 1

        LOCAL_DIR = path.join(
            NSSearchPathForDirectoriesInDomains(NS_APPLICATION_SUPPORT_DIRECTORY, NS_USER_DOMAIN, True)[0],
            michiru.__name__
        )
elif sys.platform.startswith('linux') or sys.platform.startswith('bsd'):
    SITE_DIR = path.join('/etc', '.' + michiru.__name__.lower())
    LOCAL_DIR = path.join(path.expanduser('~'), '.' + michiru.__name__.lower())
else:
    raise EnvironmentError('Unknown platform!')



def get(item, server=None, channel=None):
    global current

    if server and channel and (server, channel) in current['_overrides'] and item in current['_overrides'][server, channel]:
        return current['_overrides'][server, channel][item]
    elif server and server in current['_overrides'] and item in current['_overrides'][server]:
        return current['_overrides'][server][item]
    return current[item]

def list(item, server=None, channel=None):
    global current
    res = []

    if item in current:
        res.extend(current[item])
    if server and server in current['_overrides'] and item in current['_overrides'][server]:
        res.extend(current['_overrides'][server][item])
    if server and channel and (server, channel) in current['_overrides'] and item in current['_overrides'][server, channel]:
        res.extend(current['_overrides'][server, channel][item])
    return res

def getdict(item, server=None, channel=None):
    global current
    res = {}

    if item in current:
        res.update(current[item])
    if server and server in current['_overrides'] and item in current['_overrides'][server]:
        res.update(current['_overrides'][server][item])
    if server and channel and (server, channel) in current['_overrides'] and item in current['_overrides'][server, channel]:
        res.update(current['_overrides'][server, channel][item])
    return res

def set(item, value, server=None, channel=None):
    global current

    if server:
        if channel:
            v = server, channel
        else:
            v = server

        if v not in current['_overrides']:
            current['_overrides'][v] = {}
        current['_overrides'][v][item] = value
    else:
        current[item] = value

def delete(item, key, server=None, channel=None):
    global current

    v = get(item, server, channel)

    if isinstance(v, dict):
        if server and channel and (server, channel) in current['_overrides'] and item in current['_overrides'][server, channel] and key in current['_overrides'][server, channel][item]:
            del current['_overrides'][server, channel][item][key]
        if server and server in current['_overrides'] and item in current['_overrides'][server] and key in current['_overrides'][server][item]:
            del current['_overrides'][server][item][key]
        if item in current and key in current[item]:
            del current[item][key]

    elif isinstance(v, (builtins.list, builtins.set)):
        if server and channel and (server, channel) in current['_overrides'] and item in current['_overrides'][server, channel]:
            while key in current['_overrides'][server, channel][item]:
                current['_overrides'][server, channel][item].remove(key)
        if server and server in current['_overrides'] and item in current['_overrides'][server]:
            while key in current['_overrides'][server][item]:
                current['_overrides'][server][item].remove(key)
        if item in current:
            while key in current[item]:
                current[item].remove(key)

    else:
        raise TypeError('Can\'t delete from type {t}.'.format(t=v.__class__.__name__))

def add(item, value, server=None, channel=None):
    global current

    if server:
        if channel:
            v = server, channel
        else:
            v = server

        if v not in current['_overrides']:
            current['_overrides'][v] = {}
        if item not in current['_overrides'][v]:
            current['_overrides'][v][item] = []
        current['_overrides'][v][item].append(value)
    else:
        if item not in current:
            current[item] = []
        current[item].append(value)

def setdict(item, key, value, server=None, channel=None):
    global current

    if server:
        if channel:
            v = server, channel
        else:
            v = server

        if v not in current['_overrides']:
            current['_overrides'][v] = {}
        if item not in current['_overrides'][v]:
            current['_overrides'][v][item] = {}
        current['_overrides'][v][item][key] = value
    else:
        if not item not in current:
            current[item] = {}
        current[item][key] = value


def ensure(item, default):
    """ Ensure configuration item exists. Will initialize it to `default` if it doesn't. """
    global current

    if not item in current:
        current[item] = default

def ensure_structure():
    """ Ensure a proper configuration structure is in place. """
    global CONFIG_FILE

    ensure_dir()
    ensure_file(CONFIG_FILE)

def ensure_file(*file, writable=False):
    """ Ensure file exists and return its path. """
    global LOCAL_DIR

    # File doesn't exist, create it locally.
    path_ = filename(*file, writable=writable) 
    if not path_:
        path_ = path.join(LOCAL_DIR, *file)

        # Remove if already exists.
        if path.isdir(path_):
            shutil.rmtree(path_)

        # Update access time too.
        with open(path_, 'wb') as f:
            os.chmod(path_, stat.S_IRWXU)
            os.utime(path_, None)

    return path_

def ensure_dir(*dir, writable=False):
    """ Ensure directory exists and return its path. """
    global LOCAL_DIR

    # Dir doesn't exist, create it locally.
    path_ = directory(*dir, writable=writable)
    if not path_:
        path_ = path.join(LOCAL_DIR, *dir)

        # Remove if already exists.
        if path.isdir(path_):
            shutil.rmtree(path_)
        elif path.isfile(path_):
            os.unlink(path_)

        os.makedirs(path_, mode=stat.S_IRWXU)

    return path_


def filename(*file, writable=False):
    """ Get file from either SITE_DIR or LOCAL_DIR, or None. """
    global SITE_DIR, LOCAL_DIR

    path_ = path.join(*file)
    site_file = path.join(SITE_DIR, path_)
    local_file = path.join(LOCAL_DIR, path_)

    # Check local first, user data overrides global data. Then check the site.
    if path.isfile(local_file) and (not writable or os.access(local_file, os.W_OK)):
        return local_file
    if path.isfile(site_file) and (not writable or os.access(site_file, os.W_OK)):
        return site_file
    return None

def directory(*dir, writable=False):
    """ Get directory from either SITE_DIR or LOCAL_DIR, or None. """
    global SITE_DIR, LOCAL_DIR

    site_dir = path.join(SITE_DIR, *dir)
    local_dir = path.join(LOCAL_DIR, *dir)

    # Same goes here: user data overrides global data.
    if path.isdir(local_dir) and (not writable or os.access(local_dir, os.W_OK)):
        return local_dir
    if path.isdir(site_dir) and (not writable or os.access(site_dir, os.W_OK)):
        return site_dir
    return None


def load():
    """ Load configuration from CONFIG_FILE. """
    global current, CONFIG_FILE

    # Something is probably wrong if we don't have a configuration file.
    fn = filename(CONFIG_FILE)
    if not fn:
        ensure_structure()
        fn = filename(CONFIG_FILE)

    current = {}
    # Read the file and load its variables up.
    with open(fn, 'rb') as f: 
        exec(f.read(), current, current)

    # Ensure override data exists.
    ensure('_overrides', {})

def save():
    """ Save configuration to CONFIG_FILE. """
    global current, CONFIG_FILE

    if not current:
        raise EnvironmentError(_('No configuration loaded.'))
    
    # Get a config file we can write to.
    target = ensure_file(CONFIG_FILE, writable=True)
    if not target:
        raise EnvironmentError(_('Could not get a writable configuration file.'))

    with open(target, 'wb') as f:
        f.write('# Generated by {n}.\n'.format(n=michiru.__name__).encode('utf-8'))

        # Pretty print all config items...
        for k, v in current.items():
            # ... but only if we can actually read them back again.
            if pprint.isreadable(v):
                f.write('{} = {}\n'.format(k, pprint.pformat(v)).encode('utf-8'))

