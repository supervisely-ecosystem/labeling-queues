import datetime
from string import Formatter

import supervisely_lib as sly

import sly_globals as g

from sly_fields_names import ItemsStatusField, UserStatusField


def add_technical_tag_to_project_meta(tag_name):
    project_meta = sly.ProjectMeta.from_json(g.api.project.get_meta(g.project_id))
    technical_tag = sly.TagMeta(tag_name, sly.TagValueType.ANY_STRING)
    tags = sly.TagMetaCollection([technical_tag])
    meta_with_tag = sly.ProjectMeta(tag_metas=tags)

    updated_meta = meta_with_tag.merge(project_meta)
    g.api.project.update_meta(g.project_id, updated_meta.to_json())


def get_status_tag_id_of_project():
    add_technical_tag_to_project_meta(ItemsStatusField.TAG_NAME)
    g.project_meta = sly.ProjectMeta.from_json(g.api.project.get_meta(g.project_id))
    for project_tag in g.project_meta.tag_metas.to_json():
        if project_tag.get('name', '') == ItemsStatusField.TAG_NAME:
            return project_tag.get('id', None)




def get_item_status_by_info(item_info):
    item_tags = item_info.tags
    status_tag_id = get_status_tag_id_of_project()

    for item_tag in item_tags:
        if item_tag.get('tagId', -1) == status_tag_id:
            return item_tag.get('value', 'err')

    g.api.video.tag.add_tag(project_meta_tag_id=status_tag_id, video_id=item_info.id,
                            value=ItemsStatusField.NEW)

    return ItemsStatusField.NEW


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


def get_project_items_info(project_id):
    datasets_list = g.api.dataset.get_list(project_id)

    for current_dataset in datasets_list:
        items_list = g.api.video.get_list(current_dataset.id)

        for current_item in items_list:
            table_row = {}

            table_row['status'] = get_item_status_by_info(current_item)
            table_row['item_id'] = current_item.id
            table_row['item_name'] = current_item.name
            table_row['dataset'] = current_dataset.name
            table_row['item_frames'] = current_item.frames_count
            table_row['duration'] = get_item_duration(current_item)

            table_row['item_work_time'] = get_datetime_by_unix(0)

            g.item2stats[current_item.id] = table_row


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


def update_item_status(item_id, fields):
    g.item2stats[item_id].update(fields)


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
    current_field.update(data)

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
