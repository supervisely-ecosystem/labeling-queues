import supervisely_lib as sly
import sly_globals as g

import project_preferences
import select_users
import users_stats
import queue_stats


@sly.timeit
def init(state, data):

    project_preferences.init_fields(state=state, data=data)
    select_users.init_fields(state=state, data=data)
    users_stats.init_fields(state=state, data=data)
    queue_stats.init_fields(state=state, data=data)




