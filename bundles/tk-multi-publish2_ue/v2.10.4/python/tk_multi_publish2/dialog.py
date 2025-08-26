# Copyright (c) 2017 Shotgun Software Inc.
#
# CONFIDENTIAL AND PROPRIETARY
#
# This work is provided "AS IS" and subject to the Shotgun Pipeline Toolkit
# Source Code License included in this distribution package. See LICENSE.
# By accessing, using, copying or modifying this work you indicate your
# agreement to the Shotgun Pipeline Toolkit Source Code License. All rights
# not expressly granted therein are reserved by Shotgun Software Inc.

import traceback
import re
import sgtk
from sgtk.platform.qt import QtCore, QtGui

try:
    from tank_vendor import sgutils
except ImportError:
    from tank_vendor import six as sgutils

from .api import PublishManager, PublishItem, PublishTask
from .ui.dialog import Ui_Dialog
from .progress import ProgressHandler
from .summary_overlay import SummaryOverlay
from .publish_tree_widget import TreeNodeItem, TreeNodeTask, TopLevelTreeNodeItem

# import frameworks
settings = sgtk.platform.import_framework("tk-framework-shotgunutils", "settings")
help_screen = sgtk.platform.import_framework("tk-framework-qtwidgets", "help_screen")
task_manager = sgtk.platform.import_framework(
    "tk-framework-shotgunutils", "task_manager"
)
shotgun_model = sgtk.platform.import_framework(
    "tk-framework-shotgunutils", "shotgun_model"
)
shotgun_globals = sgtk.platform.import_framework(
    "tk-framework-shotgunutils", "shotgun_globals"
)

logger = sgtk.platform.get_logger(__name__)


class AppDialog(QtGui.QWidget):
    """
    Main dialog window for the App
    """

    # main drag and drop areas
    (DRAG_SCREEN, PUBLISH_SCREEN) = range(2)

    # details ui panes
    (
        ITEM_DETAILS,
        TASK_DETAILS,
        PLEASE_SELECT_DETAILS,
        MULTI_EDIT_NOT_SUPPORTED,
    ) = range(4)

    # gating: CL + exactly 6 digits at start
    def _refresh_publish_state(self):
        # Validate text
        try:
            txt = (self.ui.item_comments.toPlainText() or "")
        except Exception:
            txt = ""
        items = self.ui.items_tree.selectedItems()
        if self._current_item is not None and items:
            ti = items[0]
            if isinstance(ti, TreeNodeItem) and getattr(ti, "inherit_description", False):
                txt = self._summary_comment or ""
        txt = txt.strip()

        has_cl = bool(self._cl_re.match(txt))  # CL + 6 Digits
        ok_validation = (self._last_validation_issues == 0)  # Validate sin issues

        # 2) Check all tree
        checked_any = False
        it = QtGui.QTreeWidgetItemIterator(self.ui.items_tree)
        while it.value():
            node = it.value()
            if getattr(node, "checked", False):
                checked_any = True
                break
            it += 1

        # check task
        task_required_ok = True
        if self._bundle.get_setting("task_required"):
            task_required_ok = False
            for i in range(self.ui.items_tree.topLevelItemCount()):
                ctx = self.ui.items_tree.topLevelItem(i)
                if hasattr(ctx, "context") and ctx.context and ctx.context.task:
                    task_required_ok = True
                else:
                    task_required_ok = False
                    break

        # Enable push
        enable = has_cl and ok_validation and checked_any and task_required_ok
        self.ui.publish.setEnabled(enable)

        #
        if not enable:
            problems = []
            if not has_cl:
                problems.append("Description start with Perforce changelist: ")
            if not ok_validation:
                problems.append("Execute Validate for issues")
            if not checked_any:
                problems.append("Select any item")
            if not task_required_ok:
                problems.append("Select task")
            self.ui.publish.setToolTip("; ".join(problems))
        else:
            self.ui.publish.setToolTip("")

    def __init__(self, parent=None):
        """
        :param parent: The parent QWidget for this control
        """
        QtGui.QWidget.__init__(self, parent)

        # settings manager
        self._settings_manager = settings.UserSettings(sgtk.platform.current_bundle())

        # background task manager
        self._task_manager = task_manager.BackgroundTaskManager(
            self, start_processing=True, max_threads=2
        )

        # register bg task manager
        shotgun_globals.register_bg_task_manager(self._task_manager)

        self._bundle = sgtk.platform.current_bundle()
        self._validation_run = False

        # ui
        self.ui = Ui_Dialog()
        self.ui.setupUi(self)
        self._desc_prefix = "Perforce changelist: "
        self._summary_comment = self._desc_prefix
        self.ui.item_description_label.setText(
            "Description must start with 'Perforce changelist: 123456'"
        )
        # validation helper
        self._cl_re = re.compile(r"^\s*Perforce\s+changelist:\s*\d{6}\b.*", re.I)
        self._last_validation_issues = None

        #
        self.ui.item_comments.textChanged.connect(self._refresh_publish_state)

        # context widget
        self.ui.context_widget.set_up(self._task_manager)
        self.ui.context_widget.restrict_entity_types_by_link("PublishedFile", "entity")
        self.ui.context_widget.set_task_tooltip(
            "<p>The task that the selected item will be associated with "
            "in Flow Production Tracking after publishing. It is recommended "
            "to always fill out the Task field when publishing. The menu button "
            "to the right will provide suggestions for Tasks to publish "
            "including the Tasks assigned to you, recently used Tasks, "
            "and Tasks related to the entity Link populated in the field "
            "below.</p>"
        )
        self.ui.context_widget.set_link_tooltip(
            "<p>The entity that the selected item will be associated with "
            "in Flow Production Tracking after publishing. By selecting a "
            "Task in the field above, the Link will automatically be populated. "
            "It is recommended that you always populate the Task field when "
            "publishing. The Task menu above will display any tasks associated "
            "with the entity populated in this field.</p>"
        )

        self.ui.context_widget.context_changed.connect(self._on_item_context_change)

        # splitter
        self.ui.splitter.setStretchFactor(0, 0)
        self.ui.splitter.setStretchFactor(1, 1)
        self.ui.splitter.setSizes([360, 100])

        # drag and drop
        self.ui.frame.something_dropped.connect(self._on_drop)
        self.ui.large_drop_area.something_dropped.connect(self._on_drop)

        self.ui.items_tree.tree_reordered.connect(self._synchronize_tree)

        # hide the drag screen progress button by default
        self.ui.drag_progress_message.hide()

        # buttons
        self.ui.publish.clicked.connect(self.do_publish)
        self.ui.close.clicked.connect(self.close)
        self.ui.close.hide()
        self.ui.validate.clicked.connect(lambda: self.do_validate())
        self.ui.publish.setEnabled(False)

        # overlay
        self._overlay = SummaryOverlay(self.ui.main_frame)
        self._overlay.publish_again_clicked.connect(self._publish_again_clicked)

        # settings
        self.ui.items_tree.status_clicked.connect(self._on_publish_status_clicked)

        # description wiring
        self.ui.item_comments.textChanged.connect(self._on_item_comment_change)
        self.ui.item_inherited_item_label.linkActivated.connect(
            self._on_description_inherited_link_activated
        )

        # selection in tree view
        self.ui.items_tree.itemSelectionChanged.connect(self._update_details_from_selection)

        # clicking in the tree view
        self.ui.items_tree.checked.connect(self._update_details_from_selection)

        # thumbnails
        self.ui.item_thumbnail.thumbnail_changed.connect(self._update_item_thumbnail)

        # tool buttons
        self.ui.delete_items.clicked.connect(self._delete_selected)
        self.ui.expand_all.clicked.connect(lambda: self._set_tree_items_expanded(True))
        self.ui.collapse_all.clicked.connect(lambda: self._set_tree_items_expanded(False))
        self.ui.refresh.clicked.connect(self._full_rebuild)

        # stop processing
        self.ui.stop_processing.hide()
        self._stop_processing_flagged = False
        self.ui.stop_processing.clicked.connect(self._trigger_stop_processing)

        # help button
        help_url = self._bundle.get_setting("help_url")
        if help_url:
            self.ui.help.clicked.connect(lambda: self._open_url(help_url))
        else:
            self.ui.help.hide()

        # browse actions
        self._browse_file_action = QtGui.QAction(self)
        self._browse_file_action.setText("Browse files to publish")
        self._browse_file_action.setIcon(QtGui.QIcon(":/tk_multi_publish2/file.png"))
        self._browse_file_action.triggered.connect(lambda: self._on_browse(folders=False))

        self._browse_folder_action = QtGui.QAction(self)
        self._browse_folder_action.setText("Browse folders to publish image sequences")
        self._browse_folder_action.setIcon(QtGui.QIcon(":/tk_multi_publish2/image_sequence.png"))
        self._browse_folder_action.triggered.connect(lambda: self._on_browse(folders=True))

        self._browse_menu = QtGui.QMenu(self)
        self._browse_menu.addAction(self._browse_file_action)
        self._browse_menu.addAction(self._browse_folder_action)

        self.ui.browse.clicked.connect(self._on_browse)
        self.ui.browse.setMenu(self._browse_menu)
        self.ui.browse.setPopupMode(QtGui.QToolButton.DelayedPopup)

        # drop area browse
        self.ui.drop_area_browse_file.clicked.connect(lambda: self._on_browse(folders=False))
        self.ui.drop_area_browse_seq.clicked.connect(lambda: self._on_browse(folders=True))

        # current state
        self._current_item = None

        # current selected tasks
        self._current_tasks = _TaskSelection()


        # progress handler
        self._progress_handler = ProgressHandler(
            self.ui.progress_status_icon, self.ui.progress_message, self.ui.progress_bar
        )

        # link overlay status button with the log window
        self._overlay.info_clicked.connect(self._progress_handler._progress_details.toggle)

        # connect the drag screen progress button to show progress details
        self.ui.drag_progress_message.clicked.connect(self._progress_handler.show_details)

        # background publish integration
        bg_publish_app = self._bundle.engine.apps.get("tk-multi-bg-publish", None)
        if bg_publish_app:
            self.bg_publish_checkbox = QtGui.QCheckBox("Perform publish in the background")
            self.bg_publish_checkbox.setToolTip(
                "When checked, you may continue working in the DCC while the publish is performed in a background process. Open the Background Publish Monitor to see your publish progress."
            )
            default_bg_process = self._bundle.get_setting("collector_settings", {}).get(
                "Background Processing", False
            )
            self.bg_publish_checkbox.setChecked(default_bg_process)
            self.bg_publish_checkbox.stateChanged.connect(
                lambda state=None: self._set_bg_processing()
            )
            settings_layout = self.ui.item_settings.layout()
            settings_layout.addWidget(self.bg_publish_checkbox)
            settings_layout.addStretch()
            self.ui.item_settings_label.show()
            self.ui.item_settings.show()
        else:
            self.bg_publish_checkbox = None
            self.ui.item_settings_label.hide()
            self.ui.item_settings.hide()

        # publish manager
        self._publish_manager = PublishManager(self._progress_handler.logger)
        self.ui.items_tree.set_publish_manager(self._publish_manager)

        # summary thumbnail
        self._summary_thumbnail = None

        # button text
        self._display_action_name = self._bundle.get_setting("display_action_name")
        self.ui.publish.setText(self._display_action_name)

        # manual load tweaks
        self.ui.text_below_item_tree.setVisible(self.manual_load_enabled)
        self.ui.browse.setVisible(self.manual_load_enabled)

        # initial collect
        self._full_rebuild()

    @property
    def manual_load_enabled(self):
        """Returns whether user is allowed to load file to the UI"""
        return self._bundle.get_setting("enable_manual_load")

    def keyPressEvent(self, event):
        """
        Qt Keypress event
        """
        if (
            self._progress_handler.is_showing_details()
            and event.key() == QtCore.Qt.Key_Escape
        ):
            self._progress_handler.hide_details()
        else:
            super().keyPressEvent(event)

    def closeEvent(self, event):
        """
        Executed when the main dialog is closed.
        """
        logger.debug("CloseEvent Received. Begin shutting down UI.")

        shotgun_globals.unregister_bg_task_manager(self._task_manager)

        self._progress_handler.shut_down()

        try:
            self._task_manager.shut_down()
        except Exception:
            logger.exception(
                "Error running Flow Production Tracking Panel App closeEvent()"
            )

        self.ui.context_widget.save_recent_contexts()

    def _update_details_from_selection(self):
        """
        Sync right-hand details with selection in the tree.
        """
        checked_top_items = 0
        for context_index in range(self.ui.items_tree.topLevelItemCount()):
            context_item = self.ui.items_tree.topLevelItem(context_index)
            for child_index in range(context_item.childCount()):
                child_item = context_item.child(child_index)
                if child_item.checked:
                    checked_top_items += 1

        if checked_top_items == 0:
            self.ui.publish.setEnabled(False)
            self.ui.validate.setEnabled(False)
        else:
            self.ui.publish.setEnabled(True)
            self.ui.validate.setEnabled(True)
        self._refresh_publish_state()

        items = self.ui.items_tree.selectedItems()

        if self._is_task_selection_homogeneous(items):
            self._current_item = None
            publish_tasks = _TaskSelection(
                [item.get_publish_instance() for item in items]
            )
            self._update_task_details_ui(publish_tasks)
        elif len(items) != 1:
            self._current_item = None
            self._update_task_details_ui()
            self.ui.details_stack.setCurrentIndex(self.PLEASE_SELECT_DETAILS)
        else:
            tree_item = items[0]
            publish_object = tree_item.get_publish_instance()
            if isinstance(publish_object, PublishItem):
                self._update_task_details_ui()
                self._create_item_details(tree_item)
            elif publish_object is None:
                self._update_task_details_ui()
                self._create_master_summary_details()

        self._validate_task_required()

    def _is_task_selection_homogeneous(self, items):
        """
        True if selection only contains tasks and all are of the same type.
        """
        if len(items) == 0:
            return False

        first_task = items[0].get_publish_instance()

        for item in items:
            publish_instance = item.get_publish_instance()
            if not isinstance(publish_instance, PublishTask):
                return False
            if not first_task.is_same_task_type(publish_instance):
                return False

        return True

    def _update_task_details_ui(self, new_task_selection=None):
        """
        Updates the plugin UI widget.
        """
        new_task_selection = new_task_selection or _TaskSelection()

        if self._current_tasks == new_task_selection:
            return

        if self._current_tasks:
            logger.debug("Saving settings...")
            self._pull_settings_from_ui(self._current_tasks)

        if not new_task_selection:
            logger.debug("The ui is going to change, so clear the current one.")
            self.ui.task_settings.widget = None
            self._current_tasks = new_task_selection
            return

        self.ui.details_stack.setCurrentIndex(self.TASK_DETAILS)

        self.ui.task_icon.setPixmap(new_task_selection.plugin.icon)
        self.ui.task_name.setText(new_task_selection.plugin.name)

        if (
            self._current_tasks
            and self._current_tasks.is_same_task_type(new_task_selection)
        ):
            logger.debug("Reusing custom ui from %s.", new_task_selection.plugin)
        else:
            logger.debug("Building a custom ui for %s.", new_task_selection.plugin)
            widget = new_task_selection.plugin.run_create_settings_widget(
                self.ui.task_settings_parent, new_task_selection.get_task_items()
            )
            self.ui.task_settings.widget = widget

        if self._push_settings_into_ui(new_task_selection):
            self._current_tasks = new_task_selection
        else:
            self._current_tasks = _TaskSelection()

    def _pull_settings_from_ui(self, selected_tasks):
        """
        Retrieves settings from the UI and updates the task's settings.
        """
        if selected_tasks.has_custom_ui:
            widget = self.ui.task_settings.widget
            settings_dict = self._current_tasks.get_settings(widget)
        else:
            settings_dict = {}

        for task in selected_tasks:
            for k, v in settings_dict.items():
                task.settings[k].value = v

    def _push_settings_into_ui(self, selected_tasks):
        """
        Pushes the task settings into the UI.
        """
        tasks_settings = []
        for task in selected_tasks:
            settings_dict = {}
            for k, v in task.settings.items():
                settings_dict[k] = v.value
            tasks_settings.append(settings_dict)

        if selected_tasks.has_custom_ui:
            try:
                selected_tasks.set_settings(
                    self.ui.task_settings.widget, tasks_settings
                )
            except NotImplementedError:
                self.ui.details_stack.setCurrentIndex(self.MULTI_EDIT_NOT_SUPPORTED)
                return False
        return True

    def _on_publish_status_clicked(self, task_or_item):
        """
        When someone clicks the status icon in the tree
        """
        self._progress_handler.select_last_message(task_or_item)

    def _on_item_comment_change(self):
        """
        Called when someone types in the publish comments box.
        """
        tree_widget = self.ui.items_tree
        comments = self.ui.item_comments.toPlainText()
        if self._current_item is None:
            if self._summary_comment != comments:
                self._summary_comment = comments

                for node_item in tree_widget.root_items():
                    if (
                        isinstance(node_item, TreeNodeItem)
                        and node_item.inherit_description is True
                    ):
                        node_item.set_description(comments)
        else:
            description = comments
            item_desc = (
                self._current_item.description
                if self._current_item.description is not None
                else ""
            )
            if item_desc != description:
                node_item = tree_widget.selectedItems()[0]

                if comments == "":
                    node_item.inherit_description = True
                    description = self._find_inherited_description(node_item)
                else:
                    node_item.inherit_description = False

                node_item.set_description(description)
                self._set_description_inheritance_ui(node_item)

    def _on_description_inherited_link_activated(self, _link):
        """
        Selects the item the current item inherits its description from.
        """
        selected_item = self.ui.items_tree.selectedItems()[0]
        item = self._find_inherited_description_item(selected_item)
        if item:
            item.setSelected(True)
        else:
            self.ui.items_tree.summary_node.setSelected(True)
        selected_item.setSelected(False)

    def _update_item_thumbnail(self, pixmap):
        """
        Update the currently selected item with the given thumbnail pixmap
        """
        if not self._current_item:
            self._summary_thumbnail = pixmap
            if pixmap:
                for top_level_item in self._publish_manager.tree.root_item.children:
                    top_level_item.thumbnail = self._summary_thumbnail
                    top_level_item.thumbnail_explicit = False
                    for item in top_level_item.descendants:
                        item.thumbnail = self._summary_thumbnail
                        item.thumbnail_explicit = False
        else:
            self._current_item.thumbnail = pixmap
            self._current_item.thumbnail_explicit = True

    def _create_item_details(self, tree_item):
        """
        Render details pane for a given item
        """
        item = tree_item.get_publish_instance()

        self._current_item = item
        self.ui.details_stack.setCurrentIndex(self.ITEM_DETAILS)
        self.ui.item_icon.setPixmap(item.icon)

        self.ui.item_name.setText(item.name)
        self.ui.item_type.setText(item.type_display)

        if item.thumbnail_enabled:
            self.ui.item_thumbnail_label.show()
            self.ui.item_thumbnail.show()
            self.ui.item_thumbnail.setEnabled(True)
        elif not item.thumbnail_enabled and item.thumbnail:
            self.ui.item_thumbnail_label.show()
            self.ui.item_thumbnail.show()
            self.ui.item_thumbnail.setEnabled(False)
        else:
            self.ui.item_thumbnail_label.hide()
            self.ui.item_thumbnail.hide()

        # etiqueta estatica para evitar "saltos" de layout
        self.ui.item_description_label.setText("Description must have changelist number, type 'Perforce changelist: {numbers}'")

        self._set_description_inheritance_ui(tree_item)

        if tree_item.inherit_description:
            self.ui.item_comments.setText("")
            self.ui.item_comments.setPlaceholderText(self._summary_comment or self._desc_prefix)
        else:
            self.ui.item_comments.setText(item.description)
            inherited_desc = self._find_inherited_description(tree_item)
            self.ui.item_comments.setPlaceholderText(inherited_desc)

        self.ui.item_comments._show_multiple_values = False

        if self._summary_thumbnail and not item.thumbnail_explicit:
            item.thumbnail = self._summary_thumbnail

        self.ui.item_thumbnail._set_multiple_values_indicator(False)
        self.ui.item_thumbnail.set_thumbnail(item.thumbnail)

        self.ui.item_thumbnail.setEnabled(True)

        if item.parent.is_root:
            self.ui.context_widget.show()

            if item.context_change_allowed:
                self.ui.context_widget.enable_editing(
                    True, "<p>Task and Entity Link to apply to the selected item:</p>"
                )
            else:
                self.ui.context_widget.enable_editing(
                    False,
                    "<p>Context changing has been disabled for this item. "
                    "It will be associated with "
                    "<strong><a style='color:#C8C8C8; text-decoration:none' "
                    "href='%s'>%s</a></strong></p>"
                    % (item.context.shotgun_url, item.context),
                )

            self.ui.context_widget.set_context(item.context)
        else:
            self.ui.context_widget.hide()

        self.ui.item_summary_label.show()
        summary = tree_item.create_summary()
        if len(summary) == 0:
            summary_text = "No items to process."
        else:
            summary_text = "<p>The following items will be processed:</p>"
            summary_text += "".join(["<p>%s</p>" % line for line in summary])
        self.ui.item_summary.setText(summary_text)

        self._refresh_publish_state()

    def _create_master_summary_details(self):
        """
        Render the master summary representation
        """
        self._current_item = None
        self.ui.details_stack.setCurrentIndex(self.ITEM_DETAILS)

        display_name = self._bundle.get_setting("display_name")
        self.ui.item_name.setText("%s Summary" % display_name)
        self.ui.item_icon.setPixmap(QtGui.QPixmap(":/tk_multi_publish2/icon_256.png"))

        self.ui.item_thumbnail_label.show()
        self.ui.item_thumbnail.show()

        thumbnail_has_multiple_values = False
        description_had_multiple_values = False
        for top_level_item in self._publish_manager.tree.root_item.children:
            if top_level_item.thumbnail_explicit:
                thumbnail_has_multiple_values = True

            if top_level_item.description not in [None, self._summary_comment]:
                description_had_multiple_values = True

            if description_had_multiple_values and thumbnail_has_multiple_values:
                break

            for descendant in top_level_item.descendants:
                if descendant.thumbnail_explicit:
                    thumbnail_has_multiple_values = True

                if descendant.description not in [None, self._summary_comment]:
                    description_had_multiple_values = True

                if description_had_multiple_values and thumbnail_has_multiple_values:
                    break

            if thumbnail_has_multiple_values and description_had_multiple_values:
                break

        self.ui.item_thumbnail._set_multiple_values_indicator(
            thumbnail_has_multiple_values
        )
        self.ui.item_thumbnail.set_thumbnail(self._summary_thumbnail)

        self.ui.item_thumbnail.setEnabled(True)

        self.ui.item_description_label.setText("Description for all items")
        self.ui.item_inherited_item_label.hide()
        if not (self._summary_comment or "").strip():
            self._summary_comment = self._desc_prefix

        self.ui.item_comments.setText(self._summary_comment)
        self.ui.item_comments.setPlaceholderText("Perforce changelist: 123456 ...")

        self.ui.item_comments.clearFocus()
        self.ui.item_comments._show_multiple_values = description_had_multiple_values

        current_contexts = {}
        for it in QtGui.QTreeWidgetItemIterator(self.ui.items_tree):
            item = it.value()
            publish_instance = item.get_publish_instance()
            if isinstance(publish_instance, PublishItem):
                context = publish_instance.context
                context_key = str(context)
                current_contexts[context_key] = context

        if len(current_contexts) == 1:
            context_key = list(current_contexts.keys())[0]
            self.ui.context_widget.set_context(current_contexts[context_key])
            context_label_text = "Task and Entity Link to apply to all items:"
        else:
            self.ui.context_widget.set_context(
                None,
                task_display_override=" -- Multiple values -- ",
                link_display_override=" -- Multiple values -- ",
            )
            context_label_text = (
                "Currently publishing items to %s contexts. "
                "Override all items here:" % (len(current_contexts),)
            )

        self.ui.context_widget.show()
        self.ui.context_widget.enable_editing(True, context_label_text)

        self.ui.item_summary_label.hide()

        (num_items, summary) = self.ui.items_tree.get_full_summary()
        self.ui.item_summary.setText(summary)
        self.ui.item_type.setText("%d tasks to execute" % num_items)

    def _full_rebuild(self):
        """
        Full rebuild of the plugin state. Everything is recollected.
        """
        self._progress_handler.set_phase(self._progress_handler.PHASE_LOAD)
        self._progress_handler.push(
            "Collecting items to %s..." % (self._display_action_name)
        )

        previously_collected_files = self._publish_manager.collected_files
        self._publish_manager.tree.clear(clear_persistent=True)

        logger.debug("Refresh: Running collection on current session...")
        new_session_items = self._publish_manager.collect_session()

        logger.debug(
            "Refresh: Running collection on all previously collected external files"
        )
        new_file_items = self._publish_manager.collect_files(previously_collected_files)

        num_items_created = len(new_session_items) + len(new_file_items)
        num_errors = self._progress_handler.pop()

        if num_errors == 0 and num_items_created == 1:
            self._progress_handler.logger.info("One item discovered by publisher.")
        elif num_errors == 0 and num_items_created > 1:
            self._progress_handler.logger.info(
                "%d items discovered by publisher." % num_items_created
            )
        elif num_errors > 0:
            self._progress_handler.logger.error("Errors reported. See log for details.")

        self._synchronize_tree()

        self._summary_comment = self._desc_prefix

        self.ui.items_tree.select_first_item()

        self._validation_run = False

        self._set_bg_processing()

    def _on_drop(self, files):
        """
        When someone drops stuff into the publish.
        """
        if not self.manual_load_enabled:
            self._progress_handler.logger.error("Drag & drop disabled.")
            return

        self._progress_handler.set_phase(self._progress_handler.PHASE_LOAD)
        self._progress_handler.push("Processing external files...")

        str_files = [sgutils.ensure_str(f) for f in files]

        try:
            self.ui.main_stack.setCurrentIndex(self.PUBLISH_SCREEN)

            self._progress_handler.progress_details.set_parent(self.ui.main_frame)

            self._overlay.show_loading()
            self.ui.button_container.hide()
            new_items = self._publish_manager.collect_files(str_files)
            num_items_created = len(new_items)
            num_errors = self._progress_handler.pop()

            if num_errors == 0 and num_items_created == 0:
                self._progress_handler.logger.info("Nothing was added.")
            elif num_errors == 0 and num_items_created == 1:
                self._progress_handler.logger.info("One item was added.")
            elif num_errors == 0 and num_items_created > 1:
                self._progress_handler.logger.info(
                    "%d items were added." % num_items_created
                )
            elif num_errors == 1:
                self._progress_handler.logger.error(
                    "An error was reported. Please see the log for details."
                )
            else:
                self._progress_handler.logger.error(
                    "%d errors reported. Please see the log for details." % num_errors
                )

            self._synchronize_tree()

        finally:
            self._overlay.hide()
            self.ui.button_container.show()

        top_level_items = list(self._publish_manager.tree.root_item.children)
        if (
            len(top_level_items) == 0
            and self.ui.main_stack.currentIndex() == self.DRAG_SCREEN
        ):
            self.ui.drag_progress_message.setText(
                "Could not determine items to %s. Click for more info..." % (self._display_action_name,)
            )
            self.ui.drag_progress_message.show()
        else:
            self.ui.drag_progress_message.hide()

        self.ui.items_tree.select_first_item()

    def _synchronize_tree(self):
        """
        Redraws the ui and rebuilds data based on the low level plugin representation
        """
        top_level_items = list(self._publish_manager.tree.root_item.children)
        if len(top_level_items) == 0:
            if not self.manual_load_enabled:
                self._show_no_items_error()
            else:
                self.ui.main_stack.setCurrentIndex(self.DRAG_SCREEN)
                self._progress_handler.progress_details.set_parent(
                    self.ui.large_drop_area
                )
        else:
            self.ui.main_stack.setCurrentIndex(self.PUBLISH_SCREEN)
            self._progress_handler.progress_details.set_parent(self.ui.main_frame)
            self.ui.items_tree.build_tree()

    def _set_tree_items_expanded(self, expanded):
        """
        Expand/Collapse all top-level publish items in the left side tree
        """
        for it in QtGui.QTreeWidgetItemIterator(self.ui.items_tree):
            item = it.value()
            if isinstance(item, TopLevelTreeNodeItem):
                item.setExpanded(expanded)

    def _set_description_inheritance_ui(self, tree_item):
        """
        Sets up the UI based on the selected item's description inheritance state.
        """
        self.ui.item_inherited_item_label.show()
        highlight_color = self._bundle.style_constants["SG_HIGHLIGHT_COLOR"]
        base_lbl = '<span style=" font-size:10pt;">{0}</span>'

        if isinstance(tree_item, TreeNodeItem) and tree_item.inherit_description:
            self.ui.item_comments.setStyleSheet(
                "border: 1px solid {0};".format(highlight_color)
            )

            lbl_prefix = base_lbl.format(
                'Description inherited from: <a href="inherited description" style="color: {0}">{1}</a>'
            )

            desc_item = self._find_inherited_description_item(tree_item)
            if desc_item:
                name = desc_item.get_publish_instance().name
                self.ui.item_inherited_item_label.setText(
                    lbl_prefix.format(highlight_color, name)
                )
                return
            elif self._summary_comment:
                self.ui.item_inherited_item_label.setText(
                    lbl_prefix.format(highlight_color, "Summary")
                )
                return

        self.ui.item_comments.setStyleSheet(
            "border: 0px solid {0};".format(highlight_color)
        )
        self.ui.item_inherited_item_label.setText("You must Validate before Publish")

    def _set_bg_processing(self):
        """
        Set the background processing flag on the publish tree.
        """
        if not self.bg_publish_checkbox:
            return

        bg_processing = self.bg_publish_checkbox.isChecked()
        self._publish_manager.tree.root_item.properties["bg_processing"] = bg_processing

    def _delete_selected(self):
        """
        Delete all selected items. Prompt the user.
        """
        num_items = len(self.ui.items_tree.selectedItems())
        if num_items == 0:
            return

        if num_items > 1:
            msg = "This will remove %d items from the list." % num_items
        else:
            msg = "Remove the item from the list?"

        res = QtGui.QMessageBox.question(
            self, "Remove items?", msg, QtGui.QMessageBox.Ok | QtGui.QMessageBox.Cancel
        )

        if res == QtGui.QMessageBox.Cancel:
            return

        processing_items = []

        for tree_item in self.ui.items_tree.selectedItems():
            if isinstance(tree_item, TreeNodeItem):
                processing_items.append(tree_item.item)

        for item in processing_items:
            self._publish_manager.tree.remove_item(item)

        self._synchronize_tree()
        for node_item in self.ui.items_tree.root_items():
            if isinstance(node_item, TreeNodeItem):
                node_item.inherit_description = True
                node_item.set_description(self._summary_comment)
        self.ui.items_tree.select_first_item()

    def _check_all(self, checked):
        """
        Check all boxes in the currently active tree
        """
        def _check_r(parent):
            for child_index in range(parent.childCount()):
                child = parent.child(child_index)
                child.checkbox.setChecked(checked)
                _check_r(child)

        parent = self.ui.items_tree.invisibleRootItem()
        _check_r(parent)

    def _reset_tree_icon_r(self, parent):
        """
        Clear the current progress icon recursively for the given tree node
        """
        for child_index in range(parent.childCount()):
            child = parent.child(child_index)
            child.reset_progress()
            self._reset_tree_icon_r(child)

    def _prepare_tree(self, number_phases):
        """
        Prepares the tree for processing.
        """
        self._set_tree_items_expanded(True)

        parent = self.ui.items_tree.invisibleRootItem()

        self._reset_tree_icon_r(parent)

        def _begin_process_r(parent):
            total_number_nodes = 0
            for child_index in range(parent.childCount()):
                child = parent.child(child_index)
                if child.checked:
                    total_number_nodes += 1
                total_number_nodes += _begin_process_r(child)
            return total_number_nodes

        total_number_nodes = _begin_process_r(parent)
        self._progress_handler.reset_progress(total_number_nodes * number_phases)

    def do_validate(self, is_standalone=True):
        """
        Perform a full validation
        """
        self._pull_settings_from_ui(self._current_tasks)

        if is_standalone:
            self._prepare_tree(number_phases=1)

        self._progress_handler.set_phase(self._progress_handler.PHASE_VALIDATE)
        self._progress_handler.push("Running validation pass")

        num_issues = 0
        self.ui.stop_processing.show()
        try:
            failed_to_validate = self._publish_manager.validate(
                task_generator=self._validate_task_generator(is_standalone)
            )
            num_issues = len(failed_to_validate)
        finally:
            self._progress_handler.pop()
            if self._stop_processing_flagged:
                self._progress_handler.logger.info("Processing aborted by user.")
            elif num_issues > 0:
                self._progress_handler.logger.error(
                    "Validation Complete. %d issues reported." % num_issues
                )
            else:
                self._progress_handler.logger.info(
                    "Validation Complete. All checks passed."
                )

            if is_standalone:
                self._stop_processing_flagged = False
                self.ui.stop_processing.hide()
                self._progress_handler.reset_progress()

        self._validation_run = True
        self._last_validation_issues = num_issues
        self._refresh_publish_state()

        return num_issues

    def do_publish(self):
        """
        Perform a full publish
        """
        publish_failed = False

        self.ui.button_container.hide()
        self.ui.item_settings.setEnabled(False)

        self._prepare_tree(number_phases=3)

        try:
            self.ui.stop_processing.show()

            if self._bundle.get_setting("validate_on_publish"):
                if self.do_validate(is_standalone=False) > 0:
                    self._progress_handler.logger.error(
                        "Validation errors detected. Not proceeding with publish."
                    )
                    self.ui.button_container.show()
                    self.ui.item_settings.setEnabled(True)
                    return
            elif self._validation_run:
                self._progress_handler.logger.info(
                    "Skipping validation pass just before publish. It was already run manually."
                )
            else:
                button_clicked = QtGui.QMessageBox.question(
                    self,
                    "%s without Validation?" % (self._display_action_name,),
                    "You are attempting to %s without validation. Are you sure "
                    "you wish to continue?" % (self._display_action_name,),
                    buttons=QtGui.QMessageBox.Yes | QtGui.QMessageBox.Cancel,
                )
                if button_clicked == QtGui.QMessageBox.Cancel:
                    self.ui.button_container.show()
                    self.ui.item_settings.setEnabled(True)
                    return

                self._progress_handler.logger.info("User skipped validation step.")

            if self._stop_processing_flagged:
                self.ui.button_container.show()
                self.ui.item_settings.setEnabled(True)
                return

            self._progress_handler.set_phase(self._progress_handler.PHASE_PUBLISH)
            self._progress_handler.push("Running publishing pass")

            parent = self.ui.items_tree.invisibleRootItem()
            self._reset_tree_icon_r(parent)

            try:
                self._publish_manager.publish(
                    task_generator=self._publish_task_generator()
                )
            except Exception:
                logger.error("Publish error stack:\n%s" % (traceback.format_exc(),))
                self._progress_handler.logger.error("Error while publishing. Aborting.")
                publish_failed = True
            finally:
                self._progress_handler.pop()

            if not publish_failed and not self._stop_processing_flagged:
                self._progress_handler.set_phase(self._progress_handler.PHASE_FINALIZE)
                self._progress_handler.push("Running finalizing pass")

                try:
                    self._publish_manager.finalize(
                        task_generator=self._finalize_task_generator()
                    )
                except Exception:
                    logger.error(
                        "Finalize error stack:\n%s" % (traceback.format_exc(),)
                    )
                    self._progress_handler.logger.error(
                        "Error while finalizing. Aborting."
                    )
                    publish_failed = True
                finally:
                    self._progress_handler.pop()

            if self._stop_processing_flagged:
                self._progress_handler.logger.info("Processing aborted by user.")
                self.ui.button_container.show()
                self.ui.item_settings.setEnabled(True)
                return

        finally:
            self.ui.stop_processing.hide()
            self._stop_processing_flagged = False
            self._progress_handler.reset_progress()

        self.ui.validate.hide()
        self.ui.publish.hide()
        self.ui.close.show()

        if publish_failed:
            self._progress_handler.logger.error(
                "Publish Failed! For details, click here."
            )
            self._overlay.show_fail()
        else:
            try:
                self._bundle.log_metric("Published")
            except:
                pass

            self._progress_handler.logger.info(
                "Publish Complete! For details, click here."
            )
            self._overlay.show_success()

    def _publish_again_clicked(self):
        """
        Called when summary overlay close button is clicked.
        """
        self._publish_manager.tree.clear(clear_persistent=True)
        self._publish_manager.collect_session()

        self._synchronize_tree()

        self.ui.validate.show()
        self.ui.publish.show()
        self.ui.close.hide()

        self.ui.button_container.show()
        self.ui.item_settings.setEnabled(True)

        self._overlay.hide()

        self.ui.items_tree.select_first_item()

        self._validation_run = False

    def _find_inherited_description_item(self, item):
        """
        Finds the item to inherit the description from.
        """
        def _get_parent_item(item):
            if item is None:
                return None
            elif not isinstance(item, TreeNodeItem) or item.inherit_description:
                return _get_parent_item(item.parent())
            else:
                return item

        return _get_parent_item(item.parent())

    def _find_inherited_description(self, node_item):
        """
        Returns inherited description text for a given item.
        """
        inherited_desc_item = self._find_inherited_description_item(node_item)
        if inherited_desc_item:
            return inherited_desc_item.get_publish_instance().description
        else:
            return self._summary_comment

    def _get_tree_items(self):
        """
        Retrieves all the items from the tree.
        """
        tree_iterator = QtGui.QTreeWidgetItemIterator(self.ui.items_tree)
        tree_items = []
        while tree_iterator.value():
            tree_items.append(tree_iterator.value())
            tree_iterator += 1

        return tree_items

    def _task_generator(self, stage_name):
        """
        Yields tree items for pipeline stages and updates UI progress.
        """
        list_items = self._get_tree_items()

        for ui_item in list_items:

            if self._stop_processing_flagged:
                break

            if not ui_item.checked:
                continue

            self._progress_handler.push(
                "%s: %s" % (stage_name, ui_item,),
                ui_item.icon,
                ui_item.get_publish_instance(),
            )

            try:
                yield ui_item
            finally:
                self._progress_handler.increment_progress()
                self._progress_handler.pop()

    def _validate_task_generator(self, is_standalone):
        """
        Generates tasks for the validation phase.
        """
        for ui_item in self._task_generator("Validating"):
            try:
                if isinstance(ui_item, TreeNodeTask):
                    (is_successful, error) = yield ui_item.task
                    error_msg = str(error)
                else:
                    is_successful = ui_item.validate(is_standalone)
                    error_msg = "Unknown validation error!"
            except Exception as e:
                ui_item.set_status_upwards(ui_item.STATUS_VALIDATION_ERROR, str(e))
                raise
            else:
                if is_successful:
                    if is_standalone:
                        ui_item.set_status(ui_item.STATUS_VALIDATION_STANDALONE)
                    else:
                        ui_item.set_status(ui_item.STATUS_VALIDATION)
                else:
                    ui_item.set_status_upwards(
                        ui_item.STATUS_VALIDATION_ERROR, error_msg
                    )

    def _publish_task_generator(self):
        """
        Generates tasks for the publish phase.
        """
        for ui_item in self._task_generator("Publishing"):
            try:
                if isinstance(ui_item, TreeNodeTask):
                    yield ui_item.task
                else:
                    ui_item.publish()
            except Exception as e:
                ui_item.set_status_upwards(ui_item.STATUS_PUBLISH_ERROR, str(e))
                raise
            else:
                ui_item.set_status(ui_item.STATUS_PUBLISH)

    def _finalize_task_generator(self):
        """
        Generates tasks for the finalize phase.
        """
        for ui_item in self._task_generator("Finalizing"):
            try:
                if isinstance(ui_item, TreeNodeTask):
                    finalize_exception = yield ui_item.task
                else:
                    ui_item.finalize()
                    finalize_exception = None
            except Exception as e:
                ui_item.set_status_upwards(ui_item.STATUS_FINALIZE_ERROR, str(e))
                raise
            else:
                if finalize_exception:
                    ui_item.set_status_upwards(
                        ui_item.STATUS_FINALIZE_ERROR, str(finalize_exception)
                    )
                else:
                    ui_item.set_status(ui_item.STATUS_FINALIZE)

    def _on_item_context_change(self, context):
        """
        Fires when a new context is selected for the current item
        """
        sync_required = False

        if self._current_item is None:
            for top_level_item in self._publish_manager.tree.root_item.children:
                if top_level_item.context_change_allowed:
                    top_level_item.context = context
                    sync_required = True
        else:
            if self._current_item.context_change_allowed:
                self._current_item.context = context
                sync_required = True

        if sync_required:
            self._synchronize_tree()

        self._validate_task_required()

    def _on_browse(self, folders=False):
        """Opens a file dialog to browse to files for publishing."""
        if not self.manual_load_enabled:
            return

        options = [
            QtGui.QFileDialog.DontResolveSymlinks,
            QtGui.QFileDialog.DontUseNativeDialog,
        ]

        if folders:
            caption = "Browse folders to publish image sequences"
            file_mode = QtGui.QFileDialog.Directory
            options.append(QtGui.QFileDialog.ShowDirsOnly)
        else:
            caption = "Browse files to publish"
            file_mode = QtGui.QFileDialog.ExistingFiles

        file_dialog = QtGui.QFileDialog(parent=self, caption=caption)
        file_dialog.setLabelText(QtGui.QFileDialog.Accept, "Select")
        file_dialog.setLabelText(QtGui.QFileDialog.Reject, "Cancel")
        file_dialog.setFileMode(file_mode)

        for option in options:
            file_dialog.setOption(option)

        if not file_dialog.exec_():
            return

        paths = file_dialog.selectedFiles()
        if paths:
            self._on_drop(paths)

    def _open_url(self, url):
        """Opens the supplied url in the appropriate browser."""
        try:
            logger.debug("Opening url: '%s'." % (url,))
            QtGui.QDesktopServices.openUrl(QtCore.QUrl(url))
        except Exception as e:
            logger.error("Failed to open url: '%s'. Reason: %s" % (url, e))

    def _trigger_stop_processing(self):
        """
        Triggers a request to stop processing
        """
        logger.info("Processing aborted.")
        self._stop_processing_flagged = True

    def _show_no_items_error(self):
        """
        Overlay when manual load is disabled and no items collected.
        """
        self.ui.validate.hide()
        self.ui.publish.hide()
        self.ui.button_container.hide()
        self.ui.progress_bar.hide()
        self.ui.close.show()

        self._progress_handler.logger.error("Drag & drop disabled.")

        self.ui.main_stack.setCurrentIndex(self.PUBLISH_SCREEN)
        self._overlay.show_no_items_error()

    def _validate_task_required(self):
        """
        Validates that a task is selected for every item and toggles buttons.
        """
        if not self._bundle.get_setting("task_required"):
            return

        all_items_selected_task = True
        for context_index in range(self.ui.items_tree.topLevelItemCount()):
            context_item = self.ui.items_tree.topLevelItem(context_index)

            if hasattr(context_item, "context") and not context_item.context.task:
                all_items_selected_task = False
                break

        if not all_items_selected_task:
            self.ui.publish.setEnabled(False)
            self.ui.validate.setEnabled(False)
            self.ui.context_widget.ui.task_label.setStyleSheet("color: red")
        else:
            self.ui.publish.setEnabled(True)
            self.ui.validate.setEnabled(True)
            self.ui.context_widget.ui.task_label.setStyleSheet("")
        self._refresh_publish_state()


class _TaskSelection(object):
    """
    Helper to manipulate a homogeneous selection of tasks as a single object.
    """

    def __init__(self, items=None):
        self._items = items or []

    def is_same_task_type(self, task_selection):
        if self._items and task_selection._items:
            return self._items[0].is_same_task_type(task_selection._items[0])
        elif not self._items and not task_selection._items:
            return True
        else:
            return False

    @property
    def has_custom_ui(self):
        if self._items:
            return self._items[0].plugin.has_custom_ui
        else:
            return False

    @property
    def plugin(self):
        if self._items:
            return self._items[0].plugin
        else:
            return None

    def get_settings(self, widget):
        if self._items:
            publish_items = self.get_task_items()
            return self._items[0].plugin.run_get_ui_settings(widget, publish_items)
        else:
            return {}

    def set_settings(self, widget, settings):
        if self._items:
            publish_items = self.get_task_items()
            self._items[0].plugin.run_set_ui_settings(widget, settings, publish_items)

    def get_task_items(self):
        return [task.item for task in self._items]

    def __iter__(self):
        return iter(self._items)

    def __eq__(self, other):
        return self._items == other._items

    def __bool__(self):
        return bool(self._items)
