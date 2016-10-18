import random
import asyncio
import discord

from .. import config, chat, events


class DiscordPool:
    def __init__(self, loop):
        self.loop = loop
        self.clients = {}

    def new_client(self, tag, info):
        token = info['token']
        if token not in self.clients:
            self.clients[token] = DiscordClient(self.loop)
            self.loop.run_until_complete(self.clients[token].login(token))

        transport = DiscordTransport(info['name'], info, self.loop)
        transport.client = self.clients[token]
        transport.client.register_server(tag, info, transport)
        return transport

class DiscordClient(discord.Client):
    def __init__(self, loop):
        super().__init__(loop=loop)
        self.michiru_server_info = {}
        self.michiru_server_mapping = {}
        self.michiru_channel_mapping = {}
        self.michiru_user_mapping = {}
        self.michiru_transports = {}
        self.michiru_routing = {}
        self.michiru_connected = False

    def __del__(self):
        self.loop.run_until_complete(self.logout())

    def register_server(self, tag, info, transport):
        self.michiru_server_info[tag] = info
        self.michiru_server_mapping[tag] = None
        self.michiru_channel_mapping[tag] = {}
        self.michiru_transports[tag] = transport

    def deregister_server(self, tag):
        del self.michiru_server_info[tag]
        del self.michiru_server_mapping[tag]
        del self.michiru_channel_mapping[tag]
        del self.michiru_transports[tag]

    @asyncio.coroutine
    def connect(self):
        self.michiru_connected = True
        yield from super().connect()

    @asyncio.coroutine
    def on_ready(self):
        for tag in self.michiru_server_info:
            yield from self.michiru_sync_server(tag)

    @asyncio.coroutine
    def on_server_join(self, server):
        yield from self.michiru_sync_server(server.name)

    @asyncio.coroutine
    def michiru_sync_server(self, tag):
        new = tag not in self.michiru_server_mapping
        for s in self.servers:
            if s.name == self.michiru_server_info[tag]['name']:
                self.michiru_server_mapping[tag] = s
                break
        else:
            print('no such server: {}'.format(tag))
            return

        transport = self.michiru_transports[tag]
        server    = self.michiru_server_mapping[tag]
        if new:
            yield from events.emit('chat.connect', transport, tag)

        for user in server.members:
            self.michiru_user_mapping[user.name] = user

        for channel in server.channels:
            self.michiru_channel_mapping[server.name][channel.name] = channel
            if channel.type in (discord.ChannelType.voice, discord.ChannelType.private):
                continue
            if new:
                yield from events.emit('chat.join', transport, server, channel.name, server.me.name)

    @asyncio.coroutine
    def on_message(self, message):
        server = message.server
        target = message.channel
        source = message.author
        private = False

        if not server or target.type == discord.ChannelType.private:
            private = True
        if not server:
            self.michiru_routing.setdefault(message.user.name, random.choice(self.michiru_server_mapping.values()))
            server = self.michiru_routing[message.user.name]

        contents = parsed_contents = message.content
        highlight = False
        mention = self.user.mention
        prefixes = config.get('command_prefixes', server=server.name)

        if contents.startswith(mention):
            highlight = True
            parsed_contents = contents.replace(mention, '').lstrip(';:, ')
        elif any(contents.startswith(p) for p in prefixes):
            highlight = True
            parsed_contents = contents.lstrip(''.join(prefixes))

        admin = yield from self.michiru_transports[server.name].is_admin(source.name, chan=None if private else target.name)
        yield from self.michiru_transports[server.name].run_commands(target.name, source.name, contents, parsed_contents, highlight, private)

        clean_contents = message.clean_content
        yield from events.emit('chat.message', self.michiru_transports[server.name], server.name, target.name, source.name, clean_contents, private, admin)

    @asyncio.coroutine
    def on_member_join(self, member):
        server = member.server
        transport = self.michiru_transports[server.name]

        for chan in self.michiru_channel_mapping[server.name].values():
            if chan.type in (discord.ChannelType.voice, discord.ChannelType.private):
                continue
            if chan.type == discord.ChannelType.text or (chan.type == discord.ChannelType.group and member in chan.recipients):
                yield from events.emit('chat.join', transport, server.name, chan.name, member.name)

    @asyncio.coroutine
    def on_group_join(self, channel, user):
        server = channel.server
        transport = self.michiru_transports[server.name]

        yield from events.emit('chat.join', transport, server.name, channel.name, user.name)

    @asyncio.coroutine
    def on_group_remove(self, channel, user):
        server = channel.server
        transport = self.michiru_transports[server.name]

        yield from events.emit('chat.part', transport, server.name, channel.name, user.name, None)

    @asyncio.coroutine
    def on_member_ban(self, member):
        server = member.server
        transport = self.michiru_transports[server.name]

        yield from events.emit('chat.disconnect', transport, server.name, member.name, 'Banned')

    @asyncio.coroutine
    def on_member_unban(self, member):
        pass

    @asyncio.coroutine
    def on_member_update(self, before, after):
        server = after.server
        transport = self.michiru_transports[server.name]

    @asyncio.coroutine
    def on_channel_create(self, channel):
        server = channel.server
        transport = self.michiru_transports[server.name]

        yield from events.emit('chat.join', transport, server.name, channel.name, server.me.name)

    @asyncio.coroutine
    def on_channel_delete(self, channel):
        server = channel.server
        transport = self.michiru_transports[server.name]

        yield from events.emit('chat.join', transport, server.name, channel.name, server.me.name, 'Channel deleted')

    @asyncio.coroutine
    def on_channel_update(self, before, after):
        server = after.server
        transport = self.michiru_transports[server.name]

        if before.name != after.name:
            self.michiru_channel_mapping[server.name][after.name] = after
            del self.michiru_channel_mapping[server.name][before.name]
            yield from events.emit('chat.channelchange', transport, server.name, before.name, after.name)

        if before.topic != after.topic:
            yield from events.emit('chat.topicchange', transport, server.name, after.name, None, after.topic)



class DiscordTransport(chat.Transport):
    FORMAT_CODES = {
        'i': '*',
        '/i': '*',
        'b': '**',
        '/b': '**',
        'u': '__',
        '/u': '__',
        'spoiler': '`',
        '/spoiler': '`'
    }

    def __init__(self, tag, info, loop):
        super().__init__(loop, tag, info)
        self.client = None

    @asyncio.coroutine
    def connect(self, token):
        yield from self.client.login(token)

    @asyncio.coroutine
    def run(self):
        if not self.client.michiru_connected:
            yield from self.client.connect()
        else:
            f = asyncio.Future(loop=self.loop)
            f.set_result(True)
            yield from f

    @property
    def nickname(self):
        return self.discord_server.me.name

    @property
    def discord_server(self):
        return self.client.michiru_server_mapping[self.server]

    @property
    def discord_channels(self):
        return self.client.michiru_channel_mapping[self.server]

    @property
    def discord_users(self):
        return self.client.michiru_user_mapping

    @asyncio.coroutine
    def message(self, target, message):
        if target in self.discord_channels:
            target = self.discord_channels[target]
        elif target in self.discord_users:
            target = self.discord_users[target]
        else:
            target = self.discord_server.get_member_named(target)

        if target is not None:
            yield from self.client.send_message(target, message)

    @asyncio.coroutine
    def nick(self, new):
        yield from self.client.change_nickname(self.discord_server.me, new)

    @asyncio.coroutine
    def quit(self):
        self.client.deregister_server(self.server)

    def highlight(self, nickname):
        if nickname in self.discord_users:
            return self.discord_users[nickname].mention
        return nickname

def new_pool(loop):
    return DiscordPool(loop)


chat.register_type('discord', new_pool)
