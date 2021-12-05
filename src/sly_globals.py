import functools
import os
import queue
from pathlib import Path
import sys
import pickle

import supervisely_lib as sly

import sly_functions as f

from dotenv import load_dotenv  # pip install python-dotenv\

load_dotenv("../debug.env")
load_dotenv("../secret_debug.env", override=True)

sly.logger.setLevel('DEBUG')

my_app = sly.AppService()
api = my_app.public_api
task_id = my_app.task_id

team_id = int(os.environ['context.teamId'])
workspace_id = int(os.environ['context.workspaceId'])
project_id = int(os.environ['modal.state.slyProjectId'])
admin_user_id = int((os.environ['context.userId']))


team_members = api.user.get_team_members(team_id)
admin_nickname = f.get_user_login_by_id(admin_user_id)

project_info = api.project.get_info_by_id(project_id)
project_meta = sly.ProjectMeta.from_json(api.project.get_meta(project_id))

root_source_dir = str(Path(os.path.abspath(sys.argv[0])).parents[1])  # /annotation-controller/
sly.logger.info(f"Root source directory: {root_source_dir}")
sys.path.append(root_source_dir)

source_path = str(Path(sys.argv[0]).parents[0])  # /annotation-controller/src/
sly.logger.info(f"App source directory: {source_path}")
sys.path.append(source_path)

ui_sources_dir = os.path.join(source_path, "ui")  # /annotation-controller/src/ui/
sly.logger.info(f"UI source directory: {ui_sources_dir}")
sys.path.append(ui_sources_dir)

annotation_controller_status_tag_name = 'annotation_controller_status_tag'

project_custom_data = f.get_project_custom_data(project_id)

user2task = {}
task2item = {}  # item_id -> task_id
item2stats = project_custom_data.get('item2stats', {})  # item_id -> his stats
user2stats = project_custom_data.get('user2stats', {})  # user_id -> his stats

labeling_queue = queue.Queue(maxsize=int(1e5))
reviewing_queue = queue.Queue(maxsize=int(1e5))



def update_fields(func):
    """Update state field after executing function"""

    @functools.wraps(func)
    def wrapper_updater(*args, **kwargs):
        kwargs['fields_to_update'] = {}

        value = func(*args, **kwargs)

        user_api = kwargs.get('api', None)
        app_task_id = kwargs.get('task_id', None)

        if user_api and app_task_id and len(kwargs['fields_to_update']) > 0:
            user_api.task.set_fields_from_dict(app_task_id, kwargs['fields_to_update'])
        return value

    return wrapper_updater
