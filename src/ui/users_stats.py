import functools
import random
import time
import datetime

import numpy as np

import supervisely_lib as sly

import sly_globals as g
import sly_functions as f

from sly_fields_names import UserStatsField


def init_fields(state, data):
    state['refreshingUsersStatsTable'] = False

    data['usersStatsTable'] = get_users_stats_table(state, users_table=data['usersTable'])


def get_annotated_items_by_user_id(user_id):
    return 0


def update_custom_data(field_name, data):
    project_custom_data = f.get_project_custom_data(g.project_id)
    current_field = project_custom_data.get(field_name, {})
    current_field.update(data)

    project_custom_data[field_name] = current_field

    g.api.project.update_custom_data(g.project_id, project_custom_data)


def init_user_stats(user_id):
    field_name = 'user2stats'

    user_data = {
        f"{user_id}":
            {
                UserStatsField.ITEMS_ANNOTATED: 0,
                UserStatsField.TAGS_CREATED: 0,
                UserStatsField.WORK_TIME: 0
            }
    }

    g.user2stats.update(user_data)
    update_custom_data(field_name, user_data)


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


def get_users_stats_table(state, users_table):
    table = []


    user2performance = get_users_performances(users_table)

    for current_user in users_table:
        table_row = {}
        if state['annotatorsIds'].get(current_user['id'], False):
            current_user['id'] = str(current_user['id'])

            table_row['performance'] = user2performance[current_user['id']]
            table_row['id'] = current_user['id']
            table_row['login'] = current_user['login']
            table_row['role'] = current_user['role']

            user_stats = g.user2stats.get(current_user['id'], {})

            table_row['videos_annotated'] = user_stats.get(UserStatsField.ITEMS_ANNOTATED, 0)
            table_row['tags_created'] = user_stats.get(UserStatsField.TAGS_CREATED, 0)

            work_time_unix = user_stats.get(UserStatsField.WORK_TIME, 0)
            table_row['work_time'] = str(datetime.timedelta(seconds=round(work_time_unix)))

            if work_time_unix != 0:
                table_row['tags_per_time'] = f"{table_row['tags_created'] / work_time_unix: .2f}"
            else:
                table_row['tags_per_time'] = "-"
            table.append(table_row)
    return table


@g.my_app.callback("refresh_users_stats_table")
@sly.timeit
@g.update_fields
def refresh_users_stats_table(api: sly.Api, task_id, context, state, app_logger, fields_to_update):
    fields_to_update['state.refreshingUsersStatsTable'] = False

    users_table = g.api.task.get_field(g.task_id, 'data.usersTable')
    fields_to_update['data.usersStatsTable'] = get_users_stats_table(state, users_table)
