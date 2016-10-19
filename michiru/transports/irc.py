import re
import asyncio
import pydle

from .. import version as michiru, config, chat, events, personalities


class IRCPool:
    def __init__(self, loop):
        self.loop = loop

    def new_client(self, tag, info):
        bot = IRCTransport(
            tag,
            info,
            self.loop,
            nickname=info['nickname'],
            username=info.get('username'),
            realname=info.get('realname'),
        )
        bot.connect_kwargs = dict(
            hostname=info['host'],
            port=info.get('port'),
            tls=info.get('tls', False),
            tls_verify=info.get('tls_verify', False),
            encoding=info.get('encoding', 'UTF-8')
        )
        return bot

class IRCClient(pydle.Client):
    def __init__(self, transport, config, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.michiru_transport = transport
        self.michiru_config = config
        self.michiru_message_pattern = None


    ## Event handlers.

    @pydle.coroutine
    def on_connect(self):
        yield from super().on_connect()
        # Authenticate if possible.
        if self.michiru_config.get('nickserv_password'):
            yield from self.message('NickServ', 'identify {}'.format(self.michiru_config['nickserv_password']))
            yield from asyncio.sleep(1)
        yield from self.on_identified()

    @asyncio.coroutine
    def on_identified(self):
        if self.michiru_config.get('channels'):
            # Join all channels we are supposed to.
            for chan in self.michiru_config['channels']:
                if isinstance(chan, tuple):
                    chan, password = chan
                else:
                    password = None
                yield from self.join(chan, password)

        # Execute hook.
        personalities.set_current(self.michiru_transport.server, None)
        yield from events.emit('chat.connect', self.michiru_transport, self.michiru_transport.server)

    @asyncio.coroutine
    def on_join(self, channel, user):
        yield from super().on_join(channel, user)
        if self.michiru_transport.ignored(user, channel):
            return
        # Execute hook.
        personalities.set_current(self.michiru_transport.server, channel)
        yield from events.emit('chat.join', self.michiru_transport, self.michiru_transport.server, channel, user)

    @asyncio.coroutine
    def on_part(self, channel, user, reason=None):
        yield from super().on_part(channel, user, reason)
        if self.michiru_transport.ignored(user, channel):
            return
        # Execute hook.
        personalities.set_current(self.michiru_transport.server, channel)
        yield from events.emit('chat.part', self.michiru_transport, self.michiru_transport.server, channel, user, reason)

    @asyncio.coroutine
    def on_quit(self, user, reason=None):
        yield from super().on_quit(user, reason)
        if self.michiru_transport.ignored(user):
            return
        # Execute hook.
        personalities.set_current(self.michiru_transport.server, None)
        yield from events.emit('chat.disconnect', self.michiru_transport, self.michiru_transport.server, user, reason)

    @asyncio.coroutine
    def on_kick(self, channel, target, by, reason):
        yield from super().on_kick(channel, target, by, reason)
        if self.michiru_transport.ignored(target, channel) or self.michiru_transport.ignored(by, channel):
            return
        # Execute hook.
        personalities.set_current(self.michiru_transport.server, channel)
        yield from events.emit('chat.kick', self.michiru_transport, self.michiru_transport.server, channel, target, by, reason)

    @asyncio.coroutine
    def on_invite(self, channel, by):
        yield from super().on_invite(channel, by)
        if self.michiru_transport.ignored(by, channel):
            return
        # Execute hook.
        personalities.set_current(self.michiru_transport.server, None)
        yield from events.emit('chat.invite', self.michiru_transport, self.michiru_transport.server, channel, by)

    @asyncio.coroutine
    def on_nick_change(self, old, new):
        yield from super().on_nick_change(old, new)
        if self.michiru_transport.ignored(old):
            self.michiru_transport.unignore(old)
            self.michiru_transport.ignore(new)
            return
        if self.nickname == new:
            self.michiru_message_pattern = re.compile('(?:{nick}[:,;]\s*|{prefixes})(.+)'.format(
                nick=self.nickname,
                prefixes='[{chars}]'.format(chars=''.join(re.escape(x) for x in config.get('command_prefixes', server=self.michiru_transport.server)))
            ), re.IGNORECASE)

        # Execute hook.
        personalities.set_current(self.michiru_transport.server, None)
        yield from events.emit('chat.nickchange', self.michiru_transport, self.michiru_transport.server, old, new)

    @asyncio.coroutine
    def on_notice(self, target, by, message):
        yield from super().on_notice(target, by, message)
        if self.michiru_transport.ignored(by, target):
            return
        private = not self.is_channel(target)
        admin = yield from self.michiru_transport.is_admin(by)
        # Execute hook.
        personalities.set_current(self.michiru_transport.server, None if private else target)
        yield from events.emit('chat.notice', self.michiru_transport, self.michiru_transport.server, target, by, message, private, admin)

    @asyncio.coroutine
    def on_topic_change(self, channel, topic, setter):
        yield from super().on_topic_change(channel, topic, setter)
        if self.michiru_transport.ignored(setter, channel):
            return
        # Execute hook.
        personalities.set_current(self.michiru_transport.server, channel)
        yield from events.emit('chat.topicchange', self.michiru_transport, self.michiru_transport.server, channel, setter, topic)

    @pydle.coroutine
    def on_message(self, target, by, message):
        yield from super().on_message(target, by, message)
        if self.michiru_transport.ignored(by, target):
            return
        private = not self.is_channel(target)
        admin = yield from self.michiru_transport.is_admin(by)

        # See if message is meant for us, according to the following cases:
        # 1. Message starts with our nickname followed by a delimiter and optional whitespace.
        # 2. Message starts with one of our configured command prefixes.
        # 3. Message is private.
        highlight = re.match(self.michiru_message_pattern, message)
        if highlight:
            parsed_message = highlight.group(1).strip()
        else:
            if private:
                highlight = True
            parsed_message = message.strip()

        server = self.michiru_transport.server
        personalities.set_current(server, None if private else target)

        if not self.is_same_nick(self.nickname, by):
            yield from self.michiru_transport.run_commands(target, by, message, parsed_message, bool(highlight), private)

        # And execute hooks.
        yield from events.emit('chat.message', self.michiru_transport, server, target, by, message, private, admin)

    @pydle.coroutine
    def on_ctcp_version(self, by, target, contents):
        if self.michiru_transport.ignored(by, target):
            return
        yield from self.ctcp_reply(by, 'VERSION', '{m} v{v}'.format(m=michiru.__name__, v=michiru.__version__))

    @pydle.coroutine
    def on_ctcp_source(self, by, target, contents):
        if self.michiru_transport.ignored(by, target):
            return
        yield from self.ctcp_reply(by, 'SOURCE', michiru.__source__)

    @pydle.coroutine
    def on_ctcp_userinfo(self, by, target, contents):
        if self.michiru_transport.ignored(by, target):
            return
        yield from self.ctcp_reply(by, 'USERINFO', '{user} ({real})'.format(user=self.username, real=self.realname))

    @pydle.coroutine
    def on_ctcp(self, by, target, what, contents):
        yield from super().on_ctcp(by, target, what, contents)
        if self.michiru_transport.ignored(by, target):
            return
        personalities.set_current(self.michiru_transport.server, None)
        yield from events.emit('irc.ctcp', self.michiru_transport, self.michiru_transport.server, target, by, contents)

class IRCTransport(chat.Transport):
    FORMAT_CODES = {
        # Bold.
        'b': chr(0x2),
        '/b': chr(0x2),
        # Italic.
        'i': chr(0x9),
        '/i': chr(0x9),
        # Underline.
        'u': chr(0x15),
        '/u': chr(0x15),
        # Reset.
        '_': chr(0xF),
        # Colors.
        'white': chr(0x3) + '00',
        'black': chr(0x3) + '01',
        'darkblue': chr(0x3) + '02',
        'darkgreen': chr(0x3) + '03',
        'red': chr(0x3) + '04',
        'darkred': chr(0x3) + '05',
        'darkviolet': chr(0x3) + '06',
        'orange': chr(0x3) + '07',
        'yellow': chr(0x3) + '08',
        'lightgreen': chr(0x3) + '09',
        'cyan': chr(0x3) + '10',
        'lightcyan': chr(0x3) + '11',
        'blue': chr(0x3) + '12',
        'violet': chr(0x3) + '13',
        'darkgray': chr(0x3) + '14',
        'lightgray': chr(0x3) + '15',
        # Misc.
        'spoiler': chr(0x2) + chr(0x3) + '01,01',
        '/spoiler': chr(0x3) + chr(0x2)
    }

    def __init__(self, tag, info, loop, *args, **kwargs):
        super().__init__(loop, tag, info)
        self.client = IRCClient(self, info, *args, eventloop=pydle.async.EventLoop(loop), **kwargs)
        self.connect_args = ()
        self.connect_kwargs = {}

    @asyncio.coroutine
    def is_admin(self, nick, chan=None):
        """ Check if given nickname is admin or channel admin. """
        # Basic check.
        if nick not in self.admins(chan):
            return False

        if self.client.users.get(nick, {}).get('identified'):
            return True

        info = yield from self.client.whois(nick)
        if info and info['identified']:
            return True

        return False

    @asyncio.coroutine
    def run(self):
        yield from self.client.connect(*self.connect_args, **self.connect_kwargs)

    @property
    def nickname(self):
        return self.client.nickname

    @asyncio.coroutine
    def message(self, target, message):
        yield from self.client.message(target, message)

    @asyncio.coroutine
    def nick(self, new):
        yield from self.client.nick(new)

    @asyncio.coroutine
    def quit(self):
        self.client.disconnect()


def new_pool(loop):
    return IRCPool(loop)

chat.register_type('irc', new_pool)
