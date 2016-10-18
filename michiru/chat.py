# Michiru's chat core.
import traceback
import asyncio
from . import version as michiru, \
              config, \
              db, \
              personalities, \
              modules

_ = personalities.localize

config.item('servers', {})
config.item('command_prefixes', [':'])


db.table('_admins', {
    'id': db.ID,
    'server': (db.STRING, db.INDEX),
    'channel': (db.STRING, db.INDEX),
    'nickname': db.STRING
})

db.table('_ignores', {
    'id': db.ID,
    'server': (db.STRING, db.INDEX),
    'channel': db.STRING,
    'nickname': db.STRING
})

personalities.messages('tsun', {
    'Error while executing [{mod}:{cmd}]: {err}':
        'Waa~a! Couldn\'t execute {cmd}! {err} ( ´· A ·`)',
    'Error while executing hooks for {event}: {err}':
        'Waa~a! Couldn\'t spy on {event}! {err} ( ´· A ·`)'
})



class Transport:
    def __init__(self, loop, server, info):
        self.loop = loop
        self.server = server
        self.info = info
        self.ignores = []
        self.highlight_pattern = None

        # Fill ignore list from database.
        res = db.from_('_ignores').where('server', self.server).get('channel', 'nickname')
        for channel, nickname in res:
            if channel:
                self.ignores.append((nickname, channel))
            else:
                self.ignores.append(nickname)

    def ignore(self, who, chan=None):
        """ Ignore user, optionally only in `chan`. """
        if chan:
            self.ignores.append((who, chan))
        else:
            self.ignores.append(who)

        # Add ignore to database.
        db.to('_ignores').add({
            'server': self.server,
            'channel': chan,
            'nickname': who
        })

    def unignore(self, who, chan=None):
        """ Remove ignore for user. """
        if chan:
            if not (who, chan) in self.ignores:
                raise EnvironmentError(_('Not ignoring {nick} on channel {chan}.', nick=who, chan=chan))
            self.ignores.remove((who, chan))
        else:
            if not who in self.ignores:
                raise EnvironmentError(_('Not ignoring {nick}.', nick=who))
            self.ignores.remove(who)

        # Remove ignore.
        db.from_('_ignores').where('nickname', who) \
                            .and_('server', self.server) \
                            .and_('channel', chan).delete()

    def ignored(self, who, chan=None):
        """ Check if user is ignored. """
        return who in self.ignores or (who, chan) in self.ignores


    def promote(self, nick, chan=None):
        """ Promote given user to administrator, optionally only in `chan`. """
        # Check if user already is an admin.
        admin = db.from_('_admins').where('server', self.server) \
                                   .and_('channel', chan) \
                                   .and_('nickname', nick).single()

        if admin:
            if chan:
                raise EnvironmentError(_('{nick} is already an administrator for channel {chan}.', nick=nick, chan=chan))
            else:
                raise EnvironmentError(_('{nick} is already an administrator.', nick=nick))

        # Add admin to database.
        db.to('_admins').add({
            'server': self.server,
            'channel': chan,
            'nickname': nick
        })

    def demote(self, nick, chan=None):
        """ Remove administrator status from user. """
        # Check if user is an admin.
        admin = db.from_('_admins').where('server', self.server) \
                                   .and_('channel', chan) \
                                   .and_('nickname', nick).single()

        if not admin:
            if chan:
                raise EnvironmentError(_('{nick} is not an administrator for channel {chan}.', nick=nick, chan=chan))
            else:
                raise EnvironmentError(_('{nick} is not an administrator.', nick=nick))

        # Remove admin from database.
        db.from_('_admins').where('server', self.server) \
                           .and_('channel', chan) \
                           .and_('nickname', nick).delete()

    def admins(self, chan=None):
        """ List admins for server, and optionally for `chan`. """
        admins = [ x['nickname'] for x in db.from_('_admins').where('server', self.server).and_('channel', None).get('nickname') ]
        if chan:
            admins.extend([ x['nickname'] for x in db.from_('_admins').where('server', self.server)
                                                                      .and_('channel', chan)
                                                                      .get('nickname') ])

        # Weed out double entries.
        return list(set(admins))

    def highlight(self, nickname):
        return nickname

    @asyncio.coroutine
    def is_admin(self, nick, chan=None):
        """ Check if given nickname is admin or channel admin. """
        return nick in self.admins(chan)

    @asyncio.coroutine
    def run_commands(self, target, by, message, parsed_message, highlight, private):
        success = False
        source = by if private else target
        admin = yield from self.is_admin(by, chan=None if private else target)

        # Iterate through all modules enabled for us and get all the commands from them.
        for module, matcher, cmd, bare, fallback in modules.commands_for(self.server, None if private else target):
            if fallback and success:
                break

             # See if we need to invoke its handler.
            if bare or private:
                matched_message = matcher.match(message)
                # And invoke if we have to.
                if matched_message:
                    try:
                        yield from cmd(self, self.server, target, by, message, matched_message, private=private, admin=admin)
                        success = True
                    except Exception as e:
                        yield from self.message(source, _(self, 'Error while executing [{mod}:{cmd}]: {err}', mod=module, cmd=cmd.__name__, err=e))
                        traceback.print_exc()
                        break
            elif highlight:
                matched_message = matcher.match(parsed_message)
                # Dito.
                if matched_message:
                    try:
                        yield from cmd(self, self.server, target, by, parsed_message, matched_message, private=private, admin=admin)
                        success = True
                    except Exception as e:
                        yield from self.message(source, _(self, 'Error while executing [{mod}:{cmd}]: {err}', mod=module, cmd=cmd.__name__, err=e))
                        traceback.print_exc()
                        break


pools = {}
bots = {}
types = {}

def register_type(name, poolc):
    types[name] = poolc

def connect(loop, tag, info):
    type = info['type']
    if type not in types:
        raise ValueError('Unknown chat type: {}'.format(info['type']))

    # Setup pool for type if it doesn't exist yet.
    poolc = types[type]
    if type not in pools:
        pools[type] = poolc(loop)

    # Setup bot.
    return pools[type].new_client(tag, info)

def setup(loop):
    """ Setup the bots. """
    for tag, info in config.get('servers').items():
        bots[tag] = connect(loop, tag, info)

def run_forever():
    """ Run the main loop. Should not return unless all bots died. """
    loop = asyncio.get_event_loop()
    setup(loop)
    for b in bots.values():
        asyncio.ensure_future(b.run(), loop=loop)
    loop.run_forever()
