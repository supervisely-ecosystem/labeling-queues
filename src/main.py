import supervisely_lib as sly
import ui as ui

import sly_globals as g
import sly_functions as f


def fill_queues_by_project(project_id):
    f.get_project_items_info(project_id)

    items_to_put = list(g.item2stats.keys())
    [g.labeling_queue.put(query) for query in items_to_put]


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


#  @TODO: publish API method video.add_tag
#  @TODO: publish update_fields decorator

if __name__ == "__main__":
    sly.main_wrapper("main", main)
