import functools

import sly_functions as f
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

    data['itemsTable'] = fill_table()
    data['itemsTableHeaders'] = f.get_table_headers_by_table(data['itemsTable'])

    state['selectAllItems'] = False
    state['selectedItemsIds'] = {row['item_id']: False for row in data['itemsTable']}


@g.my_app.callback("toggle_all_items")
@sly.timeit
@g.update_fields
def add_data_to_queue(api: sly.Api, task_id, context, state, app_logger, fields_to_update):
    flag = state['selectAllItems']
    for curr_key in state['selectedItemsIds'].keys():
        state['selectedItemsIds'][curr_key] = flag

    fields_to_update['state.selectedItemsIds'] = state['selectedItemsIds']


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


def get_item_status_by_id(item_info):
    item_tags = item_info.tags
    status_tag_id = get_status_tag_id_of_project()

    for item_tag in item_tags:
        if item_tag.get('tagId', -1) == status_tag_id:
            return item_tag.get('value', 'err')

    g.api.video.tag.add_tag_to_video(project_meta_tag_id=status_tag_id, video_id=item_info.id,
                                     value=g.item_status_by_code[0])
    return g.item_status_by_code[0]


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
            table_row = []

            table_row.append({'title': 'selected', 'value': False})
            table_row.append({'title': 'status', 'value': get_item_status_by_id(current_item)})
            table_row.append({'title': 'id', 'value': current_item.id})
            table_row.append({'title': 'name', 'value': current_item.name})
            table_row.append({'title': 'dataset', 'value': current_dataset.name})
            table_row.append({'title': 'frames', 'value': current_item.frames_count})
            table_row.append({'title': 'duration (sec)', 'value': get_item_duration(current_item)})

            table.append({'item_id': current_item.id, 'columns': table_row})







