# Copyright (c) 2018 Shotgun Software Inc.
#
# CONFIDENTIAL AND PROPRIETARY
#
# This work is provided "AS IS" and subject to the Shotgun Pipeline Toolkit
# Source Code License included in this distribution package. See LICENSE.
# By accessing, using, copying or modifying this work you indicate your
# agreement to the Shotgun Pipeline Toolkit Source Code License. All rights
# not expressly granted therein are reserved by Shotgun Software Inc.

import sgtk
from sgtk.platform.qt import QtGui

HookBaseClass = sgtk.get_hook_baseclass()


class HieroCustomizeExportUI(HookBaseClass):
    def create_shot_processor_widget(self, parent_widget):
        widget = QtGui.QGroupBox("Settings", parent_widget)
        widget.setLayout(QtGui.QFormLayout())
        return widget

    def get_shot_processor_ui_properties(self):
        return [
            dict(
                label="Create Cut:",
                name="custom_create_cut_bool_property",
                value=True,
                tooltip="Create a Cut and CutItems in Shotgun...",
            ),
            dict(
                label="Cut In:",
                name="custom_cut_in_bool_property",
                value=True,
                tooltip="Update 'sg_cut_in' on the Shot entity.",
            ),
            dict(
                label="Cut Out:",
                name="custom_cut_out_bool_property",
                value=True,
                tooltip="Update 'sg_cut_out' on the Shot entity.",
            ),
            dict(
                label="Head In:",
                name="custom_head_in_bool_property",
                value=True,
                tooltip="Update 'sg_head_in' on the Shot entity.",
            ),
            dict(
                label="Tail Out:",
                name="custom_tail_out_bool_property",
                value=True,
                tooltip="Update 'sg_tail_out' on the Shot entity.",
            ),
            dict(
                label="Source Clip:",
                name="custom_sourceClip_bool_property",
                value=True,
                tooltip="Update 'sg_source_clip' on the Shot entity.",
            ),
            dict(
                label="Metadata:",
                name="custom_metadata_bool_property",
                value=True,
                tooltip="Update metadata fields on the Shot entity.",
            )
        ]

    def set_shot_processor_ui_properties(self, widget, properties):
        layout = widget.layout()
        for label, prop in properties.items():
            layout.addRow(label, prop)

    def create_transcode_exporter_widget(self, parent_widget):
        widget = QtGui.QGroupBox("Settings", parent_widget)
        widget.setLayout(QtGui.QFormLayout())
        return widget

    def get_transcode_exporter_ui_properties(self):
        return []

    def set_transcode_exporter_ui_properties(self, widget, properties):
        layout = widget.layout()
        for label, prop in properties.items():
            layout.addRow(label, prop)

    def create_copy_exporter_widget(self, parent_widget):
        widget = QtGui.QGroupBox("Settings", parent_widget)
        widget.setLayout(QtGui.QFormLayout())
        return widget

    def get_copy_exporter_ui_properties(self):
        return []

    def set_copy_exporter_ui_properties(self, widget, properties):
        layout = widget.layout()
        for label, prop in properties.items():
            layout.addRow(label, prop)

    def create_audio_exporter_widget(self, parent_widget):
        widget = QtGui.QGroupBox("Settings", parent_widget)
        widget.setLayout(QtGui.QFormLayout())
        return widget

    def get_audio_exporter_ui_properties(self):
        return []

    def set_audio_exporter_ui_properties(self, widget, properties):
        layout = widget.layout()
        for label, prop in properties.items():
            layout.addRow(label, prop)

    def create_nuke_shot_exporter_widget(self, parent_widget):
        widget = QtGui.QGroupBox("Settings", parent_widget)
        widget.setLayout(QtGui.QFormLayout())
        return widget

    def get_nuke_shot_exporter_ui_properties(self):
        return []

    def set_nuke_shot_exporter_ui_properties(self, widget, properties):
        layout = widget.layout()
        for label, prop in properties.items():
            layout.addRow(label, prop)
