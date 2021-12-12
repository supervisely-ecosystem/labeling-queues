import functools
import time
import datetime

import supervisely_lib as sly

from sly_fields_names import UserStatusField

import sly_globals as g
import sly_functions as f


def init_fields(state, data):
    state['refreshingUsersTable'] = True
    state['refreshingUsersTableTime'] = f.get_current_time()

    data['usersTable'] = f.get_users_table()

    state['annotatorsIds'] = {row['id']: row['can_annotate'] for row in data['usersTable']}
    state['reviewersIds'] = {row['id']: row['can_review'] for row in data['usersTable']}


@g.my_app.callback("refresh_users_table")
@sly.timeit
@g.update_fields
@g.my_app.ignore_errors_and_show_dialog_window()
def refresh_users_table(api: sly.Api, task_id, context, state, app_logger, fields_to_update):
    fields_to_update['state.refreshingUsersTable'] = False
    fields_to_update['state.refreshingUsersTableTime'] = f.get_current_time()

    newest_table = f.get_users_table()
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
