# ownCloud hook.
import json
import datetime
from michiru import config


## Module information.

__name__ = 'hooks.owncloud'
__author__ = 'Shiz'
__license__ = 'WTFPL'
__desc__ = 'ownCloud hook'
__deps__ = ['hooks']

config.item('hooks.services.owncloud', {
    'allowed_ips': [],
    'targets': {}
})


def handler(config, request):
    messages = []
    message = request.get_json(force=True)
    ident = None

    if request.headers['x-owncloud-event'] == 'owncloud://filesystem-change':
        path = message['path']
        if path.startswith('/Shared'):
            ipath = path.replace('/Shared', '', 1)
        else:
            ipath = path
        ipath = ipath.lstrip('/').split('/', 1)[0]

        ident = '{}:{}'.format(message['user'], ipath)
        if message['mimeType'] == 'httpd/unix-directory':
            messages = ['{{b}}{} folder on ownCloud:{{/b}} {}'.format(
                message['action'].capitalize(),
                path
            )]
        else:
            messages = ['{{b}}{} file on ownCloud:{{/b}} {} (type: {})'.format(
                message['action'].capitalize(),
                path,
                message['mimeType']
            )]


    return (ident, messages)

def load():
    from michiru.modules import hooks
    hooks.register('owncloud', 'owncloud', handler)
    return True

def unload():
    from michiru.modules import hooks
    hooks.unregister('owncloud', 'owncloud', handler)
