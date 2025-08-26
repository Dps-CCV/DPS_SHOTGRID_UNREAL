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
This hook gets executed before and after the context changes in Toolkit.
"""

from tank import get_hook_baseclass
import os
import sgtk



class ContextChange(get_hook_baseclass()):
    """
    - If an engine **starts up**, the ``current_context`` passed to the hook
      methods will be ``None`` and the ``next_context`` parameter will be set
      to the context that the engine is starting in.

    - If an engine is being **reloaded**, in the context of an engine restart
      for example, the ``current_context`` and ``next_context`` will usually be
      the same.

    - If a **context switch** is requested, for example when a user switches
      from project to shot mode in Nuke Studio, ``current_context`` and ``next_context``
      will contain two different context.

    .. note::

       These hooks are called whenever the context is being set in Toolkit. It is
       possible that the new context will be the same as the old context. If
       you want to trigger some behavior only when the new one is different
       from the old one, you'll need to compare the two arguments using the
       ``!=`` operator.
    """

    def pre_context_change(self, current_context, next_context):
        """
        Executed before the context has changed.

        The default implementation does nothing.

        :param current_context: The context of the engine.
        :type current_context: :class:`~sgtk.Context`
        :param next_context: The context the engine is switching to.
        :type next_context: :class:`~sgtk.Context`
        """
        pass

    def post_context_change(self, previous_context, current_context):

        """
        Executed after the context has changed.

        The default implementation does nothing.

        :param previous_context: The previous context of the engine.
        :type previous_context: :class:`~sgtk.Context`
        :param current_context: The current context of the engine.
        :type current_context: :class:`~sgtk.Context`
        """
        from sgtk.platform import current_engine
        engine = current_engine()
        try:
            os.environ["PROJECT"] = str(current_context.project["name"])
            self.logger.info("Environment variable PROJECT changed to %s", str(current_context.project["name"]))
            arnold_plugin_path = os.path.join(
                os.environ["PROJECT_PATH"], "CONFIG", "MAYA", "ARNOLD_SHADERS"
            )
            os.environ["ARNOLD_PLUGIN_PATH"] += os.pathsep + arnold_plugin_path
            if current_context.entity:
                current_engine = sgtk.platform.current_engine()
                os.environ['SHOTGUN_TASK_TYPE'] = str(current_engine.context.task['type'])
                os.environ['SHOTGUN_TASK_ID'] = str(current_engine.context.task['id'])
                os.environ['SHOTGUN_ENTITY_TYPE'] = str(current_engine.context.task['type'])
                os.environ['SHOTGUN_ENTITY_ID'] = str(current_engine.context.task['id'])

                if current_context.entity["type"] == 'Shot':
                    os.environ["SHOT"] = current_context.entity["name"]
                    tk = current_engine.sgtk
                    template = tk.templates["shot_root"]
                    fields = current_context.as_template_fields(template)
                    shot_path = template.apply_fields(fields)
                    os.environ["SHOT_FOLDER"] = str(shot_path)
                    self.logger.info("Environment variable SHOT changed to %s", str(current_context.entity["name"]))
                    self.logger.info("Environment variable SHOT_FOLDER changed to %s", str(shot_path))

                    seq = current_context.sgtk.shotgun.find_one("Shot", [["id", "is", current_context.entity["id"]]], ["project.Project.sg_format", "sg_sequence", "sg_efecto_a_hacer", "sg_method", "sg_source_clip", "sg_source_clip.SourceClip.sg_lmt"])
                    os.environ["SEQ"] = str(seq["sg_sequence"]["name"])
                    os.environ["DESCRIPTION"] = str(seq["sg_efecto_a_hacer"])
                    methods = ''
                    for i in seq["sg_method"]:
                        methods += ' ' + i['name'] + ','
                    os.environ["METHODS"] = methods
                    self.logger.info("Environment variable SEQ changed to %s", str(seq["sg_sequence"]["name"]))


                    clip = seq


                    ###Fill clip and lmt settings if we have those values. If we don't we set empty variables because OCIO configs don't work if there are no env variables created
                    if clip["sg_source_clip"]:
                        os.environ["CLIP"] = str(clip["sg_source_clip"]["name"])
                        self.logger.info("Environment variable CLIP changed to %s", str(clip["sg_source_clip"]["name"]))

                        os.environ["LMT"] = str(clip["sg_source_clip.SourceClip.sg_lmt"])
                        self.logger.info("Environment variable LMT changed to %s", str(clip["sg_source_clip"]["name"]))

                    else:
                        os.environ["CLIP"] = " "
                        os.environ["LMT"] = " "


                elif current_context.entity["type"] == 'Asset':
                    os.environ["ASSET"] = current_context.entity["name"]
                    tk = current_engine.sgtk
                    template = tk.templates["asset_root"]
                    fields = current_context.as_template_fields(template)
                    asset_path = template.apply_fields(fields)
                    os.environ["ASSET_FOLDER"] = str(shot_path)
                    self.logger.info("Environment variable ASSET_FOLDER changed to %s", str(asset_path))
                    self.logger.info("Environment variable ASSET changed to %s", str(current_context.entity["name"]))

                if current_engine._Engine__engine_instance_name == 'tk-nuke':
                    import nuke
                    # reloadConfig = nuke.root().knob('reloadConfig')
                    # reloadConfig.execute()
                    # self.logger.info("Reload Config %s", str(current_engine._Engine__engine_instance_name))
                    # ####DPS Write Shortcuts
                    # # # CUSTOM SHORTCUTS
                    # write_node_item = nuke.menu('Nodes').findItem("Image/Write")
                    # write_node_item.setShortcut("")
                    #
                    # nuke.menu('Nodes').findItem("ShotGrid").findItem("Exr 16bits [Shotgun]").setShortcut('w')
                    # nuke.menu('Nodes').findItem("ShotGrid").findItem("PRECOMP [Shotgun]").setShortcut('Alt+w')
                    # nuke.menu('Nodes').findItem("ShotGrid").findItem("TECH_PRECOMP [Shotgun]").setShortcut('Alt+j')



                elif current_engine._Engine__engine_instance_name == 'tk-houdini':
                    import hou
                    hou.Color.reloadOCIO()
                    self.logger.info("Reload Config %s", str(current_engine._Engine__engine_instance_name))

                elif current_engine._Engine__engine_instance_name == 'tk-maya':
                    import maya.cmds as cmds
                    import maya.mel as mel
                    mel.eval("colorManagementPrefs -refresh;")

                    def SetResolution(self):
                        import maya.cmds as cmds
                        import maya.mel as mel
                        import sgtk
                        engine = sgtk.platform.current_engine()
                        sg = engine.shotgun
                        context = engine.context.entity
                        shot = sg.find_one(context['type'], [['id', 'is', context['id']]],
                                           ['sg_width', 'sg_height'])
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
                    try:
                        menu_callback = lambda: SetResolution(self)
                    except Exception as e:
                        self.logger.info("Reload Config %s", str(current_engine._Engine__engine_instance_name))

                    # now register the command with the engine
                    engine.register_command("Set Shot Resolution", menu_callback)


        except:
            pass
        pass
