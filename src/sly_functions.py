import datetime
from string import Formatter

import supervisely_lib as sly

import sly_globals as g

from sly_fields_names import ItemsStatusField, UserStatusField


def init_project_items_info(project_id):
    datasets_list = g.api.dataset.get_list(project_id)

    for current_dataset in datasets_list:
        items_list = g.api.video.get_list(current_dataset.id)

        for current_item in items_list:
            table_row = {
                'status': ItemsStatusField.NEW,
                'item_id': current_item.id,
                'item_name': current_item.name,
                'dataset': current_dataset.name,
                'item_frames': current_item.frames_count,
                'duration': get_item_duration(current_item),
                'work_time': get_datetime_by_unix(0)
            }

            existing_fields = g.item2stats.get(f"{current_item.id}", {})
            table_row.update(existing_fields)  # updating by cached stats

            table_row.update({'status': ItemsStatusField.NEW})  # DEBUG
            g.item2stats[f'{current_item.id}'] = table_row

    update_custom_data('item2stats', g.item2stats)


def get_items_ids_by_status(status):
    items_with_status = []
    for item in g.item2stats.values():
        if item['status'] == status:
            items_with_status.append(item['item_id'])

    return items_with_status


def strfdelta(tdelta, fmt):
    f = Formatter()
    d = {}
    l = {'D': 86400, 'H': 3600, 'M': 60, 'S': 1}
    k = list(map(lambda x: x[1], list(f.parse(fmt))))
    rem = int(tdelta.total_seconds())

    for i in ('D', 'H', 'M', 'S'):
        if i in k and i in l.keys():
            d[i], rem = divmod(rem, l[i])

    return f.format(fmt, **d)


def get_datetime_by_unix(unix_time_delta):
    delta_obj = datetime.timedelta(seconds=round(unix_time_delta))
    return strfdelta(delta_obj, "{H:02}:{M:02}:{S:02}")


def get_project_custom_data(project_id):
    project_info = g.api.project.get_info_by_id(project_id)
    if project_info.custom_data:
        return project_info.custom_data
    else:
        return {}


def get_item_duration(current_item):
    try:
        return get_datetime_by_unix(current_item.frames_count * current_item.frames_to_timecodes[1])
    except:
        return get_datetime_by_unix(0)


def user_have_rights(user_id, task_id, user_mode):
    if user_mode == 'annotator':
        annotators_ids = g.api.task.get_field(g.task_id, 'state.annotatorsIds')
        if not annotators_ids[str(user_id)]:
            return False

    elif user_mode == 'reviewer':
        reviewers_ids = g.api.task.get_field(g.task_id, 'state.reviewersIds')
        if not reviewers_ids[str(user_id)]:
            return False
    else:
        return False

    if g.connected_users.get(str(user_id)) == task_id \
            and get_user_field(user_id, 'status') == UserStatusField.ONLINE:
        return True

    return False


def get_user_field(user_id, field_name):
    users_table = g.api.task.get_field(g.task_id, 'data.usersTable')

    for row in users_table:
        if str(row.get('id')) == str(user_id):
            return row.get(field_name, None)

    return None


def update_item_stats(item_id, fields):
    g.item2stats[f'{item_id}'].update(fields)  # update locally
    update_custom_data(field_name='item2stats', data={f"{item_id}": fields})  # update remotely


def update_user_stats(user_id, fields):
    g.user2stats[f'{user_id}'].update(fields)  # update locally
    update_custom_data(field_name='user2stats', data={f"{user_id}": fields})  # update remotely


def get_user_login_by_id(user_id):
    user_id = int(user_id)
    for current_user in g.team_members:
        if current_user.id == user_id:
            return current_user.login
    return None


def session_is_online(task_id):
    try:
        response = g.api.task.send_request(task_id, "is_online", data={}, timeout=3)
        if response is not None:
            return True
        else:
            return False
    except:
        return False


def update_custom_data(field_name, data):
    project_custom_data = get_project_custom_data(g.project_id)
    current_field = project_custom_data.get(field_name, {})

    for new_key, new_value in data.items():
        old_value = current_field.get(new_key, {})
        old_value.update(new_value)
        current_field[new_key] = old_value

    project_custom_data[field_name] = current_field
    g.api.project.update_custom_data(g.project_id, project_custom_data)


def update_table(table_name, item_id, fields_to_update):
    table = g.api.task.get_field(g.task_id, f'data.{table_name}')
    item_id = str(item_id)

    for index, row in enumerate(table):
        if str(row.get('id')) == item_id:
            table[index].update(fields_to_update)

    g.api.task.set_field(g.task_id, f'data.{table_name}', table)


def get_current_time():
    return str(datetime.datetime.now().strftime("%H:%M:%S"))


def get_queue_by_user_mode(queue_name):
    if queue_name == 'annotator':
        return g.labeling_queue
    elif queue_name == 'reviewer':
        return g.labeling_queue
