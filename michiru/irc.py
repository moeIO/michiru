#!/usr/bin/env python3
# Michiru's IRC core.
import re
import lurklib
import traceback

import version as michiru
import config
import events
import modules
import personalities
_ = personalities.localize

config.ensure('servers', {})
config.ensure('command_prefixes', [':'])

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
        # Compile regexp we'll use to see if messages are intended for us.
        self.michiru_message_pattern = '(?:{nick}[:,;]\s*|{prefixes})(.+)'.format(
            nick=self.current_nick,
            prefixes='[{chars}]'.format(chars=''.join(re.escape(x) for x in config.current['command_prefixes']))
        )

    def ctcp(self, target, message):
        return self.privmsg(target, self.ctcp_encode(message))

    def ctcp_reply(self, target, type, message):
        return self.notice(target, self.ctcp_encode(type + ' ' + message))

    def on_connect(self):
        if not self.michiru_config.get('channels'):
            return

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
        # Execute hook.
        events.emit('irc.join', self, self.michiru_server_tag, target, who)

    def on_part(self, who, target, reason):
        # Execute hook.
        events.emit('irc.part', self, self.michiru_server_tag, target, who, reason)

    def on_quit(self, who, reason):
        # Execute hook.
        events.emit('irc.disconnect', self, self.michiru_server_tag, who, reason)

    def on_kick(self, target, channel, by, reason):
        # Execute hook.
        events.emit('irc.kick', self, self.michiru_server_tag, channel, target, by, reason)

    def on_invite(self, by, channel):
        # Execute hook.
        events.emit('irc.invite', self, self.michiru_server_tag, channel, by)

    def on_nick(self, who, to):
        # Execute hook.
        events.emit('irc.nickchange', self, self.michiru_server_tag, who, to)

    def on_channotice(self, source, channel, message, private=False):
        # Execute hook.
        events.emit('irc.notice', self, self.michiru_server_tag, channel, source, message, private)

    def on_privnotice(self, source, message):
        # Private notices aren't any different.
        return self.on_channotice(source, source[0], message, private=True)

    def on_topic(self, setter, channel, topic):
        # Execute hook.
        events.emit('irc.topicchange', self, self.michiru_server_tag, channel, setter, topic)

    def on_chanmsg(self, source, channel, message, private=False):
        # See if message is meant for us, according to the following cases:
        # 1. Message starts with our nickname followed by a delimiter and optional whitespace.
        # 2. Message starts with one of our configured command prefixes.
        # 3. Message is private.
        matched_nick = re.match(self.michiru_message_pattern, message, re.IGNORECASE)
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
                        self.privmsg(channel, _('Error while executing [{mod}:{cmd}]: {err}', mod=module, cmd=cmd.__name__, err=e))
                        traceback.print_exc()
            elif matched_nick:
                matched_message = matcher.match(parsed_message)
                # Dito.
                if matched_message:
                    try:
                        cmd(self, server, channel, source, parsed_message, matched_message, private=private)
                    except Exception as e:
                        self.privmsg(channel, _('Error while executing [{mod}:{cmd}]: {err}', mod=module, cmd=cmd.__name__, err=e))
                        traceback.print_exc()

        # And execute hooks.
        try:
            events.emit('irc.message', self, server, channel, source, message, private=False)
        except Exception as e:
            self.privmsg(channel, _('Error while executing hooks for {event}: {err}', event='irc.msg', err=e))

    
    def on_privmsg(self, source, message):
        # Private messages aren't any different, except that they are always intended for us, so we don't need to check.
        return self.on_chanmsg(source, source[0], message, private=True)
    
    def on_chanctcp(self, source, channel, message, private=False):
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

