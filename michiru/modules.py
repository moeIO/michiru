# Module loading code.
import sys
import os
import os.path as path
import re
import functools
import importlib
import asyncio

from . import config, \
              events, \
              personalities
_ = personalities.localize

config.item('modules', [])


__path__ = [path.join(p, 'modules') for p in [
    # User modules.
    config.LOCAL_DIR,
    # Global modules.
    config.SITE_DIR,
    # Shipped modules.
    path.dirname(__file__)
]]

modules = {}
commands = []
dependencies = {}

# Used by decorators at module init time.
_commands = []
_hooks = []


## Commands.

def register_command(name, pattern, cmd, bare=False, case_sensitive=False, fallback=False):
    """ Register command. """
    global commands

    # Check if command is already registered.
    pattern = re.compile(pattern, re.IGNORECASE | re.UNICODE if not case_sensitive else re.UNICODE)
    if (name, pattern, cmd, bare, fallback) in commands:
        raise EnvironmentError(_('Command {cmd} already registered.', cmd=cmd.__qualname__))

    commands.append((name, pattern, cmd, bare, fallback))

def unregister_command(name, pattern, cmd, bare=False, case_sensitive=False, fallback=False):
    """ Unregister command. """
    global commands

    # Check if command is registered.
    pattern = re.compile(pattern, re.IGNORECASE | re.UNICODE if not case_sensitive else re.UNICODE)
    if (name, pattern, cmd, bare, fallback) not in commands:
        raise EnvironmentError(_('Command {cmd} not registered.', cmd=cmd.__qualname__))

    commands.remove((name, pattern, cmd, bare, fallback))

def commands_for(server, channel):
    """ Get all enabled commands for given server and channel. """
    enabledcmds = []
    fallbackcmds = []

    overrides = config.dict('modules', server, channel)
    for name, pattern, cmd, bare, fallback in commands:
        if not name in modules.keys():
            continue

        # Check global flag, configure overrides and per-channel/server overrides.
        module, initialized, enabled = modules[name]

        if name in overrides:
            enabled = overrides[name]

        if enabled:
            # Yay, an enabled command.
            if fallback:
                fallbackcmds.append((name, pattern, cmd, bare, fallback))
            else:
                enabledcmds.append((name, pattern, cmd, bare, fallback))

    return enabledcmds + sorted(fallbackcmds, key=lambda x: len(x[1].pattern), reverse=True)


## Module enabling/disabling.

def enable(name, server=None, channel=None):
    """ Enable module for given server and/or channel, or globally. """
    config.setitem('modules', name, True, server, channel)

def disable(name, server=None, channel=None):
    """ Disable module for given server and/or channel, or globally. """
    config.setitem('modules', name, False, server, channel)


## Decorators.

def command(pattern, bare=False, case_sensitive=False, fallback=False):
    """ Decorator a module can use for commands. """
    global _commands

    def inner(func):
        _commands.append((pattern, asyncio.coroutine(func), bare, case_sensitive, fallback))
        return func
    return inner

def hook(event):
    """ Decorator a module can use for hooks. """
    global _hooks

    def inner(func):
        _hooks.append((event, asyncio.coroutine(func)))
        return func
    return inner


# Module loading/unloading.

def load(name, soft=True, reload=False):
    """
    Load the given module. If doing a soft load, will not try to load the module from disk again,
    if it's not required. If doing a reload, will unload() the module first.
    """
    global __path__, modules, _commands, _hooks
    fullname = __name__ + '.' + name

    # Decide if the module is already loaded and if we need to unload it.
    if reload:
        try:
            unload(name, soft=False)
        except EnvironmentError:
            pass
    if not soft and name in modules.keys():
        raise EnvironmentError('Module {mod} already loaded.'.format(mod=name))

    # Attempt to locate the module.
    if not soft or name not in modules.keys():
        # Attempt to load module.
        _commands = []
        _hooks = []
        try:
            module = importlib.import_module(fullname)
        except Exception as e:
            raise EnvironmentError('Error while loading module {mod}: {err}'.format(mod=name, err=e))

        # Add command and hook registering/unregistering automagic to load/unload functions.
        if _commands or _hooks:
            # I love capturing variables.
            module_cmds = _commands
            module_hks = _hooks
            module_name = name
            module_load = module.load
            module_unload = module.unload

            # And local functions.
            @functools.wraps(module_load)
            def overridden_load():
                for pattern, cmd, bare, case_sensitive, fallback in module_cmds:
                    register_command(module_name, pattern, cmd, bare, case_sensitive, fallback)
                for event, cmd in module_hks:
                    events.register_hook(event, cmd)
                return module_load()

            @functools.wraps(module_unload)
            def overridden_unload():
                for pattern, cmd, bare, case_sensitive, fallback in module_cmds:
                    unregister_command(module_name, pattern, cmd, bare, case_sensitive, fallback)
                for event, cmd in module_hks:
                    events.unregister_hook(event, cmd)
                return module_unload()

            module.load = overridden_load
            module.unload = overridden_unload
            _commands = []
            _hooks = []

        modules[name] = module, False, False

    # And initialize the module.
    module, initialized, enabled = modules[name]
    if initialized and not soft and not reload:
        raise EnvironmentError('Module {mod} already loaded.'.format(mod=name))

    # Load dependencies.
    for dep in getattr(module, '__deps__', []):
        dependencies.setdefault(dep, [])
        dependencies[dep].append(name)
        load(dep, soft=True, reload=False)

    # Finally, run the load routine.
    if not initialized or reload:
        try:
            enabled = module.load()
        except Exception as e:
            del modules[name]
            del sys.modules[fullname]
            raise EnvironmentError('Error while loading module {mod}: {err}'.format(mod=name, err=e))

        modules[name] = module, True, enabled

    # And reload depending modules.
    if reload:
        for dep in dependencies.get(name, []):
            load(dep, soft=soft, reload=True)

def unload(name, soft=True):
    """
    Unload the given module. If doing a soft unload, will not remove the module from memory,
    and will error when an exception occurs in the module's unload() routine.
    """
    global modules
    fullname = __name__ + '.' + name

    if name not in modules.keys():
        # Not loaded.
        raise EnvironmentError('Module {mod} is not loaded.'.format(mod=name))

    module, initialized, enabled = modules[name]
    if not initialized:
        raise EnvironmentError('Module {mod} is not loaded.'.format(mod=name))

    # Run unload routine.
    try:
        module.unload()
    except Exception as e:
        if soft:
            raise EnvironmentError('Error while unloading module {mod}: {err}'.format(mod=name, err=e))

    # Delete module from dict and config if we're doing a hard unload.
    if not soft:
        del sys.modules[fullname]
        del modules[name]
        if name in config.list('modules'):
            config.delete('modules', name)

def unload_all(soft=True):
    """ Unload all modules. """
    global modules

    for name, (module, initialized, enabled) in modules.items():
        if not soft or initialized:
            unload(name, soft=soft)
