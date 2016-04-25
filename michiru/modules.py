# Module loading code.
import sys
import os
import os.path as path
import re
import functools
import types

from . import config, \
              events, \
              personalities
_ = personalities.localize

config.item('modules', [])


__path__ = [
    # User modules.
    config.LOCAL_DIR,
    # Global modules.
    config.SITE_DIR,
    # Shipped modules.
    path.dirname(__file__)
]

modules = {}
commands = []
dependencies = {}

# Used by decorators at module init time.
_commands = []
_hooks = []


## Commands.

def register_command(name, pattern, cmd, bare=False, case_sensitive=False):
    """ Register command. """
    global commands

    # Check if command is already registered.
    pattern = re.compile(pattern, re.IGNORECASE | re.UNICODE if not case_sensitive else re.UNICODE)
    if (name, pattern, cmd, bare) in commands:
        raise EnvironmentError(_('Command {cmd} already registered.', cmd=cmd.__qualname__))

    commands.append((name, pattern, cmd, bare))

def unregister_command(name, pattern, cmd, bare=False, case_sensitive=False):
    """ Unregister command. """
    global commands

    # Check if command is registered.
    pattern = re.compile(pattern, re.IGNORECASE | re.UNICODE if not case_sensitive else re.UNICODE)
    if (name, pattern, cmd, bare) not in commands:
        raise EnvironmentError(_('Command {cmd} not registered.', cmd=cmd.__qualname__))

    commands.remove((name, pattern, cmd, bare))

def commands_for(server, channel):
    """ Get all enabled commands for given server and channel. """
    enabledcmds = []

    overrides = config.dict('modules', server, channel)
    for name, pattern, cmd, bare in commands:
        if not name in modules.keys():
            continue

        # Check global flag, configure overrides and per-channel/server overrides.
        module, initialized, enabled = modules[name]

        if name in overrides:
            enabled = overrides[name]

        if enabled:
            # Yay, an enabled command.
            enabledcmds.append((name, pattern, cmd, bare))

    return enabledcmds


## Module enabling/disabling.

def enable(name, server=None, channel=None):
    """ Enable module for given server and/or channel, or globally. """
    config.setitem('modules', name, True, server, channel)

def disable(name, server=None, channel=None):
    """ Disable module for given server and/or channel, or globally. """
    config.setitem('modules', name, False, server, channel)


## Decorators.

def command(pattern, bare=False, case_sensitive=False):
    """ Decorator a module can use for commands. """
    global _commands

    def inner(func):
        _commands.append((pattern, func, bare, case_sensitive))
        return func
    return inner

def hook(event):
    """ Decorator a module can use for hooks. """
    global _hooks

    def inner(func):
        _hooks.append((event, func))
        return func
    return inner


# Module loading/unloading.

def get(name):
    return modules[name][0]

def load(name, soft=True, reload=False):
    """
    Load the given module. If doing a soft load, will not try to load the module from disk again,
    if it's not required. If doing a reload, will unload() the module first.
    """
    global __path__, modules, _commands, _hooks
    name = path.basename(name)

    # Decide if the module is already loaded and if we need to unload it.
    if reload:
        unload(name, soft=False)
    if not soft and name in modules.keys():
        raise EnvironmentError(_('Module {mod} already loaded.', mod=name))

    # Attempt to locate the module.
    if not soft or name not in modules.keys():
        loadpath = None
        modpath = path.join(*name.split('.'))
        for path_ in __path__:
            target = path.join(path_, 'modules', modpath + '.py')
            if path.isfile(target) and os.access(target, os.R_OK):
                loadpath = target
                break
            target = path.join(path_, 'modules', modpath)
            if path.isdir(target):
                target = path.join(target, '__init__.py')
                if path.isfile(target) and os.access(target, os.R_OK)
                    loadpath = target
                    break
        else:
            # Not found.
            raise EnvironmentError(_('Module {mod} does not exist.', mod=name))

        # And load the code.
        module = types.ModuleType(name)
        module.__package__ = __name__
        _commands = []
        try:
            with open(loadpath, 'rb') as f:
                code = compile(f.read(), loadpath, 'exec')
                exec(code, module.__dict__)
        except Exception as e:
            raise EnvironmentError(_('Error while loading module {mod}: {err}', mod=name, err=e))

        # Add command and hook registering/unregistering automagic to load/unload functions.
        if _commands or _hooks:
            # I love capturing variables.
            cmds = _commands
            hks = _hooks
            mld = module.load
            muld = module.unload

            # And local functions.
            def ld():
                for pattern, cmd, bare, case_sensitive in cmds:
                    register_command(name, pattern, cmd, bare, case_sensitive)
                for event, cmd in hks:
                    events.register_hook(event, cmd)
                return mld()

            def uld():
                for pattern, cmd, bare, case_sensitive in cmds:
                    unregister_command(name, pattern, cmd, bare, case_sensitive)
                for event, cmd in hks:
                    events.unregister_hook(event, cmd)

                return muld()

            module.load = ld
            module.unload = uld
            _commands = []
            _hooks = []

        modules[name] = module, False, False

    # And initialize the module.
    module, initialized, enabled = modules[name]
    if initialized and not soft and not reload:
        raise EnvironmentError(_('Module {mod} already loaded.', mod=name))

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
            raise EnvironmentError(_('Error while loading module {mod}: {err}', mod=name, err=e))

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

    name = path.basename(name)
    if name not in modules.keys():
        # Not loaded.
        raise EnvironmentError(_('Module {mod} is not loaded.', mod=name))

    module, initialized, enabled = modules[name]
    if not initialized:
        raise EnvironmentError(_('Module {mod} is not loaded.', mod=name))

    # Run unload routine.
    try:
        module.unload()
    except Exception as e:
        if soft:
            raise EnvironmentError(_('Error while unloading module {mod}: {err}', mod=name, err=e))

    # Delete module from dict and config if we're doing a hard unload.
    if not soft:
        del modules[name]
        if name in config.list('modules'):
            config.delete('modules', name)

def unload_all(soft=True):
    """ Unload all modules. """
    global modules

    for name, (module, initialized, enabled) in modules.items():
        if not soft or initialized:
            unload(name, soft=soft)
