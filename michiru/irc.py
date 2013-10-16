#!/usr/bin/env python3
# Michiru's IRC core.
import re
import time
import lurklib
import traceback

import version as michiru
import config
import db
import events
import modules
import personalities
_ = personalities.localize

config.ensure('servers', {})
config.ensure('command_prefixes', [':'])


db.ensure('_admins', {
    'id': db.ID,
    'server': (db.STRING, db.INDEX),
    'channel': (db.STRING, db.INDEX),
    'nickname': db.STRING
})

db.ensure('_ignores', {
    'id': db.ID,
    'server': (db.STRING, db.INDEX),
    'channel': db.STRING,
    'nickname': db.STRING
})


bots = {}

class IRCBot(lurklib.Client):
    """
    IRC bot core. Executes module commands!
    """

    def __init__(self, tag, *args, **kwargs):
        super(lurklib.Client, self).__init__(*args, **kwargs)
        self.michiru_server_tag = tag
        self.michiru_config = config.current['servers'][self.michiru_server_tag]
        self.michiru_history = {}
        self.michiru_ignores = []
        # Compile regexp we'll use to see if messages are intended for us.
        self.michiru_message_pattern = re.compile('(?:{nick}[:,;]\s*|{prefixes})(.+)'.format(
            nick=self.current_nick,
            prefixes='[{chars}]'.format(chars=''.join(re.escape(x) for x in config.current['command_prefixes']))
        ), re.IGNORECASE)

        # Fill ignore list from database.
        res = db.from_('_ignores').where('server', self.michiru_server_tag).get('channel', 'nickname')
        for channel, nickname in res:
            if channel:
                self.michiru_ignores.append((nickname, channel))
            else:
                self.michiru_ignores.append(nickname)


    ## Added functionality.

    def ctcp(self, target, message):
        """ Send CTCP request to target. """
        return self.privmsg(target, self.ctcp_encode(message))

    def ctcp_reply(self, target, type, message):
        """ Send CTCP reply to target. """
        return self.notice(target, self.ctcp_encode(type + ' ' + message))


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
                raise EnvironmentError(_('{nick} is not ignored in channel {chan}.', nick=nick, chan=chan))
            self.michiru_ignores.remove((who, chan))
        else:
            if not who in self.michiru_ignores:
                raise EnvironmentError(_('{nick} is not ignored.', nick=nick))
            self.michiru_ignores.remove(who)

        # Remove ignore.
        db.from_('_ignores').where('nickname', who) \
                            .and_('server', self.michiru_server_tag) \
                            .and_('channel', channel).delete()

    def ignored(self, who, chan=None):
        """ Check if user is ignored. """
        who = who[0] if isinstance(who, tuple) else who
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

    def admin(self, nick, chan=None):
        """ Check if given nickname is admin or channel admin. """
        return nick in self.admins(chan)


    ## Event handlers.

    def on_connect(self):
        # Authenticate if possible.
        if self.michiru_config.get('nickserv_password'):
            self.privmsg('NickServ', 'identify {}'.format(self.michiru_config['nickserv_password']))

            # Give it a tiny bit of time before attempting to join channels to verify us.
            time.sleep(1)

        if self.michiru_config.get('channels'):
            # Join all channels we are supposed to.
            for chan in self.michiru_config['channels']:
                if isinstance(chan, tuple):
                    chan, password = chan
                else:
                    password = None
                self.join_(chan, password)

        # Execute hook.
        events.emit('irc.connect', self, self.michiru_server_tag)

    def on_join(self, who, target):
        if self.ignored(who, target):
            return
        # Execute hook.
        events.emit('irc.join', self, self.michiru_server_tag, target, who)

    def on_part(self, who, target, reason):
        if self.ignored(who, target):
            return
        # Execute hook.
        events.emit('irc.part', self, self.michiru_server_tag, target, who, reason)

    def on_quit(self, who, reason):
        if self.ignored(who):
            return
        # Execute hook.
        events.emit('irc.disconnect', self, self.michiru_server_tag, who, reason)

    def on_kick(self, target, channel, by, reason):
        if self.ignored(target, channel) or self.ignored(by, channel):
            return
        # Execute hook.
        events.emit('irc.kick', self, self.michiru_server_tag, channel, target, by, reason)

    def on_invite(self, by, channel):
        if self.ignored(by, channel):
            return
        # Execute hook.
        events.emit('irc.invite', self, self.michiru_server_tag, channel, by)

    def on_nick(self, who, to):
        if self.ignored(who) or self.ignored(to):
            return
        # Execute hook.
        events.emit('irc.nickchange', self, self.michiru_server_tag, who, to)

    def on_channotice(self, source, channel, message, private=False):
        if self.ignored(source, channel):
            return
        # Execute hook.
        events.emit('irc.notice', self, self.michiru_server_tag, channel, source, message, private)

    def on_privnotice(self, source, message):
        # Private notices aren't any different.
        return self.on_channotice(source, source[0], message, private=True)

    def on_topic(self, setter, channel, topic):
        if self.ignored(setter, channel):
            return
        # Execute hook.
        events.emit('irc.topicchange', self, self.michiru_server_tag, channel, setter, topic)

    def on_chanmsg(self, source, channel, message, private=False):
        if self.ignored(source, channel):
            return

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
        # Iterate through all modules enabled for us and get all the commands from them.
        for module, matcher, cmd, bare in modules.commands_for(server, channel):
             # See if we need to invoke its handler.
            if bare or private:
                matched_message = matcher.match(message)
                # And invoke if we have to.
                if matched_message:
                    try:
                        cmd(self, server, channel, source, message, matched_message, private=private)
                    except Exception as e:
                        self.notice(source[0], _('Error while executing [{mod}:{cmd}]: {err}', mod=module, cmd=cmd.__name__, err=e))
                        traceback.print_exc()
            elif matched_nick:
                matched_message = matcher.match(parsed_message)
                # Dito.
                if matched_message:
                    try:
                        cmd(self, server, channel, source, parsed_message, matched_message, private=private)
                    except Exception as e:
                        self.notice(source[0], _('Error while executing [{mod}:{cmd}]: {err}', mod=module, cmd=cmd.__name__, err=e))
                        traceback.print_exc()

        # And execute hooks.
        try:
            events.emit('irc.message', self, server, channel, source, message, private=False)
        except Exception as e:
            self.privmsg(notice, _('Error while executing hooks for {event}: {err}', event='irc.msg', err=e))

    
    def on_privmsg(self, source, message):
        # Private messages aren't any different, except that they are always intended for us, so we don't need to check.
        return self.on_chanmsg(source, source[0], message, private=True)
    
    def on_chanctcp(self, source, channel, message, private=False):
        if self.ignored(source, channel):
            return

        # Some default CTCP replies.
        if message == 'VERSION' or message == 'FINGER':
            self.ctcp_reply(source[0], message, '{m} v{v}'.format(m=michiru.__name__, v=michiru.__version__))
        elif message == 'SOURCE':
            self.ctcp_reply(source[0], message, michiru.__source__)
        elif message == 'USERINFO':
            info = self.michiru_config
            self.ctcp_reply(source[0], message, '{user} ({real})'.format(user=info.get('username', info['nickname']), real=info.get('realname', info['nickname'])))
        
        # And execute hooks.
        events.emit('irc.ctcp', self, self.michiru_server_tag, channel, source, message)

    def on_privctcp(self, source, message):
        return self.on_chanctcp(source, source[0], message, private=True)

def setup():
    """ Setup the bots. """
    global bots

    for tag, info in config.current['servers'].items():
        # Create bot.
        bots[tag] = IRCBot(
            tag,
            info['host'],
            port=info.get('port', 6697 if info.get('tls', False) else 6667),
            encoding=info.get('encoding', 'UTF-8'),

            tls=info.get('tls', False),
            tls_verify=info.get('tls_verify', False),

            nick=info['nickname'],
            user=info.get('username', info['nickname']),
            real_name=info.get('realname', info['nickname']),

            UTC=True,
            hide_called_events=True
        )

def main_loop():
    """ Run the main loop. Should not return unless all bots died. """
    # Since lurklib by default only has a single main loop for a single client,
    # copy some code from theirs to make it work with multiple clients.
    global bots

    while bots:
        # Make a copy of the bot values so we can change them.
        for tag, bot in list(bots.items()):
            # No point in keeping it if it doesn't wanna.
            if not bot.keep_going:
                del bots[tag]

            # DANGEROUS ZONE.
            with bot.lock:
                # Run connect handler if we need to.
                if bot.on_connect and not bot.readable(2):
                    bot.on_connect()
                    bot.on_connect = None
                if bot.keep_going:
                    bot.process_once()

