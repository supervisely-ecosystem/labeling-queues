import functools
import random
import time
import datetime

import numpy as np

import supervisely_lib as sly

from sly_fields_names import ItemsStatusField
import sly_globals as g
import sly_functions as f

from sly_fields_names import UserStatsField


def init_fields(state, data):
    state['itemsCount'] = len(g.item2stats)

    state['collapsedQueues'] = {
        'labeling_q': False,
        'reviewing_q': False,
        'completed_q': False
    }

    table_names = {
        'labelingWaitingTable': ItemsStatusField.NEW,
        'labelingInProgressTable': ItemsStatusField.ANNOTATING,
        'reviewingWaitingTable': ItemsStatusField.ANNOTATED,
        'reviewingInProgressTable': ItemsStatusField.REVIEWING,
        'completedItemsTable': ItemsStatusField.COMPLETED,

    }

    for table_name, items_status in table_names.items():
        data[table_name] = get_table_by_status(items_status)


def get_table_by_items_status(items_status, fields):
    table = []

    for item_id, item_info in g.item2stats.items():
        if item_info.get('status') == items_status:
            for current_field in fields:
                if item_info.get(current_field, None) is None:
                    item_info[current_field] = '-'
            table.append(item_info)
    return table


def get_table_fields_by_status(items_status):
    if items_status == ItemsStatusField.NEW:
        return ['item_id', 'item_name', 'duration', 'worker_login', 'item_work_time']
    elif items_status == ItemsStatusField.ANNOTATING:
        return ['item_id', 'item_name', 'duration', 'worker_login', 'item_work_time']  # BETA
    elif items_status == ItemsStatusField.ANNOTATED:
        return ['item_id', 'item_name', 'duration', 'worker_login', 'item_work_time']  # BETA
    elif items_status == ItemsStatusField.REVIEWING:
        return ['item_id', 'item_name', 'duration', 'worker_login', 'item_work_time']  # BETA
    elif items_status == ItemsStatusField.REVIEWED:
        return ['item_id', 'item_name', 'duration', 'worker_login', 'item_work_time']  # BETA
    elif items_status == ItemsStatusField.COMPLETED:
        return ['item_id', 'item_name', 'duration', 'worker_login', 'item_work_time']  # BETA


def get_table_by_status(items_status):
    fields = get_table_fields_by_status(items_status)
    return get_table_by_items_status(items_status, fields)


def update_tables(fields_to_update):
    table_names = {
        'labelingWaitingTable': ItemsStatusField.NEW,
        'labelingInProgressTable': ItemsStatusField.ANNOTATING,
        'reviewingWaitingTable': ItemsStatusField.ANNOTATED,
        'reviewingInProgressTable': ItemsStatusField.REVIEWING,
        'completedItemsTable': ItemsStatusField.COMPLETED,

    }

    for table_name, items_status in table_names.items():
        fields_to_update[f'data.{table_name}'] = get_table_by_status(items_status)
