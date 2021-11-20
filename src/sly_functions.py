import datetime

import sly_globals as g

from sly_fields_names import ItemsStatusField


def get_status_tag_id_of_project():
    for project_tag in g.project_meta.tag_metas.to_json():
        if project_tag.get('name', '') == ItemsStatusField.TAG_NAME:
            return project_tag.get('id', -1)
    return -1


def get_item_status_by_info(item_info):
    item_tags = item_info.tags
    status_tag_id = get_status_tag_id_of_project()

    for item_tag in item_tags:
        if item_tag.get('tagId', -1) == status_tag_id:
            return item_tag.get('value', 'err')

    g.api.video.tag.add_tag(project_meta_tag_id=status_tag_id, video_id=item_info.id,
                            value=ItemsStatusField.NEW)

    return ItemsStatusField.NEW


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

            table_row['item_work_time'] = str(datetime.timedelta(seconds=round(0)))

            g.item2stats[current_item.id] = table_row


def get_project_custom_data(project_id):
    project_info = g.api.project.get_info_by_id(project_id)
    if project_info.custom_data:
        return project_info.custom_data
    else:
        return {}


def get_item_duration(current_item):
    try:
        return str(datetime.timedelta(seconds=round(current_item.frames_count * current_item.frames_to_timecodes[1])))
    except:
        return str(datetime.timedelta(seconds=round(0)))
