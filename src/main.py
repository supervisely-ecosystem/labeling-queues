import datetime
import time

import supervisely_lib as sly
import ui as ui

import sly_globals as g
import sly_functions as f

import queue_stats
from sly_fields_names import ItemsStatusField, UserStatusField


def main():
    sly.logger.info("Script arguments", extra={
        "context.teamId": g.team_id,
        "context.workspaceId": g.workspace_id,
        "modal.state.slyProjectId": g.project_id,
    })

    g.my_app.compile_template(g.root_source_dir)

    data = {}
    state = {}

    f.update_project_items_info(g.project_id)
    f.update_project_users_info(g.team_id)
    f.fill_queues_by_project()

    ui.init(data=data, state=state)  # init data for UI widgets

    g.my_app.run(data=data, state=state)


def get_controller_info_for_user(user_id):
    users_statuses = g.api.task.get_fields(g.task_id, ['state.annotatorsIds', 'state.reviewersIds'])
    annotatorsIds, reviewersIds = users_statuses['state.annotatorsIds'], users_statuses['state.reviewersIds']
    return {
        'admin_nickname': f'{g.admin_nickname}',
        'items_for_review_count': len(list(g.reviewing_queue.queue)),
        'items_for_annotation_count': len(list(g.labeling_queue.queue)),
        'can_annotate': annotatorsIds.get(str(user_id), False),
        'can_review': reviewersIds.get(str(user_id), False),
        'user_stats': g.user2stats.get(str(user_id))
    }


@g.my_app.callback("connect_user")
@sly.timeit
@g.update_fields
# @g.my_app.ignore_errors_and_show_dialog_window()
def connect_user(api: sly.Api, task_id, context, state, app_logger, fields_to_update):
    try:
        request_id = context["request_id"]
        user_id = state['userId']
        task_id = state['taskId']

        if g.user2task.get(f'{user_id}', None) is None:  # if user not connected before
            return_data = {'rc': 0}
        else:
            prev_task_id = g.user2task[f'{user_id}']
            # if f.session_is_online(prev_task_id): # DEBUG
            if not True:  # if preview task is alive
                return_data = {'rc': -1,
                               'taskId': prev_task_id}
            else:
                return_data = {'rc': 0}
                item_id = g.task2item.get(prev_task_id, None)
                if item_id is not None:
                    g.task2item.pop(prev_task_id)
                    g.task2item[task_id] = item_id

        if return_data['rc'] == 0:  # if connected
            g.user2task[f'{user_id}'] = task_id

            return_data.update(get_controller_info_for_user(user_id))

            g.user2stats[f'{user_id}']['status'] = UserStatusField.ONLINE

        g.my_app.send_response(request_id, data=return_data)
    except Exception as ex:
        sly.logger.warn(ex)


def get_returned_item_status(user_mode, review_needed):
    item_status = ItemsStatusField.COMPLETED

    if user_mode == 'annotator' and review_needed:
        item_status = ItemsStatusField.ANNOTATED

    elif user_mode == 'reviewer':
        item_status = ItemsStatusField.COMPLETED

    return item_status


@g.my_app.callback("return_item")
@sly.timeit
@g.update_fields
# @g.my_app.ignore_errors_and_show_dialog_window()
def return_item(api: sly.Api, task_id, context, state, app_logger, fields_to_update):
    request_id = context["request_id"]

    user_id = state['userId']
    task_id = state['taskId']
    user_mode = state['mode']

    reviewers_ids = g.api.task.get_field(g.task_id, 'state.reviewersIds')
    review_needed = True in list(reviewers_ids.values())

    item_id = g.task2item.get(task_id, None)
    if item_id is not None:
        new_item_status = get_returned_item_status(user_mode, review_needed)
        if new_item_status == ItemsStatusField.ANNOTATED:
            g.reviewing_queue.put(item_id)

        f.update_item_stats(item_id=item_id, fields={'status': new_item_status})
        f.update_user_stats(user_id=user_id, fields={'status': UserStatusField.ONLINE})

        g.task2item.pop(task_id)

    g.user2stats[f'{user_id}']['status'] = UserStatusField.ONLINE
    queue_stats.update_tables(fields_to_update)

    updated_controller_info = get_controller_info_for_user(user_id)

    g.my_app.send_response(request_id, data=updated_controller_info)


@g.my_app.callback("update_stats")
@sly.timeit
@g.update_fields
# @g.my_app.ignore_errors_and_show_dialog_window()
def update_stats(api: sly.Api, task_id, context, state, app_logger, fields_to_update):
    request_id = context["request_id"]

    user_id = state['userId']
    task_id = state['taskId']

    item_id = g.task2item.get(task_id, None)
    if item_id is not None:
        item_fields = {
            'work_time': f.get_datetime_by_unix(time.time() - g.item2stats[f'{item_id}']['work_started_unix'])
        }

        state['item_fields'].update(item_fields)
        state['item_fields'].update(f.get_additional_item_stats(item_id))

        f.update_item_stats(item_id=item_id, fields=state['item_fields'])
        f.update_user_stats(user_id=user_id, fields=state['user_fields'])

    queue_stats.update_tables(fields_to_update)
    g.my_app.send_response(request_id, data={'status': 'done'})


@g.my_app.callback("get_item")
@sly.timeit
@g.update_fields
# @g.my_app.ignore_errors_and_show_dialog_window()
def get_item(api: sly.Api, task_id, context, state, app_logger, fields_to_update):
    request_id = context["request_id"]
    user_id = state['userId']
    task_id = state['taskId']
    user_mode = state['mode']

    current_queue = f.get_queue_by_user_mode(user_mode)
    if f.user_have_rights(user_id, task_id, user_mode):

        item_id = g.task2item.get(task_id, None)
        if item_id is None:
            item_id = current_queue.get()

            item_fields = {
                'status': ItemsStatusField.ANNOTATING if user_mode == 'annotator' else ItemsStatusField.REVIEWING,
                'worker_id': f'{user_id}',
                'worker_login': f.get_user_login_by_id(user_id),
                'work_started_unix': g.item2stats[f'{item_id}']['work_started_unix'] if
                g.item2stats[f'{item_id}'].get('work_started_unix', None) is not None else time.time()
            }
            f.update_item_stats(item_id=item_id, fields=item_fields)

            g.task2item[task_id] = item_id

        g.user2stats[f'{user_id}']['status'] = UserStatusField.IN_WORK

        g.my_app.send_response(request_id, data={'item_id': item_id})
        queue_stats.update_tables(fields_to_update)
    else:
        return -1


#  INP@TODO: publish API method video.add_tag
#  INP@TODO: publish update_fields decorator
#  INP@TODO: publish AppService.periodic functional
#  INP@TODO: publish api.video_api.url method

#  DONE@TODO: connected sessions hooker — by myself
#  ?@TODO: get user_id from request — every session has info which task_id get info of owner
#  DONE@TODO: additional items stats
#  DONE@TODO: items link to project — api.image.url(TEAM_ID, WORKSPACE_ID, project.id, dataset.id, info.id), info.name)


if __name__ == "__main__":
    sly.main_wrapper("main", main)
