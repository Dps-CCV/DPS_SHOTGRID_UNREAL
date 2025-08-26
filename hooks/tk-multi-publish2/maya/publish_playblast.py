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

import sgtk
from sgtk.util.filesystem import copy_file, ensure_folder_exists
from tank_vendor import six

HookBaseClass = sgtk.get_hook_baseclass()


class PlayblastPublishPlugin(HookBaseClass):
    """
    Plugin for creating publishing playblasts
    """

    @property
    def settings(self):

        # inherit the settings from the base publish plugin
        plugin_settings = super(PlayblastPublishPlugin, self).settings or {}

        # settings specific to this class
        maya_playblast_publish_settings = {
            "Publish Template": {
                "type": "template",
                "default": None,
                "description": "Template path for published playblast. Should"
                "correspond to a template defined in "
                "templates.yml.",
            },
        }

        # update the base settings
        plugin_settings.update(maya_playblast_publish_settings)

        return plugin_settings

    @property
    def item_filters(self):
        """
        List of item types that this plugin is interested in.

        Only items matching entries in this list will be presented to the
        accept() method. Strings can contain glob patters such as *, for example
        ["maya.*", "file.maya"]
        """

        return ["maya.session.playblast", "maya.session.playblastSeq"]

    def accept(self, settings, item):
        # self.logger.debug("PlayblastPublishPlugin.accept")

        # ensure a camera file template is available on the parent item
        work_template = item.parent.properties.get("work_template")
        if not work_template:
            self.logger.debug(
                "A work template is required for the session item in order to "
                "publish a playblast. Not accepting session playblast item."
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
                "session playblast item. Not accepting the item."
            )
            return {"accepted": False}

        return super(PlayblastPublishPlugin, self).accept(settings, item)

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

        # ensure the fields work for the publish template
        missing_keys = publish_template.missing_keys(work_fields)
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
        # item.properties["publish_path"] = publish_path
        if "sequence_paths" in item.properties:
            item.properties["publish_path"] = publish_path.replace("6969", "####")
        else:
            item.properties["publish_path"] = publish_path.replace(".6969", "")
        item.properties["work_fields"] = work_fields
        item.properties["publish_template"] = publish_template

        # use the work file's version number when publishing
        if "version" in work_fields:
            item.properties["publish_version"] = work_fields["version"]

        return super(PlayblastPublishPlugin, self).validate(settings, item)

    def get_publish_path(self, settings, item):

        return item.properties.get("publish_path")

    def _copy_work_to_publish(self, settings, item):

        publish_file = item.properties.publish_path
        work_file = item.properties.path

        # copy the file
        if "sequence_paths" in item.properties:
            work_files = item.properties.get("sequence_paths", [])
            self.logger.debug("work_files = %s", work_files)
            if not work_files:
                self.logger.warning(
                    "Sequence publish without a list of files. Publishing "
                    "the sequence path in place: %s" % (item.properties.path,)
                )
                return
            for work_file in work_files:
                # get the configured work file template
                work_fields = item.properties["work_fields"]
                work_template = item.parent.properties.get("work_template")
                publish_template = item.properties.get("publish_template")

                # get the current scene path and extract fields from it using the work


                work_fields["frame_num"] = int(work_file.split(".")[-2])
                publish_file = publish_template.apply_fields(work_fields)
                try:
                    publish_folder = os.path.dirname(publish_file)
                    ensure_folder_exists(publish_folder)
                    copy_file(work_file, publish_file)
                    os.remove(work_file)

                except Exception:
                    raise Exception(
                        "Failed to copy work file from '%s' to '%s'.\n%s"
                        % (work_file, publish_file, traceback.format_exc())
                    )
        else:
            try:
                publish_folder = os.path.dirname(publish_file)
                ensure_folder_exists(publish_folder)
                copy_file(work_file, publish_file)
                os.remove(work_file)

            except Exception:
                raise Exception(
                    "Failed to copy work file from '%s' to '%s'.\n%s"
                    % (work_file, publish_file, traceback.format_exc())
                )

            self.logger.debug(
                "Copied work file '%s' to publish file '%s'." % (work_file, publish_file)
            )


def _session_path():
    """
    Return the path to the current session
    :return:
    """
    path = cmds.file(query=True, sn=True)

    if path is not None:
        path = six.ensure_str(path)

    return path