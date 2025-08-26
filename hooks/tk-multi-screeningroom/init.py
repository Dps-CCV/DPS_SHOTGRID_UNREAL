# Copyright (c) 2015 Shotgun Software Inc.
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

HookBaseClass = sgtk.get_hook_baseclass()


class ScreeningroomInit(HookBaseClass):
    """
    Controls the initialization in and around screening room
    """

    def before_rv_launch(self, path):
        """
        Executed before RV is being launched

        :param path: The path to the RV that is about to be launched
        :type path: str
        """

        # accessing the current context (current shot, etc)
        # can be done via the parent object
        #
        # > app = self.parent
        # > current_entity = app.context.entity

        # you can set environment variables like this:
        # os.environ["MY_SETTING"] = "foo bar"

        ## Acceder al contexto
        rv_launch = self.parent
        current_context = rv_launch.context

        ## Definir variables generales para su posible uso posterior dentro de las aplicaciones
        os.environ["PROJECT"] = str(current_context.project["name"])
        project_path = self.parent.tank.roots.get("primary")
        os.environ["PROJECT_PATH"] = project_path
        rawMount = os.path.normpath(project_path)
        Mount = rawMount.split(os.sep)[0]
        os.environ["MOUNT"] = Mount
        ocio_path = os.path.join(
            project_path, "CONFIG", "COLOR", "ACES", "studio-config-v1.0.0_aces-v1.3_ocio-v2.1.ocio"
        )
        os.environ["OCIO"] = ocio_path

        # filters = [["code" "is" ]]
        getColor = sgtk.platform.current_engine().shotgun.find_one("Project", [
            ["name", "is", str(current_context.project["name"])]], ["sg_espacio___color"])

        os.environ["PROJECTCOLORSPACE"] = str(getColor["sg_espacio___color"])

        getMask = sgtk.platform.current_engine().shotgun.find_one("Project", [
            ["name", "is", str(current_context.project["name"])]], ["sg_formato___ratio"])

        os.environ["PROJECTMASK"] = str(getMask["sg_formato___ratio"])

        os.environ["RV_SUPPORT_PATH"] = os.path.join(project_path, "CONFIG", "COLOR", "RV")
