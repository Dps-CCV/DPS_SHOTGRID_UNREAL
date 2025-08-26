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
Hook which chooses an environment file to use based on the current context.
"""

from sgtk import Hook
# import os


class PickEnvironment(Hook):
    def execute(self, context, **kwargs):
        """
        The default implementation assumes there are three environments, called shot, asset
        and project, and switches to these based on entity type.
        """
        # project = context.project
        # try:
        #     proj = self.parent.shotgun.find_one("Project", [['id', 'is', project['id']]], ['sg_format', 'sg_compression'])
        #     if proj != None:
        #         os.environ["FormExt"] = proj['sg_format']
        #         if proj['sg_format'] == 'exr':
        #             os.environ["CompressionExt"] = proj['sg_compression']
        #         else:
        #             os.environ["CompressionExt"] = proj['sg_format']
        # except:
        #     pass
        # if context.source_entity:
        #     if context.source_entity["type"] == "Version":
        #         return "version"
        #     elif context.source_entity["type"] == "PublishedFile":
        #         return "publishedfile"
        #     elif context.source_entity["type"] == "Playlist":
        #         return "playlist"
        #
        # if context.project is None:
        #     # Our context is completely empty. We're going into the site context.
        #     return "site"
        #
        # if context.entity is None:
        #     # We have a project but not an entity.
        #     return "project"
        # if context.project:
        #     return "project"
        #
        # if context.entity and context.step is None:
        #     # We have an entity but no step.
        #     if context.entity["type"] == "Shot":
        #         return "shot"
        #     if context.entity["type"] == "Asset":
        #         return "asset"
        #     if context.entity["type"] == "Sequence":
        #         return "sequence"
        #
        # if context.entity and context.step:
        #     # We have a step and an entity.
        #     if context.entity["type"] == "Shot":
        #         return "shot_step"
        #     if context.entity["type"] == "Asset":
        #         return "asset_step"
        #
        #     return None
        # return "site"
        if context.source_entity:
            if context.source_entity["type"] == "Version":
                return "version"
            elif context.source_entity["type"] == "PublishedFile":
                return "publishedfile"
            elif context.source_entity["type"] == "Playlist":
                return "playlist"

        if context.entity and context.step is None:
            # We have an entity but no step.
            if context.entity["type"] == "Shot":
                return "shot"

        if context.entity and context.task:
            # We have an entity and a task.
            if context.entity["type"] == "Shot":
                return "shot_step"
            if context.entity["type"] == "Asset":
                return "asset_step"

        if context.project:
            return "project"

        return "site"