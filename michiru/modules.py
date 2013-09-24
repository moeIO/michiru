#!/usr/bin/env python3
# Module loading code.
import sys
import os
import os.path as path
import re

import config
import events
import personalities
_ = personalities.localize

config.ensure('modules', [])
config.ensure('module_overrides', {})
config.ensure('module_individual_overrides', {})

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

# Used by decorators at module init time.
_commands = []
_hooks = []


## Commands.

def register_command(name, pattern, cmd, bare=False, case_sensitive=False):
    """ Register command. """
    global commands

    pattern = re.compile(pattern, re.IGNORECASE if not case_sensitive else 0)
    if (name, pattern, cmd, bare) in commands:
        raise EnvironmentError(_('Command {cmd} already registered.', cmd=cmd.__qualname__))
    commands.append((name, pattern, cmd, bare))

def unregister_command(name, pattern, cmd, bare=False, case_sensitive=False):
    """ Unregister command. """
    global commands
    
    pattern = re.compile(pattern, re.IGNORECASE if not case_sensitive else 0)
    if (name, pattern, cmd, bare) not in commands:
        raise EnvironmentError(_('Command {cmd} not registered.', cmd=cmd.__qualname__))
    commands.remove((name, pattern, cmd, bare))

def commands_for(server, channel):
    """ Get all enabled commands for given server and channel. """
    enabledcmds = []

    for name, pattern, cmd, bare in commands:
        if not name in modules.keys():
            continue
       
        # Check global flag, configure overrides and per-channel/server overrides.
        module, initialized, enabled = modules[name]
        if name in config.current['module_overrides']:
            enabled = config.current['module_overrides'][name]
        if name in config.current['module_individual_overrides']:
            overrides = config.current['module_individual_overrides'][name]
            if server in overrides:
                enabled = overrides[server]
            if (server, channel) in overrides:
                enabled = overrides[server, channel]
    
        if enabled:
            # Yay, an enabled command.
            enabledcmds.append((name, pattern, cmd, bare))

    return enabledcmds


## Module enabling/disabling.

def enable(name, server=None, channel=None):
    """ Enable module for given server and/or channel, or globally. """
    if server:
        # Set individual override.
        if channel:
            val = server, channel
        else:
            val = server
        
        if not name in config.current['module_individual_overrides']:
            config.current['module_individual_overrides'][name] = {}
        config.current['module_individual_overrides'][name][val] = True
    else:
        # Set global override.
        config.current['module_overrides'][name] = True

def disable(name, server=None, channel=None):
    """ Disable module for given server and/or channel, or globally. """
    if server:
        # Set individual override.
        if channel:
            val = server, channel
        else:
            val = server

        if not name in config.current['module_individual_overrides']:
            config.current['module_individual_overrides'][name] = {}
        config.current['module_individual_overrides'][name][val] = False
    else:
        # Set global override.
        config.current['module_overrides'][name] = False


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
        for path_ in __path__:
            target = path.join(path_, 'modules', name + '.py')
            if path.isfile(target) and os.access(target, os.R_OK):
                loadpath = target
                break
        else:
            # Not found.
            raise EnvironmentError(_('Module {mod} does not exist.', mod=name))

        # And load the code.
        module = {}
        _commands = []
        try:
            with open(loadpath, 'rb') as f:
                code = compile(f.read(), loadpath, 'exec')
                exec(code, module, module)
        except Exception as e:
            raise EnvironmentError(_('Error while loading module {mod}: {err}', mod=name, err=e))

        # Add command and hook registering/unregistering automagic to load/unload functions.
        if _commands or _hooks:
            # I love capturing variables.
            cmds = _commands
            hks = _hooks
            mld = module['load']
            muld = module['unload']

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

            module['load'] = ld
            module['unload'] = uld
            _commands = []
            _hooks = []

        modules[name] = module, False, False

    # And initialize the module.
    module, initialized, enabled = modules[name]
    if initialized and not reload:
        raise EnvironmentError(_('Module {mod} already loaded.', mod=name))

    # Finally, run the load routine.
    try:
        enabled = module['load']()
    except Exception as e:
        del modules[name]
        raise EnvironmentError(_('Error while loading module {mod}: {err}', mod=name, err=e))
    modules[name] = module, True, enabled

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
        module['unload']()
    except Exception as e:
        if soft:
            raise EnvironmentError(_('Error while unloading module {mod}: {err}', mod=name, err=e))
    
    # Delete module from dict if we're doing a hard unload.
    if not soft:
        del modules[name]

def unload_all(soft=True):
    """ Unload all modules. """
    global modules

    for name, (module, initialized, enabled) in modules.items():
        if not soft or initialized:
            unload(name)
