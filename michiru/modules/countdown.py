# 3-2-1... Anime!
import re
import functools
import asyncio

from michiru import config, db, personalities
from michiru.modules import command, hook
_ = personalities.localize


## Module information.
__name__ = 'countdown'
__author__ = 'Shiz'
__license__ = 'WTFPL'
__desc__ = '3-2-1... Anime!'


## Database stuff.

config.item('countdown.ready_messages', [r'(^|\s+)(r+|q+)($|\s+)'])

db.table('countdowns', {
    'id': db.ID,
    'server': (db.STRING, db.INDEX),
    'channel': (db.STRING, db.INDEX),
    'people': db.STRING,
    'count': db.UINT,
    'message': db.BINARY
})

@asyncio.coroutine
def check_countdown(bot, server, channel, person=None):
    current = db.from_('countdowns').where('server', server).and_('channel', channel).single()
    if not current:
        return

    people = current['people'].split(',') if current['people'] else []
    if person and person.lower() in people:
        people.remove(person.lower())
        db.on('countdowns').where('id', current['id']).update({
            'people': ','.join(people)
        })

    if not people:
        db.from_('countdowns').where('id', current['id']).delete()
        # Start countdown.
        for count in range(current['count']):
            yield from bot.message(channel, _(bot, '{count}'.format(count=current['count'] - count)))
            yield from asyncio.sleep(1)
        yield from bot.message(channel, _(bot, '{countmessage}!', countmessage=current['message'].decode('utf-8')))


## Commands.

@command(r'count ?(?P<dir>down|up)(?: with (?P<people>.+))? (?:from|to) (?P<count>[0-9]+)(?: (?:from|to) (?P<msg>.+))?')
def countdown(bot, server, target, source, message, parsed, private, admin):
    db.from_('countdowns').where('server', server).and_('channel', target).delete()

    if parsed.group('people'):
        people = re.split(r'(?:,\s*|\s*and\s*)', parsed.group('people'))
        people = ','.join(people).lower()
    else:
        people = ''

    db.to('countdowns').add({
        'server': server,
        'channel': target,
        'people': people,
        'count': max(0, min(10, int(parsed.group('count')) if parsed.group('count') else 5)),
        'message': (parsed.group('msg') or 'Go').encode('utf-8')
    })
    yield from check_countdown(bot, server, target)

@hook('chat.message')
def message(bot, server, target, who, message, private, admin):
    for ready in config.list('countdown.ready_messages', server, target):
        if re.search(ready, message, re.IGNORECASE):
            yield from check_countdown(bot, server, target, who)


## Module stuff.

def load():
    return True

def unload():
    pass
