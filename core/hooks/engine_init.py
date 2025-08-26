# Copyright (c) 2018 Shotgun Software Inc.
#
# CONFIDENTIAL AND PROPRIETARY
#
# This work is provided "AS IS" and subject to the Shotgun Pipeline Toolkit
# Source Code License included in this distribution package. See LICENSE.
# By accessing, using, copying or modifying this work you indicate your
# agreement to the Shotgun Pipeline Toolkit Source Code License. All rights
# not expressly granted therein are reserved by Shotgun Software Inc.

"""
Hook that gets executed every time an engine has been fully initialized.
"""

from tank import Hook


class EngineInit(Hook):
    def execute(self, engine, **kwargs):
        """
        Executed when a Toolkit engine has been fully initialized.

        At this point, all apps and frameworks have been loaded,
        and the engine is fully operational.

        The default implementation does nothing.

        :param engine: Engine that has been initialized.
        :type engine: :class:`~sgtk.platform.Engine`
        """
        if engine.name == "tk-maya":
            def SetResolution(self):
                import maya.cmds as cmds
                import maya.mel as mel
                import sgtk
                engine = sgtk.platform.current_engine()
                sg = engine.shotgun
                context = engine.context.entity
                shot = sg.find_one(context['type'], [['id', 'is', context['id']]], ['sg_width', 'sg_height'])
                if shot['sg_width'] != None:
                    pAx = maya.cmds.getAttr("defaultResolution.pixelAspect")
                    pAr = maya.cmds.getAttr("defaultResolution.deviceAspectRatio")
                    maya.cmds.setAttr("defaultResolution.aspectLock", 0)
                    maya.cmds.setAttr("defaultResolution.width", shot['sg_width'])
                    maya.cmds.setAttr("defaultResolution.height", shot['sg_height'])
                    maya.cmds.setAttr("defaultResolution.pixelAspect", pAx)
                    maya.cmds.setAttr("defaultResolution.deviceAspectRatio", pAr)
                    maya.cmds.setAttr("defaultResolution.aspectLock", 1)
                    texto = "Render settings resolution changed to: " + str(shot['sg_width']) + "x" + str(shot['sg_height'])
                    cmds.confirmDialog(title="Change status", message=texto)
                else:
                    texto = "Resolution fields could not be found in Shotgun"
                    cmds.confirmDialog(title="Change status", message=texto)

            # first, set up our callback, calling out to a method inside the app module contained
            # in the python folder of the app
            menu_callback = lambda: SetResolution(self)

            # now register the command with the engine
            engine.register_command("Set Shot Resolution", menu_callback)
        pass