# Michiru's core module.
import os
import sys
import io
import math
import functools

from michiru import config, db, chat, modules, personalities, version
from michiru.modules import command
_ = personalities.localize


## Module information.
__name__ = 'core'
__author__ = 'Shiz'
__license__ = 'WTFPL'
__desc__ = 'Core functionality.'


## Personality translations.

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
    'This command is restricted to administrators.':
        'B-baka! Y-you can\'t just walk up and do that kinda stuff without permission!',
    'Administrator {nick} added.':
        'I guess {nick} is a pretty cool person, huh...',
    'Administrator {nick} removed.':
        'I didn\'t like {nick} anyway, the CREEP!',
    'Administrators: {}':
        'My current masters? えとね, there\'s {}, I think...',
    'Module {mod} enabled for channel {chan}.':
        'I guess I\'ll enable {mod} just for you...',
    'Module {mod} enabled for server {srv}.':
        'よし！ {mod} in action! ヽ( ˃ ヮ˂)ノ',
    'Module {mod} globally enabled.':
        'よし！ {mod} in action! ヽ( ˃ ヮ˂)ノ',
    'Module {mod} disabled for channel {chan}.':
        'W-well, {mod} may have been just a little bit annoying...',
    'Module {mod} disabled for server {srv}.':
        'Good riddance, {mod} was the WORST!',
    'Module {mod} globally disabled.':
        'Good riddance, {mod} was the WORST!',
    'Module {mod} loaded.':
        'Michiru ＰＯＷＥＲ－ＵＰ！ {mod} activated!',
    'Module {mod} unloaded.':
        'I suddenly feel a lot thinner... (´･ω･`)',
    'Module {mod} reloaded.':
        'Michiru ＲＥＬＯＡＤ！ {mod} updated!',
    'Loaded modules: {mods}':
        'R-right now, Michiru can do this! {mods}',
    'Unknown server {srv}.':
        'Michiru doesn\'t know that server... (´･ω･`)',
    'Already connected to {tag}.':
        'Michiru\'s already there, ba-ka!',
    'Connecting to {tag}... this might take a while.':
        'I-I\'ll do my best to check it out, but it might take a bit!',
    'Connected to {tag} successfully.':
        'よし, Michiru got there! It\'s so lonely though... (´･ω･`)',
    'Configuration loaded.':
        'Now I remember!',
    'Configuration saved.':
        'Wrote these settings down to be su-per sure~! (☝ﾟ∀ﾟ)☝',
    'Configuration item {name} set.':
        'I\'ll try to remember that! (´･ω･`)',
    'config{name}: {val}.':
        'I-I think {name} is {val}, ri-right? (´･ω･`)',
    'Already ignoring {nick}.':
        'Michiru al~ready knows {nick} sucks!',
    'Already ignoring {nick} on channel {chan}.':
        'Michiru al~ready knows {nick} sucks!',
    '{nick} added to ignore list.':
        'Yeah, they are the WO~RST! ┌(`～´；)┐',
    '{nick} added to ignore list for channel {chan}.':
        'Yeah, they are the WO~RST! ┌(`～´；)┐',
    'Not ignoring {nick}.':
        'I\'m not ignoring {nick}! S-should I...? (´･ω･`)',
    'Not ignoring {nick} on channel {chan}.':
        'I\'m not ignoring {nick}! S-should I...? (´･ω･`)',
    '{nick} removed from ignore list.':
        'I-I guess {nick} can be pretty alright... b-but only because you say so!',
    '{nick} removed from ignore list for channel {chan}.':
        'I-I guess {nick} can be pretty alright... b-but only because you say so!',
    'Currently ignoring: {ignores}':
        'Fuck {ignores}!',
    'Not ignoring anyone right now.':
        'Everyone\'s okay by me! ( ¯◡◡¯·)',
    'Help yourself.':
        'Michiru ごめん！ I really don\'t know anything right now... ㅠ_ㅠ',
    'My source is at {src}.':
        'I s-suppose you could find me at {src}... but don\'t look too closely, CREEP! (/ω＼)',
    'This is {n} v{v}, ready to serve.':
        '{n} Ver.{v} でーす！ ヽ( ˃ ヮ˂)ノ',
    '"psutil" module not found.':
        'Waa! Couldn\'t find psutil! ( ´· A ·`)'
})


## Helper functions.

def restricted(func):
    @functools.wraps(func)
    def inner(bot, server, target, source, message, parsed, private, admin):
        if not admin:
            raise EnvironmentError(_(bot, 'This command is restricted to administrators.', cmd=func.__name__))
        else:
            return func(bot, server, target, source, message, parsed, private=private, admin=admin)
    return inner


## Admin commands.

@command(r'addadmin (\S+)(?: (\S+))?')
@command(r'add admin (\S+)(?: on channel (\S+))?\.?$')
@restricted
def addadmin(bot, server, target, source, message, parsed, private, admin):
    nick = parsed.group(1)
    chan = None
    if parsed.group(2):
        chan = parsed.group(2)

    bot.promote(nick, chan)
    yield from bot.message(target, _(bot, 'Administrator {nick} added.', nick=nick))

@command(r'listadmins(?: (\S+))?')
@command(r'list admins(?: for channel (\S+))?\.?$')
@restricted
def listadmins(bot, server, target, source, message, parsed, private, admin):
    yield from bot.message(target, _(bot, 'Administrators: {}', ', '.join(bot.admins(parsed.group(1)))))

@command(r'rmadmin (\S+)(?: (\S+))?')
@command(r'remove admin (\S+)(?: from channel (\S+))?\.?$')
@restricted
def rmadmin(bot, server, target, source, message, parsed, private, admin):
    nick = parsed.group(1)
    chan = None
    if parsed.group(2):
        chan = parsed.group(2)

    bot.demote(nick, chan)
    yield from bot.message(target, _(bot, 'Administrator {nick} removed.', nick=nick))


## Module commands.

@command(r'enable (\S+)(?: (\S+)(?: (\S+))?)?\.?$')
@command(r'enable (\S+) on (\S+)(?:, channel (\S+))?\.?$')
@restricted
def enable(bot, server, target, source, message, parsed, private, admin):
    module = parsed.group(1)
    if parsed.group(3):
        server = parsed.group(2)
        channel = parsed.group(3)
        modules.enable(module, server, channel)

        yield from bot.message(target, _(bot, 'Module {mod} enabled for channel {chan}.', mod=module, srv=server, chan=channel))
    elif parsed.group(2):
        server = parsed.group(2)

        if server != 'global' and server != 'globally':
            modules.enable(module, server)
            yield from bot.message(target, _(bot, 'Module {mod} enabled for server {srv}.', mod=module, srv=server))
        else:
            modules.enable(module)
            yield from bot.message(target, _(bot, 'Module {mod} globally enabled.', mod=module))
    else:
        modules.enable(module, server, target)

        yield from bot.message(target, _(bot, 'Module {mod} enabled for channel {chan}.', mod=module, srv=server, chan=target))

@command(r'disable (\S+)(?: (?: on)?(\S+)(?:(?:, channel)? (\S+))?)?\.?')
@restricted
def disable(bot, server, target, source, message, parsed, private, admin):
    module = parsed.group(1)
    if parsed.group(3):
        server = parsed.group(2)
        channel = parsed.group(3)
        modules.disable(module, server, channel)

        yield from bot.message(target, _(bot, 'Module {mod} disabled for channel {chan}.', mod=module, srv=server, chan=channel))
    elif parsed.group(2):
        server = parsed.group(2)

        if server != 'global' and server != 'globally':
            modules.disable(module, server)
            yield from bot.message(target, _(bot, 'Module {mod} disabled for server {srv}.', mod=module, srv=server))
        else:
            modules.disable(module)
            yield from bot.message(target, _(bot, 'Module {mod} globally disabled.', mod=module))
    else:
        modules.disable(module, server, target)

        yield from bot.message(target, _(bot, 'Module {mod} disabled for channel {chan}.', mod=module, srv=server, chan=target))


@command(r'load (?: the)?(\S+)(?: module)?\.?$')
@restricted
def load(bot, server, target, source, message, parsed, private, admin):
    module = parsed.group(1)
    modules.load(module)
    yield from bot.message(target, _(bot, 'Module {mod} loaded.', mod=module))

@command(r'unload (?:the )?(\S+)(?: module)?(?:(?:the )?hard(?: way)?)?\.?')
@restricted
def unload(bot, server, target, source, message, parsed, private, admin):
    module = parsed.group(1)
    modules.unload(module)
    yield from bot.message(target, _(bot, 'Module {mod} unloaded.', mod=module))

@command(r'reload (?:the )?(\S+)(?: module)?\.?')
@restricted
def reload(bot, server, target, source, message, parsed, private, admin):
    module = parsed.group(1)
    modules.load(module, reload=True)
    yield from bot.message(target, _(bot, 'Module {mod} reloaded.', mod=module))

@command(r'loaded')
def loaded(bot, server, target, source, message, parsed, private, admin):
    yield from bot.message(target, _(bot, 'Loaded modules: {mods}', mods=', '.join(sorted(modules.modules.keys()))))


## Join/part servers/channels.

@command(r'join (\S+)(?: (\S+)(?: (\S+))?)?\.?$')
@restricted
def join(bot, server, target, source, message, parsed, private, admin):
    if parsed.group(2):
        target_serv = parsed.group(1)
        target_chan = parsed.group(2)
    else:
        target_serv = server
        target_chan = parsed.group(1)

    if not target_serv in chat.bots.keys():
        raise EnvironmentError(_('Unknown server {srv}.', srv=target_serv))
    chat.bots[target_serv].join_(target_chan, parsed.group(3))

@command(r'part(?: (\S+)(?: (\S+)(?: (\S+))?)?)?\.?$')
@restricted
def part(bot, server, target, source, message, parsed, private, admin):
    if parsed.group(2):
        target_serv = parsed.group(1)
        target_chan = parsed.group(2)
    elif parsed.group(1):
        target_serv = server
        target_chan = parsed.group(1)
    else:
        target_serv = server
        target_chan = target

    if not target_serv in chat.bots.keys():
        raise EnvironmentError(_('Unknown server {srv}.', srv=target_serv))
    chat.bots[target_serv].part(target_chan, parsed.group(3) or _(bot, 'Parted.'))

@command(r'connect (\S+)(?: ([0-9]+)(?: (true|false))?)?')
@command(r'connect to (\S+)(?: with port ([0-9]+)(?: and TLS set to (true|false))?)?\.?$')
@restricted
def connect(bot, server, target, source, message, parsed, private, admin):
    info = bot.michiru_config.copy()
    info['channels'] = []
    info['host'] = parsed.group(1)
    if parsed.group(3):
        info['tls'] = parsed.group(3) == 'true'
    if parsed.group(2):
        info['port'] = int(parsed.group(2))

    tag = info['host'].rsplit('.', 2)[1]
    if tag in chat.bots:
        raise EnvironmentError(_('Already connected to {tag}.', tag=tag))

    yield from bot.message(target, _(bot, 'Connecting to {tag}... this might take a while.', tag=tag, host=info['host'], port=info['port']))
    config.current['servers'][tag] = info

    chat.connect(tag, info)

    yield from bot.message(target, _(bot, 'Connected to {tag} successfully.', tag=tag, host=info['host'], port=info['port']))

@command(r'(?:quit|gtfo)(?: (\S+)?)?\.?')
@restricted
def quit(bot, server, target, source, message, parsed, private, admin):
    if parsed.group(1):
        serv = parsed.group(1)
        if not serv in chat.bots.keys():
            raise EnvironmentError(_('Unknown server {srv}.', srv=serv))

        chat.bots[parsed.group(1)].quit(_('Quit'))
    else:
        for bot in chat.bots.values():
            bot.quit(_('Quit'))


## Ignore/unignore commands.

@command(r'(?:give|list) (?:fuck|ignore)s(?: (#\S+|everywhere))?\.?')
def ignores(bot, server, target, source, message, parsed, private, admin):
    chan = parsed.group(1)
    if chan == 'everywhere':
        chan = None
    elif chan is None:
        chan = target

    ignores = bot.ignores_for(chan)

    if ignores:
        yield from bot.message(target, _(bot, 'Currently ignoring: {ignores}', ignores=', '.join(ignores)))
    else:
        yield from bot.message(target, _(bot, 'Not ignoring anyone right now.'))

@command(r'(?:ignore|fuck) (\S+)(?: (#\S+|everywhere))?\.?')
@restricted
def ignore(bot, server, target, source, message, parsed, private, admin):
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
        yield from bot.message(target, _(bot, '{nick} added to ignore list.', nick=nick))
    else:
        if bot.ignored(nick, chan):
            raise EnvironmentError(_('Already ignoring {nick} on channel {chan}.', nick=nick, chan=chan))
        bot.ignore(nick, chan)
        yield from bot.message(target, _(bot, '{nick} added to ignore list for channel {chan}.', nick=nick, chan=chan))

@command(r'un(?:ignore|fuck) (\S+)(?: (#\S+|everywhere))?')
@command(r'stop ignoring (\S+)(?: (?:on (\S+)|(everywhere))?)?\.?')
@command(r'(\S+)(?: i|\')s cool(?: (?:on (\S+)|(everywhere))?)?\.?')
@restricted
def unignore(bot, server, target, source, message, parsed, private, admin):
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
        yield from bot.message(target, _(bot, '{nick} removed from ignore list.', nick=nick))
    else:
        if not bot.ignored(nick, chan):
            raise EnvironmentError(_('Not ignoring {nick} on channel {chan}.', nick=nick, chan=chan))
        bot.unignore(nick, chan)
        yield from bot.message(target, _(bot, '{nick} removed from ignore list for channel {chan}.', nick=nick, chan=chan))


## Configuration commands.

@command(r'loadconf')
@command(r'remember how I told you to behave\??')
@restricted
def loadconf(bot, server, target, source, message, parsed, private, admin):
    config.load()
    yield from bot.message(target, _(bot, 'Configuration loaded.'))

@command(r'saveconf')
@command(r'save (?:your |the )?configuration\.?$')
@command(r'b(?:-b)*ack that shit up\.?')
@restricted
def saveconf(bot, server, target, source, message, parsed, private, admin):
    config.save()
    yield from bot.message(target, _(bot, 'Configuration saved.'))

@command(r'set (?:(?:(\S+)\:)?(\S+)\:)?(\S+)(?: to)? (.+)\.?$')
@restricted
def set(bot, server, target, source, message, parsed, private, admin):
    serv, chan, name, value = parsed.group(1, 2, 3, 4)

    value = eval(value)
    chan = chan or (None if serv else target)
    serv = serv or server

    config.set(name, value, serv, chan)
    yield from bot.message(target, _(bot, 'Configuration item {name} set.', name=name))

@command(r'add (?:(?:(\S+)\:)?(\S+)\:)?(\S+) (.+)\.?$')
@restricted
def add(bot, server, target, source, message, parsed, private, admin):
    serv, chan, name, value = parsed.group(1, 2, 3, 4)

    value = eval(value)
    chan = chan or (None if serv else target)
    serv = serv or server

    config.add(name, value, serv, chan)
    yield from bot.message(target, _(bot, 'Added value to configuration item {name}.', name=name))

@command('setitem (?:(?:(\S+)\:)?(\S+)\:)?(\S+) (\S+) (.+)\.?$')
@restricted
def setitem(bot, server, target, source, message, parsed, private, admin):
    serv, chan, item, key, value = parsed.group(1, 2, 3, 4, 5)

    value = eval(value)
    chan = chan or (None if serv else target)
    serv = serv or server

    config.setitem(item, name, value, serv, chan)
    yield from bot.message(target, _(bot, 'Set key in configuration item {name}.', name=name))

@command(r'get (?:(?:(\S+)\:)?(\S+)\:)?(\S+)')
@command(r'what\'s the value of (\S+)\??$')
@restricted
def get(bot, server, target, source, message, parsed, private, admin):
    serv, chan, name = parsed.group(1, 2, 3)

    chan = chan or (None if serv else target)
    serv = serv or server

    val = config.get(name, serv, chan)
    yield from bot.message(target, _(bot, '{name}: {val}', name=name, val=val))

@command(r'list (?:(?:(\S+)\:)?(\S+)\:)?(\S+)\.?')
@restricted
def list_(bot, server, target, source, message, parsed, private, admin):
    serv, chan, name = parsed.group(1, 2, 3)

    chan = chan or (None if serv else target)
    serv = serv or server

    val = config.list(name, serv, chan)
    yield from bot.message(target, _(bot, '{name}: {val}', name=name, val=', '.join(val)))

@command(r'dict (?:(?:(\S+)\:)?(\S+)\:)?(\S+)')
@restricted
def dict_(bot, server, target, source, message, parsed, private, admin):
    serv, chan, name = parsed.group(1, 2, 3)

    value = eval(value)
    chan = chan or (None if serv else target)
    serv = serv or server

    val = config.dict(name, serv, chan)
    yield from bot.message(target, _(bot, '{name}: {val}', name=name, val=val))


@command(r'del (?:(?:(\S+)\:)?(\S+)\:)?(\S+) (\S+)')
@restricted
def del_(bot, server, target, source, message, parsed, private, admin):
    serv, chan, name, key = parsed.group(1, 2, 3, 4)

    chan = chan or (None if serv else target)
    serv = serv or server

    config.delete(name, key, serv, chan)
    yield from bot.message(target, _(bot, '{name}{{{key}}} deleted.', name=name, key=key))

## Misc commands.

@command(r'eval (.*)$')
@command(r'evaluate (.*)$')
@restricted
def evaluate(bot, server, target, source, message, parsed, private, admin):
    code = parsed.group(1)

    # Capture output.
    resio = io.StringIO()
    sys.stdout = resio
    sys.stderr = resio

    res = None
    try:
        res = eval(code)
    except SyntaxError:
        exec(code)

    # Restore output.
    sys.stdout = sys.__stdout__
    sys.stderr = sys.__stderr__

    # Format output.
    resio = resio.getvalue()
    if res:
        if resio:
            res = repr(res) + '\n' + resio
        else:
            res = repr(res)
    else:
        res = resio

    # Only output if we have something relevant to.
    res = res.strip()
    if res:
        res = res.replace('\n', ' - ')
        yield from bot.message(target, res)

@command(r'nick (\S+)')
@command(r'change nick(?:name)? to (\S+)\.?$')
@restricted
def nick(bot, server, target, source, message, parsed, private, admin):
    yield from bot.nick(parsed.group(1))

@command(r'help\??')
@command(r'commands')
@command(r'what are your commands\??$')
def help(bot, server, target, source, message, parsed, private, admin):
    yield from bot.message(target, _(bot, 'Help yourself.'))

@command(r'error (.*)')
def error(bot, server, target, source, message, parsed, private, admin):
    raise ValueError(parsed.group(1))

@command(r'source')
@command(r'where (?:is|can I find) your source(?: code)?\??')
def source(bot, server, target, source, message, parsed, private, admin):
    yield from bot.message(target, _(bot, 'My source is at {src}.', src=version.__source__))

@command(r'version')
@command(r'wh(?:at|o) are you\??$')
def version_(bot, server, target, source, message, parsed, private, admin):
    yield from bot.message(target, _(bot, 'This is {n} v{v}, ready to serve.', n=version.__name__, v=version.__version__))


@command(r'stats')
@command(r'(?:what(?: kind of)?|how many) resources are you using\??')
@command(r'how (?:bloated|thick) are you\??')
def stats(bot, server, target, source, message, parsed, private, admin):
    try:
        import psutil
    except:
        raise EnvironmentError(_('"psutil" module not found.'))

    # Helper function. Turn amount into readable string including SI prefix.
    def si_ify(n):
        orders = ['k', 'M', 'G', 'T', 'P', 'E', 'Z', 'Y']
        order = math.floor(math.log(n, 2) / 10)
        n /= math.pow(2, order * 10)
        if order:
            return '{n} {u}iB'.format(n=round(n, 2), u=orders[order - 1])
        return '{n} B'.format(n=n)

    # And dump info.
    proc = psutil.Process(os.getpid())
    try:
        conncount = len(proc.connections('inet'))
    except psutil.AccessDenied:
        conncount = '???'
    yield from bot.message(target, _(bot, 'I use: CPU: {cpuperc}%; RAM: {ramused}/{ramtotal} ({ramperc}%); Threads: {threadcount}; Connections: {conncount}',
        cpuperc=round(proc.cpu_percent(), 2),
        ramused=si_ify(proc.memory_info()[0]),
        ramtotal=si_ify(psutil.virtual_memory().total),
        ramperc=round(proc.memory_percent(), 2),
        threadcount=proc.num_threads(),
        conncount=conncount))


## Boilerplate.

def load():
    return True

def unload():
    pass
