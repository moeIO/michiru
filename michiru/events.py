# Event bus.
import traceback
import asyncio
hooks = {}

def register_hook(event, cmd):
    """ Register hook for `event`. """
    if event not in hooks:
        hooks[event] = []
    hooks[event].append(cmd)

def unregister_hook(event, cmd):
    """ Unregister hook for `event`. """
    if event in hooks and cmd in hooks[event]:
        hooks[event].remove(cmd)

@asyncio.coroutine
def emit(event, *args, **kwargs):
    """ Emit event. """
    if event in hooks:
        for hook in hooks[event]:
            try:
                yield from hook(*args, **kwargs)
            except:
                traceback.print_exc()
