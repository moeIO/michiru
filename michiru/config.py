#!/usr/bin/env python3
# Load and parse configuration.
import builtins
import sys
import os
import os.path as path
import stat
import pprint
import shutil

from . import version as michiru

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


def _has(name, parent=None):
    if parent is None:
        parent = current

    if '.' in name:
        pname, name = name.rsplit('.', maxsplit=1)
        try:
            parent = _get(pname, parent)
        except KeyError:
            return False

    return name in parent

def _get(name, parent=None):
    if parent is None:
        parent = current

    if '.' in name:
        pname, name = name.rsplit('.', maxsplit=1)
        parent = _get(pname, parent)
        return _get(name, parent)

    return parent[name]

def _set(name, value, parent=None):
    if parent is None:
        parent = current

    if '.' in name:
        pname, name = name.rsplit('.', maxsplit=1)
        try:
            parent = _get(pname, parent)
        except KeyError:
            _set(pname, {}, parent)
            parent = _get(pname, parent)
        return _set(name, value, parent)

    parent[name] = value


def get(item, server=None, channel=None):
    global current

    if server and channel and (server, channel) in current['_overrides'] and _has(item, current['_overrides'][server, channel]):
        return _get(item, current['_overrides'][server, channel])
    elif server and server in current['_overrides'] and _has(item, current['_overrides'][server]):
        return _get(item, current['_overrides'][server])
    return _get(item)

def list(item, server=None, channel=None):
    global current
    res = []

    if _has(item):
        res.extend(_get(item))
    if server and server in current['_overrides'] and _has(current['_overrides'][server]):
        res.extend(_get(item, current['_overrides'][server]))
    if server and channel and (server, channel) in current['_overrides'] and _has(item, current['_overrides'][server, channel]):
        res.extend(_get(item, current['_overrides'][server, channel]))
    return res

def dict(item, server=None, channel=None):
    global current
    res = {}

    if _has(item):
        res.update(_get(item))
    if server and server in current['_overrides'] and _has(item, current['_overrides'][server]):
        res.update(_get(item, current['_overrides'][server]))
    if server and channel and (server, channel) in current['_overrides'] and _has(item, current['_overrides'][server, channel]):
        res.update(_get(item, current['_overrides'][server, channel]))
    return res

def set(item, value, server=None, channel=None):
    global current
    parent = None

    if server:
        if channel:
            v = server, channel
        else:
            v = server

        if v not in current['_overrides']:
            current['_overrides'][v] = {}
        parent = current['_overrides'][v]

    _set(item, value, parent)

def delete(item, key, server=None, channel=None):
    global current

    v = get(item, server, channel)

    if isinstance(v, builtins.dict):
        if server and channel and (server, channel) in current['_overrides'] and _has(item, current['_overrides'][server, channel]):
            d = _get(item, current['_overrides'][server, channel])
            if key in d:
                del d[key]
        if server and server in current['_overrides'] and _has(item, current['_overrides'][server]):
            d = _get(item, current['_overrides'][server])
            if key in d:
                del d[key]
        if _has(item):
            d = _get(item)
            if key in d:
                del d[key]

    elif isinstance(v, (builtins.list, builtins.set)):
        if server and channel and (server, channel) in current['_overrides'] and _has(item, current['_overrides'][server, channel]):
            l = _get(item, current['_overrides'][server, channel])
            while key in l:
                l.remove(key)
        if server and server in current['_overrides'] and _has(item, current['_overrides'][server]):
            l = _get(item, current['_overrides'][server])
            while key in l:
                l.remove(key)
        if _has(item):
            l = _get(item)
            while key in l:
                l.remove(key)

    else:
        raise TypeError('Can\'t delete from type {t}.'.format(t=v.__class__.__name__))

def add(item, value, server=None, channel=None):
    global current
    parent = None

    if server:
        if channel:
            v = server, channel
        else:
            v = server

        if v not in current['_overrides']:
            current['_overrides'][v] = {}
        parent = current['_overrides'][v]

    if not _has(item, parent):
        _set(item, [], parent)
    _get(item, parent).append(value)

def setitem(item, key, value, server=None, channel=None):
    global current
    parent = None

    if server:
        if channel:
            v = server, channel
        else:
            v = server

        if v not in current['_overrides']:
            current['_overrides'][v] = {}
        parent = current['_overrides'][v]

    if not _has(item, parent):
        _set(item, {}, parent)
    _get(item, parent)[key] = value

def item(item, default):
    """ Ensure configuration item exists. Will initialize it to `default` if it doesn't. """
    global current

    if not _has(item):
        _set(item, default)

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
    item('_overrides', {})

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
