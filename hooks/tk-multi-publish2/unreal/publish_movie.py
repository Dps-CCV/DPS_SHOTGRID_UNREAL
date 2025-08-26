import sgtk
import unreal
from tank_vendor import six
import copy
import datetime
import os
import pprint
import subprocess
import sys
import tempfile
import re
from sgtk.platform.qt import QtGui


_OS_LOCAL_STORAGE_PATH_FIELD = {
    "darwin": "mac_path",
    "win32": "windows_path",
    "linux": "linux_path",
    "linux2": "linux_path",
}[sys.platform]

HookBaseClass = sgtk.get_hook_baseclass()

_CL_RE = re.compile(r"^\s*Perforce\s+changelist:\s*\d{6}\b.*", re.I)

def _require_desc_with_cl(desc: str) -> str:
    d = (desc or "").strip()
    if not d or not _CL_RE.search(d):
        raise ValueError("Description must start with your Perforce changelist. Example: 'Perforce changelist: XXXXXX ....'")
    return d

def _get_unreal_editor_exe():
    engine_dir = unreal.Paths.engine_dir()
    cand_cmd = os.path.join(engine_dir, "Binaries", "Win64", "UnrealEditor-Cmd.exe")
    cand_gui = os.path.join(engine_dir, "Binaries", "Win64", "UnrealEditor.exe")
    if os.path.isfile(cand_cmd):
        return cand_cmd
    return cand_gui


class UnrealMoviePublishPlugin(HookBaseClass):
    @property
    def description(self):
        return "Publishes a Level Sequence via Movie Render Queue or Sequencer."

    @property
    def settings(self):
        base_settings = super(UnrealMoviePublishPlugin, self).settings or {}
        base_settings.update({
            "Publish Template": {
                "type": "template",
                "default": None,
                "description": "Template path for published work files."
            },
            "Movie Render Queue Presets Path": {
                "type": "string",
                "default": None,
                "description": "Unreal path to saved MRQ presets."
            },
            "Publish Folder": {
                "type": "string",
                "default": None,
                "description": "Root folder to use for publishes."
            }
        })
        return base_settings

    @property
    def item_filters(self):
        return ["unreal.asset.LevelSequence"]

    def _install_ui_guards(self, root):
        from sgtk.platform.qt import QtCore, QtGui

        pub_btn = None
        val_btn = None
        desc_edit = None

        for w in root.findChildren(QtGui.QAbstractButton):
            t = (w.text() or "").strip().lower()
            if t in ("publish", "publicar"):
                pub_btn = w
            elif t in ("validate", "validar"):
                val_btn = w

        # intenta localizar el campo de descripción
        edits = []
        for w in root.findChildren(QtCore.QObject):
            if hasattr(w, "toPlainText") and callable(getattr(w, "toPlainText", None)) and hasattr(w,
                                                                                                   "setPlaceholderText"):
                edits.append(w)
        if edits:
            try:
                desc_edit = max(edits, key=lambda e: e.width() * e.height())
            except Exception:
                desc_edit = edits[0]

        # sustituye “Description not inherited” por el aviso rojo
        try:
            for lab in root.findChildren(QtGui.QLabel):
                txt = (lab.text() or "").strip().lower()
                if txt in ("description not inherited", "descripción no heredada"):
                    lab.setText("REQUIRED: Description must start with Perforce changelist (e.g. CL 123456 - …)")
                    lab.setStyleSheet("color:#c62828; font-weight:bold;")
                    break
        except Exception:
            pass

        def _refresh():
            ok = bool(desc_edit and _CL_RE.search(desc_edit.toPlainText()))
            if pub_btn:
                pub_btn.setEnabled(ok)

        if pub_btn:
            pub_btn.setEnabled(False)
        if desc_edit:
            try:
                desc_edit.setPlaceholderText("REQUIRED: start with Perforce changelist, e.g. CL 123456 - …")
                desc_edit.textChanged.connect(_refresh)
            except Exception:
                pass
        if val_btn:
            try:
                val_btn.clicked.connect(_refresh)
            except Exception:
                pass

        _refresh()

    def create_settings_widget(self, parent):
        from sgtk.platform.qt import QtGui, QtCore
        settings_frame = QtGui.QFrame(parent)
        settings_frame.description_label = QtGui.QLabel(self.description)
        settings_frame.description_label.setWordWrap(True)
        settings_frame.description_label.setOpenExternalLinks(True)
        settings_frame.description_label.setTextFormat(QtCore.Qt.RichText)
        settings_frame.unreal_render_presets_label = QtGui.QLabel("Render with Movie Pipeline Presets:")
        settings_frame.unreal_render_presets_widget = QtGui.QComboBox()
        settings_frame.unreal_render_presets_widget.addItem("No presets")
        presets_folder = unreal.MovieRenderPipelineProjectSettings().preset_save_dir
        for preset in unreal.EditorAssetLibrary.list_assets(presets_folder.path):
            settings_frame.unreal_render_presets_widget.addItem(preset.split(".")[0])
        settings_frame.unreal_publish_folder_label = QtGui.QLabel("Publish folder:")
        storage_roots = self.parent.shotgun.find("LocalStorage", [], ["code", _OS_LOCAL_STORAGE_PATH_FIELD])
        settings_frame.storage_roots_widget = QtGui.QComboBox()
        settings_frame.storage_roots_widget.addItem("Current Unreal Project")
        for storage_root in storage_roots:
            if storage_root[_OS_LOCAL_STORAGE_PATH_FIELD]:
                settings_frame.storage_roots_widget.addItem(
                    "%s (%s)" % (storage_root["code"], storage_root[_OS_LOCAL_STORAGE_PATH_FIELD]),
                    userData=storage_root,
                )
        settings_layout = QtGui.QVBoxLayout()
        settings_layout.addWidget(settings_frame.description_label)
        req_label = QtGui.QLabel("REQUIRED: Description must start with Perforce changelist (e.g. CL 123456 - …)")
        req_label.setStyleSheet("color:#c62828; font-weight:bold;")
        settings_layout.addWidget(req_label)
        settings_layout.addWidget(settings_frame.unreal_render_presets_label)
        settings_layout.addWidget(settings_frame.unreal_render_presets_widget)
        settings_layout.addWidget(settings_frame.unreal_publish_folder_label)
        settings_layout.addWidget(settings_frame.storage_roots_widget)
        settings_layout.addStretch()
        settings_frame.setLayout(settings_layout)
        root = settings_frame.window()
        try:
            # Cambiar el texto "Description not inherited" por el aviso rojo
            for lab in root.findChildren(QtGui.QLabel):
                txt = lab.text().strip().lower()
                if txt in ("description not inherited", "descripción no heredada"):
                    lab.setText("REQUIRED: Description must start with Perforce changelist (e.g. CL 123456 - …)")
                    lab.setStyleSheet("color:#c62828; font-weight:bold;")
                    break

            # Localiza botones y el editor de descripcioon
            pub_btn, val_btn, desc_edit = None, None, None
            for btn in root.findChildren(QtGui.QAbstractButton):
                t = btn.text().strip().lower()
                if t in ("publish", "publicar"):
                    pub_btn = btn
                elif t in ("validate", "validar"):
                    val_btn = btn
            edits = root.findChildren(QtGui.QPlainTextEdit)
            if edits:
                # el de mayor tamanyo suele ser el de descripcioon
                desc_edit = max(edits, key=lambda e: e.width() * e.height())

            def _refresh():
                ok = bool(desc_edit and _CL_RE.search(desc_edit.toPlainText()))
                if pub_btn:
                    pub_btn.setEnabled(ok)

            if pub_btn:
                pub_btn.setEnabled(False)
            if desc_edit:
                desc_edit.textChanged.connect(_refresh)
            if val_btn:
                val_btn.clicked.connect(_refresh)
            _refresh()
        except Exception:
            pass
        from sgtk.platform.qt import QtCore
        QtCore.QTimer.singleShot(0, lambda: self._install_ui_guards(settings_frame.window()))
        return settings_frame

    def get_ui_settings(self, widget):
        from sgtk.platform.qt import QtCore
        render_presets_path = None
        if widget.unreal_render_presets_widget.currentIndex() > 0:
            render_presets_path = six.ensure_str(widget.unreal_render_presets_widget.currentText())
        storage_index = widget.storage_roots_widget.currentIndex()
        publish_folder = None
        if storage_index > 0:
            storage = widget.storage_roots_widget.itemData(storage_index, role=QtCore.Qt.UserRole)
            publish_folder = storage[_OS_LOCAL_STORAGE_PATH_FIELD]
        return {
            "Movie Render Queue Presets Path": render_presets_path,
            "Publish Folder": publish_folder,
        }

    def set_ui_settings(self, widget, settings):
        from sgtk.platform.qt import QtCore
        if len(settings) > 1:
            raise NotImplementedError
        cur_settings = settings[0]
        render_presets_path = cur_settings["Movie Render Queue Presets Path"]
        preset_index = 0
        if render_presets_path:
            preset_index = widget.unreal_render_presets_widget.findText(render_presets_path)
        widget.unreal_render_presets_widget.setCurrentIndex(preset_index)
        publish_template_setting = cur_settings.get("Publish Template")
        publisher = self.parent
        publish_template = publisher.get_template_by_name(publish_template_setting)
        if isinstance(publish_template, sgtk.TemplatePath):
            widget.unreal_publish_folder_label.setEnabled(False)
            widget.storage_roots_widget.setEnabled(False)
        folder_index = 0
        publish_folder = cur_settings["Publish Folder"]
        if publish_folder:
            for i in range(widget.storage_roots_widget.count()):
                data = widget.storage_roots_widget.itemData(i, role=QtCore.Qt.UserRole)
                if data and data[_OS_LOCAL_STORAGE_PATH_FIELD] == publish_folder:
                    folder_index = i
                    break
        widget.storage_roots_widget.setCurrentIndex(folder_index)

    def load_saved_ui_settings(self, settings):
        fw = self.load_framework("tk-framework-shotgunutils_v5.x.x")
        module = fw.import_module("settings")
        settings_manager = module.UserSettings(self.parent)
        settings["Movie Render Queue Presets Path"].value = settings_manager.retrieve(
            "publish2.movie_render_queue_presets_path",
            settings["Movie Render Queue Presets Path"].value,
            settings_manager.SCOPE_PROJECT,
        )
        settings["Publish Folder"].value = settings_manager.retrieve(
            "publish2.publish_folder",
            settings["Publish Folder"].value,
            settings_manager.SCOPE_PROJECT
        )

    def save_ui_settings(self, settings):
        fw = self.load_framework("tk-framework-shotgunutils_v5.x.x")
        module = fw.import_module("settings")
        settings_manager = module.UserSettings(self.parent)
        render_presets_path = settings["Movie Render Queue Presets Path"].value
        settings_manager.store("publish2.movie_render_queue_presets_path", render_presets_path, settings_manager.SCOPE_PROJECT)
        publish_folder = settings["Publish Folder"].value
        settings_manager.store("publish2.publish_folder", publish_folder, settings_manager.SCOPE_PROJECT)

    def accept(self, settings, item):
        accepted = True
        checked = True
        if sys.platform != "win32":
            return {"accepted": False}
        publisher = self.parent
        publish_template_setting = settings.get("Publish Template")
        publish_template = publisher.get_template_by_name(publish_template_setting.value)
        if not publish_template:
            accepted = False
        item.properties["publish_template"] = publish_template
        self.load_saved_ui_settings(settings)
        return {"accepted": accepted, "checked": checked}

    def validate(self, settings, item):
        asset_path = item.properties.get("asset_path")
        asset_name = item.properties.get("asset_name")
        if not asset_path or not asset_name:
            return False
        edits_path = item.properties.get("edits_path")
        if not edits_path:
            return False
        item.properties["unreal_master_sequence"] = edits_path[0]
        item.properties["unreal_shot"] = ".".join([lseq.get_name() for lseq in edits_path[1:]])
        publish_template = item.properties["publish_template"]
        context = item.context
        try:
            fields = context.as_template_fields(publish_template)
        except Exception:
            self.parent.sgtk.create_filesystem_structure(
                context.entity["type"], context.entity["id"], self.parent.engine.instance_name
            )
            fields = item.context.as_template_fields(publish_template)
        unreal_map = unreal.EditorLevelLibrary.get_editor_world()
        unreal_map_path = unreal_map.get_path_name()
        if unreal_map_path.startswith("/Temp/"):
            return False
        world_name = unreal_map.get_name()
        fields["ue_world"] = world_name
        if len(edits_path) > 1:
            fields["ue_level_sequence"] = "%s_%s" % (edits_path[0].get_name(), edits_path[-1].get_name())
        else:
            fields["ue_level_sequence"] = edits_path[0].get_name()
        item.properties["unreal_asset_path"] = asset_path
        item.properties["unreal_map_path"] = unreal_map_path
        version_number = self._unreal_asset_get_version(asset_path) + 1
        fields["version"] = version_number
        date = datetime.date.today()
        fields["YYYY"] = date.year
        fields["MM"] = date.month
        fields["DD"] = date.day
        use_movie_render_queue = False
        render_presets = None
        if hasattr(unreal, "MoviePipelineQueueEngineSubsystem"):
            if hasattr(unreal, "MoviePipelineAppleProResOutput"):
                use_movie_render_queue = True
                render_presets_path = settings["Movie Render Queue Presets Path"].value
                if render_presets_path:
                    render_presets = unreal.EditorAssetLibrary.load_asset(render_presets_path)
                    for _, reason in self._check_render_settings(render_presets):
                        self.logger.warning(reason)
        if not use_movie_render_queue:
            if item.properties["unreal_shot"]:
                raise ValueError("Rendering individual shots requires Movie Render Queue.")
        item.properties["use_movie_render_queue"] = use_movie_render_queue
        item.properties["movie_render_queue_presets"] = render_presets
        if use_movie_render_queue:
            fields["ue_mov_ext"] = "mov"
        else:
            fields["ue_mov_ext"] = "avi" if sys.platform == "win32" else "mov"
        missing_keys = publish_template.missing_keys(fields)
        if missing_keys:
            raise ValueError("Missing keys for publish template %s" % (missing_keys))
        publish_path = publish_template.apply_fields(fields)
        if not os.path.isabs(publish_path):
            publish_folder = settings["Publish Folder"].value or unreal.Paths.project_saved_dir()
            publish_path = os.path.abspath(os.path.join(publish_folder, publish_path))
        item.properties["path"] = publish_path
        item.properties["publish_path"] = publish_path
        item.properties["publish_type"] = "Unreal Render"
        item.properties["version_number"] = version_number
        self.save_ui_settings(settings)
        item.description = _require_desc_with_cl(item.description)
        

        return True

    def _check_render_settings(self, render_config):
        invalid_settings = []
        for setting in render_config.get_all_settings():
            if isinstance(setting, unreal.MoviePipelineImagePassBase) and type(setting) != unreal.MoviePipelineDeferredPassBase:
                invalid_settings.append((setting, "Render pass %s would cause multiple outputs" % setting.get_name()))
            elif isinstance(setting, unreal.MoviePipelineOutputBase) and not isinstance(setting, unreal.MoviePipelineAppleProResOutput):
                invalid_settings.append((setting, "Render output %s would cause multiple outputs" % setting.get_name()))
        return invalid_settings

    def publish(self, settings, item):
        publish_path = os.path.normpath(item.properties["publish_path"])
        destination_folder, movie_name = os.path.split(publish_path)
        movie_name = os.path.splitext(movie_name)[0]
        self.parent.ensure_folder_exists(destination_folder)
        unreal_asset_path = item.properties["unreal_asset_path"]
        unreal_map_path = item.properties["unreal_map_path"]
        if item.properties.get("use_movie_render_queue"):
            presets = item.properties["movie_render_queue_presets"]
            if presets:
                self.logger.info("Rendering %s with MRQ and presets %s" % (publish_path, presets.get_name()))
            else:
                self.logger.info("Rendering %s with MRQ" % publish_path)
            res, _ = self._unreal_render_sequence_with_movie_queue(
                publish_path, unreal_map_path, unreal_asset_path, presets, item.properties.get("unreal_shot") or None
            )
        else:
            self.logger.info("Rendering %s with Sequencer" % publish_path)
            res, _ = self._unreal_render_sequence_with_sequencer(publish_path, unreal_map_path, unreal_asset_path)
        if not res:
            raise RuntimeError("Unable to render %s" % publish_path)
        self._unreal_asset_set_version(unreal_asset_path, item.properties["version_number"])
        super(UnrealMoviePublishPlugin, self).publish(settings, item)
        self.logger.info("Creating Version...")
        version_data = {
            "project": item.context.project,
            "code": movie_name,
            "description": item.description,
            "entity": self._get_version_entity(item),
            "sg_path_to_movie": publish_path,
            "sg_task": item.context.task,
        }
        publish_data = item.properties.get("sg_publish_data")
        if publish_data:
            version_data["published_files"] = [publish_data]
        self.logger.debug(
            "Populated Version data...",
            extra={
                "action_show_more_info": {
                    "label": "Version Data",
                    "tooltip": "Show the complete Version data dictionary",
                    "text": "<pre>%s</pre>" % (pprint.pformat(version_data),),
                }
            },
        )
        version = self.parent.shotgun.create("Version", version_data)
        item.properties["sg_version_data"] = version
        upload_path = str(item.properties.get("publish_path"))
        self.logger.info("Uploading content...")
        self.parent.shotgun.upload("Version", version["id"], upload_path, "sg_uploaded_movie")
        self.logger.info("Upload complete!")

    def finalize(self, settings, item):
        super(UnrealMoviePublishPlugin, self).finalize(settings, item)

    def _get_version_entity(self, item):
        if item.context.entity:
            return item.context.entity
        elif item.context.project:
            return item.context.project
        else:
            return None

    def _unreal_asset_get_version(self, asset_path):
        asset = unreal.EditorAssetLibrary.load_asset(asset_path)
        version_number = 0
        if not asset:
            return version_number
        engine = sgtk.platform.current_engine()
        tag = engine.get_metadata_tag("version_number")
        metadata = unreal.EditorAssetLibrary.get_metadata_tag(asset, tag)
        if not metadata:
            return version_number
        try:
            version_number = int(metadata)
        except ValueError:
            pass
        return version_number

    def _unreal_asset_set_version(self, asset_path, version_number):
        asset = unreal.EditorAssetLibrary.load_asset(asset_path)
        if not asset:
            return
        engine = sgtk.platform.current_engine()
        tag = engine.get_metadata_tag("version_number")
        unreal.EditorAssetLibrary.set_metadata_tag(asset, tag, str(version_number))
        unreal.EditorAssetLibrary.save_loaded_asset(asset)
        engine = sgtk.platform.current_engine()
        for dialog in engine.created_qt_dialogs:
            dialog.raise_()

    def _unreal_render_sequence_with_sequencer(self, output_path, unreal_map_path, sequence_path):
        output_folder, output_file = os.path.split(output_path)
        movie_name = os.path.splitext(output_file)[0]
        if os.path.isfile(output_path):
            try:
                os.remove(output_path)
            except OSError:
                self.logger.error("Couldn't delete %s before render" % output_path)
                return False, None
        cmdline_args = [
            _get_unreal_editor_exe(),
            os.path.join(unreal.SystemLibrary.get_project_directory(), "%s.uproject" % unreal.SystemLibrary.get_game_name()),
            unreal_map_path,
            "-LevelSequence=%s" % sequence_path,
            "-MovieFolder=%s" % output_folder,
            "-MovieName=%s" % movie_name,
            "-game",
            "-MovieSceneCaptureType=/Script/MovieSceneCapture.AutomatedLevelSequenceCapture",
            "-ResX=1280",
            "-ResY=720",
            "-ForceRes",
            "-Windowed",
            "-MovieCinematicMode=yes",
            "-MovieFormat=Video",
            "-MovieFrameRate=24",
            "-MovieQuality=75",
            "-NoTextureStreaming",
            "-NoLoadingScreen",
            "-NoScreenMessages",
        ]
        run_env = copy.copy(os.environ)
        for k in ("UE_SHOTGUN_BOOTSTRAP", "UE_SHOTGRID_BOOTSTRAP"):
            if k in run_env:
                del run_env[k]
        subprocess.call(cmdline_args, env=run_env)
        return os.path.isfile(output_path), output_path

    def _unreal_render_sequence_with_movie_queue(self, output_path, unreal_map_path, sequence_path, presets=None, shot_name=None):
        output_folder, output_file = os.path.split(output_path)
        movie_name = os.path.splitext(output_file)[0]
        qsub = unreal.get_engine_subsystem(unreal.MoviePipelineQueueEngineSubsystem)
        queue = qsub.get_queue()
        try:
            queue.delete_all_jobs()
        except Exception:
            pass
        job = queue.allocate_new_job(unreal.MoviePipelineExecutorJob)
        job.sequence = unreal.SoftObjectPath(sequence_path)
        job.map = unreal.SoftObjectPath(unreal_map_path)
        if shot_name:
            shot_found = False
            for shot in job.shot_info:
                if shot.outer_name != shot_name:
                    shot.enabled = False
                else:
                    shot_found = True
            if not shot_found:
                raise ValueError("Unable to find shot %s in sequence %s" % (shot_name, sequence_path))
        if presets:
            job.set_preset_origin(presets)
        config = job.get_configuration()
        output_setting = config.find_or_add_setting_by_class(unreal.MoviePipelineOutputSetting)
        output_setting.output_directory = unreal.DirectoryPath(output_folder)
        output_setting.output_resolution = unreal.IntPoint(1280, 720)
        output_setting.file_name_format = movie_name
        output_setting.override_existing_output = True
        for setting, reason in self._check_render_settings(config):
            self.logger.warning("Disabling %s: %s." % (setting.get_name(), reason))
            config.remove_setting(setting)
        config.find_or_add_setting_by_class(unreal.MoviePipelineDeferredPassBase)
        config.find_or_add_setting_by_class(unreal.MoviePipelineAppleProResOutput)
        _, manifest_path = unreal.MoviePipelineEditorLibrary.save_queue_to_manifest_file(queue)
        manifest_path = os.path.abspath(manifest_path)
        manifest_dir, manifest_file = os.path.split(manifest_path)
        f, new_path = tempfile.mkstemp(suffix=os.path.splitext(manifest_file)[1], dir=manifest_dir)
        os.close(f)
        os.replace(manifest_path, new_path)
        saved_dir = os.path.abspath(os.path.join(unreal.SystemLibrary.get_project_directory(), "Saved"))
        try:
            manifest_rel = os.path.relpath(new_path, saved_dir)
            if manifest_rel.startswith(".."):
                raise ValueError("Manifest not under Saved")
        except Exception:
            import uuid, shutil
            ext = os.path.splitext(new_path)[1]
            dest = os.path.join(saved_dir, "MoviePipeline", f"sg_publish_{uuid.uuid4().hex}{ext}")
            os.makedirs(os.path.dirname(dest), exist_ok=True)
            try:
                shutil.copy2(new_path, dest)
            except Exception:
                shutil.move(new_path, dest)
            new_path = dest
            manifest_rel = os.path.relpath(new_path, saved_dir)
        manifest_path = manifest_rel
        cmd_args = [
            _get_unreal_editor_exe(),
            os.path.join(unreal.SystemLibrary.get_project_directory(), "%s.uproject" % unreal.SystemLibrary.get_game_name()),
            "MoviePipelineEntryMap?game=/Script/MovieRenderPipelineCore.MoviePipelineGameMode",
            "-game",
            "-Multiprocess",
            "-NoLoadingScreen",
            "-FixedSeed",
            "-log",
            "-Unattended",
            "-messaging",
            "-SessionName=\"Publish2 Movie Render\"",
            "-nohmd",
            "-windowed",
            "-ResX=1280",
            "-ResY=720",
            "-dpcvars=%s" % ",".join([
                "sg.ViewDistanceQuality=4",
                "sg.AntiAliasingQuality=4",
                "sg.ShadowQuality=4",
                "sg.PostProcessQuality=4",
                "sg.TextureQuality=4",
                "sg.EffectsQuality=4",
                "sg.FoliageQuality=4",
                "sg.ShadingQuality=4",
                "r.TextureStreaming=0",
                "r.ForceLOD=0",
                "r.SkeletalMeshLODBias=-10",
                "r.ParticleLODBias=-10",
                "foliage.DitheredLOD=0",
                "foliage.ForceLOD=0",
                "r.Shadow.DistanceScale=10",
                "r.ShadowQuality=5",
                "r.Shadow.RadiusThreshold=0.001000",
                "r.ViewDistanceScale=50",
                "r.D3D12.GPUTimeout=0",
                "a.URO.Enable=0",
            ]),
            "-execcmds=r.HLOD 0",
            "-MoviePipelineConfig=\"%s\"" % manifest_path,
        ]
        run_env = copy.copy(os.environ)
        for k in ("UE_SHOTGUN_BOOTSTRAP", "UE_SHOTGRID_BOOTSTRAP"):
            if k in run_env:
                del run_env[k]
        subprocess.call(cmd_args, env=run_env)
        return os.path.isfile(output_path), output_path
