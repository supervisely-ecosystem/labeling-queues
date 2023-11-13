import functools
import random
import time
import datetime

import numpy as np

import queue_stats
import supervisely as sly
from supervisely import handle_exceptions

import sly_globals as g
import sly_functions as f

from sly_fields_names import UserStatsField, UserStatusField


def init_fields(state, data):
    state['refreshingUsersStatsTable'] = True
    state['refreshingUsersStatsTableTime'] = f.get_current_time()

    update_users_additional_stats()


def get_users_performances(users_table):
    user2coefficient = {}
    user2performance = {}

    for current_user in users_table:
        current_user['id'] = str(current_user['id'])
        user_stats = g.user2stats.get(current_user['id'], None)

        tags_created = user_stats.get(UserStatsField.TAGS_CREATED, 0)
        work_time_unix = user_stats.get(UserStatsField.WORK_TIME_UNIX, 0)

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


def get_user_frames_per_time_value(user_id):
    work_time_unix = g.user2stats[user_id].get(UserStatsField.WORK_TIME_UNIX, 0)

    if work_time_unix != 0:
        return f"{g.user2stats[user_id].get(UserStatsField.FRAMES_ANNOTATED, 0) / work_time_unix: .2f}"
    else:
        return None


def update_users_additional_stats():
    users_table = f.get_users_table()
    user2performance = get_users_performances(users_table)

    for user_id, user_stats in g.user2stats.items():
        additional_stats = {
            'performance': user2performance.get(user_id, None),
            'frames_per_time': get_user_frames_per_time_value(user_id)
        }
        g.user2stats[user_id].update(additional_stats)

    f.update_custom_data('user2stats', g.user2stats)


@g.my_app.periodic(seconds=5)
@g.update_fields
@handle_exceptions
def recheck_user_statuses(api, task_id, fields_to_update):
    # sly.logger.info('function called')
    for user_id, user_stats in g.user2stats.items():
        user_task_id = g.user2task.get(f'{user_id}', None)

        if user_task_id is not None:
            if not f.session_is_online(user_task_id):
                user_stats['status'] = UserStatusField.OFFLINE
                user_stats['task_id'] = None
                g.user2task.pop(f'{user_id}')

                if g.task2item.get(user_task_id) is not None:
                    item_id = g.task2item.pop(user_task_id)

                    f.return_item_to_queue(item_id)
                    queue_stats.update_tables(fields_to_update)

        else:
            user_stats['status'] = UserStatusField.OFFLINE

        g.user2stats[f'{user_id}'].update(user_stats)


@g.my_app.callback("refresh_users_stats_table")
@sly.timeit
@g.update_fields
@g.my_app.ignore_errors_and_show_dialog_window()
@handle_exceptions
def refresh_users_stats_table(api: sly.Api, task_id, context, state, app_logger, fields_to_update):
    fields_to_update['state.refreshingUsersStatsTable'] = False
    fields_to_update['state.refreshingUsersStatsTableTime'] = f.get_current_time()

    update_users_additional_stats()

    fields_to_update['data.usersTable'] = f.get_users_table()
