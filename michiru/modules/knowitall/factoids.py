# Know-it-all factoids module.
import re
from datetime import datetime

from michiru import db, personalities
from michiru.modules import command
_ = personalities.localize


## Module information.

__name__ = 'knowitall.factoids'
__author__ = 'Shiz'
__license__ = 'WTFPL'
__desc__ = 'Get knowledge from stored factoids.'

db.table('factoids', {
    'id': db.INT,
    'server': (db.STRING, db.INDEX),
    'factoid': (db.STRING, db.INDEX),
    'definition': db.STRING,
    'author': db.STRING,
    'time': db.DATETIME
})

personalities.messages('tsun', {
    '{factoid} defined.':
        'gotcha!',
    '{factoid} deleted.':
        'gotcha!',
    'Unknown definition: {factoid}':
        'I-I didn\'t know much about {factoid} in the first place... (´･ω･`)',
    'You can\'t define yourself.':
        'Nice try! ( ﾟ ヮﾟ)'
})


## Module.

@command(r'(\S+) is (.*[^\?])$', fallback=True)
def define(bot, server, target, source, message, parsed, private, admin):
    factoid = parsed.group(1)
    definition = parsed.group(2).strip()

    if factoid in ('what', 'who', 'where', 'how', 'why'):
        return
    if source == factoid:
        bot.message(target, _('You can\'t define yourself.', factoid=factoid))

    db.from_('factoids').where('factoid', factoid).and_('server', server).delete()
    db.to('factoids').add({
        'server': server,
        'factoid': factoid,
        'definition': definition,
        'author': source,
        'time': datetime.now()
    })

    bot.message(target, _('{factoid} defined.', source=source, factoid=factoid, definition=definition))

@command(r'forget about (\S+)$')
def undefine(bot, server, target, source, message, parsed, private, admin):
    factoid = parsed.group(1)

    if db.from_('factoids').where('factoid', factoid).and_('server', server).delete():
        bot.message(target, _('{factoid} deleted.', source=source, factoid=factoid))
    else:
        bot.message(target, _('Unknown definition: {factoid}', source=source, factoid=factoid))

def define_factoid(definition, bot, source, server, channel):
    query = db.from_('factoids').where('factoid', definition).and_('server', server).single('definition')
    if query:
        return query['definition']

def load():
    from michiru.modules import knowitall
    knowitall.register(1, 'factoids', define_factoid)
    return True

def unload():
    from michiru.modules import knowitall
    knowitall.unregister(1, 'factoids', define_factoid)
