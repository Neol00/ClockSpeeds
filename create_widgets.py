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
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, Gio, Gdk
import logging
from log_setup import get_logger
from shared import global_state

class WidgetFactory:
    def __init__(self, spacing=global_state.SPACING):
        self.logger = get_logger()
        self.spacing = spacing

    def create_grid(self):
        try:
            grid = Gtk.Grid()
            return grid
        except Exception as e:
            self.logger.error("Failed to create grid: %s", e)
            return None

    def create_notebook(self, parent):
        try:
            notebook = Gtk.Notebook()
            parent.pack_start(notebook, expand=True, fill=True, padding=self.spacing)
            notebook.get_style_context().add_class('notebook')
            return notebook
        except Exception as e:
            self.logger.error("Failed to create notebook: %s", e)
            return None

    def create_tab(self, notebook, tab_name):
        try:
            scrolled_window = Gtk.ScrolledWindow()
            scrolled_window.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
            scrolled_window.set_min_content_width(535)
            scrolled_window.set_min_content_height(350)

            tab = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
            tab.set_border_width(4)
            scrolled_window.add(tab)

            tab_label = Gtk.Label(label=tab_name)
            tab_label.get_style_context().add_class('tab-label')
            notebook.append_page(scrolled_window, tab_label)

            tab.show_all()
            tab_label.show()
            scrolled_window.show_all()
            return tab
        except Exception as e:
            self.logger.error("Failed to create tab: %s", e)
            return None

    def create_settings_tab(self, notebook, settings_tab_name):
        try:
            settings_tab = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
            settings_tab.set_border_width(10)
            settings_tab_label = Gtk.Label(label=settings_tab_name)
            settings_tab_label.get_style_context().add_class('settings-tab-label')
            notebook.append_page(settings_tab, settings_tab_label)
            settings_tab.show_all()
            settings_tab_label.show()
            return settings_tab
        except Exception as e:
            self.logger.error("Failed to create settings tab: %s", e)
            return None

    def create_about_tab(self, notebook, about_tab_name):
        try:
            about_tab = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
            about_tab.set_border_width(10)
            about_tab_label = Gtk.Label(label=about_tab_name)
            about_tab_label.get_style_context().add_class('about-tab-label')
            notebook.append_page(about_tab, about_tab_label)
            about_tab.show_all()
            about_tab_label.show()
            return about_tab
        except Exception as e:
            self.logger.error("Failed to create about tab: %s", e)
            return None

    def create_label(self, container, text=None, markup=None, style=None, x=0, y=0, **kwargs):
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

    def create_entry(self, container, text="N/A MHz", editable=False, width_chars=10, x=0, y=0, **kwargs):
        try:
            entry = Gtk.Entry()
            entry.set_text(text)
            entry.set_editable(editable)
            entry.set_width_chars(width_chars)

            # Override the event handlers to make the Entry non-interactable
            entry.connect("button-press-event", lambda w, e: True)
            entry.connect("button-release-event", lambda w, e: True)
            entry.connect("key-press-event", lambda w, e: True)

            self._set_margins(entry, **kwargs)

            self._attach_widget(container, entry, x, y)
            return entry
        except Exception as e:
            self.logger.error("Failed to create entry: %s", e)
            return None

    def create_cellrendererprogress(self, container, x=0, y=0, **kwargs):
        try:
            list_store = Gtk.ListStore(int, str)
            list_store.append([0, "0%"])

            tree_view = Gtk.TreeView(model=list_store)
            tree_view.add_events(Gdk.EventMask.BUTTON_PRESS_MASK | Gdk.EventMask.BUTTON_RELEASE_MASK)

            # Override the event handlers to make the TreeView non-interactable
            tree_view.connect("button-press-event", lambda w, e: True)
            tree_view.connect("button-release-event", lambda w, e: True)

            progress_renderer = Gtk.CellRendererProgress()
            column = Gtk.TreeViewColumn("CPU Load", progress_renderer, value=0, text=1)

            tree_view.append_column(column)

            self._set_margins(tree_view, **kwargs)

            self._attach_widget(container, tree_view, x, y)
            return tree_view
        except Exception as e:
            self.logger.error("Failed to create CellRendererProgress: %s", e)
            return None

    def create_scale(self, container, command, from_value, to_value, x=0, y=0, **kwargs):
        try:
            adjustment = Gtk.Adjustment(lower=from_value, upper=to_value)
            scale = Gtk.Scale(orientation=Gtk.Orientation.HORIZONTAL, adjustment=adjustment)
            scale.set_digits(0)
            if command:
                scale.connect("value-changed", command)

            self._set_margins(scale, **kwargs)

            self._attach_widget(container, scale, x, y)
            return scale
        except Exception as e:
            self.logger.error("Failed to create scale: %s", e)
            return None

    def create_button(self, container, text, command=None, press_event=None, release_event=None, x=0, y=0, **kwargs):
        try:
            button = Gtk.Button(label=text)
            if command:
                button.connect("clicked", command)
            button.get_style_context().add_class('button')

            self._set_margins(button, **kwargs)

            self._attach_widget(container, button, x, y)
            return button
        except Exception as e:
            self.logger.error("Failed to create button: %s", e)
            return None

    def create_info_button(self, container, callback, x=0, y=0):
        try:
            button = Gtk.Button()
            button.connect("clicked", callback)
            info_icon = Gio.ThemedIcon(name="dialog-information")
            info_image = Gtk.Image.new_from_gicon(info_icon, Gtk.IconSize.BUTTON)
            button.add(info_image)
            button.set_relief(Gtk.ReliefStyle.NONE)

            self._attach_widget(container, button, x, y)
            return button
        except Exception as e:
            self.logger.error("Failed to create info button: %s", e)
            return None

    def create_spinbutton(self, container, value, lower, upper, step_increment, page_increment, climb_rate, digits, command=None, x=0, y=0, **kwargs):
        try:
            adjustment = Gtk.Adjustment(value=value, lower=lower, upper=upper, step_increment=step_increment, page_increment=page_increment)
            spinbutton = Gtk.SpinButton(adjustment=adjustment, climb_rate=climb_rate, digits=digits)
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
            
            self._set_margins(combobox, **kwargs)
                    
            self._attach_widget(container, combobox, x, y)
            return combobox
        except Exception as e:
            self.logger.error("Failed to create combobox: %s", e)
            return None

    def create_checkbutton(self, container, text, variable, command=None, style=None, x=0, y=0, **kwargs):
        try:
            checkbutton = Gtk.CheckButton(label=text)
            if command is not None:
                checkbutton.connect("toggled", command)

            self._set_margins(checkbutton, **kwargs)

            self._attach_widget(container, checkbutton, x, y)
            return checkbutton
        except Exception as e:
            self.logger.error("Failed to create checkbutton: %s", e)
            return None

    def _attach_widget(self, container, widget, x=0, y=0):
        try:
            if widget.get_parent() is not None:
                self.logger.warning("Widget already has a parent and won't be reattached.")
                return

            if isinstance(container, Gtk.Dialog):
                content_area = container.get_content_area()
                content_area.pack_start(widget, expand=True, fill=True, padding=self.spacing)
            elif isinstance(container, Gtk.Grid):
                next_row = len(container.get_children()) // container.get_column_homogeneous()
                next_col = len(container.get_children()) % container.get_column_homogeneous()
                container.attach(widget, next_col, next_row, 1, 1)
            elif isinstance(container, Gtk.Box):
                container.pack_start(widget, expand=True, fill=True, padding=self.spacing)
            elif isinstance(container, Gtk.Fixed):
                container.put(widget, x, y)
            else:
                self.logger.error(f"Container of type {type(container).__name__} does not support pack_start or attach")
                raise TypeError(f"Unsupported container type {type(container).__name__}")
        except Exception as e:
            self.logger.error("Failed to attach widget: %s", e)

    def _set_margins(self, widget, **kwargs):
        margin_properties = {
            'margin_start': widget.set_margin_start,
            'margin_end': widget.set_margin_end,
            'margin_top': widget.set_margin_top,
            'margin_bottom': widget.set_margin_bottom,
        }
        for prop, setter in margin_properties.items():
            if prop in kwargs and kwargs[prop] is not None:
                setter(kwargs[prop])

widget_factory = WidgetFactory()
