import functools
import random
import time
import datetime

import numpy as np

import queue_stats
import supervisely_lib as sly

import sly_globals as g
import sly_functions as f

from sly_fields_names import UserStatsField, UserStatusField


def init_fields(state, data):
    state['refreshingUsersStatsTable'] = False
    state['refreshingUsersStatsTableTime'] = f.get_current_time()

    data['usersStatsTable'] = get_users_stats_table(state, users_table=data['usersTable'])


def init_user_stats(user_id):
    user_data = {

        UserStatsField.ITEMS_ANNOTATED: 0,
        UserStatsField.FRAMES_ANNOTATED: 0,
        UserStatsField.TAGS_CREATED: 0,
        UserStatsField.WORK_TIME: 0

    }

    existing_fields = g.user2stats.get(f"{user_id}", {})
    user_data.update(existing_fields)  # updating by cached stats

    f.update_user_stats(user_id, user_data)


def get_users_performances(users_table):
    user2coefficient = {}
    user2performance = {}

    for current_user in users_table:
        current_user['id'] = str(current_user['id'])
        user_stats = g.user2stats.get(current_user['id'], None)
        if user_stats is None:
            init_user_stats(current_user['id'])
            user_stats = g.user2stats[current_user['id']]

        tags_created = user_stats.get(UserStatsField.TAGS_CREATED, 0)
        work_time_unix = user_stats.get(UserStatsField.WORK_TIME, 0)

        if work_time_unix != 0:
            user2coefficient[current_user['id']] = tags_created / work_time_unix
        else:
            user2performance[current_user['id']] = 'normal'

    if len(user2coefficient) > 0:
        sigma = np.std(list(user2coefficient.values())) / 2
        mean_value = np.mean(list(user2coefficient.values()))

        for current_user in user2coefficient.keys():
            user_c = user2coefficient[current_user]

            if mean_value - sigma < user_c < mean_value + sigma:
                user2performance[current_user] = 'normal'

            elif (mean_value - sigma * 2) < user_c < (mean_value - sigma):
                user2performance[current_user] = 'low'

            elif user_c < (mean_value - sigma * 2):
                user2performance[current_user] = 'very low'

            elif (mean_value + sigma) < user_c < (mean_value + sigma * 2):
                user2performance[current_user] = 'high'

            elif (mean_value + sigma * 2) < user_c:
                user2performance[current_user] = 'very_high'

            else:
                user2performance[current_user] = 'normal'

    return user2performance


def get_user_status_by_id(user_id):
    task_id = g.user2task.get(f'{user_id}', None)

    if task_id is not None:
        f.session_is_online(task_id)
    else:
        return UserStatusField.OFFLINE


def get_users_stats_table(state, users_table):
    table = []

    user2performance = get_users_performances(users_table)

    for current_user in users_table:
        table_row = {}
        current_user['id'] = str(current_user['id'])
        user_local_stats = g.user2stats.get(current_user['id'], {})  # fill additional fields

        if state['annotatorsIds'].get(current_user['id'], False):  # ANNOTATORS STATS
            table_row['performance'] = user2performance[current_user['id']]
            table_row['status'] = user_local_stats.get('status', UserStatusField.OFFLINE)

            for current_field in ['id', 'login', 'role']:  # fill general fields
                table_row[current_field] = current_user[current_field]

            for additional_field in [UserStatsField.ITEMS_ANNOTATED, UserStatsField.FRAMES_ANNOTATED,
                                     UserStatsField.TAGS_CREATED]:
                table_row[additional_field] = user_local_stats.get(additional_field, 0)

            work_time_unix = user_local_stats.get(UserStatsField.WORK_TIME, 0)
            table_row['work_time'] = f.get_datetime_by_unix(work_time_unix)

            if work_time_unix != 0:
                table_row['frames_per_time'] = f"{table_row[UserStatsField.FRAMES_ANNOTATED] / work_time_unix: .2f}"
            else:
                table_row['frames_per_time'] = "-"

            table.append(table_row)
    return table


@g.my_app.periodic(seconds=5)
@g.update_fields
def recheck_user_statuses(api, task_id, fields_to_update):
    sly.logger.info('function called')
    for user_id, user_stats in g.user2stats.items():

        user_task_id = g.user2task.get(f'{user_id}', None)

        if user_task_id is not None:
            if not f.session_is_online(user_task_id):
                updated_user_stats['status'] = UserStatusField.OFFLINE
                updated_user_stats['task_id'] = None

                g.user2task.pop(f'{user_id}')
                item_id = g.task2item.pop(user_task_id)

                f.return_item_to_queue(item_id)
                queue_stats.update_tables(fields_to_update)


        else:
            updated_user_stats['status'] = UserStatusField.OFFLINE

        g.user2stats[f'{user_id}'].update(updated_user_stats)


@g.my_app.callback("refresh_users_stats_table")
@sly.timeit
@g.update_fields
def refresh_users_stats_table(api: sly.Api, task_id, context, state, app_logger, fields_to_update):
    fields_to_update['state.refreshingUsersStatsTable'] = False
    fields_to_update['state.refreshingUsersStatsTableTime'] = f.get_current_time()

    users_table = g.api.task.get_field(g.task_id, 'data.usersTable')
    fields_to_update['data.usersStatsTable'] = get_users_stats_table(state, users_table)
