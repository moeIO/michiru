# Michiru's IRC core.
import re
import time
import traceback
import pydle

from . import version as michiru, \
              config, \
              db, \
              events, \
              modules, \
              personalities
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


bots = {}
pool = pydle.ClientPool()


class IRCBot(pydle.Client):
    """
    IRC bot core. Executes module commands!
    """
    def __init__(self, tag, config, *args, **kwargs):
        self.michiru_server_tag = tag
        self.michiru_config = config
        super().__init__(*args, **kwargs)

    def _reset_attributes(self):
        super()._reset_attributes()
        self.michiru_history = {}
        self.michiru_ignores = []
        self.michiru_message_pattern = None

        # Fill ignore list from database.
        res = db.from_('_ignores').where('server', self.michiru_server_tag).get('channel', 'nickname')
        for channel, nickname in res:
            if channel:
                self.michiru_ignores.append((nickname, channel))
            else:
                self.michiru_ignores.append(nickname)


    ## Added functionality.

    def ignore(self, who, chan=None):
        """ Ignore user, optionally only in `chan`. """
        if chan:
            self.michiru_ignores.append((who, chan))
        else:
            self.michiru_ignores.append(who)

        # Add ignore to database.
        db.to('_ignores').add({
            'server': self.michiru_server_tag,
            'channel': chan,
            'nickname': who
        })

    def unignore(self, who, chan=None):
        """ Remove ignore for user. """
        if chan:
            if not (who, chan) in self.michiru_ignores:
                raise EnvironmentError(_('Not ignoring {nick} on channel {chan}.', nick=who, chan=chan))
            self.michiru_ignores.remove((who, chan))
        else:
            if not who in self.michiru_ignores:
                raise EnvironmentError(_('Not ignoring {nick}.', nick=who))
            self.michiru_ignores.remove(who)

        # Remove ignore.
        db.from_('_ignores').where('nickname', who) \
                            .and_('server', self.michiru_server_tag) \
                            .and_('channel', chan).delete()

    def ignored(self, who, chan=None):
        """ Check if user is ignored. """
        return who in self.michiru_ignores or (who, chan) in self.michiru_ignores


    def promote(self, nick, chan=None):
        """ Promote given user to administrator, optionally only in `chan`. """
        # Check if user already is an admin.
        admin = db.from_('_admins').where('server', self.michiru_server_tag) \
                                   .and_('channel', chan) \
                                   .and_('nickname', nick).single()

        if admin:
            if chan:
                raise EnvironmentError(_('{nick} is already an administrator for channel {chan}.', nick=nick, chan=chan))
            else:
                raise EnvironmentError(_('{nick} is already an administrator.', nick=nick))

        # Add admin to database.
        db.to('_admins').add({
            'server': self.michiru_server_tag,
            'channel': chan,
            'nickname': nick
        })

    def demote(self, nick, chan=None):
        """ Remove administrator status from user. """
        # Check if user is an admin.
        admin = db.from_('_admins').where('server', self.michiru_server_tag) \
                                   .and_('channel', chan) \
                                   .and_('nickname', nick).single()

        if not admin:
            if chan:
                raise EnvironmentError(_('{nick} is not an administrator for channel {chan}.', nick=nick, chan=chan))
            else:
                raise EnvironmentError(_('{nick} is not an administrator.', nick=nick))

        # Remove admin from database.
        db.from_('_admins').where('server', self.michiru_server_tag) \
                           .and_('channel', chan) \
                           .and_('nickname', nick).delete()

    def admins(self, chan=None):
        """ List admins for server, and optionally for `chan`. """
        admins = [ x['nickname'] for x in db.from_('_admins').where('server', self.michiru_server_tag).and_('channel', None).get('nickname') ]
        if chan:
            admins.extend([ x['nickname'] for x in db.from_('_admins').where('server', self.michiru_server_tag)
                                                                      .and_('channel', chan)
                                                                      .get('nickname') ])

        # Weed out double entries.
        return list(set(admins))

    @pydle.coroutine
    def is_admin(self, nick, chan=None):
        """ Check if given nickname is admin or channel admin. """
        # Basic check.
        if nick not in self.admins(chan):
            return False

        if self.users.get(nick, {}).get('identified'):
            return True

        info = yield self.whois(nick)
        if info and info['identified']:
            return True

        return False

    ## Event handlers.

    def on_connect(self):
        super().on_connect()
        # Authenticate if possible.
        if self.michiru_config.get('nickserv_password'):
            self.message('NickServ', 'identify {}'.format(self.michiru_config['nickserv_password']))

        self.eventloop.schedule_in(1, self.on_identified)

    def on_identified(self):
        if self.michiru_config.get('channels'):
            # Join all channels we are supposed to.
            for chan in self.michiru_config['channels']:
                if isinstance(chan, tuple):
                    chan, password = chan
                else:
                    password = None
                self.join(chan, password)

        # Execute hook.
        personalities.set_current(self.michiru_server_tag, None)
        events.emit('irc.connect', self, self.michiru_server_tag)

    def on_join(self, channel, user):
        super().on_join(channel, user)
        if self.ignored(user, channel):
            return
        # Execute hook.
        personalities.set_current(self.michiru_server_tag, channel)
        events.emit('irc.join', self, self.michiru_server_tag, channel, user)

    def on_part(self, channel, user, reason=None):
        super().on_part(channel, user, reason)
        if self.ignored(user, channel):
            return
        # Execute hook.
        personalities.set_current(self.michiru_server_tag, channel)
        events.emit('irc.part', self, self.michiru_server_tag, channel, user, reason)

    def on_quit(self, user, reason=None):
        super().on_quit(user, reason)
        if self.ignored(user):
            return
        # Execute hook.
        personalities.set_current(self.michiru_server_tag, None)
        events.emit('irc.disconnect', self, self.michiru_server_tag, user, reason)

    def on_kick(self, channel, target, by, reason):
        super().on_kick(channel, target, by, reason)
        if self.ignored(target, channel) or self.ignored(by, channel):
            return
        # Execute hook.
        personalities.set_current(self.michiru_server_tag, channel)
        events.emit('irc.kick', self, self.michiru_server_tag, channel, target, by, reason)

    def on_invite(self, channel, by):
        super().on_invite(channel, by)
        if self.ignored(by, channel):
            return
        # Execute hook.
        personalities.set_current(self.michiru_server_tag, None)
        events.emit('irc.invite', self, self.michiru_server_tag, channel, by)

    def on_nick_change(self, old, new):
        super().on_nick_change(old, new)
        if self.ignored(old):
            self.unignore(old)
            self.ignore(new)
            return
        if self.nickname == new:
            self.michiru_message_pattern = re.compile('(?:{nick}[:,;]\s*|{prefixes})(.+)'.format(
                nick=self.nickname,
                prefixes='[{chars}]'.format(chars=''.join(re.escape(x) for x in config.get('command_prefixes', server=self.michiru_server_tag)))
            ), re.IGNORECASE)

        # Execute hook.
        personalities.set_current(self.michiru_server_tag, None)
        events.emit('irc.nickchange', self, self.michiru_server_tag, old, new)

    @pydle.coroutine
    def on_notice(self, target, by, message):
        super().on_notice(target, by, message)
        if self.ignored(by, target):
            return
        private = not self.is_channel(target)
        admin = yield self.is_admin(by)
        # Execute hook.
        personalities.set_current(self.michiru_server_tag, None if private else target)
        events.emit('irc.notice', self, self.michiru_server_tag, target, by, message, private, admin)

    def on_topic_change(self, channel, topic, setter):
        super().on_topic_change(channel, topic, setter)
        if self.ignored(setter, channel):
            return
        # Execute hook.
        personalities.set_current(self.michiru_server_tag, channel)
        events.emit('irc.topicchange', self, self.michiru_server_tag, channel, setter, topic)

    @pydle.coroutine
    def on_message(self, target, by, message):
        super().on_message(target, by, message)
        if self.ignored(by, target):
            return
        private = not self.is_channel(target)
        source = by if private else target
        admin = yield self.is_admin(by)

        # See if message is meant for us, according to the following cases:
        # 1. Message starts with our nickname followed by a delimiter and optional whitespace.
        # 2. Message starts with one of our configured command prefixes.
        # 3. Message is private.
        matched_nick = re.match(self.michiru_message_pattern, message)
        if matched_nick:
            parsed_message = matched_nick.group(1).strip()
        elif private:
            matched_nick = True
            parsed_message = message.strip()

        server = self.michiru_server_tag
        personalities.set_current(server, None if private else target)
        success = False

        # Iterate through all modules enabled for us and get all the commands from them.
        for module, matcher, cmd, bare, fallback in modules.commands_for(server, None if private else target):
            if fallback and success:
                break

             # See if we need to invoke its handler.
            if bare or private:
                matched_message = matcher.match(message)
                # And invoke if we have to.
                if matched_message:
                    try:
                        cmd(self, server, target, by, message, matched_message, private=private, admin=admin)
                        success = True
                    except Exception as e:
                        self.message(source, _('Error while executing [{mod}:{cmd}]: {err}', mod=module, cmd=cmd.__name__, err=e))
                        traceback.print_exc()
            elif matched_nick:
                matched_message = matcher.match(parsed_message)
                # Dito.
                if matched_message:
                    try:
                        cmd(self, server, target, by, parsed_message, matched_message, private=private, admin=admin)
                        success = True
                    except Exception as e:
                        self.message(source, _('Error while executing [{mod}:{cmd}]: {err}', mod=module, cmd=cmd.__name__, err=e))
                        traceback.print_exc()

        # And execute hooks.
        try:
            events.emit('irc.message', self, server, target, by, message, private, admin)
        except Exception as e:
            self.message(source, _('Error while executing hooks for {event}: {err}', event='irc.msg', err=e))

    def on_ctcp_version(self, by, target, contents):
        if self.ignored(by, target):
            return
        self.ctcp_reply(by, 'VERSION', '{m} v{v}'.format(m=michiru.__name__, v=michiru.__version__))

    def on_ctcp_source(self, by, target, contents):
        if self.ignored(by, target):
            return
        self.ctcp_reply(by, 'SOURCE', michiru.__source__)

    def on_ctcp_userinfo(self, by, target, contents):
        if self.ignored(by, target):
            return
        self.ctcp_reply(by, 'USERINFO', '{user} ({real})'.format(user=self.username, real=self.realname))

    def on_ctcp(self, by, target, what, contents):
        super().on_ctcp(by, target, what, contents)
        if self.ignored(by, target):
            return
        personalities.set_current(self.michiru_server_tag, None)
        events.emit('irc.ctcp', self, self.michiru_server_tag, target, by, contents)


def connect(bots, pool, tag, info):
    # Create bot.
    bots[tag] = IRCBot(
        tag,
        info,
        nickname=info['nickname'],
        username=info.get('username'),
        realname=info.get('realname'),
    )
    pool.connect(bots[tag],
        hostname=info['host'],
        port=info.get('port'),
        tls=info.get('tls', False),
        tls_verify=info.get('tls_verify', False),
        encoding=info.get('encoding', 'UTF-8')
    )

def setup(bots, pool):
    """ Setup the bots. """
    for tag, info in config.get('servers').items():
        connect(bots, pool, tag, info)

def run_forever():
    """ Run the main loop. Should not return unless all bots died. """
    # Since lurklib by default only has a single main loop for a single client,
    # copy some code from theirs to make it work with multiple clients.
    global bots, pool

    setup(bots, pool)
    pool.handle_forever()
