from sly_globals import *

# from supervisely_lib.video_annotation.key_id_map import KeyIdMap

from functools import partial
from sly_visualize_progress import get_progress_cb, reset_progress, init_progress


class AnnotationKeeper:
    def __init__(self, video_shape, objects_count, class_name, color):

        self.video_shape = video_shape
        self.objects_count = objects_count
        self.class_name = class_name
        self.color = color

        self.project = None
        self.dataset = None
        self.meta = None

        # self.key_id_map = KeyIdMap()
        self.sly_objects_list = []
        self.video_object_list = []

        self.get_sly_objects()
        self.get_video_objects_list()

        self.video_object_collection = sly.VideoObjectCollection(self.video_object_list)

        self.figures = []
        self.frames_list = []
        self.frames_collection = []

    def add_figures_by_frame(self, coords_data, objects_indexes, frame_index):
        temp_figures = []

        for i in range(len(coords_data)):
            temp_figures.append(sly.VideoFigure(self.video_object_list[objects_indexes[i]],
                                                coords_data[i], frame_index))

        self.figures.append(temp_figures)

    def init_project_remotely(self, project_id=None, ds_id=None,
                              project_name='vSynthTest', ds_name='ds_0000'):
        if not project_id:
            self.project = api.project.create(workspace_id, project_name, type=sly.ProjectType.VIDEOS,
                                              change_name_if_conflict=True)

            self.meta = sly.ProjectMeta(
                obj_classes=sly.ObjClassCollection(self.get_unique_objects(self.sly_objects_list)))

            api.project.update_meta(self.project.id, self.meta.to_json())
        else:
            self.project = api.project.get_info_by_id(project_id)
            curr_meta = sly.ProjectMeta(obj_classes=sly.ObjClassCollection(self.get_unique_objects(self.sly_objects_list)))
            remote_meta = sly.ProjectMeta.from_json(api.project.get_meta(self.project.id))

            self.meta = remote_meta.merge(curr_meta)
            api.project.update_meta(self.project.id, self.meta.to_json())

        if not ds_id:
            self.dataset = api.dataset.create(self.project.id, f'{ds_name}',
                                              change_name_if_conflict=True)
        else:
            for dataset in api.dataset.get_list(project_id):
                if dataset.id == ds_id:
                    self.dataset = dataset
                    break


    def upload_annotation(self, video_path):
        self.get_frames_list()
        self.frames_collection = sly.FrameCollection(self.frames_list)

        video_annotation = sly.VideoAnnotation(self.video_shape, len(self.frames_list),
                                               self.video_object_collection, self.frames_collection)

        video_name = video_path.split('/')[-1]

        uploading_progress = get_progress_cb('UploadVideo', "Uploading video", sly.fs.get_file_size(video_path),
                                             is_size=True,
                                             min_report_percent=1)

        file_info = api.video.upload_paths(self.dataset.id, [video_name], [video_path],
                                           item_progress=uploading_progress)

        if len(self.figures) > 0:
            api.video.annotation.append(file_info[0].id, video_annotation)

    def get_unique_objects(self, obj_list):
        unique_objects = []
        for obj in obj_list:
            # @TODO: to add different types shapes
            if obj.name not in [temp_object.name for temp_object in unique_objects]:
                unique_objects.append(obj)

        return unique_objects

    def get_sly_objects(self):
        for obj in range(self.objects_count):
            self.sly_objects_list.append(sly.ObjClass(self.class_name, sly.Rectangle, self.color))

    def get_video_objects_list(self):
        for sly_object in self.sly_objects_list:
            self.video_object_list.append(sly.VideoObject(sly_object))

    def get_frames_list(self):
        for index, figure in enumerate(self.figures):
            self.frames_list.append(sly.Frame(index, figure))
