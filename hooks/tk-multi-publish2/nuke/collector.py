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
import nuke
import sgtk

HookBaseClass = sgtk.get_hook_baseclass()

# A look up of node types to parameters for finding outputs to publish
_NUKE_OUTPUTS = {
    "Write": "file",
    "WriteGeo": "file",
}


class NukeSessionCollector(HookBaseClass):
    """
    Collector that operates on the current nuke/nukestudio session. Should
    inherit from the basic collector hook.
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
        collector_settings = super(NukeSessionCollector, self).settings or {}

        # settings specific to this collector
        nuke_session_settings = {
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
        collector_settings.update(nuke_session_settings)

        return collector_settings

    def process_current_session(self, settings, parent_item):
        """
        Analyzes the current session open in Nuke/NukeStudio and parents a
        subtree of items under the parent_item passed in.

        :param dict settings: Configured settings for this collector
        :param parent_item: Root item instance
        """

        publisher = self.parent
        engine = publisher.engine

        if nuke.root().knob("proxy").value()==False:
            if (hasattr(engine, "studio_enabled") and engine.studio_enabled) or (
                hasattr(engine, "hiero_enabled") and engine.hiero_enabled
            ):

                # running nuke studio or hiero
                self.collect_current_nukestudio_session(settings, parent_item)

                # since we're in NS, any additional collected outputs will be
                # parented under the root item
                project_item = parent_item
            else:
                # running nuke. ensure additional collected outputs are parented
                # under the session
                project_item = self.collect_current_nuke_session(settings, parent_item)

            # run node collection if not in hiero
            if hasattr(engine, "hiero_enabled") and not engine.hiero_enabled:
                self.collect_sg_writenodes(project_item)
                self.collect_sg_writeGeoCam_nodes(project_item)
                self.collect_sg_writeGeo_nodes(project_item)
                self.collect_node_outputs(project_item)
        else:
            nuke.message("Estás en modo proxy. Desactivalo para publicar")

    def collect_current_nuke_session(self, settings, parent_item):
        """
        Analyzes the current session open in Nuke and parents a subtree of items
        under the parent_item passed in.

        :param dict settings: Configured settings for this collector
        :param parent_item: Root item instance
        """

        publisher = self.parent

        # get the current path
        path = _session_path()

        # determine the display name for the item
        if path:
            file_info = publisher.util.get_file_path_components(path)
            display_name = file_info["filename"]
        else:
            display_name = "Current Nuke Session"

        # create the session item for the publish hierarchy
        session_item = parent_item.create_item(
            "nuke.session", "Nuke Script", display_name
        )

        # get the icon path to display for this item
        icon_path = os.path.join(self.disk_location, os.pardir, "icons", "nuke.png")
        session_item.set_icon_from_path(icon_path)

        # if a work template is defined, add it to the item properties so
        # that it can be used by attached publish plugins
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
            self.logger.debug("Work template defined for Nuke collection.")

        self.logger.info("Collected current Nuke script")
        return session_item

    def collect_current_nukestudio_session(self, settings, parent_item):
        """
        Analyzes the current session open in NukeStudio and parents a subtree of
        items under the parent_item passed in.

        :param dict settings: Configured settings for this collector
        :param parent_item: Root item instance
        """

        # import here since the hooks are imported into nuke and nukestudio.
        # hiero module is only available in later versions of nuke
        import hiero.core

        publisher = self.parent

        # go ahead and build the path to the icon for use by any projects
        icon_path = os.path.join(
            self.disk_location, os.pardir, "icons", "nukestudio.png"
        )

        if hiero.ui.activeSequence():
            active_project = hiero.ui.activeSequence().project()
        else:
            active_project = None

        # attempt to retrive a configured work template. we can attach
        # it to the collected project items
        work_template_setting = settings.get("Work Template")
        work_template = None
        if work_template_setting:
            work_template = publisher.engine.get_template_by_name(
                work_template_setting.value
            )

        # FIXME: begin temporary workaround
        # we use different logic here only because we don't have proper support
        # for multi context workflows when templates are in play. So if we have
        # a work template configured, for now we'll only collect the current,
        # active document. Once we have proper multi context support, we can
        # remove this.
        if work_template:
            # same logic as the loop below but only processing the active doc
            if not active_project:
                return
            project_item = parent_item.create_item(
                "nukestudio.project", "NukeStudio Project", active_project.name()
            )
            self.logger.info(
                "Collected Nuke Studio project: %s" % (active_project.name(),)
            )
            project_item.set_icon_from_path(icon_path)
            project_item.properties["project"] = active_project
            project_item.properties["work_template"] = work_template
            self.logger.debug("Work template defined for NukeStudio collection.")
            return
        # FIXME: end temporary workaround

        for project in hiero.core.projects():

            # create the session item for the publish hierarchy
            project_item = parent_item.create_item(
                "nukestudio.project", "NukeStudio Project", project.name()
            )
            project_item.set_icon_from_path(icon_path)

            # add the project object to the properties so that the publish
            # plugins know which open project to associate with this item
            project_item.properties["project"] = project

            self.logger.info("Collected Nuke Studio project: %s" % (project.name(),))

            # enable the active project and expand it. other projects are
            # collapsed and disabled.
            if active_project and active_project.guid() == project.guid():
                project_item.expanded = True
                project_item.checked = True
            elif active_project:
                # there is an active project, but this isn't it. collapse and
                # disable this item
                project_item.expanded = False
                project_item.checked = False

            # store the template on the item for use by publish plugins. we
            # can't evaluate the fields here because there's no guarantee the
            # current session path won't change once the item has been created.
            # the attached publish plugins will need to resolve the fields at
            # execution time.
            if work_template:
                project_item.properties["work_template"] = work_template
                self.logger.debug("Work template defined for NukeStudio collection.")

    def collect_node_outputs(self, parent_item):
        """
        Scan known output node types in the session and see if they reference
        files that have been written to disk.

        :param parent_item: The parent item for any nodes collected
        """
        # iterate over all the known output types
        for node_type in _NUKE_OUTPUTS:
            ##Limit this routine for WriteGeo nodes until we have a workflow
            if node_type == 'WriteGeo':

                # get all the instances of the node type
                all_nodes_of_type = [n for n in nuke.allNodes() if n.Class() == node_type]

                # iterate over each instance
                for node in all_nodes_of_type:

                    param_name = _NUKE_OUTPUTS[node_type]

                    # evaluate the output path parameter which may include frame
                    # expressions/format
                    file_path = node[param_name].evaluate()

                    if not file_path or not os.path.exists(file_path):
                        # no file or file does not exist, nothing to do
                        continue

                    self.logger.info("Processing %s node: %s" % (node_type, node.name()))

                    # file exists, let the basic collector handle it
                    item = super(NukeSessionCollector, self)._collect_file(
                        parent_item, file_path, frame_sequence=True
                    )

                    # the item has been created. update the display name to include
                    # the nuke node to make it clear to the user how it was
                    # collected within the current session.
                    item.name = "%s (%s)" % (item.name, node.name())

    def collect_sg_writenodes(self, parent_item):
        """
        Collect any rendered sg write nodes in the session.

        :param parent_item:  The parent item for any sg write nodes collected
        """

        publisher = self.parent
        engine = publisher.engine

        sg_writenode_app = engine.apps.get("tk-nuke-writenode")
        if not sg_writenode_app:
            self.logger.debug(
                "The tk-nuke-writenode app is not installed. "
                "Will not attempt to collect those nodes."
            )
            return

        first_frame = int(nuke.root()["first_frame"].value())
        last_frame = int(nuke.root()["last_frame"].value())

        for node in sg_writenode_app.get_write_nodes():
            publish_path_CHECK = sg_writenode_app.get_node_render_path(node)

            self.logger.info(str(node))
            # if 'PRECOMP' not in node.knob('tk_profile_list').value():
            # if item.context.entity == 'Asset':
            # see if any frames have been rendered for this write node
            rendered_files = sg_writenode_app.get_node_render_files(node)
            if not rendered_files:
                continue

            # some files rendered, use first frame to get some publish item info
            path = rendered_files[0]
            item_info = super(NukeSessionCollector, self)._get_item_info(path)

            # item_info will be for the single file. we'll update the type and
            # display to represent a sequence. This is the same pattern used by
            # the base collector for image sequences. We're not using the base
            # collector to create the publish item though since we already have
            # the sequence path, template knowledge provided by the
            # tk-nuke-writenode app. The base collector makes some "zero config"
            # assupmtions about the path that we don't need to make here.
            if node.knob('tk_profile_list').value() in ["Render 16bits", "Render JPG", "IMAGE_PLANE"]:
                item_type = "%s.sequence" % (item_info["item_type"],)
            else:
                item_type = "%s.precompSequence" % (item_info["item_type"],)
            type_display = "%s Sequence" % (item_info["type_display"],)

            # we'll publish the path with the frame/eye spec (%V, %04d)
            publish_path = sg_writenode_app.get_node_render_path(node)

            # construct publish name:
            render_template = sg_writenode_app.get_node_render_template(node)
            render_path_fields = render_template.get_fields(publish_path)

            # rp_name = render_path_fields.get("name")
            # rp_channel = render_path_fields.get("channel")
            # if not rp_name and not rp_channel:
            #     publish_name = "%s %s" %(node.knob('tk_profile_list').value(), node.knob('tank_channel').value())
            # elif not rp_name:
            #     publish_name = "Channel %s" % rp_channel
            # elif not rp_channel:
            #     publish_name = rp_name
            # else:
            #     publish_name = "%s, Channel %s" % (rp_name, rp_channel)

            publish_name = "%s %s" % ('_'.join(os.path.splitext(os.path.basename(publish_path))[0].split('_')[:-1]), node.knob('tank_channel').value())

            # get the version number from the render path
            version_number = render_path_fields.get("version")

            # use the path basename and nuke writenode name for display
            (_, filename) = os.path.split(publish_path)
            display_name = "%s (%s)" % (publish_name, node.name())

            # create and populate the item
            item = parent_item.create_item(item_type, type_display, display_name)
            item.set_icon_from_path(item_info["icon_path"])

            # if the supplied path is an image, use the path as # the thumbnail.
            item.set_thumbnail_from_path(path)

            # disable thumbnail creation since we get it for free
            item.thumbnail_enabled = False

            # all we know about the file is its path. set the path in its
            # properties for the plugins to use for processing.
            item.properties["path"] = publish_path

            # include an indicator that this is an image sequence and the known
            # file that belongs to this sequence
            item.properties["sequence_paths"] = rendered_files

            # store publish info on the item so that the base publish plugin
            # doesn't fall back to zero config path parsing
            item.properties["publish_name"] = publish_name
            item.properties["publish_version"] = version_number
            item.properties[
                "publish_template"
            ] = sg_writenode_app.get_node_publish_template(node)
            item.properties[
                "work_template"
            ] = sg_writenode_app.get_node_render_template(node)
            item.properties["color_space"] = self._get_node_colorspace(node)
            item.properties["first_frame"] = first_frame
            item.properties["last_frame"] = last_frame

            # store the nuke writenode on the item as well. this can be used by
            # secondary publish plugins
            item.properties["sg_writenode"] = node

            if node.knob('tk_profile_list').value() == "MATTE_PAINT":
                item.properties["publish_type"] = "BG_MATTEPAINT"
            elif node.knob('tk_profile_list').value() == "IMAGE_PLANE":
                item.properties["publish_type"] = "IMAGE_PLANE"
            elif node.knob('tk_profile_list').value() == "PRECOMP":
                item.properties["publish_type"] = "PRECOMP"
            elif node.knob('tk_profile_list').value() == "TECH_PRECOMP":
                item.properties["publish_type"] = "TECH_PRECOMP"
            elif node.knob('tk_profile_list').value() == "ALPHA":
                item.properties["publish_type"] = "ALPHA_RENDER"
            else:
                item.properties["publish_type"] = "RENDER_NUKE"

            # Collect dependencies from node
            item.properties["publish_dependencies"] = self.list_dependencies(node)

            # we have a publish template so disable context change. This
            # is a temporary measure until the publisher handles context
            # switching natively.
            item.context_change_allowed = False

            self.logger.info("Collected file: %s" % (publish_path,))


    def collect_sg_writeGeoCam_nodes(self, parent_item):
        """
        Collect any rendered sg write nodes in the session.

        :param parent_item:  The parent item for any sg write nodes collected
        """

        publisher = self.parent
        engine = publisher.engine

        first_frame = int(nuke.root()["first_frame"].value())
        last_frame = int(nuke.root()["last_frame"].value())

        for node in nuke.allNodes("ShotgunWriteCam.gizmo"):

            self.logger.info(str(node))
            # if 'PRECOMP' not in node.knob('tk_profile_list').value():
            # if item.context.entity == 'Asset':
            # see if any frames have been rendered for this write node
            rendered_files = []
            try:
                for file in os.listdir(os.path.dirname(node['Path'].value())):
                    full_path = os.path.normpath(os.path.join(os.path.dirname(node['Path'].value()), file))
                    if os.path.isfile(full_path):
                        pattern = os.path.normpath(node['Path'].value()[:node['Path'].value().find('_v')+5])
                        if pattern in os.path.normpath(full_path):
                            rendered_files.append(full_path)
            except:
                self.logger.info("No renders found for node '%s'" % (node['name'].value()))
                continue

            if len(rendered_files) == 0:
                continue

            # some files rendered, use first frame to get some publish item info
            path = rendered_files[0]
            item_info = super(NukeSessionCollector, self)._get_item_info(path)

            # item_info will be for the single file. we'll update the type and
            # display to represent a sequence. This is the same pattern used by
            # the base collector for image sequences. We're not using the base
            # collector to create the publish item though since we already have
            # the sequence path, template knowledge provided by the
            # tk-nuke-writenode app. The base collector makes some "zero config"
            # assupmtions about the path that we don't need to make here.
            item_type = "nuke.camera"
            type_display = "Camera"

            # we'll publish the path with the frame/eye spec (%V, %04d)
            render_path = node['Path'].value()
            publish_path = node['Publish_path'].value()

            # construct publish name:
            node_work_template_node = node['work_template'].value()
            tk = engine.sgtk
            render_template = tk.templates[node_work_template_node]
            render_path_fields = render_template.get_fields(render_path)

            node_publish_template_node = node['publish_template'].value()
            publish_template = tk.templates[node_publish_template_node]
            publish_path_fields = publish_template.get_fields(publish_path)

            # rp_name = publish_path_fields.get("name")
            # rp_channel = publish_path_fields.get("channel")
            # if not rp_name and not rp_channel:
            #     publish_name = "%s %s" %(node.knob('tk_profile_list').value(), node.knob('tank_channel').value())
            # elif not rp_name:
            #     publish_name = "Channel %s" % rp_channel
            # elif not rp_channel:
            #     publish_name = rp_name
            # else:
            #     publish_name = "%s, Channel %s" % (rp_name, rp_channel)

            publish_name = "%s %s %s" % ('_'.join(os.path.splitext(os.path.basename(publish_path))[0].split('_')[:-1]), publish_path_fields.get("name"), "Camera")

            # get the version number from the render path
            version_number = publish_path_fields.get("version")

            # use the path basename and nuke writenode name for display
            (_, filename) = os.path.split(publish_path)
            display_name = "%s (%s) %s" % ("Camera Publish", publish_name, node.name())

            # create and populate the item
            item = parent_item.create_item(item_type, type_display, display_name)
            icon_path = os.path.join(self.disk_location, os.pardir, "icons", "camera.png")
            item.set_icon_from_path(icon_path)

            # if the supplied path is an image, use the path as # the thumbnail.
            item.set_thumbnail_from_path(path)

            # disable thumbnail creation since we get it for free
            item.thumbnail_enabled = False

            # all we know about the file is its path. set the path in its
            # properties for the plugins to use for processing.
            item.properties["path"] = render_path
            item.properties["publish_path"] = publish_path

            # include an indicator that this is an image sequence and the known
            # file that belongs to this sequence
            item.properties["sequence_paths"] = rendered_files

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
            item.properties["first_frame"] = first_frame
            item.properties["last_frame"] = last_frame
            item.properties["publish_fields"] = {'sg_status_list': 'cmpt'}

            # store the nuke writenode on the item as well. this can be used by
            # secondary publish plugins
            item.properties["sg_writenode"] = node

            # Collect dependencies from node
            item.properties["publish_dependencies"] = self.list_dependencies(node)

            # we have a publish template so disable context change. This
            # is a temporary measure until the publisher handles context
            # switching natively.
            item.context_change_allowed = False

            self.logger.info("Collected file: %s" % (publish_path,))

    def collect_sg_writeGeo_nodes(self, parent_item):
        """
        Collect any rendered sg write nodes in the session.

        :param parent_item:  The parent item for any sg write nodes collected
        """

        publisher = self.parent
        engine = publisher.engine

        first_frame = int(nuke.root()["first_frame"].value())
        last_frame = int(nuke.root()["last_frame"].value())

        for node in nuke.allNodes("ShotgunWriteGeo.gizmo"):

            self.logger.info(str(node))
            # if 'PRECOMP' not in node.knob('tk_profile_list').value():
            # if item.context.entity == 'Asset':
            # see if any frames have been rendered for this write node
            rendered_files = []
            try:
                for file in os.listdir(os.path.dirname(node['Path'].value())):
                    full_path = os.path.normpath(os.path.join(os.path.dirname(node['Path'].value()), file))
                    if os.path.isfile(full_path):
                        pattern = os.path.normpath(node['Path'].value()[:node['Path'].value().find('_v') + 5])
                        if pattern in os.path.normpath(full_path):
                            rendered_files.append(full_path)
            except:
                self.logger.info("No renders found for node '%s'" % (node['name'].value()))
                continue

            if len(rendered_files) == 0:
                continue

            # some files rendered, use first frame to get some publish item info
            path = rendered_files[0]
            item_info = super(NukeSessionCollector, self)._get_item_info(path)

            # item_info will be for the single file. we'll update the type and
            # display to represent a sequence. This is the same pattern used by
            # the base collector for image sequences. We're not using the base
            # collector to create the publish item though since we already have
            # the sequence path, template knowledge provided by the
            # tk-nuke-writenode app. The base collector makes some "zero config"
            # assupmtions about the path that we don't need to make here.
            item_type = "nuke.geo"
            type_display = "Geometry"

            # we'll publish the path with the frame/eye spec (%V, %04d)
            render_path = node['Path'].value()
            publish_path = node['Publish_path'].value()

            # construct publish name:
            node_work_template_node = node['work_template'].value()
            tk = engine.sgtk
            render_template = tk.templates[node_work_template_node]
            render_path_fields = render_template.get_fields(render_path)

            node_publish_template_node = node['publish_template'].value()
            publish_template = tk.templates[node_publish_template_node]
            publish_path_fields = publish_template.get_fields(publish_path)

            # rp_name = publish_path_fields.get("name")
            # rp_channel = publish_path_fields.get("channel")
            # if not rp_name and not rp_channel:
            #     publish_name = "Publish"
            # elif not rp_name:
            #     publish_name = "Channel %s" % rp_channel
            # elif not rp_channel:
            #     publish_name = rp_name
            # else:
            #     publish_name = "%s, Channel %s" % (rp_name, rp_channel)

            publish_name = "%s %s %s" % ('_'.join(os.path.splitext(os.path.basename(publish_path))[0].split('_')[:-1]), publish_path_fields.get("name"), "Geometry")

            # get the version number from the render path
            version_number = publish_path_fields.get("version")

            # use the path basename and nuke writenode name for display
            (_, filename) = os.path.split(publish_path)
            display_name = "%s (%s) %s" % ("Camera Publish", publish_name, node.name())

            # create and populate the item
            item = parent_item.create_item(item_type, type_display, display_name)
            item.set_icon_from_path(item_info["icon_path"])

            # if the supplied path is an image, use the path as # the thumbnail.
            item.set_thumbnail_from_path(path)

            # disable thumbnail creation since we get it for free
            item.thumbnail_enabled = False

            # all we know about the file is its path. set the path in its
            # properties for the plugins to use for processing.
            item.properties["path"] = render_path
            item.properties["publish_path"] = publish_path

            # include an indicator that this is an image sequence and the known
            # file that belongs to this sequence
            item.properties["sequence_paths"] = rendered_files

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
            item.properties["first_frame"] = first_frame
            item.properties["last_frame"] = last_frame
            item.properties["publish_fields"] = {'sg_status_list': 'cmpt'}

            # store the nuke writenode on the item as well. this can be used by
            # secondary publish plugins
            item.properties["sg_writenode"] = node

            #Collect dependencies from node
            item.properties["publish_dependencies"] = self.list_dependencies(node)


            # we have a publish template so disable context change. This
            # is a temporary measure until the publisher handles context
            # switching natively.
            item.context_change_allowed = False

            self.logger.info("Collected file: %s" % (publish_path,))

    def _get_node_colorspace(self, node):
        """
        Get the colorspace for the specified nuke node

        :param node:    The nuke node to find the colorspace for
        :returns:       The string representing the colorspace for the node
        """
        cs_knob = node.knob("colorspace")
        if not cs_knob:
            return

        cs = cs_knob.value()
        # handle default value where cs would be something like: 'default (linear)'
        if cs.startswith("default (") and cs.endswith(")"):
            cs = cs[9:-1]
        return cs

    def list_dependencies(self, node):
        nodeslist = []

        def select_node_dependencies_recursive(node):
            if node.Class() in ['Read', 'Camera2', 'ReadGeo2']:
                file_path = node['file'].value()
                if not file_path:
                    pass
                else:
                    if node['file'].value() not in nodeslist:
                        nodeslist.append(node['file'].value())
            for dep in node.dependencies(nuke.INPUTS):
                try:
                    select_node_dependencies_recursive(dep)
                except:
                    print("WARNING: there was a problem with %s, please check" % dep.name())

        select_node_dependencies_recursive(node)
        return nodeslist



def _session_path():
    """
    Return the path to the current session
    :return:
    """
    root_name = nuke.root().name()
    return None if root_name == "Root" else root_name
