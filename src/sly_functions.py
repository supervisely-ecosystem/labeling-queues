import sly_globals as g

from sly_fields_names import ItemsStatusField


def get_status_tag_id_of_project():
    for project_tag in g.project_meta.tag_metas.to_json():
        if project_tag.get('name', '') == ItemsStatusField.TAG_NAME:
            return project_tag.get('id', -1)
    return -1


def get_item_status_by_id(item_info):
    item_tags = item_info.tags
    status_tag_id = get_status_tag_id_of_project()

    for item_tag in item_tags:
        if item_tag.get('tagId', -1) == status_tag_id:
            return item_tag.get('value', 'err')

    g.api.video.tag.add_value(project_meta_tag_id=status_tag_id, video_id=item_info.id,
                              value=ItemsStatusField.NEW)

    return ItemsStatusField.NEW


def get_items_list():
    datasets_list = g.api.dataset.get_list(g.project_id)

    for current_dataset in datasets_list:
        items_list = g.api.video.get_list(current_dataset.id)
        print()


def load_users_stats_from_project(project_id):
    pass


def get_project_custom_data(project_id):
    project_info = g.api.project.get_info_by_id(project_id)
    if project_info.custom_data:
        return project_info.custom_data
    else:
        return {}
