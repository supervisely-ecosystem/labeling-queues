import sly_globals as g


def init_fields(state, data):
    state['addNewItemsAuto'] = True

    data['projectInfo'] = {
        'id': g.project_info.id,
        'name': g.project_info.name,
        'reference_image_url': g.project_info.reference_image_url,
        'project_type': g.project_meta.project_type,
        'items_count': g.project_info.items_count,
        'classes_count': len(g.project_meta.obj_classes),
        'tags_count': len(g.project_meta.tag_metas)

    }
