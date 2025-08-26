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
import hou
import sgtk

HookBaseClass = sgtk.get_hook_baseclass()

# A dict of dicts organized by category, type and output file parm
_HOUDINI_OUTPUTS = {
    # rops
    hou.ropNodeTypeCategory(): {
        "alembic": "filename",  # alembic cache
        "comp": "copoutput",  # composite
        "ifd": "vm_picture",  # mantra render node
        "opengl": "picture",  # opengl render
        "wren": "wr_picture",  # wren wireframe
    },
}


class HoudiniSessionCollector(HookBaseClass):
    """
    Collector that operates on the current houdini session. Should inherit from
    the basic collector hook.
    """

    @property
    def settings(self):
        """
        Dictionary defining the settings that this collector expects to receive
        through the settings parameter in the process_current_session and
        process_file methods.

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

        # grab any base class settings
        collector_settings = super(HoudiniSessionCollector, self).settings or {}

        # settings specific to this collector
        houdini_session_settings = {
            "Work Template": {
                "type": "template",
                "default": None,
                "description": "Template path for artist work files. Should "
                "correspond to a template defined in "
                "templates.yml. If configured, is made available"
                "to publish plugins via the collected item's "
                "properties. ",
            },
        }

        # update the base settings with these settings
        collector_settings.update(houdini_session_settings)

        return collector_settings

    def process_current_session(self, settings, parent_item):
        """
        Analyzes the current Houdini session and parents a subtree of items
        under the parent_item passed in.

        :param dict settings: Configured settings for this collector
        :param parent_item: Root item instance
        """
        # create an item representing the current houdini session
        item = self.collect_current_houdini_session(settings, parent_item)

        # remember if we collect any alembic/mantra nodes
        self._alembic_nodes_collected = False
        self._mantra_nodes_collected = False
        self._geometry_nodes_collected = False
        self._arnold_nodes_collected = False


        # methods to collect tk alembic/mantra nodes if the app is installed
        self.collect_tk_alembicnodes(item)
        self.collect_tk_mantranodes(item)
        self.collect_tk_arnoldnodes(item)
        self.collect_tk_geometrynodes(item)


        # # collect other, non-toolkit outputs to present for publishing
        # self.collect_node_outputs(item)

    def collect_current_houdini_session(self, settings, parent_item):
        """
        Creates an item that represents the current houdini session.

        :param dict settings: Configured settings for this collector
        :param parent_item: Parent Item instance

        :returns: Item of type houdini.session
        """

        publisher = self.parent

        # get the path to the current file
        path = hou.hipFile.path()

        # determine the display name for the item
        if path:
            file_info = publisher.util.get_file_path_components(path)
            display_name = file_info["filename"]
        else:
            display_name = "Current Houdini Session"

        # create the session item for the publish hierarchy
        session_item = parent_item.create_item(
            "houdini.session", "Houdini File", display_name
        )

        # get the icon path to display for this item
        icon_path = os.path.join(self.disk_location, os.pardir, "icons", "houdini.png")
        session_item.set_icon_from_path(icon_path)

        # if a work template is defined, add it to the item properties so that
        # it can be used by attached publish plugins
        work_template_setting = settings.get("Work Template")
        if work_template_setting:
            work_template = publisher.engine.get_template_by_name(
                work_template_setting.value
            )

            # store the template on the item for use by publish plugins. we
            # can't evaluate the fields here because there's no guarantee the
            # current session path won't change once the item has been created.
            # the attached publish plugins will need to resolve the fields at
            # execution time.
            session_item.properties["work_template"] = work_template
            self.logger.debug("Work template defined for Houdini collection.")

        self.logger.info("Collected current Houdini session")
        return session_item

    # def collect_node_outputs(self, parent_item):
    #     """
    #     Creates items for known output nodes
    #
    #     :param parent_item: Parent Item instance
    #     """
    #
    #     for node_category in _HOUDINI_OUTPUTS:
    #         for node_type in _HOUDINI_OUTPUTS[node_category]:
    #
    #             if node_type == "alembic" and self._alembic_nodes_collected:
    #                 self.logger.debug(
    #                     "Skipping regular alembic node collection since tk "
    #                     "alembic nodes were collected. "
    #                 )
    #                 continue
    #
    #             if node_type == "ifd" and self._mantra_nodes_collected:
    #                 self.logger.debug(
    #                     "Skipping regular mantra node collection since tk "
    #                     "mantra nodes were collected. "
    #                 )
    #                 continue
    #
    #             path_parm_name = _HOUDINI_OUTPUTS[node_category][node_type]
    #
    #             # get all the nodes for the category and type
    #             nodes = hou.nodeType(node_category, node_type).instances()
    #
    #             # iterate over each node
    #             for node in nodes:
    #
    #                 # get the evaluated path parm value
    #                 path = node.parm(path_parm_name).eval()
    #
    #                 # ensure the output path exists
    #                 if not os.path.exists(path):
    #                     continue
    #
    #                 self.logger.info(
    #                     "Processing %s node: %s" % (node_type, node.path())
    #                 )
    #
    #                 # allow the base class to collect and create the item. it
    #                 # should know how to handle the output path
    #                 item = super(HoudiniSessionCollector, self)._collect_file(
    #                     parent_item, path, frame_sequence=True
    #                 )
    #
    #                 # the item has been created. update the display name to
    #                 # include the node path to make it clear to the user how it
    #                 # was collected within the current session.
    #                 item.name = "%s (%s)" % (item.name, node.path())

    def collect_tk_alembicnodes(self, parent_item):
        """
        Checks for an installed `tk-houdini-alembicnode` app. If installed, will
        search for instances of the node in the current session and create an
        item for each one with an output on disk.

        :param parent_item: The item to parent new items to.
        """

        publisher = self.parent
        engine = publisher.engine

        alembicnode_app = engine.apps.get("tk-houdini-alembicnode")
        if not alembicnode_app:
            self.logger.debug(
                "The tk-houdini-alembicnode app is not installed. "
                "Will not attempt to collect those nodes."
            )
            return

        try:
            tk_alembic_nodes = alembicnode_app.get_nodes()
        except AttributeError:
            self.logger.warning(
                "Unable to query the session for tk-houdini-alembicnode "
                "instances. It looks like perhaps an older version of the "
                "app is in use which does not support querying the nodes. "
                "Consider updating the app to allow publishing their outputs."
            )
            return

        # retrieve the work file template defined by the app. we'll set this
        # on the collected alembicnode items for use during publishing.
        work_template = alembicnode_app.get_work_file_template()

        for node in tk_alembic_nodes:

            out_path = alembicnode_app.get_output_path(node)
            # see if any frames have been rendered for this write node

            file_name = out_path

            if '$F4' in out_path:
                out_path = file_name.replace('$F4', '%04d')
                current_engine = sgtk.platform.current_engine()
                tk = current_engine.sgtk

                output_profile_parm = node.parm('output_profile')
                output_profile_name = output_profile_parm.menuLabels()[
                    output_profile_parm.eval()
                ]


                template = tk.templates[output_profile_name]



                # if not template.validate(file_name):
                #     raise Exception("Could not resolve the files on disk for node %s."
                #                     "The path '%s' is not recognized by Shotgun!" % (node.name(), file_name))

                fields = template.get_fields(out_path)

                # tk_houdini_alembic = alembicnode_app.import_module("tk_houdini_alembicnode")

                # make sure we don't look for any eye - %V or SEQ - %04d stuff
                rendered_files = self.parent.tank.paths_from_template(template, fields, ["SEQ", "eye"])

                if not rendered_files:
                    continue

            else:
                out_path = alembicnode_app.get_output_path(node)
                if not os.path.exists(out_path):
                    continue

            self.logger.info("Processing sgtk_alembic node: %s" % (node.path(),))

            # we'll publish the path with the frame/eye spec (%V, %04d)
            render_path = out_path

            # construct publish name:
            tk_houdini_alembic = alembicnode_app.import_module("tk_houdini_alembicnode")
            nodeHandler = tk_houdini_alembic.TkAlembicNodeHandler(alembicnode_app)
            output_profile = nodeHandler._get_output_profile(node)
            render_template = alembicnode_app.get_template_by_name(output_profile["output_cache_template"])
            render_path_fields = render_template.get_fields(render_path)
            publish_template = alembicnode_app.get_template_by_name(output_profile["publish_cache_template"])

            Nname = node.parm('basename').evalAsString()
            Nname = Nname.replace("-", " ").replace("_", " ")

            rp_name = Nname + "_" + str(render_path_fields.get("Step"))
            context = publisher.engine.context
            self.logger.info("Name: %s" % (rp_name,))

            publish_name = rp_name

            # get the version number from the render path
            version_number = render_path_fields.get("version")

            # We allow the information to be pre-populated by the collector or a
            # base class plugin. They may have more information than is available
            # here such as custom type or template settings.

            publish_path = self.get_publish_path(out_path, render_template, publish_template)
            # ---- check for conflicting publishes of this path with a status

            # Note the name, context, and path *must* match the values supplied to
            # register_publish in the publish phase in order for this to return an
            # accurate list of previous publishes of this file.
            publishes = publisher.util.get_conflicting_publishes(
                context,
                publish_path,
                publish_name,
                filters=["sg_status_list", "is_not", None],
            )
            if publishes:
                self.logger.info("Conflicting publishes: %s" % (node.name(),))
                continue
            self.logger.info("PATH3: %s" % (out_path,))
            if '%04d' in out_path:
                # allow the base class to collect and create the item. it
                # should know how to handle the output path
                item = super(HoudiniSessionCollector, self)._collect_file(
                    parent_item, out_path, frame_sequence=True
                )
                # include an indicator that this is an image sequence and the known
                # file that belongs to this sequence
                item.properties["sequence_paths"] = rendered_files

            else:
                # allow the base class to collect and create the item. it
                # should know how to handle the output path
                item = super(HoudiniSessionCollector, self)._collect_file(
                    parent_item, out_path
                )

            # the item has been created. update the display name to
            # include the node path to make it clear to the user how it
            # was collected within the current session.
            item.name = "%s (%s)" % (node.name(), item.name)

            if work_template:
                item.properties["work_template"] = work_template

            # all we know about the file is its path. set the path in its
            # properties for the plugins to use for processing.
            item.properties["path"] = render_path

            # store publish info on the item so that the base publish plugin
            # doesn't fall back to zero config path parsing
            item.properties["publish_name"] = publish_name
            item.properties["publish_version"] = version_number
            item.properties[
                "publish_template"
            ] = publish_template
            item.properties[
                "work_template"
            ] = render_template

        self._alembic_nodes_collected = True

    def collect_tk_geometrynodes(self, parent_item):
        """
        Checks for an installed `tk-houdini-geometrynode` app. If installed, will
        search for instances of the node in the current session and create an
        item for each one with an output on disk.

        :param parent_item: The item to parent new items to.
        """

        publisher = self.parent
        engine = publisher.engine

        geometrynode_app = engine.apps.get("tk-houdini-geometrynode")
        if not geometrynode_app:
            self.logger.debug(
                "The tk-houdini-geometrynode app is not installed. "
                "Will not attempt to collect those nodes."
            )
            return

        try:
            tk_geometry_nodes = geometrynode_app.get_nodes()
        except AttributeError:
            self.logger.warning(
                "Unable to query the session for tk-houdini-geometrynode "
                "instances. It looks like perhaps an older version of the "
                "app is in use which does not support querying the nodes. "
                "Consider updating the app to allow publishing their outputs."
            )
            return

        # retrieve the work file template defined by the app. we'll set this
        # on the collected geometrynode items for use during publishing.
        work_template = geometrynode_app.get_work_file_template()

        for node in tk_geometry_nodes:

            out_path = node.parm("sopoutput").evalAsString()
            # see if any frames have been rendered for this write node

            file_name = out_path
            # if not os.path.exists(out_path):
            #     continue
            if '$F4' in out_path:

                out_path = file_name.replace('$F4', '%04d')
                current_engine = sgtk.platform.current_engine()
                tk = current_engine.sgtk

                output_profile_parm = node.parm('output_profile')
                output_profile_name = output_profile_parm.menuLabels()[
                    output_profile_parm.eval()
                ]

                template = tk.templates[output_profile_name]



                # if not template.validate(file_name):
                #     raise Exception("Could not resolve the files on disk for node %s."
                #                     "The path '%s' is not recognized by Shotgun!" % (node.name(), file_name))

                fields = template.get_fields(out_path)

                # make sure we don't look for any eye - %V or SEQ - %04d stuff
                rendered_files = self.parent.tank.paths_from_template(template, fields, ["SEQ", "eye"])


                if not rendered_files:
                    continue

                # out_path = rendered_files[0]
            else:
                out_path = geometrynode_app.get_output_path(node)
                if not os.path.exists(out_path):
                    continue


            self.logger.info("Processing sgtk_geometry node: %s" % (node.path(),))

            # we'll publish the path with the frame/eye spec (%V, %04d)
            render_path = out_path

            # construct publish name:
            tk_houdini_geometry = geometrynode_app.import_module("tk_houdini_geometrynode")
            nodeHandler = tk_houdini_geometry.TkGeometryNodeHandler(geometrynode_app)
            output_profile = nodeHandler._get_output_profile(node)
            render_template = geometrynode_app.get_template_by_name(output_profile["output_cache_template"])
            render_path_fields = render_template.get_fields(render_path)
            publish_template = geometrynode_app.get_template_by_name(output_profile["publish_cache_template"])

            Nname = node.parm('basename').evalAsString()
            Nname = Nname.replace("-", " ").replace("_", " ")

            rp_name = Nname + "_" + str(render_path_fields.get("Step"))
            context = publisher.engine.context
            self.logger.info("Name: %s" % (rp_name,))

            publish_name = rp_name

            # get the version number from the render path
            version_number = render_path_fields.get("version")

            # We allow the information to be pre-populated by the collector or a
            # base class plugin. They may have more information than is available
            # here such as custom type or template settings.

            publish_path = self.get_publish_path(out_path, render_template, publish_template)
            # ---- check for conflicting publishes of this path with a status

            # Note the name, context, and path *must* match the values supplied to
            # register_publish in the publish phase in order for this to return an
            # accurate list of previous publishes of this file.
            publishes = publisher.util.get_conflicting_publishes(
                context,
                publish_path,
                publish_name,
                filters=["sg_status_list", "is_not", None],
            )
            if publishes:
                self.logger.info("Conflicting publishes: %s" % (node.name(),))
                continue

            if '%04d' in out_path:
                # allow the base class to collect and create the item. it
                # should know how to handle the output path
                item = super(HoudiniSessionCollector, self)._collect_file(
                    parent_item, out_path, frame_sequence=True
                )
                # include an indicator that this is an image sequence and the known
                # file that belongs to this sequence
                item.properties["sequence_paths"] = rendered_files
            else:
                # allow the base class to collect and create the item. it
                # should know how to handle the output path
                item = super(HoudiniSessionCollector, self)._collect_file(
                    parent_item, out_path
                )

            # the item has been created. update the display name to
            # include the node path to make it clear to the user how it
            # was collected within the current session.
            item.name = "%s (%s)" % (node.name(), item.name)

            if work_template:
                item.properties["work_template"] = work_template

            # all we know about the file is its path. set the path in its
            # properties for the plugins to use for processing.
            item.properties["path"] = render_path



            # store publish info on the item so that the base publish plugin
            # doesn't fall back to zero config path parsing
            item.properties["publish_name"] = publish_name
            item.properties["publish_version"] = version_number
            item.properties[
                "publish_template"
            ] = publish_template
            item.properties[
                "work_template"
            ] = render_template

        self._geometry_nodes_collected = True

    def collect_tk_arnoldnodes(self, parent_item):
        """
        Checks for an installed `tk-houdini-arnoldnode` app. If installed, will
        search for instances of the node in the current session and create an
        item for each one with an output on disk.

        :param parent_item: The item to parent new items to.
        """

        publisher = self.parent
        engine = publisher.engine

        arnoldnode_app = engine.apps.get("tk-houdini-arnoldnode")
        if not arnoldnode_app:
            self.logger.debug(
                "The tk-houdini-arnoldnode app is not installed. "
                "Will not attempt to collect those nodes."
            )
            return

        try:
            tk_arnold_nodes = arnoldnode_app.get_nodes()
        except AttributeError:
            self.logger.warning(
                "Unable to query the session for tk-houdini-arnoldnode "
                "instances. It looks like perhaps an older version of the "
                "app is in use which does not support querying the nodes. "
                "Consider updating the app to allow publishing their outputs."
            )
            return

        # retrieve the work file template defined by the app. we'll set this
        # on the collected alembicnode items for use during publishing.
        work_template = arnoldnode_app.get_work_file_template()

        for node in tk_arnold_nodes:
            out_path = node.parm('sgtk_ar_picture').rawValue()
            self.logger.info("FRAMES: %s" % (out_path,))


            # see if any frames have been rendered for this write node

            file_name = out_path

            out_path = file_name.replace('$F4', '%04d')
            current_engine = sgtk.platform.current_engine()
            tk = current_engine.sgtk
            app = current_engine.apps['tk-houdini-arnoldnode']
            output_profile_name = app.get_setting('output_profiles', [])[0]['output_render_template']


            template = tk.templates[output_profile_name]



            fields = template.get_fields(out_path)



            # make sure we don't look for any eye - %V or SEQ - %04d stuff
            rendered_files = self.parent.tank.paths_from_template(template, fields, ["SEQ", "eye"])
            self.logger.info("FRAMES: %s" % (rendered_files,))

            if not rendered_files:
                continue

            self.logger.info("CONT: %s" % (out_path,))

            # out_path = rendered_files[0]
            render_path = out_path


            # construct publish name:
            tk_houdini_arnold = arnoldnode_app.import_module("tk_houdini_arnoldnode")
            nodeHandler = tk_houdini_arnold.TkArnoldNodeHandler(arnoldnode_app)
            output_profile = nodeHandler._get_output_profile(node)
            render_template = arnoldnode_app.get_template_by_name(output_profile["output_render_template"])
            render_path_fields = render_template.get_fields(render_path)
            publish_template = arnoldnode_app.get_template_by_name(output_profile["output_publish_render"])
            self.logger.info("PRPRO: %s" % (out_path,))



            # if not os.path.exists(out_path):
            #     continue

            self.logger.info("Processing sgtk_arnold node: %s" % (node.path(),))
            rp_name = str("Render" + "_" + str(render_path_fields.get("Step")))
            context = publisher.engine.context
            self.logger.info("Name: %s" % (rp_name,))

            publish_name = rp_name

            # get the version number from the render path
            version_number = render_path_fields.get("version")

            publish_path = self.get_publish_path(out_path, render_template, publish_template)
            # ---- check for conflicting publishes of this path with a status

            # Note the name, context, and path *must* match the values supplied to
            # register_publish in the publish phase in order for this to return an
            # accurate list of previous publishes of this file.
            publishes = publisher.util.get_conflicting_publishes(
                context,
                publish_path,
                publish_name,
                filters=["sg_status_list", "is_not", None],
            )
            if publishes:
                self.logger.info("Conflicting publishes: %s" % (node.name(),))
                continue
            # allow the base class to collect and create the item. it
            # should know how to handle the output path
            item = super(HoudiniSessionCollector, self)._collect_file(
                parent_item, out_path, frame_sequence=True
            )
            # include an indicator that this is an image sequence and the known
            # file that belongs to this sequence
            item.properties["sequence_paths"] = rendered_files
            self.logger.info("POSTPRO: %s" % (out_path,))

            # the item has been created. update the display name to
            # include the node path to make it clear to the user how it
            # was collected within the current session.
            item.name = "%s (%s)" % (node.name(), item.name())

            if work_template:
                item.properties["work_template"] = work_template



            # all we know about the file is its path. set the path in its
            # properties for the plugins to use for processing.
            item.properties["path"] = render_path

            # store publish info on the item so that the base publish plugin
            # doesn't fall back to zero config path parsing
            item.properties["publish_name"] = publish_name
            item.properties["publish_version"] = version_number
            item.properties[
                "publish_template"
            ] = publish_template
            item.properties[
                "work_template"
            ] = render_template


        for node in tk_arnold_nodes:
            # Collect ASS renders
            if node.parm("ar_ass_export_enable").evalAsInt() == 1:
                out_path = node.parm("sgtk_ass_diskfile").rawValue()
                self.logger.info("Ass file: %s" % (out_path,))

                current_engine = sgtk.platform.current_engine()
                tk = current_engine.sgtk
                app = current_engine.apps['tk-houdini-arnoldnode']


                # see if any frames have been rendered for this write node

                file_name = out_path

                if '$F4' in out_path:
                    self.logger.info("ASSFRAMES: %s" % (out_path,))
                    out_path = file_name.replace('$F4', '%04d')

                    output_profile_name = app.get_setting('output_profiles', [])[0]['output_ass_seq_template']
                    self.logger.info("Profile name: %s" % (output_profile_name,))
                    template = tk.templates[output_profile_name]
                    self.logger.info("Ass template: %s" % (template,))

                    fields = template.get_fields(out_path)

                    # make sure we don't look for any eye - %V or SEQ - %04d stuff
                    rendered_files = self.parent.tank.paths_from_template(template, fields, ["SEQ", "eye"])
                    self.logger.info("ASSCONT: %s" % (out_path,))

                    if not rendered_files:
                        continue

                    # out_path = rendered_files[0]
                else:
                    out_path = arnoldnode_app.get_output_path(node)
                    output_profile_name = app.get_setting('output_profiles', [])[0]['output_ass_template']
                    if not os.path.exists(out_path):
                        continue

                render_path = out_path

                tk_houdini_arnold = arnoldnode_app.import_module("tk_houdini_arnoldnode")
                nodeHandler = tk_houdini_arnold.TkArnoldNodeHandler(arnoldnode_app)
                output_profile = nodeHandler._get_output_profile(node)


                if '%04d' in out_path:
                    render_template = arnoldnode_app.get_template_by_name(output_profile_name)
                    render_path_fields = render_template.get_fields(render_path)
                    publish_template = arnoldnode_app.get_template_by_name(output_profile["output_publish_seq_ass"])
                else:
                    render_template = arnoldnode_app.get_template_by_name(output_profile_name)
                    render_path_fields = render_template.get_fields(publish_path)
                    publish_template = arnoldnode_app.get_template_by_name(output_profile["output_publish_ass"])

                # if not os.path.exists(out_path):
                #     continue

                self.logger.info("Processing sgtk_arnold node: %s" % (node.path(),))

                rp_name = str("Ass_" + node.name() + '_' + str(render_path_fields.get("Step")))
                context = publisher.engine.context
                self.logger.info("Name: %s" % (rp_name,))
                publish_name = rp_name

                # get the version number from the render path
                version_number = render_path_fields.get("version")

                publish_path = self.get_publish_path(out_path, render_template, publish_template)
                # ---- check for conflicting publishes of this path with a status

                # Note the name, context, and path *must* match the values supplied to
                # register_publish in the publish phase in order for this to return an
                # accurate list of previous publishes of this file.
                publishes = publisher.util.get_conflicting_publishes(
                    context,
                    publish_path,
                    publish_name,
                    filters=["sg_status_list", "is_not", None],
                )
                if publishes:
                    self.logger.info("Conflicting publishes: %s" % (node.name(),))
                    continue

                if '%04d' in out_path:
                    # allow the base class to collect and create the item. it
                    # should know how to handle the output path
                    item = super(HoudiniSessionCollector, self)._collect_file(
                        parent_item, out_path, frame_sequence=True
                    )
                    # include an indicator that this is an image sequence and the known
                    # file that belongs to this sequence
                    item.properties["sequence_paths"] = rendered_files
                else:
                    # allow the base class to collect and create the item. it
                    # should know how to handle the output path
                    item = super(HoudiniSessionCollector, self)._collect_file(
                        parent_item, out_path, frame_sequence=False
                    )

                item.name = "ASS_" + str(version_number)
                # the item has been created. update the display name to
                # include the node path to make it clear to the user how it
                # was collected within the current session.
                item.name = "%s (%s)" % (node.name(), item.name)

                if work_template:
                    item.properties["work_template"] = work_template


                # all we know about the file is its path. set the path in its
                # properties for the plugins to use for processing.
                item.properties["path"] = render_path

                # store publish info on the item so that the base publish plugin
                # doesn't fall back to zero config path parsing
                item.properties["publish_name"] = publish_name
                item.properties["publish_version"] = version_number
                item.properties[
                    "publish_template"
                ] = publish_template
                item.properties[
                    "work_template"
                ] = render_template

        for node in tk_arnold_nodes:
            # Collect aovs renders
            planeNumbers = int(node.parm("ar_aovs").rawValue())

            if planeNumbers > 0:

                for plane_number in range(planeNumbers):

                    parm1 = "sgtk_ar_aov_separate_file" + str(plane_number + 1)
                    parm2 = "ar_aov_label" + str(plane_number + 1)
                    out_path = node.parm(parm1).eval()
                    aovname = node.parm(parm2).eval()


                    # we'll publish the path with the frame/eye spec (%V, %04d)
                    publish_path = out_path
                    # see if any frames have been rendered for this write node

                    file_name = out_path
                    file_name = file_name.replace('$F4', '%04d')
                    current_engine = sgtk.platform.current_engine()
                    tk = current_engine.sgtk

                    app = current_engine.apps['tk-houdini-arnoldnode']
                    output_profile_name = app.get_setting('output_profiles', [])[0]['output_aov_render_template']

                    template = tk.templates[output_profile_name]

                    if not template.validate(file_name):
                        raise Exception("Could not resolve the files on disk for node %s."
                                        "The path '%s' is not recognized by Shotgun!" % (node.name(), file_name))

                    fields = template.get_fields(file_name)

                    if not os.path.exists(out_path):
                        continue
                    # make sure we don't look for any eye - %V or SEQ - %04d stuff
                    rendered_files = self.parent.tank.paths_from_template(template, fields, ["SEQ", "eye"])

                    if not rendered_files:
                        continue

                    # out_path = rendered_files[0]


                    # construct publish name:
                    tk_houdini_arnold = arnoldnode_app.import_module("tk_houdini_arnoldnode")
                    nodeHandler = tk_houdini_arnold.TkArnoldNodeHandler(arnoldnode_app)
                    output_profile = nodeHandler._get_output_profile(node)
                    render_template = arnoldnode_app.get_template_by_name(output_profile["output_aov_render_template"])
                    render_path_fields = render_template.get_fields(publish_path)
                    publish_template = arnoldnode_app.get_template_by_name(
                        output_profile["output_publish_aov"])

                    if not os.path.exists(out_path):
                        continue



                    self.logger.info("Processing sgtk_arnold node: %s" % (node.path(),))

                    rp_name = str("AOV" + "_" + render_path_fields.get("aov_name")) + "_" + str(render_path_fields.get("Step"))
                    context = publisher.engine.context
                    self.logger.info("Name: %s" % (rp_name,))

                    publish_name = rp_name
                    # get the version number from the render path
                    version_number = render_path_fields.get("version")

                    publish_path = self.get_publish_path(out_path, render_template, publish_template)
                    # ---- check for conflicting publishes of this path with a status

                    # Note the name, context, and path *must* match the values supplied to
                    # register_publish in the publish phase in order for this to return an
                    # accurate list of previous publishes of this file.
                    publishes = publisher.util.get_conflicting_publishes(
                        context,
                        publish_path,
                        publish_name,
                        filters=["sg_status_list", "is_not", None],
                    )
                    if publishes:
                        self.logger.info("Conflicting publishes: %s" % (node.name(),))
                        continue

                    # allow the base class to collect and create the item. it
                    # should know how to handle the output path
                    item = super(HoudiniSessionCollector, self)._collect_file(
                        parent_item, out_path, frame_sequence=True
                    )
                    # include an indicator that this is an image sequence and the known
                    # file that belongs to this sequence
                    item.properties["sequence_paths"] = rendered_files
                    item.name = "AOV_" + aovname + "_" + item.name

                    # the item has been created. update the display name to
                    # include the node path to make it clear to the user how it
                    # was collected within the current session.
                    item.name = "%s (%s)" % (node.name(), item.name)

                    if work_template:
                        item.properties["work_template"] = work_template


                    # all we know about the file is its path. set the path in its
                    # properties for the plugins to use for processing.
                    item.properties["path"] = publish_path

                    # store publish info on the item so that the base publish plugin
                    # doesn't fall back to zero config path parsing
                    item.properties["publish_name"] = publish_name
                    item.properties["publish_version"] = version_number
                    item.properties[
                        "publish_template"
                    ] = publish_template
                    item.properties[
                        "work_template"
                    ] = render_template



        self._arnold_nodes_collected = True
    def collect_tk_mantranodes(self, parent_item):
        """
        Checks for an installed `tk-houdini-mantranode` app. If installed, will
        search for instances of the node in the current session and create an
        item for each one with an output on disk.

        :param parent_item: The item to parent new items to.
        """

        publisher = self.parent
        engine = publisher.engine

        mantranode_app = engine.apps.get("tk-houdini-mantranode")
        if not mantranode_app:
            self.logger.debug(
                "The tk-houdini-mantranode app is not installed. "
                "Will not attempt to collect those nodes."
            )
            return

        try:
            tk_mantra_nodes = mantranode_app.get_nodes()
        except AttributeError:
            self.logger.warning(
                "Unable to query the session for tk-houdini-mantranode "
                "instances. It looks like perhaps an older version of the "
                "app is in use which does not support querying the nodes. "
                "Consider updating the app to allow publishing their outputs."
            )
            return

        # retrieve the work file template defined by the app. we'll set this
        # on the collected alembicnode items for use during publishing.
        work_template = mantranode_app.get_work_file_template()

        for node in tk_mantra_nodes:
            out_path = mantranode_app.get_output_path(node)

            # we'll publish the path with the frame/eye spec (%V, %04d)
            publish_path = out_path
            # see if any frames have been rendered for this write node

            file_name = mantranode_app.get_output_path(node)
            file_name = file_name.replace('$F4', '%04d')
            current_engine = sgtk.platform.current_engine()
            tk = current_engine.sgtk

            output_profile_parm = node.parm('output_profile')
            output_profile_name = output_profile_parm.menuLabels()[
                output_profile_parm.eval()
            ]

            template = tk.templates[output_profile_name]

            if not template.validate(file_name):
                raise Exception("Could not resolve the files on disk for node %s."
                                "The path '%s' is not recognized by Shotgun!" % (node.name(), file_name))

            fields = template.get_fields(file_name)


            if not os.path.exists(out_path):
                continue
            # make sure we don't look for any eye - %V or SEQ - %04d stuff
            rendered_files = self._app.tank.paths_from_template(template, fields, ["SEQ", "eye"])

            if not rendered_files:
                continue

            # out_path = rendered_files[0]


            # construct publish name:
            tk_houdini_mantra = mantranode_app.import_module("tk_houdini_mantranode")
            nodeHandler = tk_houdini_mantra.TkMantraNodeHandler(mantranode_app)
            output_profile = nodeHandler._get_output_profile(node)
            render_template = mantranode_app.get_template_by_name(output_profile["output_render_template"])
            render_path_fields = render_template.get_fields(publish_path)
            publish_template = mantranode_app.get_template_by_name(output_profile["publish_render_template"])



            if not os.path.exists(out_path):
                continue

            self.logger.info("Processing sgtk_mantra node: %s" % (node.path(),))

            # allow the base class to collect and create the item. it
            # should know how to handle the output path
            item = super(HoudiniSessionCollector, self)._collect_file(
                parent_item, out_path, frame_sequence=True
            )
            # include an indicator that this is an image sequence and the known
            # file that belongs to this sequence
            item.properties["sequence_paths"] = rendered_files

            # the item has been created. update the display name to
            # include the node path to make it clear to the user how it
            # was collected within the current session.
            item.name = "%s (%s)" % (item.name, node.path())

            if work_template:
                item.properties["work_template"] = work_template

            rp_name = item.name

            publish_name = rp_name

            # get the version number from the render path
            version_number = render_path_fields.get("version")

            # all we know about the file is its path. set the path in its
            # properties for the plugins to use for processing.
            item.properties["path"] = publish_path

            # store publish info on the item so that the base publish plugin
            # doesn't fall back to zero config path parsing
            item.properties["publish_name"] = publish_name
            item.properties["publish_version"] = version_number
            item.properties[
                "publish_template"
            ] = publish_template
            item.properties[
                "work_template"
            ] = render_template



            # Collect DCM renders
            if node.parm("vm_deepresolver").eval() == "camera":
                out_path = node.parm("sgtk_vm_dcmfilename").eval()

                # we'll publish the path with the frame/eye spec (%V, %04d)
                publish_path = out_path
                # see if any frames have been rendered for this write node

                file_name = out_path
                file_name = file_name.replace('$F4', '%04d')
                current_engine = sgtk.platform.current_engine()
                tk = current_engine.sgtk

                output_profile_parm = node.parm('output_profile')
                output_profile_name = output_profile_parm.menuLabels()[
                    output_profile_parm.eval()
                ]

                template = tk.templates[output_profile_name]

                if not template.validate(file_name):
                    raise Exception("Could not resolve the files on disk for node %s."
                                    "The path '%s' is not recognized by Shotgun!" % (node.name(), file_name))

                fields = template.get_fields(file_name)

                if not os.path.exists(out_path):
                    continue
                # make sure we don't look for any eye - %V or SEQ - %04d stuff
                rendered_files = self._app.tank.paths_from_template(template, fields, ["SEQ", "eye"])

                if not rendered_files:
                    continue

                # out_path = rendered_files[0]


                # construct publish name:
                tk_houdini_mantra = mantranode_app.import_module("tk_houdini_mantranode")
                nodeHandler = tk_houdini_mantra.TkMantraNodeHandler(mantranode_app)
                output_profile = nodeHandler._get_output_profile(node)
                render_template = mantranode_app.get_template_by_name(output_profile["output_dcm_template"])
                render_path_fields = render_template.get_fields(publish_path)
                publish_template = mantranode_app.get_template_by_name(output_profile["publish_dcm_template"])

                if not os.path.exists(out_path):
                    continue

                self.logger.info("Processing sgtk_mantra node: %s" % (node.path(),))

                # allow the base class to collect and create the item. it
                # should know how to handle the output path
                item = super(HoudiniSessionCollector, self)._collect_file(
                    parent_item, out_path, frame_sequence=True
                )
                # include an indicator that this is an image sequence and the known
                # file that belongs to this sequence
                item.properties["sequence_paths"] = rendered_files
                item.name = "DCM_" + item.name

                # the item has been created. update the display name to
                # include the node path to make it clear to the user how it
                # was collected within the current session.
                item.name = "%s (%s)" % (item.name, node.path())

                if work_template:
                    item.properties["work_template"] = work_template

                rp_name = item.name

                publish_name = rp_name

                # get the version number from the render path
                version_number = render_path_fields.get("version")

                # all we know about the file is its path. set the path in its
                # properties for the plugins to use for processing.
                item.properties["path"] = publish_path

                # store publish info on the item so that the base publish plugin
                # doesn't fall back to zero config path parsing
                item.properties["publish_name"] = publish_name
                item.properties["publish_version"] = version_number
                item.properties[
                    "publish_template"
                ] = publish_template
                item.properties[
                    "work_template"
                ] = render_template



            # Collect extra planes renders
            planeNumbers = node.parm("vm_numaux").eval()

            if planeNumbers > 0:

                for plane_number in range(planeNumbers):

                    parm1 = "sgtk_vm_filename_plane" + str(plane_number + 1)
                    parm2 = "sgtk_aov_name" + str(plane_number + 1)
                    out_path = node.parm(parm1).eval()
                    aovname = node.parm(parm2).eval()

                    # we'll publish the path with the frame/eye spec (%V, %04d)
                    publish_path = out_path
                    # see if any frames have been rendered for this write node

                    file_name = out_path
                    file_name = file_name.replace('$F4', '%04d')
                    current_engine = sgtk.platform.current_engine()
                    tk = current_engine.sgtk

                    output_profile_parm = node.parm('output_profile')
                    output_profile_name = output_profile_parm.menuLabels()[
                        output_profile_parm.eval()
                    ]

                    template = tk.templates[output_profile_name]

                    if not template.validate(file_name):
                        raise Exception("Could not resolve the files on disk for node %s."
                                        "The path '%s' is not recognized by Shotgun!" % (node.name(), file_name))

                    fields = template.get_fields(file_name)

                    if not os.path.exists(out_path):
                        continue
                    # make sure we don't look for any eye - %V or SEQ - %04d stuff
                    rendered_files = self._app.tank.paths_from_template(template, fields, ["SEQ", "eye"])

                    if not rendered_files:
                        continue

                    # out_path = rendered_files[0]


                    # construct publish name:
                    tk_houdini_mantra = mantranode_app.import_module("tk_houdini_mantranode")
                    nodeHandler = tk_houdini_mantra.TkMantraNodeHandler(mantranode_app)
                    output_profile = nodeHandler._get_output_profile(node)
                    render_template = mantranode_app.get_template_by_name(output_profile["output_extra_plane_template"])
                    render_path_fields = render_template.get_fields(publish_path)
                    publish_template = mantranode_app.get_template_by_name(
                        output_profile["publish_extra_plane_template"])

                    if not os.path.exists(out_path):
                        continue

                    self.logger.info("Processing sgtk_mantra node: %s" % (node.path(),))

                    # allow the base class to collect and create the item. it
                    # should know how to handle the output path
                    item = super(HoudiniSessionCollector, self)._collect_file(
                        parent_item, out_path, frame_sequence=True
                    )
                    # include an indicator that this is an image sequence and the known
                    # file that belongs to this sequence
                    item.properties["sequence_paths"] = rendered_files
                    item.name = "ExtraPlane_" + aovname + "_" + item.name

                    # the item has been created. update the display name to
                    # include the node path to make it clear to the user how it
                    # was collected within the current session.
                    item.name = "%s (%s)" % (item.name, node.path())

                    if work_template:
                        item.properties["work_template"] = work_template

                    rp_name = item.name

                    publish_name = rp_name

                    # get the version number from the render path
                    version_number = render_path_fields.get("version")

                    # all we know about the file is its path. set the path in its
                    # properties for the plugins to use for processing.
                    item.properties["path"] = publish_path

                    # store publish info on the item so that the base publish plugin
                    # doesn't fall back to zero config path parsing
                    item.properties["publish_name"] = publish_name
                    item.properties["publish_version"] = version_number
                    item.properties[
                        "publish_template"
                    ] = publish_template
                    item.properties[
                        "work_template"
                    ] = render_template



        self._mantra_nodes_collected = True

    def get_publish_path(self, path, work_template, publish_template):
        """
        Get a publish path for the supplied settings and item.

        :param settings: This plugin instance's configured settings
        :param item: The item to determine the publish path for

        :return: A string representing the output path to supply when
            registering a publish for the supplied item

        Extracts the publish path via the configured work and publish templates
        if possible.
        """


        work_fields = []
        publish_path = None

        # We need both work and publish template to be defined for template
        # support to be enabled.
        if work_template and publish_template:
            if work_template.validate(path):
                work_fields = work_template.get_fields(path)

            missing_keys = publish_template.missing_keys(work_fields)

            if missing_keys:
                self.logger.warning(
                    "Not enough keys to apply work fields (%s) to "
                    "publish template (%s) Missing: %s" % (work_fields, publish_template, missing_keys)
                )
            else:
                publish_path = publish_template.apply_fields(work_fields)
                self.logger.debug(
                    "Used publish template to determine the publish path: %s"
                    % (publish_path,)
                )
        else:
            self.logger.debug("publish_template: %s" % publish_template)
            self.logger.debug("work_template: %s" % work_template)

        if not publish_path:
            publish_path = path
            self.logger.debug(
                "Could not validate a publish template. Publishing in place."
            )

        return publish_path

