class ItemsStatusField:
    TAG_NAME = 'annotation_controller_status_tag'
    NEW = 'new'
    ANNOTATING = 'annotating'
    ANNOTATED = 'annotated'
    REVIEWING = 'reviewing'
    REVIEWED = 'reviewed'
    COMPLETED = 'completed'


class UserStatusField:
    OFFLINE = 'offline'
    ONLINE = 'online'
    IN_WORK = 'in work'


class UserStatsField:
    ITEMS_ANNOTATED = "items_annotated"
    TAGS_CREATED = "tags_created"
    WORK_TIME = "work_time"
