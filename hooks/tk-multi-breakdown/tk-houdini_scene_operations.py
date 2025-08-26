# Copyright (c) 2013 Shotgun Software Inc.
#
# CONFIDENTIAL AND PROPRIETARY
#
# This work is provided "AS IS" and subject to the Shotgun Pipeline Toolkit
# Source Code License included in this distribution package. See LICENSE.
# By accessing, using, copying or modifying this work you indicate your
# agreement to the Shotgun Pipeline Toolkit Source Code License. All rights
# not expressly granted therein are reserved by Shotgun Software Inc.

import os

import sgtk
import hou

HookBaseClass = sgtk.get_hook_baseclass()


class BreakdownSceneOperations(HookBaseClass):
    """
    Breakdown operations for Houdini.

    This implementation handles detection of alembic node paths.
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

        items = []

        # get a list of all regular alembic nodes in the file
        alembic_nodes = hou.nodeType(hou.sopNodeTypeCategory(), "alembic").instances()
        fileCop_nodes = hou.nodeType(hou.cop2NodeTypeCategory(), "file").instances()
        cam_nodes = hou.nodeType(hou.objNodeTypeCategory(), "cam").instances()
        alembicarchive_nodes = hou.nodeType(hou.objNodeTypeCategory(), "alembicarchive").instances()
        file_nodes = hou.nodeType(hou.sopNodeTypeCategory(), "file").instances()
        procedural_nodes = hou.nodeType(hou.objNodeTypeCategory(), "procedural").instances()
        include_nodes = hou.nodeType(hou.objNodeTypeCategory(), "arnold_include").instances()

        # return an item for each alembic node found. the breakdown app will check
        # the paths of each looking for a template match and a newer version.
        for alembic_node in alembic_nodes:

            file_parm = alembic_node.parm("fileName")
            file_path = os.path.normpath(file_parm.eval())

            items.append(
                {"node_name": alembic_node.path(), "node_type": "alembic", "path": file_path}
            )

        for fileCop_node in fileCop_nodes:

            file_parm = fileCop_node.parm("filename1")
            file_path = os.path.normpath(file_parm.eval())

            items.append(
                {"node_name": fileCop_node.path(), "node_type": "fileCop", "path": file_path}
            )

        for cam_node in cam_nodes:

            file_parm = cam_node.parm("vm_background")
            file_path = os.path.normpath(file_parm.eval())

            items.append(
                {"node_name": cam_node.path(), "node_type": "cam", "path": file_path}
            )

        for alembicarchive_node in alembicarchive_nodes:

            file_parm = alembicarchive_node.parm("fileName")
            file_path = os.path.normpath(file_parm.eval())

            items.append(
                {"node_name": alembicarchive_node.path(), "node_type": "alembicarchive", "path": file_path}
            )

        for file_node in file_nodes:

            file_parm = file_node.parm("file")
            file_path = os.path.normpath(file_parm.eval())

            items.append(
                {"node_name": file_node.path(), "node_type": "file", "path": file_path}
            )

        for procedural_node in procedural_nodes:

            file_parm = procedural_node.parm("ar_filename")
            file_path = os.path.normpath(file_parm.eval())

            items.append(
                {"node_name": procedural_node.path(), "node_type": "procedural", "path": file_path}
            )

        for include_node in include_nodes:
            for layer in range(1, include_node.parm("ar_includes")):
                file_parm = include_node.parm(str("ar_filename"+str(layer)))
                file_path = os.path.normpath(file_parm.eval())

                items.append(
                    {"node_name": include_node.path(), "node_type": "include", "entry": str(layer), "path": file_path}
                )

        return items

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
        path = item["path"]

        path = path.replace("\\", "/")

        # update the alembic fileName parm to the new path
        if node_type == "alembic":

            alembic_node = hou.node(node_name)
            engine.log_debug(
                "Updating alembic node '%s' to: %s" % (node_name, path)
            )
            alembic_node.parm("fileName").set(path)

        if node_type == "fileCop":

            fileCop_node = hou.node(node_name)
            engine.log_debug(
                "Updating file node '%s' to: %s" % (node_name, path)
            )
            fileCop_node.parm("fileName1").set(path)

        if node_type == "cam":

            cam_node = hou.node(node_name)
            engine.log_debug(
                "Updating cam background node '%s' to: %s" % (node_name, path)
            )
            cam_node.parm("vm_background").set(path)

        if node_type == "alembicarchive":

            alembicarchive_node = hou.node(node_name)
            engine.log_debug(
                "Updating alembicarchive node '%s' to: %s" % (node_name, path)
            )
            alembicarchive_node.parm("fileName").set(path)

        if node_type == "file":

            file_node = hou.node(node_name)
            engine.log_debug(
                "Updating file node '%s' to: %s" % (node_name, path)
            )
            file_node.parm("file").set(path)

        if node_type == "procedural":

            file_node = hou.node(node_name)
            engine.log_debug(
                "Updating procedural node '%s' to: %s" % (node_name, path)
            )
            file_node.parm("ar_filename").set(path)

        if node_type == "include":

            file_node = hou.node(node_name)
            engine.log_debug(
                "Updating arnold_include entry '%s' to: %s" % (node_name, path)
            )
            file_node.parm("ar_filename"+str(item["entry"])).set(path)
