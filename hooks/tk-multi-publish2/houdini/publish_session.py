# Copyright (c) 2017 Shotgun Software Inc.
#
# CONFIDENTIAL AND PROPRIETARY
#
# This work is provided "AS IS" and subject to the Shotgun Pipeline Toolkit
# Source Code License included in this distribution package. See LICENSE.
# By accessing, using, copying or modifying this work you indicate your
# agreement to the Shotgun Pipeline Toolkit Source Code License. All rights
# not expressly granted therein are reserved by Shotgun Software Inc.

import os
import hou
import sgtk
import subprocess
import shutil

from tank_vendor import six
import pprint

HookBaseClass = sgtk.get_hook_baseclass()


try:
    from sgtk.platform.qt import QtCore, QtGui
except ImportError:
    CustomWidgetController = None
else:
    class PlayblastWidget(QtGui.QWidget):
        """
        This is the plugin's custom UI.
        It is meant to allow the user to generate a playblast and upload it as a version
        """

        def __init__(self, parent):
            super(PlayblastWidget, self).__init__(parent)

            # Create a nice simple layout with a checkbox in it.
            layout = QtGui.QFormLayout(self)
            self.setLayout(layout)

            label = QtGui.QLabel(
                "Clicking this checkbox will create a playblast of the scene during publish.",
                self
            )
            label.setWordWrap(True)
            layout.addRow(label)

            self._check_box = QtGui.QCheckBox("Create Playblast", self)
            self._check_box.setTristate(False)
            layout.addRow(self._check_box)

        @property
        def state(self):
            """
            :returns: ``True`` if the checkbox is checked, ``False`` otherwise.
            """
            return self._check_box.checkState() == QtCore.Qt.Checked

        @state.setter
        def state(self, is_checked):
            """
            Update the status of the checkbox.
            :param bool is_checked: When set to ``True``, the checkbox will be
                checked.
            """
            if is_checked:
                self._check_box.setCheckState(QtCore.Qt.Checked)
            else:
                self._check_box.setCheckState(QtCore.Qt.Unchecked)

class HoudiniSessionPublishPlugin(HookBaseClass):
    """
    Plugin for publishing an open houdini session.

    This hook relies on functionality found in the base file publisher hook in
    the publish2 app and should inherit from it in the configuration. The hook
    setting for this plugin should look something like this::

        hook: "{self}/publish_file.py:{engine}/tk-multi-publish2/basic/publish_session.py"

    """
    _CREATE_PLAYBLAST = "Create Playblast"
    # NOTE: The plugin icon and name are defined by the base file plugin.

    @property
    def description(self):
        """
        Verbose, multi-line description of what the plugin does. This can
        contain simple html for formatting.
        """

        loader_url = "https://support.shotgunsoftware.com/hc/en-us/articles/219033078"

        return """
        Publishes the file to Shotgun. A <b>Publish</b> entry will be
        created in Shotgun which will include a reference to the file's current
        path on disk. If a publish template is configured, a copy of the
        current session will be copied to the publish template path which
        will be the file that is published. Other users will be able to access
        the published file via the <b><a href='%s'>Loader</a></b> so long as
        they have access to the file's location on disk.

        If the session has not been saved, validation will fail and a button
        will be provided in the logging output to save the file.

        <h3>File versioning</h3>
        If the filename contains a version number, the process will bump the
        file to the next version after publishing.

        The <code>version</code> field of the resulting <b>Publish</b> in
        Shotgun will also reflect the version number identified in the filename.
        The basic worklfow recognizes the following version formats by default:

        <ul>
        <li><code>filename.v###.ext</code></li>
        <li><code>filename_v###.ext</code></li>
        <li><code>filename-v###.ext</code></li>
        </ul>

        After publishing, if a version number is detected in the work file, the
        work file will automatically be saved to the next incremental version
        number. For example, <code>filename.v001.ext</code> will be published
        and copied to <code>filename.v002.ext</code>

        If the next incremental version of the file already exists on disk, the
        validation step will produce a warning, and a button will be provided in
        the logging output which will allow saving the session to the next
        available version number prior to publishing.

        <br><br><i>NOTE: any amount of version number padding is supported. for
        non-template based workflows.</i>

        <h3>Overwriting an existing publish</h3>
        In non-template workflows, a file can be published multiple times,
        however only the most recent publish will be available to other users.
        Warnings will be provided during validation if there are previous
        publishes.
        """ % (
            loader_url,
        )

    @property
    def settings(self):
        """
        Dictionary defining the settings that this plugin expects to receive
        through the settings parameter in the accept, validate, publish and
        finalize methods.

        A dictionary on the following form::

            {
                "Settings Name": {
                    "type": "settings_type",
                    "default": "default_value",
                    "description": "One line description of the setting"
            }

        The type string should be one of the data types that toolkit accepts as
        part of its environment configuration.
        """

        # inherit the settings from the base publish plugin
        base_settings = super(HoudiniSessionPublishPlugin, self).settings or {}

        # settings specific to this class
        houdini_publish_settings = {
            "Publish Template": {
                "type": "template",
                "default": None,
                "description": "Template path for published work files. Should"
                "correspond to a template defined in "
                "templates.yml.",
            },
            "Dailies Template": {
                "type": "template",
                "default": None,
                "description": "Template path for dailies work files. Should"
                               "correspond to a template defined in "
                               "templates.yml.",
            },
            self._CREATE_PLAYBLAST: {
                "type": "bool",
                "default": False,
                "description": "Create Playblast for maya scene."
            },
        }

        # update the base settings
        base_settings.update(houdini_publish_settings)

        return base_settings


    def create_settings_widget(self, parent):
        """
        Creates the widget for our plugin.
        :param parent: Parent widget for the settings widget.
        :type parent: :class:`QtGui.QWidget`
        :returns: Custom widget for this plugin.
        :rtype: :class:`QtGui.QWidget`
        """
        return PlayblastWidget(parent)

    def get_ui_settings(self, widget):
        """
        Retrieves the state of the ui and returns a settings dictionary.
        :param parent: The settings widget returned by :meth:`create_settings_widget`
        :type parent: :class:`QtGui.QWidget`
        :returns: Dictionary of settings.
        """
        return {self._CREATE_PLAYBLAST: widget.state}

    def set_ui_settings(self, widget, settings):
        """
        Populates the UI with the settings for the plugin.
        :param parent: The settings widget returned by :meth:`create_settings_widget`
        :type parent: :class:`QtGui.QWidget`
        :param list(dict) settings: List of settings dictionaries, one for each
            item in the publisher's selection.
        :raises NotImplementeError: Raised if this implementation does not
            support multi-selection.
        """
        if len(settings) > 1:
            raise NotImplementedError()
        settings = settings[0]
        widget.state = settings[self._CREATE_PLAYBLAST]

    @property
    def item_filters(self):
        """
        List of item types that this plugin is interested in.

        Only items matching entries in this list will be presented to the
        accept() method. Strings can contain glob patters such as *, for example
        ["maya.*", "file.maya"]
        """
        return ["houdini.session"]

    def accept(self, settings, item):
        """
        Method called by the publisher to determine if an item is of any
        interest to this plugin. Only items matching the filters defined via the
        item_filters property will be presented to this method.

        A publish task will be generated for each item accepted here. Returns a
        dictionary with the following booleans:

            - accepted: Indicates if the plugin is interested in this value at
                all. Required.
            - enabled: If True, the plugin will be enabled in the UI, otherwise
                it will be disabled. Optional, True by default.
            - visible: If True, the plugin will be visible in the UI, otherwise
                it will be hidden. Optional, True by default.
            - checked: If True, the plugin will be checked in the UI, otherwise
                it will be unchecked. Optional, True by default.

        :param settings: Dictionary of Settings. The keys are strings, matching
            the keys returned in the settings property. The values are `Setting`
            instances.
        :param item: Item to process

        :returns: dictionary with boolean keys accepted, required and enabled
        """

        # if a publish template is configured, disable context change. This
        # is a temporary measure until the publisher handles context switching
        # natively.
        if settings.get("Publish Template").value:
            item.context_change_allowed = False

        path = _session_path()

        if not path:
            # the session has not been saved before (no path determined).
            # provide a save button. the session will need to be saved before
            # validation will succeed.
            self.logger.warn(
                "The Houdini session has not been saved.", extra=_get_save_as_action()
            )

        self.logger.info(
            "Houdini '%s' plugin accepted the current Houdini session." % (self.name,)
        )
        return {"accepted": True, "checked": True}

    def validate(self, settings, item):
        """
        Validates the given item to check that it is ok to publish. Returns a
        boolean to indicate validity.

        :param settings: Dictionary of Settings. The keys are strings, matching
            the keys returned in the settings property. The values are `Setting`
            instances.
        :param item: Item to process
        :returns: True if item is valid, False otherwise.
        """

        # this method will handle validation specific to the houdini script
        # itself. the base class plugin will handle validation of the file
        # itself

        publisher = self.parent
        path = _session_path()

        # ---- ensure the session has been saved

        if not path:
            # the session still requires saving. provide a save button.
            # validation fails.
            error_msg = "The Houdini session has not been saved."
            self.logger.error(error_msg, extra=_get_save_as_action())
            raise Exception(error_msg)

        # ---- check the session against any attached work template

        # get the path in a normalized state. no trailing separator,
        # separators are appropriate for current os, no double separators,
        # etc.
        path = sgtk.util.ShotgunPath.normalize(path)

        # if the session item has a known work template, see if the path
        # matches. if not, warn the user and provide a way to save the file to
        # a different path
        work_template = item.properties.get("work_template")
        if work_template:
            if not work_template.validate(path):
                self.logger.warning(
                    "The current session does not match the configured work "
                    "template.",
                    extra={
                        "action_button": {
                            "label": "Save File",
                            "tooltip": "Save the current Houdini session to a "
                            "different file name",
                            # will launch wf2 if configured
                            "callback": _get_save_as_action(),
                        }
                    },
                )
            else:
                self.logger.debug("Work template configured and matches session file.")
        else:
            self.logger.debug("No work template configured.")

        # ---- see if the version can be bumped post-publish

        # check to see if the next version of the work file already exists on
        # disk. if so, warn the user and provide the ability to jump to save
        # to that version now
        (next_version_path, version) = self._get_next_version_info(path, item)
        if next_version_path and os.path.exists(next_version_path):

            # determine the next available version_number. just keep asking for
            # the next one until we get one that doesn't exist.
            while os.path.exists(next_version_path):
                (next_version_path, version) = self._get_next_version_info(
                    next_version_path, item
                )

            error_msg = "The next version of this file already exists on disk."
            self.logger.error(
                error_msg,
                extra={
                    "action_button": {
                        "label": "Save to v%s" % (version,),
                        "tooltip": "Save to the next available version number, "
                        "v%s" % (version,),
                        "callback": lambda: _save_session(next_version_path),
                    }
                },
            )
            raise Exception(error_msg)

        # ---- populate the necessary properties and call base class validation

        # populate the publish template on the item if found
        publish_template_setting = settings.get("Publish Template")
        publish_template = publisher.engine.get_template_by_name(
            publish_template_setting.value
        )
        if publish_template:
            item.properties["publish_template"] = publish_template

        # set the session path on the item for use by the base plugin validation
        # step. NOTE: this path could change prior to the publish phase.
        item.properties["path"] = path

        # run the base class validation
        return super(HoudiniSessionPublishPlugin, self).validate(settings, item)

    def publish(self, settings, item):
        """
        Executes the publish logic for the given item and settings.

        :param settings: Dictionary of Settings. The keys are strings, matching
            the keys returned in the settings property. The values are `Setting`
            instances.
        :param item: Item to process
        """

        # get the path in a normalized state. no trailing separator, separators
        # are appropriate for current os, no double separators, etc.
        path = sgtk.util.ShotgunPath.normalize(_session_path())

        # ensure the session is saved
        _save_session(path)

        # update the item with the saved session path
        item.properties["path"] = path

        # let the base class register the publish
        super(HoudiniSessionPublishPlugin, self).publish(settings, item)

        if settings[self._CREATE_PLAYBLAST].value == True:

            uploadPath = self.get_dailies_path(settings, item)
            publisher = self.parent

            # Obtén una lista de todas las cámaras en la escena
            cameras = hou.nodeType(hou.objNodeTypeCategory(), 'cam').instances()

            # Crea una lista de nombres de cámaras
            camera_names = [cam.name() for cam in cameras]
            ShotCam = False

            first = hou.playbar.playbackRange()[0]
            last = hou.playbar.playbackRange()[1]

            for c in camera_names:
                if "camMain" in c:
                    chosen_camera_index = camera_names.index(c)
                    ShotCam = True
                else:
                    camera_names.remove(cam)
            if len(camera_names)==0:
                obj = hou.node('/obj')
                gira = obj.createNode('Giratutto')
                gira_camera = hou.node(gira.path() + '/Giratutto')

            # # Define el nombre de la cámara que quieres seleccionar
            # desired_camera_name = "RD_Pipehoudini_FX_Flipbook_v001"

            # # Comprueba si el nombre de la cámara deseada está en la lista de cámaras
            # if desired_camera_name in camera_names:
            #     # Si está en la lista, obtén el índice de ese nombre
            #     chosen_camera_index = camera_names.index(desired_camera_name)
            # else:
            #     # Si no está en la lista, muestra un mensaje de error y termina el script
            #     print("Error: No se encontró ninguna cámara con el nombre '" + desired_camera_name + "'.")
            #     exit()



            # Configura las opciones de flipbook
            cur_desktop = hou.ui.curDesktop()
            scene_viewer = hou.paneTabType.SceneViewer
            scene = cur_desktop.paneTabOfType(scene_viewer)
            scene.flipbookSettings().stash()
            flip_book_options = scene.flipbookSettings()

            # Configura la cámara seleccionada en el visor de la escena
            if ShotCam == True:
                # Obtén la cámara seleccionada
                chosen_camera = cameras[chosen_camera_index]
                scene.curViewport().setCamera(chosen_camera)
            else:
                scene.curViewport().setCamera(gira_camera)

            # Define la nueva ruta de salida para las imágenes del flipbook
            hip = os.path.dirname(hou.hipFile.path())
            hip_name = hou.hipFile.basename()[:-4]
            flipbookPath = hip + '/Temp/flipbook/flipbook.$F4.jpeg'

            flipbook_path = flipbookPath
            flip_book_options.output(flipbook_path)  # Proporciona la ruta completa del flipbook con relleno.
            flip_book_options.frameRange(hou.playbar.playbackRange())  # Usa el rango de fotogramas de la escena
            flip_book_options.useResolution(1)
            flip_book_options.resolution((1920, 1080))  # Basado en la resolución de tu cámara

            # Crea la carpeta si no existe
            flipbook_dir = os.path.dirname(flipbook_path)
            if not os.path.exists(flipbook_dir):
                os.makedirs(flipbook_dir)

            # Genera el flipbook
            scene.flipbook(scene.curViewport(), flip_book_options)

            # Define la ruta de salida para el video
            video_output_path = uploadPath

            # Crea la carpeta si no existe
            video_dir = os.path.dirname(video_output_path)
            if not os.path.exists(video_dir):
                os.makedirs(video_dir)

            # Reemplaza '$F4' con '%04d' en flipbook_path
            flipbook_path_format = flipbook_path.replace('$F4', '%04d')

            # Comando ffmpeg para convertir el video
            ffmpeg_command = f"C:/ffmpeg/bin/ffmpeg.exe -framerate 24 -start_number {first} -i {flipbook_path_format} -c:v prores_ks -profile:v 3 -vf scale=1920:1080 -an -loglevel debug {video_output_path}"

            # Ejecutar el comando ffmpeg
            try:
                subprocess.run(ffmpeg_command, shell=True, check=True)
                print("Conversión exitosa.")
            except subprocess.CalledProcessError as e:
                print(f"Error al ejecutar ffmpeg: {e}")


            ###### ANTIGUO
            # uploadPath = self.get_dailies_path(settings, item)
            # publisher = self.parent
            # first = hou.playbar.playbackRange()[0]
            # last = hou.playbar.playbackRange()[1]
            #
            # cur_desktop = hou.ui.curDesktop()
            # scene_viewer = hou.paneTabType.SceneViewer
            # scene = cur_desktop.paneTabOfType(scene_viewer)
            # scene.flipbookSettings().stash()
            # flip_book_options = scene.flipbookSettings()
            #
            # flip_book_options.output(uploadPath)  # Provide flipbook full path with padding.
            # flip_book_options.frameRange((first, last))  # Enter Frame Range Here in x & y
            # flip_book_options.useResolution(1)
            # flip_book_options.resolution((1920, 1080))  # Based on your camera resolution
            # scene.flipbook(scene.curViewport(), flip_book_options)



            # Start generation of shotgun version

            path = item.properties["path"]

            publish_name = item.properties.get("publish_name")
            versionName = os.path.splitext(os.path.basename(uploadPath))[0]
            if not publish_name:
                self.logger.debug("Using path info hook to determine publish name.")

            # use the path's filename as the publish name
            # path_components = publisher.util.get_file_path_components(path)
            # publish_name = '_'.join(path_components["filename"].split('_')[:-1])

            self.logger.debug("Publish name: %s" % (publish_name,))

            self.logger.info("Creating Version...")
            version_data = {
                "project": item.context.project,
                "code": versionName,
                "description": item.description,
                "entity": self._get_version_entity(item),
                "sg_task": item.context.task,
                "sg_first_frame": int(first),
                "sg_last_frame": int(last),
                "frame_range": str(int(first)) + "-" + str(int(last)),
            }

            if "sg_publish_data" in item.properties:
                publish_data = item.properties["sg_publish_data"]
            version_data["published_files"] = [publish_data]

            version_data["sg_path_to_movie"] = uploadPath

            # log the version data for debugging
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

            # Create the version
            version = publisher.shotgun.create("Version", version_data)
            self.logger.info("Version created!")

            # stash the version info in the item just in case
            item.properties["sg_version_data"] = version

            self.logger.info("Uploading content...")

            # on windows, ensure the path is utf-8 encoded to avoid issues with
            # the shotgun api
            if sgtk.util.is_windows():
                upload_path = six.ensure_text(uploadPath)
            else:
                upload_path = uploadPath

            self.parent.shotgun.upload(
                "Version", version["id"], upload_path, "sg_uploaded_movie"

            )

            self.logger.info("Upload complete!")

        status = {"sg_status_list": "rev"}
        self.parent.sgtk.shotgun.update("Task", item.context.task['id'], status)

        if settings[self._CREATE_PLAYBLAST].value == True:
            shutil.rmtree(os.path.dirname(flipbookPath))
            if ShotCam == False:
                gira.destroy()

        # self.parent.sgtk.shotgun.update("Shot", item.context.entity['id'], status)

    def finalize(self, settings, item):
        """
        Execute the finalization pass. This pass executes once all the publish
        tasks have completed, and can for example be used to version up files.

        :param settings: Dictionary of Settings. The keys are strings, matching
            the keys returned in the settings property. The values are `Setting`
            instances.
        :param item: Item to process
        """

        # do the base class finalization
        super(HoudiniSessionPublishPlugin, self).finalize(settings, item)

        # bump the session file to the next version
        self._save_to_next_version(item.properties["path"], item, _save_session)


    def _get_version_entity(self, item):
        """
        Returns the best entity to link the version to.
        """

        if item.context.entity:
            return item.context.entity
        elif item.context.project:
            return item.context.project
        else:
            return None


    def get_dailies_template(self, settings, item):
        """
        Get a publish template for the supplied settings and item.

        :param settings: This plugin instance's configured settings
        :param item: The item to determine the publish template for

        :return: A template representing the publish path of the item or
            None if no template could be identified.
        """

        publisher = self.parent
        template_name = settings["Dailies Template"].value
        dailies_template = publisher.get_template_by_name(template_name)
        item.properties["dailies_template"] = dailies_template

        return dailies_template


    def get_dailies_path(self, settings, item):
        """
        Get a publish path for the supplied settings and item.

        :param settings: This plugin instance's configured settings
        :param item: The item to determine the publish path for

        :return: A string representing the output path to supply when
            registering a publish for the supplied item

        Extracts the publish path via the configured work and publish templates
        if possible.
        """

        # fall back to template/path logic
        path = _session_path()

        work_template = item.properties.get("work_template")
        dailies_template = self.get_dailies_template(settings, item)

        work_fields = []
        dailies_path = None

        # We need both work and publish template to be defined for template
        # support to be enabled.
        if work_template and dailies_template:

            if work_template.validate(path):
                work_fields = work_template.get_fields(path)
                work_fields["extension"] = "avi"

            missing_keys = dailies_template.missing_keys(work_fields)

            if missing_keys:
                self.logger.warning(
                    "Not enough keys to apply work fields (%s) to "
                    "publish template (%s)" % (work_fields, dailies_template)
                )
            else:
                dailies_path = dailies_template.apply_fields(work_fields)
                self.logger.debug(
                    "Used publish template to determine the publish path: %s"
                    % (dailies_path,)
                )
        else:
            self.logger.debug("dailies_template: %s" % dailies_template)
            self.logger.debug("work_template: %s" % work_template)

        return dailies_path


def _save_session(path):
    """
    Save the current session to the supplied path.
    """
    # We need to flip the slashes on Windows to avoid a bug in Houdini. If we don't
    # the next Save As dialog will have the filename box populated with the complete
    # file path.
    sanitized_path = six.ensure_str(path.replace("\\", "/"))
    hou.hipFile.save(file_name=sanitized_path)


def _session_path():
    """
    Return the path to the current session
    :return:
    """

    # Houdini always returns a file path, even for new sessions. We key off the
    # houdini standard of "untitled.hip" to indicate that the file has not been
    # saved.
    if hou.hipFile.name() == "untitled.hip":
        return None

    return hou.hipFile.path()


def _get_save_as_action():
    """
    Simple helper for returning a log action dict for saving the session
    """

    engine = sgtk.platform.current_engine()

    # default save callback
    callback = engine.save_as

    # if workfiles2 is configured, use that for file save
    if "tk-multi-workfiles2" in engine.apps:
        app = engine.apps["tk-multi-workfiles2"]
        if hasattr(app, "show_file_save_dlg"):
            callback = app.show_file_save_dlg

    return {
        "action_button": {
            "label": "Save As...",
            "tooltip": "Save the current session",
            "callback": callback,
        }
    }
