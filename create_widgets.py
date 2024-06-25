#!/usr/bin/env python

# ClockSpeeds - CPU Monitoring and Control Application for Linux
# Copyright (c) 2024 Noel Ejemyr <noelejemyr@protonmail.com>
#
# ClockSpeeds is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# ClockSpeeds is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program. If not, see <https://www.gnu.org/licenses/>.

import gi
gi.require_version('Gtk', '4.0')
from gi.repository import Gtk
import logging
from log_setup import get_logger
from shared import global_state

class WidgetFactory:
    def __init__(self):
        # Initialize the logger
        self.logger = get_logger()

        self.scales = []  # Store references to created scales

    def create_window(self, title, transient_for=None, default_width=100, default_height=100):
        # Create a new Gtk.Window
        try:
            window = Gtk.Window()
            window.set_title(title)
            window.set_default_size(default_width, default_height)
            if transient_for:
                window.set_transient_for(transient_for)
            window.set_resizable(False)
            return window
        except Exception as e:
            self.logger.error("Failed to create window: %s", e)
            return None

    def create_box(self, container, x=0, y=0, **kwargs):
        # Create a new Gtk.Box widget with vertical orientation and add it to the container
        try:
            box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
            self._set_margins(box, **kwargs)
            self._attach_widget(container, box, x, y)
            return box
        except Exception as e:
            self.logger.error("Failed to create box: %s", e)
            return None

    def create_grid(self):
        # Create a new Gtk.Grid widget
        try:
            grid = Gtk.Grid()
            return grid
        except Exception as e:
            self.logger.error("Failed to create grid: %s", e)
            return None

    def create_notebook(self, parent):
        # Create a new Gtk.Notebook widget and add it to the parent container
        try:
            notebook = Gtk.Notebook()
            parent.append(notebook)
            notebook.get_style_context().add_class('notebook')
            return notebook
        except Exception as e:
            self.logger.error("Failed to create notebook: %s", e)
            return None

    def create_tab(self, notebook, tab_name):
        # Create a new tab for the Gtk.Notebook widget
        try:
            scrolled_window = Gtk.ScrolledWindow()
            scrolled_window.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
            scrolled_window.set_min_content_width(535)
            scrolled_window.set_min_content_height(400)

            tab = Gtk.Box()
            tab.set_orientation(Gtk.Orientation.VERTICAL)
            scrolled_window.set_child(tab)

            tab_label = Gtk.Label(label=tab_name)
            tab_label.get_style_context().add_class('tab-label')
            notebook.append_page(scrolled_window, tab_label)
            return tab
        except Exception as e:
            self.logger.error("Failed to create tab: %s", e)
            return None

    def create_settings_tab(self, notebook, settings_tab_name):
        # Create a new settings tab for the Gtk.Notebook widget
        try:
            settings_tab = Gtk.Box()
            settings_tab.set_orientation(Gtk.Orientation.VERTICAL)
            settings_tab_label = Gtk.Label(label=settings_tab_name)
            settings_tab_label.get_style_context().add_class('settings-tab-label')
            notebook.append_page(settings_tab, settings_tab_label)
            return settings_tab
        except Exception as e:
            self.logger.error("Failed to create settings tab: %s", e)
            return None

    def create_about_tab(self, notebook, about_tab_name):
        # Create a new about tab for the Gtk.Notebook widget
        try:
            about_tab = Gtk.Box()
            about_tab.set_orientation(Gtk.Orientation.VERTICAL)
            about_tab_label = Gtk.Label(label=about_tab_name)
            about_tab_label.get_style_context().add_class('about-tab-label')
            notebook.append_page(about_tab, about_tab_label)
            return about_tab
        except Exception as e:
            self.logger.error("Failed to create about tab: %s", e)
            return None

    def create_label(self, container, text=None, markup=None, style=None, x=0, y=0, **kwargs):
        # Create a new Gtk.Label widget and add it to the container
        try:
            label = Gtk.Label()
            if markup:
                label.set_markup(markup)
            else:
                label.set_text(text)

            self._set_margins(label, **kwargs)
            self._attach_widget(container, label, x, y)
            return label
        except Exception as e:
            self.logger.error("Failed to create label: %s", e)
            return None

    def create_entry(self, container, text="N/A", editable=False, width_chars=10, x=0, y=0, **kwargs):
        # Create a new Gtk.Entry widget and add it to the container
        try:
            entry = Gtk.Entry()
            entry.set_text(text)
            entry.set_editable(editable)
            entry.set_width_chars(width_chars)
            entry.set_can_focus(False)  # Disable focus if not editable

            self._set_margins(entry, **kwargs)
            self._attach_widget(container, entry, x, y)
            return entry
        except Exception as e:
            self.logger.error("Failed to create entry: %s", e)
            return None

    def create_cellrendererprogress(self, container, x=0, y=0, **kwargs):
        # Create a new Gtk.CellRendererProgress widget and add it to the container
        try:
            list_store = Gtk.ListStore(int, str)
            list_store.append([0, "0%"])

            tree_view = Gtk.TreeView(model=list_store)

            # Create and configure the progress renderer
            progress_renderer = Gtk.CellRendererProgress()
            tree_view.get_selection().set_mode(Gtk.SelectionMode.NONE)  # Disable row selection

            column = Gtk.TreeViewColumn("CPU Load", progress_renderer, value=0, text=1)
            tree_view.append_column(column)

            self._set_margins(tree_view, **kwargs)
            self._attach_widget(container, tree_view, x, y)
            return tree_view
        except Exception as e:
            self.logger.error("Failed to create CellRendererProgress: %s", e)
            return None

    def create_scale(self, container, command, from_value, to_value, x=0, y=0, Negative=False, Frequency=False, **kwargs):
        # Create a new Gtk.Scale widget and add it to the container
        try:
            adjustment = Gtk.Adjustment(lower=from_value, upper=to_value, step_increment=1)
            scale = Gtk.Scale(orientation=Gtk.Orientation.HORIZONTAL, adjustment=adjustment)
            scale.set_digits(2 if Frequency and global_state.display_ghz else 0)  # Set scale digits based on display_ghz if Frequency is True
            scale.set_round_digits(2 if Frequency and global_state.display_ghz else 0)
            overlay = Gtk.Overlay()
            overlay.add_overlay(scale)
            label = Gtk.Label()

            def update_label(scale, label):
                value = scale.get_value()
                if Frequency and global_state.display_ghz:
                    display_value = value / 1000.0
                    label.set_text(f"{display_value:.2f} GHz")
                else:
                    if Negative:
                        display_value = -value
                    else:
                        display_value = value
                    label.set_text(f"{display_value:.0f} MHz" if Frequency else str(int(display_value)))
                self._update_scale_label_position(scale, label)

            def on_scale_value_changed(scale):
                update_label(scale, label)

            if command:
                scale.connect("value-changed", command)
            scale.connect("value-changed", lambda s: on_scale_value_changed(s))
            on_scale_value_changed(scale)
            overlay.add_overlay(label)
            label.set_halign(Gtk.Align.START)
            label.set_valign(Gtk.Align.CENTER)

            self._set_margins(overlay, **kwargs)
            self._attach_widget(container, overlay, x, y)

            # Store references to the scale and label for later updates
            self.scales.append((scale, label, Frequency))

            return scale
        except Exception as e:
            self.logger.error(f"Failed to create scale: {e}")
            return None

    def update_all_scale_labels(self):
        # Update the position of all scale labels
        for scale, label in self.scales:
            self._update_scale_label_position(scale, label)

    def _update_scale_label_position(self, scale, label):
        try:
            adjustment = scale.get_adjustment()
            scale_width = scale.get_allocated_width()
            handle_position = (scale.get_value() - adjustment.get_lower()) / (adjustment.get_upper() - adjustment.get_lower())
            handle_x = scale_width * handle_position

            label_width = label.get_allocated_width()
            label_x = handle_x - (label_width / 2)
            label_x = max(min(label_x, scale_width - label_width), 0)
            label.set_margin_start(int(label_x))
            label.set_margin_top(65)
        except Exception as e:
            self.logger.error(f"Failed to calculate scales position: {e}")

    def update_frequency_scale_labels(self):
        # Update the labels for all frequency scales
        for scale, label, is_frequency in self.scales:
            if is_frequency:  # Only update if it is a frequency scale
                try:
                    adjustment = scale.get_adjustment()
                    value = adjustment.get_value()
                    if global_state.display_ghz:
                        display_value = value / 1000.0
                        label.set_text(f"{display_value:.2f} GHz")
                    else:
                        label.set_text(f"{value:.0f} MHz")
                    self._update_scale_label_position(scale, label)
                except Exception as e:
                    self.logger.error(f"Error updating label for scale: {e}")

    def create_button(self, container, text, command=None, press_event=None, release_event=None, x=0, y=0, **kwargs):
        # Create a new Gtk.Button widget and add it to the container
        try:
            button = Gtk.Button()
            # Use a label widget for the text inside the button
            label = Gtk.Label(label=text)
            button.set_child(label)
            if command:
                button.connect("clicked", command)
            button.get_style_context().add_class('button')

            self._set_margins(button, **kwargs)
            self._attach_widget(container, button, x, y)
            return button
        except Exception as e:
            self.logger.error("Failed to create button: %s", e)
            return None

    def create_info_button(self, container, callback, x=0, y=0, **kwargs):
        # Create a new info button (Gtk.Button) with an information icon and add it to the container
        try:
            button = Gtk.Button()
            button.connect("clicked", callback)

            # Create an image with the icon name
            info_icon = Gtk.Image.new_from_icon_name("dialog-information")
            button.set_child(info_icon)

            self._set_margins(button, **kwargs)
            self._attach_widget(container, button, x, y)
            return button
        except Exception as e:
            self.logger.error("Failed to create info button: %s", e)
            return None

    def create_spinbutton(self, container, value, lower, upper, step_increment, page_increment, climb_rate, digits, command=None, x=0, y=0, **kwargs):
        # Create a new Gtk.SpinButton widget and add it to the container
        try:
            adjustment = Gtk.Adjustment(value=value, lower=lower, upper=upper, step_increment=step_increment, page_increment=page_increment)
            spinbutton = Gtk.SpinButton()
            spinbutton.set_adjustment(adjustment)
            spinbutton.set_climb_rate(climb_rate)
            spinbutton.set_digits(digits)
            if command:
                spinbutton.connect("value-changed", command)

            self._set_margins(spinbutton, **kwargs)
            self._attach_widget(container, spinbutton, x, y)
            return spinbutton
        except Exception as e:
            self.logger.error("Failed to create SpinButton: %s", e)
            return None

    def create_combobox(self, container, values, command, style=None, x=0, y=0, **kwargs):
        try:
            store = Gtk.ListStore(str)
            for val in values:
                store.append([val])
            combobox = Gtk.ComboBox.new_with_model(store)
            renderer_text = Gtk.CellRendererText()
            combobox.pack_start(renderer_text, True)
            combobox.add_attribute(renderer_text, "text", 0)
            combobox.connect("changed", command)

            # Apply hexpand and vexpand if provided in kwargs
            if 'hexpand' in kwargs:
                combobox.set_hexpand(kwargs['hexpand'])
            if 'vexpand' in kwargs:
                combobox.set_vexpand(kwargs['vexpand'])

            self._set_margins(combobox, **kwargs)
            self._attach_widget(container, combobox, x, y)
            return combobox
        except Exception as e:
            self.logger.error("Failed to create combobox: %s", e)
            return None

    def create_checkbutton(self, container, text, variable, command=None, style=None, x=0, y=0, **kwargs):
        # Create a new Gtk.CheckButton widget and add it to the container
        try:
            checkbutton = Gtk.CheckButton()
            label = Gtk.Label(label=text)
            checkbutton.set_child(label)
            if command is not None:
                checkbutton.connect("toggled", command)

            self._set_margins(checkbutton, **kwargs)
            self._attach_widget(container, checkbutton, x, y)
            return checkbutton
        except Exception as e:
            self.logger.error("Failed to create checkbutton: %s", e)
            return None

    def _attach_widget(self, container, widget, x=0, y=0):
        # Attach a widget to the given container
        try:
            if widget.get_parent() is not None:
                self.logger.warning("Widget already has a parent and won't be reattached.")
                return

            if isinstance(container, Gtk.Dialog):
                content_area = container.get_content_area()
                content_area.append(widget)
            elif isinstance(container, Gtk.Grid):
                next_row = len(container.get_children()) // container.get_column_homogeneous()
                next_col = len(container.get_children()) % container.get_column_homogeneous()
                container.attach(widget, next_col, next_row, 1, 1)
            elif isinstance(container, Gtk.Box):
                container.append(widget)
            elif isinstance(container, Gtk.Fixed):
                container.put(widget, x, y)
            elif isinstance(container, (Gtk.ApplicationWindow, Gtk.Popover, Gtk.Window)):
                container.set_child(widget)
            else:
                self.logger.error(f"Container of type {type(container).__name__} does not support pack_start or attach")
                raise TypeError(f"Unsupported container type {type(container).__name__}")
        except Exception as e:
            self.logger.error("Failed to attach widget: %s", e)

    def _set_margins(self, widget, **kwargs):
        # Set margins for a widget if specified in kwargs
        margin_properties = {
            'margin_start': widget.set_margin_start,
            'margin_end': widget.set_margin_end,
            'margin_top': widget.set_margin_top,
            'margin_bottom': widget.set_margin_bottom,
        }
        for prop, setter in margin_properties.items():
            if prop in kwargs and kwargs[prop] is not None:
                setter(kwargs[prop])

# Create an instance of WidgetFactory
widget_factory = WidgetFactory()
