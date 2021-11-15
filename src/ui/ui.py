import supervisely_lib as sly
import sly_globals as g

import select_data
import select_users


@sly.timeit
def init(state, data):
    select_data.init_fields(state=state, data=data)
    select_users.init_fields(state=state, data=data)




