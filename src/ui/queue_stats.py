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
    state['itemsCount'] = len(g.item2stats)

    state['collapsedQueues'] = {
        'labeling_q': False,
        'reviewing_q': False,
        'completed_q': False
    }

    data['labelingWaitingTable'] = get_table_by_queue('labeling', in_waiting=True)
    data['labelingInProgressTable'] = []

    data['reviewingWaitingTable'] = []
    data['reviewingInProgressTable'] = []

    data['completedItemsTable'] = []


def get_table_by_items_ids(items_ids, fields):
    table = []
    for item_id in items_ids:
        item_info = g.item2stats.get(item_id, None)
        if item_info:
            for current_field in fields:
                if item_info.get(current_field, None) is None:
                    item_info[current_field] = '-'

            table.append(item_info)
    return table


def get_table_by_queue(queue_name, in_waiting=False):
    if queue_name == 'labeling':
        current_queue = g.labeling_queue
        fields = ['item_id', 'item_name', 'duration', 'worker_login', 'item_work_time']

    elif queue_name == 'reviewing':
        current_queue = g.labeling_queue
        fields = ['item_id', 'item_name', 'duration', 'worker_login', 'item_work_time']
    else:
        raise ValueError(f'Queue with name {queue_name} does not exists!')

    items_in_queue = list(current_queue.queue)
    return get_table_by_items_ids(items_in_queue, fields)

