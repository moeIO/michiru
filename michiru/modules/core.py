#!/usr/bin/env python3
# Michiru's core module.
import config
import db
import irc
import modules
import personalities
import version
from modules import command
_ = personalities.localize


personalities.messages('fancy', {
    'This command is restricted to administrators.':
        '{b}{msg}{/b} is restricted to administrators.',
    'Administrator {nick} added.':
        'Administrator {b}[{nick}]{/b} added.',
    'Administrator {nick} removed.':
        'Administrator {b}[{nick}]{/b} removed.',
    'Module {mod} enabled for channel {chan}.':
        'Module {b}[{mod}]{/b} enabled for channel {b}[{srv}:{chan}]{/b}.',
    'Module {mod} enabled for server {srv}.':
        'Module {b}[{mod}]{/b} enabled for server {b}[{srv}]{/b}.',
    'Module {mod} globally enabled.':
        'Module {b}[{mod}]{/b} enabled globally.',
    'Module {mod} disabled for channel {chan}.':
        'Module {b}[{mod}]{/b} disabled for channel {b}[{srv}:{chan}]{/b}.',
    'Module {mod} disabled for server {srv}.':
        'Module {b}[{mod}]{/b} disabled for server {b}[{srv}]{/b}.',
    'Module {mod} globally disabled.':
        'Module {b}[{mod}]{/b} disabled globally.',
    'Module {mod} loaded.':
        'Module {b}[{mod}]{/b} loaded.',
    'Module {mod} unloaded.':
        'Module {b}[{mod}]{/b} unloaded.',
    'Module {mod} reloaded.':
        'Module {b}[{mod}]{/b} reloaded.',
    'Unknown server {srv}.':
        'Unknown server {b}[{srv}]{/b}',
    'Already connected to {tag}.':
        'Already connected to {b}[{tag}]{/b}.',
    'Connecting to {tag}... this might take a while.':
        'Connecting to {u}{tag}{/u} {b}[{host}:{port}]{/b}... this might take a while.',
    'Connected to {tag} successfully.':
        'Connected to {u}{tag}{/u} {b}[{host}:{port}]{/b} successfully.',
    'Configuration loaded.':
        'Configuration {u}loaded{/u}.',
    'Configuration saved.':
        'Configuration {u}saved{/u}.',
    'Configuration item {name} set.':
        'Configuration item {b}{name}{/b} set.',
    'config{name}: {val}.':
        '{b}[config{name}]:{/b} {val}.'
})

personalities.messages('tsun', {

})


## Helper functions.

def _identified(bot, nick, channel):
    # LELELELELELE
    return bot.admin(nick, channel)

def restricted(func):
    def inner(bot, server, target, source, message, parsed, private):
        if not _identified(bot, source[0], target):
            raise EnvironmentError(_('This command is restricted to administrators.', cmd=func.__name__))
        else:
            return func(bot, server, target, source, message, parsed, private=private)
    inner.__name__ = func.__name__
    inner.__qualname__ = func.__qualname__
    inner.__doc__ = func.__doc__
    return inner


## Admin commands.

@command(r'addadmin (\S+)(?: (\S+))?')
@command(r'add admin (\S+)(?: on channel (\S+))?\.?$')
@restricted
def addadmin(bot, server, target, source, message, parsed, private):
    nick = parsed.group(1)
    chan = None
    if parsed.group(2):
        chan = parsed.group(2)

    bot.promote(nick, chan)
    bot.privmsg(target, _('Administrator {nick} added.', nick=nick))

@command(r'listadmins(?: (\S+))?')
@command(r'list admins(?: for channel (\S+))?\.?$')
@restricted
def listadmins(bot, server, target, source, message, parsed, private):
    bot.privmsg(target, _('Administrators: {}', ', '.join(bot.admins(parsed.group(1)))))

@command(r'rmadmin (\S+)(?: (\S+))?')
@command(r'remove admin (\S+)(?: from channel (\S+))?\.?$')
@restricted
def rmadmin(bot, server, target, source, message, parsed, private):
    nick = parsed.group(1)
    chan = None
    if parsed.group(2):
        chan = parsed.group(2)

    bot.demote(nick, chan)
    bot.privmsg(target, _('Administrator {nick} removed.', nick=nick))


## Module commands.

@command(r'enable (\S+)(?: (\S+)(?: (\S+))?)?')
@command(r'enable (\S+)(?: on (\S+)(?:, channel (\S+))?)?\.?$')
@restricted
def enable(bot, server, target, source, message, parsed, private):
    module = parsed.group(1)
    if parsed.group(3):
        server = parsed.group(2)
        channel = parsed.group(3)
        modules.enable(module, server, channel)

        bot.privmsg(target, _('Module {mod} enabled for channel {chan}.', mod=module, srv=server, chan=channel))
    elif parsed.group(2):
        server = parsed.group(2)

        if server != 'global' and server != 'globally':
            modules.enable(module, server)
            bot.privmsg(target, _('Module {mod} enabled for server {srv}.', mod=module, srv=server))
        else:
            modules.enable(module)
            bot.privmsg(target, _('Module {mod} globally enabled.', mod=module))
    else:
        modules.enable(module, server, target)

        bot.privmsg(target, _('Module {mod} enabled for channel {chan}.', mod=module, srv=server, chan=target))

@command(r'disable (\S+)(?: (?: on)?(\S+)(?:(?:, channel)? (\S+))?)?\.?')
@restricted
def disable(bot, server, target, source, message, parsed, private):
    module = parsed.group(1)
    if parsed.group(3):
        server = parsed.group(2)
        channel = parsed.group(3)
        modules.disable(module, server, channel)

        bot.privmsg(target, _('Module {mod} disabled for channel {chan}.', mod=module, srv=server, chan=channel))
    elif parsed.group(2):
        server = parsed.group(2)

        if server != 'global' and server != 'globally':
            modules.disable(module, server)
            bot.privmsg(target, _('Module {mod} disabled for server {srv}.', mod=module, srv=server))
        else:
            modules.disable(module)
            bot.privmsg(target, _('Module {mod} globally disabled.', mod=module))
    else:
        modules.disable(module, server, target)

        bot.privmsg(target, _('Module {mod} disabled for channel {chan}.', mod=module, srv=server, chan=target))


@command(r'load (?: the)?(\S+)(?: module)?\.?$')
@restricted
def load(bot, server, target, source, message, parsed, private):
    module = parsed.group(1)
    modules.load(module)
    bot.privmsg(target, _('Module {mod} loaded.', mod=module))

@command(r'unload (?:the )?(\S+)(?: module)?(?:(?:the )?hard(?: way)?)?\.?')
@restricted
def unload(bot, server, target, source, message, parsed, private):
    module = parsed.group(1)
    modules.unload(module)
    bot.privmsg(target, _('Module {mod} unloaded.', mod=module))

@command(r'reload (?:the )?(\S+)(?: module)?\.?')
@restricted
def reload(bot, server, target, source, message, parsed, private):
    module = parsed.group(1)
    modules.load(module, reload=True)
    bot.privmsg(target, _('Module {mod} reloaded.', mod=module))


## Join/part servers/channels.

@command(r'join (\S+)(?: (\S+)(?: (\S+))?)?\.?$')
@restricted
def join(bot, server, target, source, message, parsed, private):
    if parsed.group(2):
        target_serv = parsed.group(1)
        target_chan = parsed.group(2)
    else:
        target_serv = server
        target_chan = parsed.group(1)

    if not target_serv in irc.bots.keys():
        raise EnvironmentError(_('Unknown server {srv}.', srv=target_serv))
    irc.bots[target_serv].join_(target_chan, parsed.group(3))

@command(r'part(?: (\S+)(?: (\S+)(?: (\S+))?)?)?\.?$')
@restricted
def part(bot, server, target, source, message, parsed, private):
    if parsed.group(2):
        target_serv = parsed.group(1)
        target_chan = parsed.group(2)
    elif parsed.group(1):
        target_serv = server
        target_chan = parsed.group(1)
    else:
        target_serv = server
        target_chan = target

    if not target_serv in irc.bots.keys():
        raise EnvironmentError(_('Unknown server {srv}.', srv=target_serv))
    irc.bots[target_serv].part(target_chan, parsed.group(3) or _('Parted.'))

@command(r'connect (\S+)(?: ([0-9]+)(?: (true|false))?)?')
@command(r'connect to (\S+)(?: with port ([0-9]+)(?: and TLS set to (true|false))?)?\.?$')
@restricted
def connect(bot, server, target, source, message, parsed, private):
    info = bot.michiru_config.copy()
    info['channels'] = []
    info['host'] = parsed.group(1)
    if parsed.group(3):
        info['tls'] = parsed.group(3) == 'true'
    if parsed.group(2):
        info['port'] = int(parsed.group(2))

    tag = info['host'].rsplit('.', 2)[1]
    if tag in irc.bots:
        raise EnvironmentError(_('Already connected to {tag}.', tag=tag))

    bot.privmsg(target, _('Connecting to {tag}... this might take a while.', tag=tag, host=info['host'], port=info['port']))
    config.current['servers'][tag] = info

    irc.bots[tag] = irc.IRCBot(
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

    bot.privmsg(target, _('Connected to {tag} successfully.', tag=tag, host=info['host'], port=info['port']))

@command(r'quit(?: (\S+)?)?\.?')
@restricted
def quit(bot, server, target, source, message, parsed, private):
    if parsed.group(1):
        serv = parsed.group(1)
        if not serv in irc.bots.keys():
            raise EnvironmentError(_('Unknown server {srv}.', srv=serv))

        irc.bots[parsed.group(1)].quit(_('Quit'))
    else:
        for bot in irc.bots.values():
            bot.quit(_('Quit'))


## Ignore/unignore commands.

@command(r'ignore (\S+)(?: (#\S+|everywhere))?\.?')
@restricted
def ignore(bot, server, target, source, message, parsed, private):
    nick = parsed.group(1)
    chan = parsed.group(2)
    if chan == 'everywhere':
        chan = None
    elif chan is None:
        chan = target

    if not chan:
        if bot.ignored(nick):
            raise EnvironmentError(_('Already ignoring {nick}.', nick=nick))
        bot.ignore(nick)
        bot.privmsg(target, _('{nick} added to ignore list.', nick=nick))
    else:
        if bot.ignored(nick, chan):
            raise EnvironmentError(_('Already ignoring {nick} on channel {chan}.', nick=nick, chan=chan))
        bot.ignore(nick, chan)
        bot.privmsg(target, _('{nick} added to ignore list for channel {chan}.', nick=nick, chan=chan))

@command(r'unignore (\S+)(?: (#\S+|everywhere))?')
@command(r'stop ignoring (\S+)(?: (?:on (\S+)|(everywhere))?)?\.?')
def unignore(bot, server, target, source, message, parsed, private):
    nick = parsed.group(1)
    chan = parsed.group(2)
    if chan == 'everywhere':
        chan = None
    elif chan is None:
        chan = target

    if not chan:
        if not bot.ignored(nick):
            raise EnvironmentError(_('Not ignoring {nick}.', nick=nick))
        bot.unignore(nick)
        bot.privmsg(target, _('{nick} removed from ignore list.', nick=nick))
    else:
        if not bot.ignored(nick, chan):
            raise EnvironmentError(_('Not ignoring {nick} on channel {chan}.', nick=nick, chan=chan))
        bot.unignore(nick, chan)
        bot.privmsg(target, _('{nick} removed from ignore list for channel {chan}.', nick=nick, chan=chan))


## Configuration commands.

@command(r'loadconf')
@restricted
def loadconf(bot, server, target, source, message, parsed, private):
    config.load()
    bot.privmsg(target, _('Configuration loaded.'))

@command(r'saveconf')
@command(r'save (?:your |the )?configuration\.?$')
@restricted
def saveconf(bot, server, target, source, message, parsed, private):
    config.save()
    bot.privmsg(target, _('Configuration saved.'))

@command(r'set (\S+)(?: to)? (.+)\.?$')
@restricted
def set(bot, server, target, source, message, parsed, private):
    name, value = parsed.group(1, 2)
    config.current[name] = eval(value)
    bot.privmsg(target, _('Configuration item {name} set.', name=name))

@command(r'setraw (\S+) (.+)')
@command(r'set (\S+) raw to (.+)\.?$')
def setraw(bot, server, target, source, message, parsed, private):
    name, value = parsed.group(1, 2)
    exec('config.current{name} = {val}'.format(name=name, val=value))
    bot.privmsg(target, _('Configuration item {name} set.', name=name))

@command(r'get (\S+)')
@command(r'what\'s the value of (\S+)\??$')
@restricted
def set(bot, server, target, source, message, parsed, private):
    name = parsed.group(1)
    val = eval('repr(config.current{})'.format(name))
    bot.privmsg(target, _('config{name}: {val}.', name=name, val=val))


## Misc commands.

@command(r'nick (\S+)')
@command(r'change nick(?:name)? to (\S+)\.?$')
@restricted
def nick(bot, server, target, source, message, parsed, private):
    bot.nick(parsed.group(1))

@command(r'help\??')
@command(r'commands')
@command(r'what are your commands\??$')
def help(bot, server, target, source, message, parsed, private):
    bot.privmsg(target, _('Help yourself.'))

@command(r'error (.*)')
def error(bot, server, target, source, message, parsed, private):
    raise ValueError(parsed.group(1))

@command(r'version')
@command(r'what are you\??$')
def version_(bot, server, target, source, message, parsed, private):
    bot.privmsg(target, 'This is {n} v{v}, ready to serve.'.format(n=version.__name__, v=version.__version__))


def load():
    return True

def unload():
    pass
