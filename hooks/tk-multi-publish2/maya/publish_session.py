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
import maya.cmds as cmds
import maya.mel as mel
import sgtk
from sgtk.util.filesystem import ensure_folder_exists
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

class MayaSessionPublishPlugin(HookBaseClass):
    """
    Plugin for publishing an open maya session.

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
        base_settings = super(MayaSessionPublishPlugin, self).settings or {}

        # settings specific to this class
        maya_publish_settings = {
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
                "default": True,
                "description": "Create Playblast for maya scene."
            },
        }

        # update the base settings
        base_settings.update(maya_publish_settings)

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
        return ["maya.session"]

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
                "The Maya session has not been saved.", extra=_get_save_as_action()
            )

        self.logger.info(
            "Maya '%s' plugin accepted the current Maya session." % (self.name,)
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

        publisher = self.parent
        path = _session_path()



        # ---- ensure the session has been saved

        if not path:
            # the session still requires saving. provide a save button.
            # validation fails.
            error_msg = "The Maya session has not been saved."
            self.logger.error(error_msg, extra=_get_save_as_action())
            raise Exception(error_msg)

        # ensure we have an updated project root
        project_root = cmds.workspace(q=True, rootDirectory=True)
        item.properties["project_root"] = project_root

        # log if no project root could be determined.
        if not project_root:
            self.logger.info(
                "Your session is not part of a maya project.",
                extra={
                    "action_button": {
                        "label": "Set Project",
                        "tooltip": "Set the maya project",
                        "callback": lambda: mel.eval('setProject ""'),
                    }
                },
            )

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
                    "file template.",
                    extra={
                        "action_button": {
                            "label": "Save File",
                            "tooltip": "Save the current Maya session to a "
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
        return super(MayaSessionPublishPlugin, self).validate(settings, item)

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

        # add dependencies for the base class to register when publishing
        item.properties[
            "publish_dependencies"
        ] = _maya_find_additional_session_dependencies()

        # let the base class register the publish
        super(MayaSessionPublishPlugin, self).publish(settings, item)



        if settings[self._CREATE_PLAYBLAST].value == True:

            # Create Playblast either by generating a turntable camera or using camMain

            uploadPath = self.get_dailies_path(settings, item)
            publisher = self.parent


            '''En esta funcion chequeo que la estructura en la escena y del propia escena sea la correcta,
            es decir que contenga los nulls geo, basemesh debajo del nombre del asset'''


            ##Set First frame
            first = cmds.playbackOptions(q=True, min=True)

            # Checking Root Structure
            #rootNodes = cmds.ls(assemblies=True)  # variable con la lista de objetos de la escena
            rootNodes = cmds.ls(o=True)  # variable con la lista de objetos de la escena
            maxKeyframe = 120
            minKeyframe = 0
            all_keys = []

            '''Se comprueba que solo exista un root null en la escena obviando las camaras'''

            cameras = cmds.listCameras()
            turntable = True
            for cam in cameras:
                if "camMain" in cam:
                    turntable = False
                    main = cam
                else:
                    try:
                        rootNodes.remove(cam)
                    except:
                        pass
            '''Compruebo que la estructura del root es correcta'''
            if len(rootNodes) == 0:
                error_msg = "Scene structure is incorrect. There is no root nodes."
                self.logger.error(error_msg)
                raise Exception(error_msg)

            else:

                # Check for animations
                anim = False
                for node in rootNodes:
                    all_keys = sorted(cmds.keyframe(node,
                                                    q=True) or [])  # Get all the keys and sort them by order. We use `or []` in-case it has no keys, which will use an empty list instead so it doesn't crash `sort`.
                    if len(all_keys)>0:  # Check to see if it at least has one key.
                        anim = True
                        minKeyframe, maxKeyframe = (all_keys[0], all_keys[-1])  # Print the start and end frames
                        if all_keys[0] < minKeyframe:
                            minKeyframe = all_keys[0]
                        if all_keys[-1] > maxKeyframe:
                            maxKeyframe = all_keys[-1]

                #rootNode = cmds.listRelatives(rootNodes[0], fullPath=True)

                if turntable == True:
                    first = 0
                    ###Set last frame
                    last = maxKeyframe

                    ### Create camera turntable
                    obj = cmds.camera()
                    obj = cmds.rename(obj[0], "turnCam")
                    cmds.group(obj, name='rotGrp')

                    ## Select asset in scene
                    if anim:
                        first = minKeyframe
                        cmds.setAttr((obj + '.rotate'), -15, 0, 0, type="double3")
                        cmds.setAttr((obj + 'Shape.panZoomEnabled'), 1)
                        cmds.xform('rotGrp', ws=True, rp=[0, 0, 0])
                        cmds.setAttr((obj + 'Shape.zoom'), 1)
                        cmds.expression(s = 'rotGrp.rotateY = 45')
                        cmds.viewFit(obj, f=1)
                        cmds.setAttr((obj + 'Shape.farClipPlane'), (cmds.getAttr(obj + 'Shape.centerOfInterest')*2))
                        ###Set last frame
                        cmds.playbackOptions(animationStartTime=first, animationEndTime=maxKeyframe, minTime=first,
                                             maxTime=maxKeyframe)
                    else:
                        cmds.setAttr((obj + '.rotate'), -15, 45, 0, type="double3")
                        cmds.setAttr((obj + 'Shape.panZoomEnabled'), 0)
                        cmds.xform('rotGrp', ws=True, rp=[0, 0, 0])
                        cmds.setAttr((obj + 'Shape.zoom'), 1)
                        cmds.expression(s = 'rotGrp.rotateY = frame * (360/120)')
                        cmds.viewFit(obj, f=1)
                        cmds.setAttr((obj + 'Shape.farClipPlane'), (cmds.getAttr(obj + 'Shape.centerOfInterest')*2))
                        ###Set last frame
                        cmds.playbackOptions(animationStartTime=0, animationEndTime=maxKeyframe, minTime=0,
                                             maxTime=maxKeyframe)

                    cmds.lookThru(obj)

                else:
                    ##Set First frame
                    first = cmds.playbackOptions(q=True, min=True)
                    last = cmds.playbackOptions(q=True, max=True)
                    cmds.lookThru(main)




                ## Process avi
                cmds.playblast(format='avi',
                filename = uploadPath,
                startTime = first,
                endTime = last,
                widthHeight = [1920, 1080],
                sequenceTime = 0,
                clearCache = 1,
                viewer = 0,
                showOrnaments = 1,
                percent = 100,
                compression = 'none',
                quality = 100,
                fo = 1)

                if turntable == True:
                    cmds.delete('rotGrp')

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
                "frame_range": str(int(first))+"-"+str(int(last)),
                }

                if "sg_publish_data" in item.properties:
                    publish_data = item.properties["sg_publish_data"]
                version_data["published_files"] = [publish_data]

                version_data["sg_path_to_movie"] = uploadPath

                # log the version data for debugging
                self.logger.debug(
                "Populated Version data...",
                extra = {
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
        super(MayaSessionPublishPlugin, self).finalize(settings, item)

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

    def _copy_work_to_publish(self, settings, item):
        """
        This method handles copying work file path(s) to a designated publish
        location.

        This method requires a "work_template" and a "publish_template" be set
        on the supplied item.

        The method will handle copying the "path" property to the corresponding
        publish location assuming the path corresponds to the "work_template"
        and the fields extracted from the "work_template" are sufficient to
        satisfy the "publish_template".

        The method will not attempt to copy files if any of the above
        requirements are not met. If the requirements are met, the file will
        ensure the publish path folder exists and then copy the file to that
        location.

        If the item has "sequence_paths" set, it will attempt to copy all paths
        assuming they meet the required criteria with respect to the templates.

        """
        # ---- ensure templates are available
        work_template = item.properties.get("work_template")
        if not work_template:
            self.logger.debug(
                "No work template set on the item. "
                "Skipping copy file to publish location."
            )
            return

        publish_template = self.get_publish_template(settings, item)
        if not publish_template:
            self.logger.debug(
                "No publish template set on the item. "
                "Skipping copying file to publish location."
            )
            return


        # by default, the path that was collected for publishing
        work_file = item.properties.path

        # ---- copy the work files to the publish location


        if not work_template.validate(work_file):
            self.logger.warning(
                "Work file '%s' did not match work template '%s'. "
                "Publishing in place." % (work_file, work_template)
            )
            return

        work_fields = work_template.get_fields(work_file)

        missing_keys = publish_template.missing_keys(work_fields)

        if missing_keys:
            self.logger.warning(
                "Work file '%s' missing keys required for the publish "
                "template: %s" % (work_file, missing_keys)
            )
            return

        publish_file = publish_template.apply_fields(work_fields)
        if work_fields["extension"] == "ma":
            typeFile = "mayaAscii"
        else:
            typeFile = "mayaBinary"
        if not os.path.isdir(os.path.dirname(publish_file)):
            os.makedirs(os.path.dirname(publish_file))

        if item.context.step['name'] in ['RIG', 'TEXTURE', 'SHADING', 'RIG_A', 'TEXTURE_A', 'SHADING_A']:
            cmds.file(publish_file, exportAll=True, preserveReferences=False, force=True, type=typeFile)
        else:
            cmds.file(publish_file, exportAll=True, preserveReferences=True, force=True, type=typeFile)



        self.logger.debug(
            "Copied work file '%s' to publish file '%s'."
            % (work_file, publish_file)
        )


def _maya_find_additional_session_dependencies():
    """
    Find additional dependencies from the session
    """

    # default implementation looks for references and
    # textures (file nodes) and returns any paths that
    # match a template defined in the configuration
    ref_paths = set()

    # first let's look at maya references
    ref_nodes = cmds.ls(references=True)
    for ref_node in ref_nodes:
        # get the path:
        ref_path = cmds.referenceQuery(ref_node, filename=True)
        # make it platform dependent
        # (maya uses C:/style/paths)
        ref_path = ref_path.replace("/", os.path.sep)
        if ref_path:
            ref_paths.add(ref_path)

    # now look at file texture nodes
    for file_node in cmds.ls(l=True, type="file"):
        # ensure this is actually part of this session and not referenced
        if cmds.referenceQuery(file_node, isNodeReferenced=True):
            # this is embedded in another reference, so don't include it in
            # the breakdown
            continue

        # get path and make it platform dependent
        # (maya uses C:/style/paths)
        texture_path = cmds.getAttr("%s.fileTextureName" % file_node).replace(
            "/", os.path.sep
        )
        if texture_path:
            ref_paths.add(texture_path)

    return list(ref_paths)


def _session_path():
    """
    Return the path to the current session
    :return:
    """
    path = cmds.file(query=True, sn=True)

    if path is not None:
        path = six.ensure_str(path)

    return path


def _save_session(path):
    """
    Save the current session to the supplied path.
    """

    # Maya can choose the wrong file type so we should set it here
    # explicitly based on the extension
    maya_file_type = None
    if path.lower().endswith(".ma"):
        maya_file_type = "mayaAscii"
    elif path.lower().endswith(".mb"):
        maya_file_type = "mayaBinary"

    # Maya won't ensure that the folder is created when saving, so we must make sure it exists
    folder = os.path.dirname(path)
    ensure_folder_exists(folder)

    cmds.file(rename=path)

    # save the scene:
    if maya_file_type:
        cmds.file(save=True, force=True, type=maya_file_type)
    else:
        cmds.file(save=True, force=True)


# TODO: method duplicated in all the maya hooks
def _get_save_as_action():
    """
    Simple helper for returning a log action dict for saving the session
    """

    engine = sgtk.platform.current_engine()

    # default save callback
    callback = cmds.SaveScene

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

