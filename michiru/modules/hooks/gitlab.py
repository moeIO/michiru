# Test hook.
import operator
import json
import datetime
from michiru import config, db


## Module information.

__name__ = 'hooks.gitlab'
__author__ = 'Shiz'
__license__ = 'WTFPL'
__desc__ = 'GitLab hook'
__deps__ = ['hooks']

config.item('hooks.services.gitlab', {
    'allowed_ips': [],
    'targets': {}
})

db.table('hooks_gitlab_issues', {
    'id': db.ID,
    'project': (db.STRING, db.INDEX),
    'issue_id': (db.INT, db.INDEX),
    'data': db.STRING,
    'time': db.DATETIME
})


def handler(config, request):
    messages = []
    message = request.get_json(force=True)
    repo = message['project']['homepage']

    # An issue update.
    if message['object_kind'] == 'issue':
        data = message['object_attributes']
        try:
            entry = db.from_('hooks_gitlab_issues').where('project', repo).and_('issue_id', data['iid']).single('id', 'data')
            if entry:
                old_data = json.loads(entry['data'])
            else:
                old_data = None
        except:
            old_data = None

        # An issue we don't know about.
        if not old_data:
            if data['created_at'] == data['updated_at']:
                messages = ['{{b}}New issue on {}:{{/b}} {} - {{u}}{}{{/u}}'.format(
                    message['project']['name'],
                    data['title'],
                    data['url']
                )]
            else:
                messages = ['{{b}}Issue on {} updated:{{/b}} {} - {{u}}{}{{/u}}'.format(
                    message['project']['name'],
                    data['title'],
                    data['url']
                )]
        # An issue we have info about.
        else:
            if old_data['state'] != data['state']:
                messages.append('{{b}}Issue on {} {}:{{/b}} {} - {{u}}{}{{/u}}'.format(
                    message['project']['name'],
                    data['state'],
                    data['title'],
                    data['url']
                ))
            if old_data['assignee_id'] != data['assignee_id']:
                messages.append('{{b}}Issue on {} reassigned:{{/b}} {} - {{u}}{}{{/u}}'.format(
                    message['project']['name'],
                    data['title'],
                    data['url']
                ))
            if old_data['title'] != data['title']:
                messages.append('{{b}}Issue on {} renamed:{{/b}} {} -> {} - {{u}}{}{{/u}}'.format(
                    message['project']['name'],
                    old_data['title'],
                    data['title'],
                    data['url']
                ))
            if old_data['milestone_id'] != data['milestone_id']:
                messages.append('{{b}}Issue milestone on {} updated:{{/b}} {} - {{u}}{}{{/u}}'.format(
                    message['project']['name'],
                    data['title'],
                    data['url']
                ))
            if old_data != data and not messages:
                messages = ['{{b}}Issue on {} updated:{{/b}} {} - {{u}}{}{{/u}}'.format(
                    message['project']['name'],
                    data['title'],
                    data['url']
                )]


        data = {
            'project': repo,
            'issue_id': data['iid'],
            'data': json.dumps(data),
            'time': datetime.datetime.utcnow()
        }
        if entry:
            db.in_('hooks_gitlab_issues').where('id', entry['id']).update(data)
        else:
            db.to('hooks_gitlab_issues').add(data)
    # Pushed commits.
    elif message['object_kind'] == 'push':
        for commit in sorted(message['commits'], key=operator.itemgetter('timestamp')):
            messages.append('{{b}}Commit on {} by {}:{{/b}} {} - {{u}}{}{{/u}}'.format(
                message['project']['name'],
                commit['author']['name'],
                commit['message'].strip(),
                commit['url']
            ))
    # Comments.
    elif message['object_kind'] == 'note':
        data = message['object_attributes']
        if data['created_at'] == data['updated_at']:
            heading = 'New {} comment on {}'.format(
                data['noteable_type'].lower(),
                message['project']['name']
            )
        else:
            heading = '{} comment on {} updated'.format(
                data['noteable_type'],
                message['project']['name']
            )

        data['note'] = data['note'].replace('\n', ' ').strip()
        if len(data['note']) > 400:
            data['note'] = data['note'][:400] + '...'
        messages = ['{{b}}{}:{{/b}} <{}> {} - {{u}}{}{{/u}}'.format(
            heading,
            message['user']['name'],
            data['note'], data['url']
        )]

    return (repo, messages)

def load():
    from michiru.modules import hooks
    hooks.register('gitlab', 'gitlab', handler)
    return True

def unload():
    from michiru.modules import hooks
    hooks.unregister('gitlab', 'gitlab', handler)
