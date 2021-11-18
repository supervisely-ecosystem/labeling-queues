import functools
import time
import datetime

import supervisely_lib as sly

import sly_globals as g
import sly_functions as f


def init_fields(state, data):
    state['refreshingUsersTable'] = False
    state['reviewNeeded'] = False

    data['usersTable'] = fill_users_table()
    data['usersTableHeaders'] = f.get_table_headers_by_table(data['usersTable'])

    state['annotatorsIds'] = {row['user_id']: get_user_status(data['usersTable'], row['user_id'], 'can annotate')
                              for row in data['usersTable']}

    state['reviewersIds'] = {row['user_id']: get_user_status(data['usersTable'], row['user_id'], 'can review')
                             for row in data['usersTable']}


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


def fill_users_table():
    table = []

    g.team_members = g.api.user.get_team_members(g.team_id)
    for current_item in g.team_members:
        table_row = []

        table_row.append({'title': 'id', 'value': current_item.id})
        table_row.append({'title': 'login', 'value': current_item.login})
        table_row.append({'title': 'role', 'value': current_item.role})
        table_row.append({'title': 'last login', 'value': get_user_last_seen(current_item.last_login)})
        table_row.append({'title': 'can annotate', 'value': current_item.role == 'annotator'})
        table_row.append({'title': 'can review', 'value': current_item.role == 'reviewer'})

        table.append({'user_id': current_item.id, 'columns': table_row})
    return table


def get_user_status(table, user_id, key):
    for row in table:
        if row['user_id'] == user_id:
            for column in row['columns']:
                if column['title'] == key:
                    return column['value']



@g.my_app.callback("refresh_users_table")
@sly.timeit
@g.update_fields
def refresh_table(api: sly.Api, task_id, context, state, app_logger, fields_to_update):
    fields_to_update['state.refreshingUsersTable'] = False
    fields_to_update['data.usersTable'] = fill_users_table()
