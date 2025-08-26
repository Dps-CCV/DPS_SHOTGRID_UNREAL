# Copyright (c) 2013 Shotgun Software Inc.
#
# CONFIDENTIAL AND PROPRIETARY
#
# This work is provided "AS IS" and subject to the Shotgun Pipeline Toolkit
# Source Code License included in this distribution package. See LICENSE.
# By accessing, using, copying or modifying this work you indicate your
# agreement to the Shotgun Pipeline Toolkit Source Code License. All rights
# not expressly granted therein are reserved by Shotgun Software Inc.

import sgtk
import maya.cmds as cmds
import os
import glob
import re
import maya.OpenMaya as OpenMaya

HookBaseClass = sgtk.get_hook_baseclass()


class BreakdownSceneOperations(HookBaseClass):
    """
    Breakdown operations for Maya.

    This implementation handles detection of maya references and file texture nodes.
    """

    def scan_scene(self):
        """
        The scan scene method is executed once at startup and its purpose is
        to analyze the current scene and return a list of references that are
        to be potentially operated on.

        The return data structure is a list of dictionaries. Each scene reference
        that is returned should be represented by a dictionary with three keys:

        - "node": The name of the 'node' that is to be operated on. Most DCCs have
          a concept of a node, path or some other way to address a particular
          object in the scene.
        - "type": The object type that this is. This is later passed to the
          update method so that it knows how to handle the object.
        - "path": Path on disk to the referenced object.

        Toolkit will scan the list of items, see if any of the objects matches
        any templates and try to determine if there is a more recent version
        available. Any such versions are then displayed in the UI as out of date.
        """

        refs = []

        # first let's look at maya references
        for ref in cmds.file(q=True, reference=True):
        # for ref in cmds.ls(references=True):
            node_name = cmds.referenceQuery(ref, referenceNode=True)

            # get the path and make it platform dependent
            # (maya uses C:/style/paths)
            maya_path = cmds.referenceQuery(
                ref, filename=True, withoutCopyNumber=True
            ).replace("/", os.path.sep)
            refs.append(
                {"node_name": node_name, "node_type": "reference", "path": maya_path}
            )

        # now look at file texture nodes
        for file_node in cmds.ls(l=True, type="file"):
            # ensure this is actually part of this scene and not referenced
            if cmds.referenceQuery(file_node, isNodeReferenced=True):
                # this is embedded in another reference, so don't include it in the breakdown
                continue

            # get path and make it platform dependent (maya uses C:/style/paths)
            path = cmds.getAttr("%s.fileTextureName" % file_node).replace(
                "/", os.path.sep
            )

            refs.append({"node_name": file_node, "node_type": "file", "path": path})

        # now look at alembic nodes
        for alembic_node in cmds.ls(l=True, type="AlembicNode"):
            # ensure this is actually part of this scene and not referenced
            if cmds.referenceQuery(alembic_node, isNodeReferenced=True):
                # this is embedded in another reference, so don't include it in the breakdown
                continue

            # get path and make it platform dependent (maya uses C:/style/paths)
            path = cmds.getAttr("%s.abc_File" % alembic_node).replace(
                "/", os.path.sep
            )

            refs.append({"node_name": alembic_node, "node_type": "AlembicNode", "path": path})

        # now look at imagePlane nodes
        for imagePlane_node in cmds.ls(l=True, type="imagePlane"):
            # ensure this is actually part of this scene and not referenced
            if cmds.referenceQuery(imagePlane_node, isNodeReferenced=True):
                # this is embedded in another reference, so don't include it in the breakdown
                continue

            # get path and make it platform dependent (maya uses C:/style/paths)
            path = cmds.getAttr("%s.imageName" % imagePlane_node).replace(
                "/", os.path.sep
            )

            refs.append({"node_name": imagePlane_node, "node_type": "imagePlane", "path": path})

        # now look at StandIns nodes
        for standIn in cmds.ls(l=True, type="aiStandIn"):
            # ensure this is actually part of this scene and not referenced
            if cmds.referenceQuery(standIn, isNodeReferenced=True):
                # this is embedded in another reference, so don't include it in the breakdown
                continue

            # get path and make it platform dependent (maya uses C:/style/paths)
            path = cmds.getAttr("%s.dso" % standIn).replace(
                "/", os.path.sep
            )

            refs.append({"node_name": standIn, "node_type": "standIn", "path": path})

        # now look at Volume nodes
        for volume in cmds.ls(l=True, type="aiVolume"):
            # ensure this is actually part of this scene and not referenced
            if cmds.referenceQuery(volume, isNodeReferenced=True):
                # this is embedded in another reference, so don't include it in the breakdown
                continue

            # get path and make it platform dependent (maya uses C:/style/paths)
            path = cmds.getAttr("%s.filename" % volume).replace(
                "/", os.path.sep
            )

            refs.append({"node_name": volume, "node_type": "volume", "path": path})

        for audio in cmds.ls(l=True, type="audio"):
            # ensure this is actually part of this scene and not referenced
            if cmds.referenceQuery(audio, isNodeReferenced=True):
                # this is embedded in another reference, so don't include it in the breakdown
                continue

            # get path and make it platform dependent (maya uses C:/style/paths)
            path = cmds.getAttr("%s.filename" % audio).replace(
                "/", os.path.sep
            )

            refs.append({"node_name": audio, "node_type": "audio", "path": path})

        return refs

    def update(self, item):
        """
        Perform replacements given a number of scene items passed from the app.

        Once a selection has been performed in the main UI and the user clicks
        the update button, this method is called.

        The items parameter is a list of dictionaries on the same form as was
        generated by the scan_scene hook above. The path key now holds
        the that each node should be updated *to* rather than the current path.
        """



        node_name = item["node_name"]
        node_type = item["node_type"]
        new_path = item["path"]

        if node_type == "reference":
            # maya reference
            self.logger.debug(
                "Maya Reference %s: Updating to version %s" % (node_name, new_path)
            )
            cmds.file(new_path, loadReference=node_name)

        elif node_type == "file":
            # file texture node
            self.logger.debug(
                "File Texture %s: Updating to version %s" % (node_name, new_path)
            )
            file_name = cmds.getAttr("%s.fileTextureName" % node_name)
            cmds.setAttr("%s.fileTextureName" % node_name, new_path, type="string")

        elif node_type == "AlembicNode":
            # alembic node
            self.logger.debug(
                "Alembic node %s: Updating to version %s" % (node_name, new_path)
            )
            file_name = cmds.getAttr("%s.abc_File" % node_name)
            cmds.setAttr("%s.abc_File" % node_name, new_path, type="string")

        elif node_type == "imagePlane":
            # imagePlane node
            self.logger.debug(
                "ImagePlane node %s: Updating to version %s" % (node_name, new_path)
            )
            file_name = cmds.getAttr("%s.imageName" % node_name)

            # replace any %0#d format string with a glob character. then just find
            # an existing frame to use. example %04d => *
            has_frame_spec = False
            frame_pattern = re.compile("(%0\dd)")
            frame_match = re.search(frame_pattern, new_path)
            if frame_match:
                has_frame_spec = True
                frame_spec = frame_match.group(1)
                glob_path = new_path.replace(frame_spec, "*")
                frame_files = glob.glob(glob_path)
                if frame_files:
                    new_path = frame_files[0]

            cmds.setAttr("%s.imageName" % node_name, new_path, type="string")

        elif node_type == "standIn":
            # standIn node
            self.logger.debug(
                "StandIn node %s: Updating to version %s" % (node_name, new_path)
            )
            file_name = cmds.getAttr("%s.dso" % node_name)
            cmds.setAttr("%s.dso" % node_name, new_path, type="string")

        elif node_type == "volume":
            # standIn node
            self.logger.debug(
                "Volume node %s: Updating to version %s" % (node_name, new_path)
            )
            file_name = cmds.getAttr("%s.filename" % node_name)
            cmds.setAttr("%s.filename" % node_name, new_path, type="string")

        elif node_type == "audio":
            # audio node
            self.logger.debug(
                "Audio node %s: Updating to version %s" % (node_name, new_path)
            )
            file_name = cmds.getAttr("%s.filename" % node_name)
            cmds.setAttr("%s.filename" % node_name, new_path, type="string")
            link = sg_publish_data['entity']['id']
            offset = sgtk.platform.current_engine().shotgun.find_one('Shot', [['id', 'is', link]], ['sg_cut_in'])
            cmds.setAttr("%s.offset" % node_name, float(offset['sg_cut_in']), type="float")
    def register_scene_change_callback(self, scene_change_callback):
        """
        Register the callback such that it is executed on a scene change event.

        This hook method is useful to reload the breakdown data when the data in the scene has
        changed.

        :param callback: The callback to register and execute on scene chagnes.
        :type callback: function
        """

        self.__callback_ids = []
        scene_events = [
            OpenMaya.MSceneMessage.kAfterCreateReference,
            OpenMaya.MSceneMessage.kAfterRemoveReference,
            OpenMaya.MSceneMessage.kAfterOpen,
            OpenMaya.MSceneMessage.kAfterNew,
        ]

        # when registering the Maya callbacks, we need to use a lambda as the addCallback method always return an
        # argument (None by default)
        # also, we are not adding these events to the maya scene watcher because this one is destroyed as soon as
        # the context is switched. So, in case we're opening a new file with the Breakdown2 app is still opened, this
        # functionality will be broken
        for ev in scene_events:
            callback_id = OpenMaya.MSceneMessage.addCallback(
                ev, lambda x: scene_change_callback()
            )
            self.__callback_ids.append(callback_id)

        # adding callbacks for file nodes as well (to handle texture nodes)
        callback_id = OpenMaya.MDGMessage.addNodeAddedCallback(
            lambda n, c: scene_change_callback(), "file"
        )
        self.__callback_ids.append(callback_id)
        callback_id = OpenMaya.MDGMessage.addNodeRemovedCallback(
            lambda n, c: scene_change_callback(), "file"
        )
        self.__callback_ids.append(callback_id)

    def unregister_scene_change_callback(self):
        """Unregister the scene change callbacks by disconnecting any signals."""

        for callback_id in self.__callback_ids:
            OpenMaya.MSceneMessage.removeCallback(callback_id)
