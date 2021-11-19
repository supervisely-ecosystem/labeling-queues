import functools
import time
import datetime

import supervisely_lib as sly

import sly_globals as g
import sly_functions as f


def init_fields(state, data):
    state['refreshingUsersTable'] = False

    data['usersTable'] = get_users_table()

    state['annotatorsIds'] = {row['id']: row['can_annotate'] for row in data['usersTable']}
    state['reviewersIds'] = {row['id']: row['can_review'] for row in data['usersTable']}


def get_user_last_seen(datetime_str):
    d = datetime.datetime.strptime(datetime_str, '%Y-%m-%dT%H:%M:%S.%f%z')

    last_seen_unix = time.mktime(time.gmtime()) - time.mktime(d.timetuple())
    last_seen_datetime = datetime.timedelta(seconds=round(last_seen_unix))

    if last_seen_datetime.days == 0:
        return f"{last_seen_datetime} ago"
    elif 30 > last_seen_datetime.days > 0:
        return f"{last_seen_datetime.days} days ago"
    else:
        return "long time ago"


def get_users_table():
    table = []

    g.team_members = g.api.user.get_team_members(g.team_id)

    # for i in range(100):  # DEBUG
    for current_item in g.team_members:
        table_row = {}

        table_row['id'] = current_item.id
        table_row['login'] = current_item.login
        table_row['role'] = current_item.role
        table_row['last_login'] = get_user_last_seen(current_item.last_login)
        table_row['can_annotate'] = current_item.role == 'annotator'
        table_row['can_review'] = current_item.role == 'reviewer'

        table.append(table_row)
    return table


@g.my_app.callback("refresh_users_table")
@sly.timeit
@g.update_fields
def refresh_users_table(api: sly.Api, task_id, context, state, app_logger, fields_to_update):
    fields_to_update['state.refreshingUsersTable'] = False

    newest_table = get_users_table()
    current_table = api.task.get_field(g.task_id, 'data.usersTable')

    users_ids_in_table = [row['id'] for row in current_table]

    for row in newest_table:
        if row['id'] not in users_ids_in_table:
            current_table.append(row)

    state['annotatorsIds'].update({row['id']: row['can_annotate'] for row in current_table
                                   if row['id'] not in users_ids_in_table})

    state['reviewersIds'].update({row['id']: row['can_review'] for row in current_table
                                  if row['id'] not in users_ids_in_table})

    fields_to_update['state.annotatorsIds'] = state['annotatorsIds']
    fields_to_update['state.reviewersIds'] = state['reviewersIds']
    fields_to_update['data.usersTable'] = current_table
