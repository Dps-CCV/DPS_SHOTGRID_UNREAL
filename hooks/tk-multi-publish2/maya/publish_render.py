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
import pprint
import traceback

import maya.cmds as cmds

from tank_vendor import six
import sys
import platform

import sgtk
from sgtk.util.filesystem import copy_file, ensure_folder_exists

HookBaseClass = sgtk.get_hook_baseclass()

try:
    from sgtk.platform.qt import QtCore, QtGui
except ImportError:
    CustomWidgetController = None
else:
    class RenderVersionWidget(QtGui.QWidget):
        """
        This is the plugin's custom UI.
        It is meant to allow the user to generate a version qt of the render layer and upload it as a version
        """

        def __init__(self, parent):
            super(RenderVersionWidget, self).__init__(parent)

            # Create a nice simple layout with a checkbox in it.
            layout = QtGui.QFormLayout(self)
            self.setLayout(layout)

            label = QtGui.QLabel(
                "Clicking this checkbox will create a version of the render layer during publish.",
                self
            )
            label.setWordWrap(True)
            layout.addRow(label)

            self._check_box = QtGui.QCheckBox("Create Version", self)
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


class RenderPublishPlugin(HookBaseClass):
    """
    Plugin for creating publishing renders
    """
    _CREATE_VERSION = "Create Version"
    @property
    def settings(self):

        # inherit the settings from the base publish plugin
        plugin_settings = super(RenderPublishPlugin, self).settings or {}

        # settings specific to this class
        maya_render_publish_settings = {
            "Publish Template": {
                "type": "template",
                "default": None,
                "description": "Template path for published renders. Should"
                "correspond to a template defined in "
                "templates.yml.",
            },
            "Dailies Template": {
                "type": "template",
                "default": None,
                "description": "Template path for published renders. Should"
                               "correspond to a template defined in "
                               "templates.yml.",
            },
            "Link Local File": {
                "type": "bool",
                "default": True,
                "description": "Should the local file be referenced by Shotgun",
            },
            self._CREATE_VERSION: {
                "type": "bool",
                "default": False,
                "description": "Create Version for render layer."
            },
        }

        # update the base settings
        plugin_settings.update(maya_render_publish_settings)

        return plugin_settings

    def create_settings_widget(self, parent):
        """
        Creates the widget for our plugin.
        :param parent: Parent widget for the settings widget.
        :type parent: :class:`QtGui.QWidget`
        :returns: Custom widget for this plugin.
        :rtype: :class:`QtGui.QWidget`
        """
        return RenderVersionWidget(parent)

    def get_ui_settings(self, widget):
        """
        Retrieves the state of the ui and returns a settings dictionary.
        :param parent: The settings widget returned by :meth:`create_settings_widget`
        :type parent: :class:`QtGui.QWidget`
        :returns: Dictionary of settings.
        """
        return {self._CREATE_VERSION: widget.state}

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
        widget.state = settings[self._CREATE_VERSION]

    @property
    def item_filters(self):
        """
        List of item types that this plugin is interested in.

        Only items matching entries in this list will be presented to the
        accept() method. Strings can contain glob patters such as *, for example
        ["maya.*", "file.maya"]
        """

        return ["maya.session.render"]

    def accept(self, settings, item):
        # self.logger.debug("PlayblastPublishPlugin.accept")

        # ensure a camera file template is available on the parent item
        work_template = item.parent.properties.get("work_template")
        if not work_template:
            self.logger.debug(
                "A work template is required for the session item in order to "
                "publish a render. Not accepting session render item."
            )
            return {"accepted": False}

        # ensure the publish template is defined and valid and that we also have
        publisher = self.parent
        publish_template_name = settings["Publish Template"].value
        publish_template = publisher.get_template_by_name(publish_template_name)
        if publish_template:
            item.properties["publish_template"] = publish_template
            # because a publish template is configured, disable context change.
            # This is a temporary measure until the publisher handles context
            # switching natively.
            item.context_change_allowed = False
        else:
            self.logger.debug(
                "The valid publish template could not be determined for the "
                "session render item. Not accepting the item."
            )
            return {"accepted": False}

        if publisher.context.step['name'] in ['LIGHT', 'LIGHT_A', 'TEXTURE_A']:
            return {"accepted": True, "checked": True}
        else:
            return {"accepted": True, "checked": False}
        
    def validate(self, settings, item):
        # self.logger.debug("PlayblastPublishPlugin.validate")

        path = _session_path()

        # get the configured work file template
        work_template = item.parent.properties.get("work_template")
        publish_template = item.properties.get("publish_template")

        # get the current scene path and extract fields from it using the work
        # template:
        work_fields = work_template.get_fields(path)

        # include the extension in the fields
        filename, extension = os.path.splitext(item.properties["path"])
        work_fields["extension"] = extension[1:]
        work_fields["frame_num"] = 6969
        work_fields["maya.layer_name"] = item.properties.get("maya.layer_name")

        # ensure the fields work for the publish template
        missing_keys = publish_template.missing_keys(work_fields)
        # if len(missing_keys) != 1 or "frame_num" not in missing_keys:
        if missing_keys:
            error_msg = (
                "Work file '%s' missing keys required for the "
                "publish template: %s" % (path, missing_keys)
            )
            self.logger.error(error_msg)
            raise Exception(error_msg)

        # create the publish path by applying the fields. store it in the item's
        # properties. This is the path we'll create and then publish in the base
        # publish plugin. Also set the publish_path to be explicit.
        publish_path = publish_template.apply_fields(work_fields)
        item.properties["publish_path"] = publish_path.replace("6969", "####")
        item.properties["publish_template"] = publish_template
        item.properties["work_fields"] = work_fields

        # use the work file's version number when publishing
        if "version" in work_fields:
            item.properties["publish_version"] = work_fields["version"]


        # TBR: revise if any parent class code is reusable
        # return super(PlayblastPublishPlugin, self).validate(settings, item)
        return super(RenderPublishPlugin, self).accept(settings, item)

    def publish(self, settings, item):
        """
        Executes the publish logic for the given item and settings.

        :param settings: Dictionary of Settings. The keys are strings, matching
            the keys returned in the settings property. The values are `Setting`
            instances.
        :param item: Item to process
        """

        publisher = self.parent

        # ---- determine the information required to publish

        # We allow the information to be pre-populated by the collector or a
        # base class plugin. They may have more information than is available
        # here such as custom type or template settings.

        number = '{0:03d}'.format(self.get_publish_version(settings, item))
        rawversion = "_v" + str(number)
        publish_name = self.get_publish_name(settings, item).replace(rawversion, '')
        publish_type = self.get_publish_type(settings, item)
        #publish_name = self.get_publish_name(settings, item)
        publish_version = self.get_publish_version(settings, item)
        publish_path = self.get_publish_path(settings, item)
        publish_dependencies_paths = self.get_publish_dependencies(settings, item)
        publish_user = self.get_publish_user(settings, item)
        publish_fields = self.get_publish_fields(settings, item)
        # catch-all for any extra kwargs that should be passed to register_publish.
        publish_kwargs = self.get_publish_kwargs(settings, item)



        # if item.properties.get("maya.layer_name") != "masterLayer":
        #     publish_name = self.newPublishName(settings, item)

        # if the parent item has publish data, get it id to include it in the list of
        # dependencies
        publish_dependencies_ids = []
        if "sg_publish_data" in item.parent.properties:
            publish_dependencies_ids.append(
                item.parent.properties.sg_publish_data["id"]
            )

        # handle copying of work to publish if templates are in play

        self._copy_work_to_publish(settings, item)

        # arguments for publish registration
        self.logger.info("Registering publish...")
        publish_data = {
            "tk": publisher.sgtk,
            "context": item.context,
            "comment": item.description,
            "path": publish_path,
            "name": publish_name,
            "created_by": publish_user,
            "version_number": publish_version,
            "thumbnail_path": item.get_thumbnail_as_path(),
            "published_file_type": publish_type,
            "dependency_paths": publish_dependencies_paths,
            "dependency_ids": publish_dependencies_ids,
            "sg_fields": publish_fields,
        }

        # add extra kwargs
        publish_data.update(publish_kwargs)

        # log the publish data for debugging
        self.logger.debug(
            "Populated Publish data...",
            extra={
                "action_show_more_info": {
                    "label": "Publish Data",
                    "tooltip": "Show the complete Publish data dictionary",
                    "text": "<pre>%s</pre>" % (pprint.pformat(publish_data),),
                }
            },
        )

        # create the publish and stash it in the item properties for other
        # plugins to use.
        item.properties.sg_publish_data = sgtk.util.register_publish(**publish_data)
        self.logger.info("Publish registered!")
        self.logger.debug(
            "Shotgun Publish data...",
            extra={
                "action_show_more_info": {
                    "label": "Shotgun Publish Data",
                    "tooltip": "Show the complete Shotgun Publish Entity dictionary",
                    "text": "<pre>%s</pre>"
                    % (pprint.pformat(item.properties.sg_publish_data),),
                }
            },
        )

        # DPS Workaround to be able to generate video file while publishing exr render sequences. It creates an image plane of the render and then process a playblast.
        if settings[self._CREATE_VERSION].value == True:

            path = publish_path

            uploadPath = self.get_dailies_path(settings, item)

            first = item.properties['sequence_paths'][0][-8:-4]
            last =item.properties['sequence_paths'][-1][-8:-4]
            pathNum = path.replace("####", str(first))
            # create an image plane for the supplied path, visible in all views
            (dumyCam, dumyCam_shape) = cmds.camera()
            (img_plane, img_plane_shape) = cmds.imagePlane(camera=dumyCam, fileName=pathNum, showInAllViews=True)

            cmds.setAttr("%s.useFrameExtension" % (img_plane_shape,), 1)
            cmds.setAttr("%s.depth" % (img_plane_shape,), 0.1)
            cmds.setAttr("%s.displayMode" % (img_plane_shape,), 2)
            if 'EXR' in path:
                cmds.setAttr("%s.colorSpace" % (img_plane_shape,), 'ACEScg', type='string')
            elif 'JPG' in path:
                cmds.setAttr("%s.colorSpace" % (img_plane_shape,), 'Output - Rec.709', type='string')
            cmds.lookThru(dumyCam)
            # viewport = cmds.getPanel(withFocus=True)
            # cmds.modelEditor(viewport, da="smoothShaded", wos=False, swf=False)
            cmds.playblast(format="movie", filename=uploadPath, forceOverwrite=True, percent=100,
                           widthHeight=[1920, 1080], showOrnaments=False, viewer=False, startTime=int(first), endTime=int(last))
            # cmds.playblast(fmt= "movie", completeFilename="C:\Users\USER\Desktop\test.avi", viewer=False, showOrnaments=False, percent=100, width=1920, height=1080, startTime=1001, endTime=1020)
            cmds.delete(img_plane)
            cmds.delete(dumyCam)



            publish_name = item.properties.get("publish_name")
            if not publish_name:
                self.logger.debug("Using path info hook to determine publish name.")

                # use the path's filename as the publish name
                path_components = publisher.util.get_file_path_components(path)
                publish_name = path_components["filename"]

            self.logger.debug("Publish name: %s" % (publish_name,))

            self.logger.info("Creating Version...")
            version_data = {
                "project": item.context.project,
                "code": publish_name,
                "description": item.description,
                "entity": self._get_version_entity(item),
                "sg_task": item.context.task,
            }

            if "sg_publish_data" in item.properties:
                publish_data = item.properties["sg_publish_data"]
                version_data["published_files"] = [publish_data]

            if settings["Link Local File"].value:
                version_data["sg_path_to_movie"] = uploadPath

            version_data["sg_path_to_frames"] = publish_path
            version_data["frame_count"] = int(int(last)-int(first))
            version_data["frame_range"] = first + "-" + last

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

            thumb = item.get_thumbnail_as_path()

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

    def get_publish_path(self, settings, item):

        return item.properties.get("publish_path")

    # def newPublishName(self, settings, item):
    #     number = '{0:03d}'.format(self.get_publish_version(settings, item))
    #     rawversion = "_v" + str(number)
    #     layer = item.properties.get("maya.layer_name")
    #     #newname = "_" + layer + rawversion
    #     newname = "_" + layer
    #     publish_name = self.get_publish_name(settings, item).replace(rawversion, newname)
    #     item.properties["publish_name"] = publish_name
    #
    #     return publish_name

    def _copy_work_to_publish(self, settings, item):

        publish_template = item.properties.publish_template
        work_file = item.properties.path

        # by default, the path that was collected for publishing
        work_files = [item.properties.path]

        # if this is a sequence, get the attached files
        if "sequence_paths" in item.properties:
            work_files = item.properties.get("sequence_paths", [])
            self.logger.debug("work_files = %s", work_files)
            if not work_files:
                self.logger.warning(
                    "Sequence publish without a list of files. Publishing "
                    "the sequence path in place: %s" % (item.properties.path,)
                )
                return

        # work_fields = work_template.get_fields(work_file)
        work_fields = item.properties["work_fields"]
        work_fields["frame_num"] = int(work_files[0].split(".")[-2])
        missing_keys = publish_template.missing_keys(work_fields)

        if missing_keys:
            self.logger.warning(
                "Work file '%s' missing keys required for the publish "
                "template: %s" % (work_file, missing_keys)
            )


        publish_file = publish_template.apply_fields(work_fields)

        publish_folder = os.path.dirname(publish_file)
        ensure_folder_exists(os.path.dirname(publish_folder))
        # workFileNorm = os.path.normpath(work_file)
        # publishFileNorm = os.path.normpath(publish_file)
        try:
            os.rename(os.path.normpath(os.path.dirname(work_files[0])), publish_folder)
        except Exception:
            raise Exception(
                "Failed to move work file from '%s' to '%s'.\n%s"
                % (work_file, publish_file, traceback.format_exc())
            )

        self.logger.debug(
            "Moved work file '%s' to publish file '%s'."
            % (work_file, publish_file)
        )

        # # ---- copy the work files to the publish location
        # for work_file in work_files:
        #
        #     # if not work_template.validate(work_file):
        #     #     self.logger.warning(
        #     #         "Work file '%s' did not match work template '%s'. "
        #     #         "Publishing in place." % (work_file, work_template)
        #     #     )
        #     #     return
        #
        #     # work_fields = work_template.get_fields(work_file)
        #     work_fields = item.properties["work_fields"]
        #     work_fields["frame_num"] = int(work_file.split(".")[-2])
        #
        #     missing_keys = publish_template.missing_keys(work_fields)
        #
        #     if missing_keys:
        #         self.logger.warning(
        #             "Work file '%s' missing keys required for the publish "
        #             "template: %s" % (work_file, missing_keys)
        #         )
        #         continue
        #
        #     publish_file = publish_template.apply_fields(work_fields)
        #
        #     # copy the file
        #     try:
        #         self.logger.debug("Copying %s --> %s", work_file, publish_file)
        #         publish_folder = os.path.dirname(publish_file)
        #         ensure_folder_exists(publish_folder)
        #         workFileNorm = os.path.normpath(work_file)
        #         publishFileNorm = os.path.normpath(publish_file)
        #         os.rename(workFileNorm, publishFileNorm)
        #     except Exception:
        #         raise Exception(
        #             "Failed to move work file from '%s' to '%s'.\n%s"
        #             % (work_file, publish_file, traceback.format_exc())
        #         )
        #
        #     self.logger.debug(
        #         "Moved work file '%s' to publish file '%s'."
        #         % (work_file, publish_file)
        #     )

        # # copy the file
        # try:
        #     publish_folder = os.path.dirname(publish_file)
        #     ensure_folder_exists(publish_folder)
        #     workFileNorm = os.path.normpath(work_file)
        #     publishFileNorm = os.path.normpath(publish_file)
        #     print (workFileNorm)
        #     os.rename(workFileNorm, publishFileNorm)
        # except Exception:
        #     raise Exception(
        #         "Failed to move work file from '%s' to '%s'.\n%s"
        #         % (work_file, publish_file, traceback.format_exc())
        #     )
        #
        # self.logger.debug(
        #     "Copied work file '%s' to publish file '%s'." % (work_file, publish_file)
        # )

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

        work_template = item.parent.properties.get("work_template")
        dailies_template = self.get_dailies_template(settings, item)



        work_fields = []
        dailies_path = None

        # We need both work and publish template to be defined for template
        # support to be enabled.
        if work_template and dailies_template:

            if work_template.validate(path):
                work_fields = work_template.get_fields(path)
                work_fields["maya.layer_name"] = item.properties["maya.layer_name"]

                if platform.system() == 'Windows':
                    work_fields["extension"] = "avi"
                else:
                    work_fields["extension"] = "mov"

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



def _session_path():
    """
    Return the path to the current session
    :return:
    """
    path = cmds.file(query=True, sn=True)

    if path is not None:
        path = six.ensure_str(path)

    return path