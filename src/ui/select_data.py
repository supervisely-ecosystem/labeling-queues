import functools

import sly_globals as g
import supervisely_lib as sly


def fill_table():
    table = []

    g.project_info = g.api.project.get_info_by_id(g.project_id)
    g.project_meta = sly.ProjectMeta.from_json(g.api.project.get_meta(g.project_id))

    if g.project_info.type == 'videos':
        fill_table_for_videos_project(table)

    return table


def init_fields(state, data):
    state['refreshingData'] = False
    state['reviewNeeded'] = False

    data['dataTable'] = fill_table()


@g.my_app.callback("add_data_to_queue")
@sly.timeit
@g.update_fields
def add_data_to_queue(api: sly.Api, task_id, context, state, app_logger, fields_to_update):
    fields_to_update['state.refreshingData'] = False


@g.my_app.callback("refresh_data_table")
@sly.timeit
@g.update_fields
def refresh_table(api: sly.Api, task_id, context, state, app_logger, fields_to_update):
    fields_to_update['state.refreshingData'] = False
    fields_to_update['data.dataTable'] = fill_table()


def get_status_tag_id_of_project():
    for project_tag in g.project_meta.tag_metas.to_json():
        if project_tag.get('name', '') == g.annotation_controller_status_tag_name:
            return project_tag.get('id', -1)
    return -1


def get_item_status_by_id(item_id, item_type):
    item_info = eval(f'g.api.{item_type}.get_info_by_id({item_id})')
    item_tags = item_info.tags

    status_tag_id = get_status_tag_id_of_project()

    for item_tag in item_tags:
        if item_tag.get('tagId', -1) == status_tag_id:
            return 'F'  # @TODO: replace to real value

    return 'NF'  # @TODO: replace to real value


def get_item_duration(current_item):
    try:
        return round(current_item.frames_count * current_item.frames_to_timecodes[1])
    except:
        return None


def fill_table_for_videos_project(table):
    datasets_list = g.api.dataset.get_list(g.project_id)

    for current_dataset in datasets_list:
        items_list = g.api.video.get_list(current_dataset.id)

        for current_item in items_list:
            table_row = {key: None for key in ['status', 'name', 'dataset', 'frames', 'duration']}

            table_row['status'] = get_item_status_by_id(current_item.id, 'video')
            table_row['name'] = current_item.name
            table_row['dataset'] = current_dataset.name
            table_row['frames'] = current_item.frames_count
            table_row['duration'] = get_item_duration(current_item)

            table.append(table_row)







