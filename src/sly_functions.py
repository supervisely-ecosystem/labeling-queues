import datetime
import time
from string import Formatter

import supervisely_lib as sly

import sly_globals as g

from sly_fields_names import ItemsStatusField, UserStatusField, UserStatsField


def get_item_url(item_id):
    if g.project_info.type == 'videos':
        item_info = g.api.video.get_info_by_id(item_id)
        return g.api.video.url(item_info.dataset_id, item_id)


def update_project_items_info(project_id):
    datasets_list = g.api.dataset.get_list(project_id)

    for current_dataset in datasets_list:
        if g.project_info.type == 'videos':
            items_list = g.api.video.get_list(current_dataset.id)
        else:
            raise NotImplemented(f'Project type {g.project_info.type} not implemented')

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

            table_row.update(get_additional_item_stats(current_item.id))
            table_row.update({'item_url': get_item_url(current_item.id)})

            table_row.update({'status': ItemsStatusField.NEW})  # DEBUG
            g.item2stats[f'{current_item.id}'] = table_row

    update_custom_data('item2stats', g.item2stats)


def update_project_users_info(team_id):
    g.team_members = g.api.user.get_team_members(team_id)

    # for i in range(100):  # DEBUG
    for current_item in g.team_members:
        table_row = {'status': UserStatusField.OFFLINE,
                     'id': f'{current_item.id}',
                     'login': current_item.login,
                     'role': current_item.role,
                     'last_login': get_user_last_seen(current_item.last_login),
                     'can_annotate': current_item.role == 'annotator',
                     'can_review': current_item.role == 'reviewer',
                     'performance': 'normal',

                     UserStatsField.WORK_TIME_UNIX: 0,
                     UserStatsField.WORK_TIME: get_datetime_by_unix(0),
                     UserStatsField.FRAMES_ANNOTATED: 0,
                     UserStatsField.ITEMS_ANNOTATED: 0,
                     UserStatsField.TAGS_CREATED: 0,
                     'frames_per_time': '-'}

        existing_fields = g.user2stats.get(f"{current_item.id}", {})
        table_row.update(existing_fields)  # updating by cached stats

        g.user2stats[f'{current_item.id}'] = table_row

    update_custom_data('user2stats', g.user2stats)


def get_user_last_seen(datetime_str):
    if datetime_str is None:
        return "never"
    d = datetime.datetime.strptime(datetime_str, '%Y-%m-%dT%H:%M:%S.%f%z')

    last_seen_unix = time.mktime(time.gmtime()) - time.mktime(d.timetuple())
    last_seen_datetime = datetime.timedelta(seconds=round(last_seen_unix))

    if last_seen_datetime.days == 0:
        return f"{last_seen_datetime} ago"
    elif 30 > last_seen_datetime.days > 0:
        return f"{last_seen_datetime.days} days ago"
    else:
        return "long time ago"


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
        if annotators_ids[str(user_id)]:
            return True

    elif user_mode == 'reviewer':
        reviewers_ids = g.api.task.get_field(g.task_id, 'state.reviewersIds')
        if reviewers_ids[str(user_id)]:
            return True

    else:
        return False

    # if g.user2task.get(str(user_id)) == task_id \
    #         and g.user2stats[f'{user_id}']['status'] == UserStatusField.ONLINE:
    #     return True

    return False


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
        response = g.api.task.send_request(task_id, "is_online", data={}, timeout=5)
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


# legacy
# def update_table(table_name, item_id, fields_to_update):
#     table = g.api.task.get_field(g.task_id, f'data.{table_name}')
#     item_id = str(item_id)
#
#     for index, row in enumerate(table):
#         if str(row.get('id')) == item_id:
#             table[index].update(fields_to_update)
#
#     g.api.task.set_field(g.task_id, f'data.{table_name}', table)


def get_current_time():
    return str(datetime.datetime.now().strftime("%H:%M:%S"))


def get_queue_by_user_mode(queue_name):
    if queue_name == 'annotator':
        return g.labeling_queue
    elif queue_name == 'reviewer':
        return g.reviewing_queue


def return_item_to_queue(item_id):
    item_to_return = g.item2stats[f'{item_id}']

    if item_to_return['status'] == ItemsStatusField.ANNOTATING:
        g.labeling_queue.put(item_to_return['item_id'])
        item_to_return['status'] = ItemsStatusField.NEW

        item_to_return['worker_id'] = None  # may be in another format
        item_to_return['worker_login'] = None

    elif item_to_return['status'] == ItemsStatusField.REVIEWING:
        g.reviewing_queue.put(item_to_return['item_id'])
        item_to_return['status'] = ItemsStatusField.ANNOTATED

        item_to_return['worker_id'] = None  # may be in another format
        item_to_return['worker_login'] = None

    g.item2stats[f'{item_id}'] = item_to_return


def fill_queues_by_project():
    [g.labeling_queue.put(item) for item in get_items_ids_by_status(ItemsStatusField.NEW)]
    [g.reviewing_queue.put(item) for item in get_items_ids_by_status(ItemsStatusField.ANNOTATED)]


def get_users_table():
    table = []

    update_project_users_info(g.team_id)

    for table_row in g.user2stats.values():
        table.append(table_row)

    return table


def get_tags_count_by_annotation(video_annotation):
    tags_count = 0

    for tag in video_annotation['tags']:
        frame_range = tag.get('frameRange', [0, -1])
        tags_count += frame_range[1] - frame_range[0] + 1

    return tags_count


def get_additional_item_stats(item_id):
    stats_to_return = {}

    if g.project_info.type == 'videos':
        video_annotation = g.api.video.annotation.download(item_id)

        stats_to_return.update({
            'tags_count': get_tags_count_by_annotation(video_annotation),
            'objects_count': len(video_annotation['objects']),
        })

    return stats_to_return


def add_user_to_workers(item_id, user_id, user_mode):
    item_info = g.item2stats.get(f'{item_id}')
    if user_mode == 'annotator':
        existing_annotators = set(item_info.get('annotators', []))
        existing_annotators.add(get_user_login_by_id(user_id))
        item_info['annotators'] = list(existing_annotators)

        return {'annotators': item_info['annotators']}
    if user_mode == 'reviewer':
        existing_reviewers = set(item_info.get('reviewers', []))
        existing_reviewers.add(get_user_login_by_id(user_id))
        item_info['reviewers'] = list(existing_reviewers)

        return {'reviewers': item_info['reviewers']}
