import supervisely_lib as sly
import ui as ui

import sly_globals as g
import sly_functions as f

import queue_stats

from sly_fields_names import ItemsStatusField, UserStatusField


def fill_queues_by_project(project_id):
    f.get_project_items_info(project_id)

    items_to_put = list(g.item2stats.keys())
    [g.labeling_queue.put(query) for query in items_to_put]

    for item_to_put_id in items_to_put:
        f.update_item_status(item_to_put_id, {'status': ItemsStatusField.NEW})


def main():
    sly.logger.info("Script arguments", extra={
        "context.teamId": g.team_id,
        "context.workspaceId": g.workspace_id,
        "modal.state.slyProjectId": g.project_id,
    })

    g.my_app.compile_template(g.root_source_dir)

    data = {}
    state = {}

    fill_queues_by_project(g.project_id)
    ui.init(data=data, state=state)  # init data for UI widgets

    g.my_app.run(data=data, state=state)


@g.my_app.callback("connect_user")
@sly.timeit
@g.update_fields
# @g.my_app.ignore_errors_and_show_dialog_window()
def connect_user(api: sly.Api, task_id, context, state, app_logger, fields_to_update):
    try:
        request_id = context["request_id"]
        user_id = state['userId']
        task_id = state['taskId']

        users_statuses = g.api.task.get_fields(g.task_id, ['state.annotatorsIds', 'state.reviewersIds'])
        annotatorsIds, reviewersIds = users_statuses['state.annotatorsIds'], users_statuses['state.reviewersIds']

        additional_fields = {
            'admin_nickname': 'ADMIN',  # @TODO: real nickname
            'items_for_review_count': len(list(g.reviewing_queue.queue)),
            'items_for_annotation_count': len(list(g.labeling_queue.queue)),
            'can_annotate': annotatorsIds.get(str(user_id), False),
            'can_review': reviewersIds.get(str(user_id), False),
            'user_stats': g.user2stats.get(str(user_id))
        }

        if g.connected_users.get(f'{user_id}', None) is None:  # if user not connected before
            return_data = {'rc': 0}
        else:
            prev_task_id = g.connected_users[f'{user_id}']
            # if session_is_online(prev_task_id): # DEBUG
            if not True:                                       # if preview task is alive
                return_data = {'rc': -1,
                               'taskId': prev_task_id}
            else:
                return_data = {'rc': 0}
                item_id = g.task2item.get(prev_task_id, None)
                if item_id is not None:
                    g.task2item.pop(prev_task_id)
                    g.task2item[task_id] = item_id

        if return_data['rc'] == 0:
            g.connected_users[f'{user_id}'] = task_id
            return_data.update(additional_fields)
            f.update_table('usersTable', user_id, {'status': UserStatusField.ONLINE})

        g.my_app.send_response(request_id, data=return_data)
    except Exception as ex:
        sly.logger.warn(ex)


def get_queue_by_user_mode(queue_name):
    if queue_name == 'annotator':
        return g.labeling_queue
    elif queue_name == 'reviewer':
        return g.labeling_queue


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

        f.update_item_status(item_id=item_id, fields=state['item_fields'])
        f.update_table('usersTable', user_id, state['user_fields'])

        g.user2stats[str(user_id)].update(state['user_fields'])  # user2stats is old needs to remove
        g.task2item[task_id] = item_id

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

    current_queue = get_queue_by_user_mode(user_mode)
    if f.user_have_rights(user_id, task_id, user_mode):

        item_id = g.task2item.get(task_id, None)
        if item_id is None:
            item_id = current_queue.get()

            item_fields = {
                'status': ItemsStatusField.ANNOTATING if user_mode == 'annotator' else ItemsStatusField.REVIEWING,
                'worker_id': f'{user_id}',
                'worker_login': f.get_user_login_by_id(user_id)
            }
            f.update_item_status(item_id=item_id, fields=item_fields)

            g.task2item[task_id] = item_id

        f.update_table('usersTable', user_id, {'status': UserStatusField.IN_WORK})
        g.my_app.send_response(request_id, data={'item_id': item_id})
        queue_stats.update_tables(fields_to_update)
    else:
        return -1


#  @TODO: publish API method video.add_tag
#  @TODO: publish update_fields decorator
#  @TODO: get user_id from request
#  @TODO: admin nickname from env
#  @TODO: preferences func

if __name__ == "__main__":
    sly.main_wrapper("main", main)
