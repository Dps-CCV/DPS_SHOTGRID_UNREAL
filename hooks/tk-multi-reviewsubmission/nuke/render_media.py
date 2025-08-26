# Copyright (c) 2019 Shotgun Software Inc.
#
# CONFIDENTIAL AND PROPRIETARY
#
# This work is provided "AS IS" and subject to the Shotgun Pipeline Toolkit
# Source Code License included in this distribution package. See LICENSE.
# By accessing, using, copying or modifying this work you indicate your
# agreement to the Shotgun Pipeline Toolkit Source Code License. All rights
# not expressly granted therein are reserved by Shotgun Software Inc.

import sgtk
import os
import sys
import nuke
import shutil
from datetime import date
import time

from tank_vendor import six

HookBaseClass = sgtk.get_hook_baseclass()


class RenderMedia(HookBaseClass):
    """
    RenderMedia hook implementation for the tk-nuke engine.
    """

    def __init__(self, *args, **kwargs):
        super(RenderMedia, self).__init__(*args, **kwargs)

        self.__app = self.parent

        ###Get Burnin nuke script file from CONFIG/NUKE folder
        project_path = self.parent.tank.roots.get("primary")
        nuke_environ_path = os.path.join(
            project_path, "CONFIG/NUKE"
        )
        self._burnin_nk = os.path.join(
            nuke_environ_path, "burnin.nk"
        )
        self._font = os.path.join(
            self.__app.disk_location, "resources", "liberationsans_regular.ttf"
        )
        # If the slate_logo supplied was an empty string, the result of getting
        # the setting will be the config folder which is invalid so catch that
        # and make our logo path an empty string which Nuke won't have issues with.
        self._logo = None
        if os.path.isfile(self.__app.get_setting("slate_logo", "")):
            self._logo = self.__app.get_setting("slate_logo", "")
        else:
            self._logo = ""

        # now transform paths to be forward slashes, otherwise it wont work on windows.
        if sgtk.util.is_windows():
            self._font = self._font.replace(os.sep, "/")
            self._logo = self._logo.replace(os.sep, "/")
            self._burnin_nk = self._burnin_nk.replace(os.sep, "/")

    def render(
        self,
        input_path,
        output_path,
        width,
        height,
        first_frame,
        last_frame,
        version,
        name,
        color_space,
    ):
        """
        Use Nuke to render a movie.

        :param str input_path:      Path to the input frames for the movie
        :param str output_path:     Path to the output movie that will be rendered
        :param int width:           Width of the output movie
        :param int height:          Height of the output movie
        :param int first_frame:     The first frame of the sequence of frames.
        :param int last_frame:      The last frame of the sequence of frames.
        :param str version:         Version number to use for the output movie slate and burn-in
        :param str name:            Name to use in the slate for the output movie
        :param str color_space:     Colorspace of the input frames

        :returns:               Location of the rendered media
        :rtype:                 str
        """
        output_node = None
        ctx = self.__app.context

        if os.environ['PROJECT'] == 'AVATAR_GLASGOW':
            width = 1080
            height = 1920

        # create group where everything happens
        group = nuke.nodes.Group()

        # now operate inside this group
        group.begin()
        try:
            # create read node
            read = nuke.nodes.Read(name="source", file=input_path.replace(os.sep, "/"))
            read["on_error"].setValue("black")
            read["first"].setValue(first_frame)
            read["last"].setValue(last_frame)
            read['reload'].execute()

            ## Disable localization to ensure that frames are rendered without problems
            read["localizationPolicy"].setValue('off')
            #read.forceUpdateLocalization()
            if color_space:
                read["colorspace"].setValue(color_space)
            if "_IPL_" in read['file'].value():
                read["colorspace"].setValue('Output - Rec.709')
            elif "_IMP_" in read['file'].value():
                read["colorspace"].setValue('ACEScg')
            elif "_ALPHA_" in read['file'].value():
                read["colorspace"].setValue('Utility - Raw')
            elif "_TECH_PRECOMP_" in read['file'].value():
                read["colorspace"].setValue('ACEScg')
            else:
                projectColorspace = os.environ['PROJECTCOLORSPACE']
                read["colorspace"].setValue(projectColorspace)

            # now create the slate/burnin node
            burn = nuke.nodePaste(self._burnin_nk)
            burn.setInput(0, read)

            # set the fonts for all text fields
            burn.node("top_left_text")["font"].setValue(self._font)
            burn.node("top_right_text")["font"].setValue(self._font)
            burn.node("bottom_left_text")["font"].setValue(self._font)
            burn.node("framecounter")["font"].setValue(self._font)
            burn.node("slate_info")["font"].setValue(self._font)

            # add the logo
            burn.node("logo")["file"].setValue(self._logo)

            # format the burnins
            version_padding_format = "%%0%dd" % self.__app.get_setting(
                "version_number_padding"
            )
            version_str = version_padding_format % version

            if ctx.task:
                version_label = "%s, v%s" % (ctx.task["name"], version_str)
            elif ctx.step:
                version_label = "%s, v%s" % (ctx.step["name"], version_str)
            else:
                version_label = "v%s" % version_str

            burn.node("top_left_text")["message"].setValue(ctx.project["name"])
            burn.node("top_right_text")["message"].setValue(ctx.entity["name"])
            burn.node("bottom_left_text")["message"].setValue(version_label)

            # and the slate
            slate_str = "Project: %s\n" % ctx.project["name"]
            slate_str += "%s: %s\n" % (ctx.entity["type"], ctx.entity["name"])
            slate_str += "Name: %s\n" % name.capitalize()
            slate_str += "Version: %s\n" % version_str

            if ctx.task:
                slate_str += "Task: %s\n" % ctx.task["name"]
            elif ctx.step:
                slate_str += "Step: %s\n" % ctx.step["name"]

            slate_str += "Frames: %s - %s\n" % (first_frame, last_frame)

            burn.node("slate_info")["message"].setValue(slate_str)

            # create a scale node
            scale = self.__create_scale_node(width, height)
            scale.setInput(0, burn)

            # Create the output node
            output_node = self.__create_output_node(output_path)
            output_node.setInput(0, scale)

            ###Set Write colorspace output to render ACES - Output - Rec 709
            if os.environ['PROJECT'] == 'AVATAR_GLASGOW':
                output_node.knob('colorspace').setValue('sRGB')
            else:
                output_node.knob('colorspace').setValue('Output - Rec.709')
            output_node.knob('create_directories').setValue(True)



        finally:
            group.end()

        if output_node:
            serverPath = output_node.knob('file').evaluate()
            try:
                farmkey = os.environ['ON_FARM']
                farm = True
            except:
                farm = False
            if farm is not True:
                local = nuke.toNode("preferences").knob("localCachePath").evaluate()[:-1]
                localPath = serverPath.replace(os.environ['MOUNT'], local)
                output_node.knob('file').setValue(localPath)


            # Make sure the output folder exists
            output_folder = os.path.dirname(output_path)
            self.__app.ensure_folder_exists(output_folder)
            read['reload'].execute()
            time.sleep(5)
            nuke.executeMultiple(
                    [output_node], ([first_frame - 1, last_frame, 1],), [nuke.views()[0]]
                )
            if farm is not True:
                shutil.copy(localPath, serverPath)
                os.remove(localPath)
                output_node.knob('file').setValue(serverPath)


        # Cleanup after ourselves
        nuke.delete(group)

        return output_path

    def __create_scale_node(self, width, height):
        """
        Create the Nuke scale node to resize the content.

        :param int width:           Width of the output movie
        :param int height:          Height of the output movie

        :returns:               Pre-configured Reformat node
        :rtype:                 Nuke node
        """
        scale = nuke.nodes.Reformat()
        scale["type"].setValue("to box")
        scale["box_width"].setValue(width)
        scale["box_height"].setValue(height)
        scale["resize"].setValue("width")
        scale["box_fixed"].setValue(True)
        scale["center"].setValue(True)
        scale["black_outside"].setValue(True)
        return scale

    def __create_output_node(self, path):
        """
        Create the Nuke output node for the movie.

        :param str path:           Path of the output movie

        :returns:               Pre-configured Write node
        :rtype:                 Nuke node
        """
        # get the Write node settings we'll use for generating the Quicktime
        wn_settings = self.__get_quicktime_settings()

        node = nuke.nodes.Write(file_type=wn_settings.get("file_type"))

        # apply any additional knob settings provided by the hook. Now that the knob has been
        # created, we can be sure specific file_type settings will be valid.
        for knob_name, knob_value in wn_settings.items():
            if knob_name != "file_type":
                node.knob(knob_name).setValue(knob_value)

        # DPS Get audio Node to export with the quicktime file
        if nuke.allNodes("AudioRead", nuke.root()):
            if nuke.toNode("AudioRead1"):
                if nuke.toNode("AudioRead1")['file'].value() != "":
                    if os.path.isfile(nuke.toNode("AudioRead1")['file'].value()):
                        node["mov64_audiofile"].setValue(nuke.toNode("AudioRead1")['file'].value())
                    else:
                        self.__app.log_info("No valid audio file found in AudioRead node")
                else:
                    self.__app.log_info("No valid audio file found in AudioRead node")
            else:
                self.__app.log_info("No AudioRead1 found in the script, check if existing AudioRead node is correctly named as AudioRead1")
        else:
            self.__app.log_info("No audio found in the script")

        # Don't fail if we're in proxy mode. The default Nuke publish will fail if
        # you try and publish while in proxy mode. But in earlier versions of
        # tk-multi-publish (< v0.6.9) if there is no proxy template set, it falls
        # back on the full-res version and will succeed. This handles that case
        # and any custom cases where you may want to send your proxy render to
        # screening room.
        root_node = nuke.root()
        is_proxy = root_node["proxy"].value()
        if is_proxy:
            self.__app.log_info("Proxy mode is ON. Rendering proxy.")
            node["proxy"].setValue(path.replace(os.sep, "/"))
        else:
            node["file"].setValue(path.replace(os.sep, "/"))


        return node

    def __get_quicktime_settings(self, **kwargs):
        """
        Allows modifying default codec settings for Quicktime generation.
        Returns a dictionary of settings to be used for the Write Node that generates
        the Quicktime in Nuke.

        :returns:               Codec settings
        :rtype:                 dict
        """
        settings = {}
        if sgtk.util.is_windows() or sgtk.util.is_macos():
            settings["file_type"] = "mov"
            if nuke.NUKE_VERSION_MAJOR >= 9:
                # Nuke 9.0v1 changed the codec knob name to meta_codec and added an encoder knob
                # (which defaults to the new mov64 encoder/decoder).
                settings["meta_codec"] = "jpeg"
                settings["mov64_quality_max"] = "3"
            else:
                settings["codec"] = "jpeg"

        elif sgtk.util.is_linux():
            if nuke.NUKE_VERSION_MAJOR >= 9:
                # Nuke 9.0v1 removed ffmpeg and replaced it with the mov64 writer
                # http://help.thefoundry.co.uk/nuke/9.0/#appendices/appendixc/supported_file_formats.html
                settings["file_type"] = "mov64"
                settings["mov64_codec"] = "jpeg"
                settings["mov64_quality_max"] = "3"
            else:
                # the 'codec' knob name was changed to 'format' in Nuke 7.0
                settings["file_type"] = "ffmpeg"
                settings["format"] = "MOV format (mov)"

        return settings
