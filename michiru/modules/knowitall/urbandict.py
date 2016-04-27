# Know-it-all UrbanDictionary module.
import re
import urbandict


## Module information.

__name__ = 'knowitall.urbandict'
__author__ = 'Shiz'
__license__ = 'WTFPL'
__desc__ = 'Get (questionable) knowledge from Urban Dictionary.'


## Module.

def define_urbandict(definition, bot, source, server, channel):
    res = urbandict.define(definition)
    if res:
        definition = res['definitions'][0]['definition']
        # Remove annoying formatting we can't do anything with.
        definition = re.sub(r'\[(.+?)\](.+?)\[\/\1\]', r'\2', definition)
        definition = re.sub(r'\[(.+?)\]', r'\1', definition)
        definition = re.sub(r'\\n', '\n', definition)
        definition = re.sub(r'\s+', ' ', definition)
        return definition

def load():
    from michiru.modules import knowitall
    knowitall.register(5, 'Urban Dictionary', define_urbandict)
    return True

def unload():
    from michiru.modules import knowitall
    knowitall.deregister(5, 'Urban Dictionary', define_urbandict)
