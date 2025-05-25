"""
load.py - Plugin Browser for EDMarketConnector

Allows users to browse, install, and manage other EDMC plugins.
This is the main entry point for the PluginBrowser plugin.
"""
from __future__ import annotations

import tkinter as tk
from tkinter import ttk
from tkinter import messagebox as tk_messagebox
import threading
import logging # For plugin-specific logger setup
import pathlib
import webbrowser # For opening repository URLs
from typing import List, Optional, Callable, Any # For type hinting

# EDMC core imports
try:
    import myNotebook as nb # EDMC's custom notebook and frame widgets
    from config import config, appname, appversion # EDMC's global configuration object, app name, and appversion function
    from l10n import translations as tr # EDMC's translation system
    from EDMCLogging import get_plugin_logger # EDMC's helper for plugin loggers
except ImportError:
    # Fallback for standalone development/testing if EDMC isn't fully in PYTHONPATH
    print("CRITICAL: EDMC core modules (myNotebook, config, l10n, EDMCLogging) not found. "
          "This plugin must be run within EDMC.")
    # Define dummy/fallback versions if needed for linting or partial execution outside EDMC
    class DummyNb: # type: ignore
        Frame = ttk.Frame
        Notebook = ttk.Notebook
    nb = DummyNb() # type: ignore
    class DummyConfig: # type: ignore
        def get_str(self, key, default=None): return default
        def set(self, key, value): pass
    config = DummyConfig() # type: ignore
    def appversion(): return "0.0.0-fallback" # Dummy appversion
    class DummyTr: # type: ignore
        def tl(self, text): return text
    tr = DummyTr() # type: ignore
    def get_plugin_logger(name): return logging.getLogger(name) # type: ignore
    appname = "EDMarketConnector_fallback"


# Import this plugin's own logic module
try:
    # When running as part of EDMC, EDMC adds the plugin's directory to sys.path,
    # so we should be able to import modules from the same directory directly.
    import plugin_manager_module as plugin_manager
except ImportError as e:
    print(f"CRITICAL: Failed to import 'plugin_manager_module.py' from the PluginBrowser plugin directory: {e}. "
          "Ensure it's in the same folder as this load.py.")
    # Define a dummy plugin_manager if it's missing, so the rest of the UI can at least try to load
    class DummyPluginManager: # type: ignore
        DEFAULT_PLUGIN_BROWSER_MANIFEST_URL = "ERROR_MANIFEST_NOT_LOADED"
        PluginInfo = dict # type: ignore
        InstalledPluginInfo = dict # type: ignore
        def fetch_available_plugins(self, url, cb): return []
        def get_installed_plugins(self): return []
        def install_plugin(self, info, cb): return False
        def remove_plugin(self, name, cb): return False
        def enable_plugin(self, name, cb): return False
        def disable_plugin(self, name, cb): return False
    plugin_manager = DummyPluginManager() # type: ignore


# --- Plugin Globals ---
PLUGIN_NAME = "Plugin Browser" # This will be the tab name in settings
this_plugin_logger: Optional[logging.Logger] = None

# This will hold the instance of our UI class, created in plugin_prefs
plugin_browser_ui_instance: Optional['PluginBrowserUI'] = None


class PluginBrowserUI:
    """Encapsulates the UI for the Plugin Browser tab."""

    def __init__(self, parent_frame: nb.Frame): # parent_frame is nb.Frame
        self.parent_frame = parent_frame
        self.PADX = 10
        self.PADY = 5 # Increased for better spacing between sections
        self.BOXY = 2

        # Make the main content area expand
        self.parent_frame.rowconfigure(1, weight=1) # Available plugins section
        self.parent_frame.rowconfigure(2, weight=1) # Installed plugins section
        self.parent_frame.columnconfigure(0, weight=1)

        # --- Manifest URL Setting ---
        url_frame = ttk.LabelFrame(self.parent_frame, text=tr.tl("Plugin Manifest Source"), padding=(self.PADX, self.PADY))
        url_frame.grid(row=0, column=0, sticky=tk.EW, padx=self.PADX, pady=self.PADY)
        url_frame.columnconfigure(1, weight=1)

        ttk.Label(url_frame, text=tr.tl("Manifest URL:")).grid(row=0, column=0, padx=self.PADX, pady=self.BOXY, sticky=tk.W)
        self.manifest_url_var = tk.StringVar(
            value=config.get_str("PluginBrowser_ManifestURL", default=plugin_manager.DEFAULT_PLUGIN_BROWSER_MANIFEST_URL)
        )
        self.manifest_url_entry = ttk.Entry(url_frame, textvariable=self.manifest_url_var, width=70)
        self.manifest_url_entry.grid(row=0, column=1, padx=self.PADX, pady=self.BOXY, sticky=tk.EW)
        # Manifest URL is saved in prefs_changed

        # --- Available Plugins Section ---
        available_outer_frame = ttk.Frame(self.parent_frame)
        available_outer_frame.grid(row=1, column=0, sticky=tk.NSEW, padx=self.PADX, pady=self.PADY)
        available_outer_frame.columnconfigure(0, weight=1)
        available_outer_frame.rowconfigure(0, weight=1) # LabelFrame row expands

        available_frame = ttk.LabelFrame(available_outer_frame, text=tr.tl("Available Plugins"), padding=(self.PADX, self.PADY))
        available_frame.grid(row=0, column=0, sticky=tk.NSEW)
        available_frame.columnconfigure(0, weight=1) # Treeview column expands
        available_frame.rowconfigure(0, weight=1)    # Treeview row expands

        available_cols = ("name", "author", "version", "description")
        self.available_plugins_tree = ttk.Treeview(available_frame, columns=available_cols, show="headings", height=10, selectmode="browse")
        self.available_plugins_tree.grid(row=0, column=0, sticky=tk.NSEW, padx=self.PADX, pady=self.BOXY)

        for col, heading, width, stretch in [
            ("name", tr.tl("Name"), 150, tk.NO),
            ("author", tr.tl("Author"), 120, tk.NO),
            ("version", tr.tl("Version"), 70, tk.NO),
            ("description", tr.tl("Description"), 300, tk.YES)
        ]:
            self.available_plugins_tree.heading(col, text=heading)
            self.available_plugins_tree.column(col, width=width, anchor=tk.W, stretch=stretch)

        available_scrollbar = ttk.Scrollbar(available_frame, orient=tk.VERTICAL, command=self.available_plugins_tree.yview)
        self.available_plugins_tree.configure(yscrollcommand=available_scrollbar.set)
        available_scrollbar.grid(row=0, column=1, sticky='ns')

        available_buttons_frame = ttk.Frame(available_outer_frame)
        available_buttons_frame.grid(row=1, column=0, sticky=tk.EW, padx=self.PADX, pady=(self.BOXY, self.PADY)) # Add bottom padding

        self.refresh_button = ttk.Button(available_buttons_frame, text=tr.tl("Refresh List"), command=self._refresh_available_plugins_list)
        self.refresh_button.pack(side=tk.LEFT, padx=(0, self.PADX))

        self.install_button = ttk.Button(available_buttons_frame, text=tr.tl("Install Selected"), command=self._install_selected_plugin, state=tk.DISABLED)
        self.install_button.pack(side=tk.LEFT, padx=(0, self.PADX))

        self.view_repo_button = ttk.Button(available_buttons_frame, text=tr.tl("View Repository"), command=self._view_selected_plugin_repo, state=tk.DISABLED)
        self.view_repo_button.pack(side=tk.LEFT)

        # --- Installed Plugins Section ---
        installed_outer_frame = ttk.Frame(self.parent_frame)
        installed_outer_frame.grid(row=2, column=0, sticky=tk.NSEW, padx=self.PADX, pady=self.PADY)
        installed_outer_frame.columnconfigure(0, weight=1)
        installed_outer_frame.rowconfigure(0, weight=1)

        installed_frame = ttk.LabelFrame(installed_outer_frame, text=tr.tl("Installed Plugins"), padding=(self.PADX, self.PADY))
        installed_frame.grid(row=0, column=0, sticky=tk.NSEW)
        installed_frame.columnconfigure(0, weight=1)
        installed_frame.rowconfigure(0, weight=1)

        installed_cols = ("name", "status")
        self.installed_plugins_tree = ttk.Treeview(installed_frame, columns=installed_cols, show="headings", height=7, selectmode="browse")
        self.installed_plugins_tree.grid(row=0, column=0, sticky=tk.NSEW, padx=self.PADX, pady=self.BOXY)

        self.installed_plugins_tree.heading("name", text=tr.tl("Name"))
        self.installed_plugins_tree.column("name", width=250, anchor=tk.W, stretch=tk.YES)
        self.installed_plugins_tree.heading("status", text=tr.tl("Status"))
        self.installed_plugins_tree.column("status", width=100, anchor=tk.W, stretch=tk.NO)

        installed_scrollbar = ttk.Scrollbar(installed_frame, orient=tk.VERTICAL, command=self.installed_plugins_tree.yview)
        self.installed_plugins_tree.configure(yscrollcommand=installed_scrollbar.set)
        installed_scrollbar.grid(row=0, column=1, sticky='ns')

        installed_buttons_frame = ttk.Frame(installed_outer_frame)
        installed_buttons_frame.grid(row=1, column=0, sticky=tk.EW, padx=self.PADX, pady=(self.BOXY, self.PADY))

        self.enable_disable_button = ttk.Button(installed_buttons_frame, text=tr.tl("Enable/Disable"), command=self._toggle_selected_plugin_status, state=tk.DISABLED)
        self.enable_disable_button.pack(side=tk.LEFT, padx=(0, self.PADX))

        self.remove_button = ttk.Button(installed_buttons_frame, text=tr.tl("Remove Selected"), command=self._remove_selected_plugin, state=tk.DISABLED)
        self.remove_button.pack(side=tk.LEFT)

        # --- Status Label (at the bottom of the parent_frame) ---
        self.status_var = tk.StringVar()
        self.status_label = ttk.Label(self.parent_frame, textvariable=self.status_var, relief=tk.SUNKEN, anchor=tk.W)
        self.status_label.grid(row=3, column=0, sticky=tk.EW, padx=self.PADX, pady=(self.PADY * 2, self.PADY)) # pady adjusted

        self.available_plugins_list: List[plugin_manager.PluginInfo] = []

        self.available_plugins_tree.bind("<<TreeviewSelect>>", self._on_available_plugin_select)
        self.installed_plugins_tree.bind("<<TreeviewSelect>>", self._on_installed_plugin_select)

        self._refresh_installed_plugins_list()
        self._refresh_available_plugins_list()

    def _update_status(self, message: str, msg_type: Optional[str] = "info") -> None:
        if not self.status_label.winfo_exists(): return
        self.status_var.set(message)
        color = "black"
        if msg_type == "error": color = "red"
        elif msg_type == "warning": color = "orange" # Or another suitable color
        elif msg_type == "success": color = "green"
        self.status_label.config(foreground=color)

    def _run_threaded_task(self, task_func: Callable, *args: Any) -> None:
        def task_wrapper():
            try:
                task_func(*args)
            except Exception as e:
                if this_plugin_logger: this_plugin_logger.exception(f"Error in threaded task {task_func.__name__}: {e}")
                if self.parent_frame.winfo_exists():
                     self.parent_frame.after(0, lambda: self._update_status(f"Error: {e}", "error"))

        thread = threading.Thread(target=task_wrapper, daemon=True)
        thread.start()

    def _populate_available_plugins_tree(self, plugins_list: List[plugin_manager.PluginInfo]) -> None:
        if not self.available_plugins_tree.winfo_exists(): return
        self.available_plugins_tree.delete(*self.available_plugins_tree.get_children())
        self.available_plugins_list = plugins_list
        for plugin in plugins_list:
            desc = plugin.get("description", "")
            short_desc = desc[:100] + ("..." if len(desc) > 100 else "")
            self.available_plugins_tree.insert("", tk.END, values=(
                plugin.get("name", "N/A"), plugin.get("author", "N/A"),
                plugin.get("version", "N/A"), short_desc
            ), iid=plugin.get("id"))
        self._on_available_plugin_select()

    def _refresh_available_plugins_list(self) -> None:
        self._update_status(tr.tl("Refreshing available plugins list..."), "info")
        def fetch_and_populate():
            url = self.manifest_url_var.get()
            plugins = plugin_manager.fetch_available_plugins(url, self._update_status)
            if self.parent_frame.winfo_exists():
                self.parent_frame.after(0, lambda: self._populate_available_plugins_tree(plugins))
            if not plugins:
                if self.parent_frame.winfo_exists():
                    self.parent_frame.after(0, lambda: self._update_status(tr.tl("Failed to fetch plugin list or list is empty."), "warning"))
            else:
                if self.parent_frame.winfo_exists():
                    self.parent_frame.after(0, lambda: self._update_status(tr.tl("Available plugins list refreshed."), "info"))
        self._run_threaded_task(fetch_and_populate)

    def _populate_installed_plugins_tree(self, plugins_list: List[plugin_manager.InstalledPluginInfo]) -> None:
        if not self.installed_plugins_tree.winfo_exists(): return
        self.installed_plugins_tree.delete(*self.installed_plugins_tree.get_children())
        for plugin in plugins_list:
            self.installed_plugins_tree.insert("", tk.END, values=(plugin["name"], plugin["status"]), iid=plugin["name"])
        self._on_installed_plugin_select()

    def _refresh_installed_plugins_list(self) -> None:
        self._update_status(tr.tl("Refreshing installed plugins list..."), "info")
        def fetch_and_populate_installed():
            installed_plugins = plugin_manager.get_installed_plugins()
            if self.parent_frame.winfo_exists():
                self.parent_frame.after(0, lambda: self._populate_installed_plugins_tree(installed_plugins))
                self.parent_frame.after(0, lambda: self._update_status(tr.tl("Installed plugins list refreshed."), "info"))
        self._run_threaded_task(fetch_and_populate_installed)

    def _get_selected_available_plugin_info(self) -> Optional[plugin_manager.PluginInfo]:
        selected_item_ids = self.available_plugins_tree.selection()
        if not selected_item_ids: return None
        plugin_id = selected_item_ids[0] # Treeview selection returns IID
        return next((p for p in self.available_plugins_list if p['id'] == plugin_id), None)

    def _install_selected_plugin(self) -> None:
        plugin_to_install = self._get_selected_available_plugin_info()
        if not plugin_to_install:
            self._update_status(tr.tl("Please select a plugin to install."), "warning")
            return

        if tk_messagebox.askyesno(
            tr.tl("Confirm Installation"),
            tr.tl("Are you sure you want to install plugin '{plugin_name}'?\nEDMC will need to be restarted after installation.").format(plugin_name=plugin_to_install['name'])
        ):
            self._update_status(tr.tl("Installing {plugin_name}...").format(plugin_name=plugin_to_install['name']), "info")
            def do_install():
                success = plugin_manager.install_plugin(plugin_to_install, self._update_status)
                if self.parent_frame.winfo_exists():
                    self.parent_frame.after(0, self._refresh_installed_plugins_list)
                    if success: # Only refresh available if install was successful, to reduce calls
                        self.parent_frame.after(0, self._refresh_available_plugins_list)
                        self.parent_frame.after(0, lambda: tk_messagebox.showinfo(tr.tl("Installation Complete"), tr.tl("Plugin '{plugin_name}' installed. Please restart EDMC.").format(plugin_name=plugin_to_install['name'])))
            self._run_threaded_task(do_install)

    def _view_selected_plugin_repo(self) -> None:
        plugin_info = self._get_selected_available_plugin_info()
        if plugin_info and plugin_info.get("repositoryUrl"):
            try:
                webbrowser.open_new_tab(plugin_info["repositoryUrl"])
            except Exception as e:
                self._update_status(f"Could not open repository URL: {e}", "error")
                if this_plugin_logger: this_plugin_logger.error(f"Error opening URL {plugin_info['repositoryUrl']}: {e}")
        elif plugin_info:
            self._update_status(tr.tl("No repository URL specified for this plugin."), "info")
        else:
            self._update_status(tr.tl("Please select a plugin to view its repository."), "warning")


    def _remove_selected_plugin(self) -> None:
        selected_item_ids = self.installed_plugins_tree.selection()
        if not selected_item_ids: return

        item_values = self.installed_plugins_tree.item(selected_item_ids[0], "values")
        if not item_values or len(item_values) < 2: return

        plugin_folder_name = item_values[0]
        plugin_status = item_values[1]
        actual_folder_name_to_delete = f"{plugin_folder_name}.disabled" if plugin_status == "disabled" else plugin_folder_name

        if tk_messagebox.askyesno(
            tr.tl("Confirm Removal"),
            tr.tl("Are you sure you want to remove plugin '{plugin_name}'?\nThis will delete the plugin's folder. EDMC will need to be restarted.").format(plugin_name=plugin_folder_name)
        ):
            self._update_status(tr.tl("Removing {plugin_name}...").format(plugin_name=plugin_folder_name), "info")
            def do_remove():
                success = plugin_manager.remove_plugin(actual_folder_name_to_delete, self._update_status)
                if self.parent_frame.winfo_exists():
                    self.parent_frame.after(0, self._refresh_installed_plugins_list)
                    if success: # Only refresh available if remove was successful
                        self.parent_frame.after(0, self._refresh_available_plugins_list)
                        self.parent_frame.after(0, lambda: tk_messagebox.showinfo(tr.tl("Removal Complete"), tr.tl("Plugin '{plugin_name}' removed. Please restart EDMC.").format(plugin_name=plugin_folder_name)))
            self._run_threaded_task(do_remove)

    def _toggle_selected_plugin_status(self) -> None:
        selected_item_ids = self.installed_plugins_tree.selection()
        if not selected_item_ids: return

        item_values = self.installed_plugins_tree.item(selected_item_ids[0], "values")
        if not item_values or len(item_values) < 2: return

        plugin_name = item_values[0]
        current_status = item_values[1]

        action_text = tr.tl("enable") if current_status == "disabled" else tr.tl("disable")
        if tk_messagebox.askyesno(
            tr.tl("Confirm Action"),
            tr.tl("Are you sure you want to {action} plugin '{plugin_name}'?\nEDMC will need to be restarted.").format(action=action_text, plugin_name=plugin_name)
        ):
            self._update_status(tr.tl("Changing status of {plugin_name}...").format(plugin_name=plugin_name), "info")
            def do_toggle():
                success = False
                if current_status == "disabled":
                    success = plugin_manager.enable_plugin(plugin_name, self._update_status)
                else:
                    success = plugin_manager.disable_plugin(plugin_name, self._update_status)
                if self.parent_frame.winfo_exists():
                    self.parent_frame.after(0, self._refresh_installed_plugins_list)
                    if success:
                        self.parent_frame.after(0, lambda: tk_messagebox.showinfo(tr.tl("Status Changed"), tr.tl("Plugin '{plugin_name}' status changed. Please restart EDMC.").format(plugin_name=plugin_name)))
            self._run_threaded_task(do_toggle)

    def _on_available_plugin_select(self, event=None) -> None:
        if not self.available_plugins_tree.winfo_exists(): return
        selected = self.available_plugins_tree.selection()
        self.install_button.config(state=tk.NORMAL if selected else tk.DISABLED)

        plugin_info = self._get_selected_available_plugin_info()
        self.view_repo_button.config(state=tk.NORMAL if plugin_info and plugin_info.get("repositoryUrl") else tk.DISABLED)

    def _on_installed_plugin_select(self, event=None) -> None:
        if not self.installed_plugins_tree.winfo_exists(): return
        selected = self.installed_plugins_tree.selection()
        self.remove_button.config(state=tk.NORMAL if selected else tk.DISABLED)
        self.enable_disable_button.config(state=tk.NORMAL if selected else tk.DISABLED)

    def save_plugin_browser_config(self) -> None:
        """Saves settings specific to the Plugin Browser plugin."""
        config.set("PluginBrowser_ManifestURL", self.manifest_url_var.get())
        if this_plugin_logger: this_plugin_logger.info("Plugin Browser settings saved.")


# --- EDMC Plugin Hook Functions ---

def plugin_start3(plugin_dir: str) -> str:
    """
    EDMC calls this function when the plugin is loaded.
    :param plugin_dir: The directory path of the plugin.
    :return: The name of the plugin, which EDMC uses for display.
    """
    global this_plugin_logger
    try:
        current_plugin_folder_name = pathlib.Path(plugin_dir).name
        this_plugin_logger = get_plugin_logger(current_plugin_folder_name)
    except NameError:
        this_plugin_logger = logging.getLogger(f"{appname}.{PLUGIN_NAME}") # Fallback

    this_plugin_logger.info(f"Plugin '{PLUGIN_NAME}' version {appversion()} loaded from '{plugin_dir}'") # Use appversion from config module
    return PLUGIN_NAME


def plugin_stop() -> None:
    """
    EDMC calls this function when the plugin is unloaded or EDMC is shutting down.
    """
    if this_plugin_logger:
        this_plugin_logger.info(f"Plugin '{PLUGIN_NAME}' is stopping.")

def plugin_prefs(parent_notebook: nb.Notebook, cmdr: str, is_beta: bool) -> Optional[nb.Frame]:
    """
    EDMC calls this function to get the plugin's preferences tab.
    """
    global plugin_browser_ui_instance
    if not this_plugin_logger: return None

    this_plugin_logger.info(f"plugin_prefs called for CMDR '{cmdr}', is_beta: {is_beta}")

    plugin_settings_frame = nb.Frame(parent_notebook)

    # Make the frame expand to fill the tab
    plugin_settings_frame.columnconfigure(0, weight=1)
    plugin_settings_frame.rowconfigure(0, weight=0) # URL frame
    plugin_settings_frame.rowconfigure(1, weight=1) # Available plugins
    plugin_settings_frame.rowconfigure(2, weight=1) # Installed plugins
    plugin_settings_frame.rowconfigure(3, weight=0) # Status bar

    try:
        plugin_browser_ui_instance = PluginBrowserUI(plugin_settings_frame)
        # Store a reference on the frame itself if needed by prefs_changed, though it's a bit hacky
        setattr(plugin_settings_frame, '_plugin_browser_ui_instance', plugin_browser_ui_instance)
    except Exception as e:
        this_plugin_logger.error(f"Failed to create PluginBrowserUI: {e}", exc_info=True)
        error_label = ttk.Label(plugin_settings_frame, text=f"Error loading Plugin Browser UI: {e}\nCheck logs for details.")
        error_label.pack(padx=10, pady=10, fill=tk.BOTH, expand=True)

    return plugin_settings_frame


def prefs_changed(cmdr: str, is_beta: bool) -> None:
    """
    EDMC calls this function when the user closes the preferences dialog.
    """
    if not this_plugin_logger: return

    this_plugin_logger.info(f"prefs_changed called for CMDR '{cmdr}', is_beta: {is_beta}. Saving plugin settings.")
    if plugin_browser_ui_instance:
        try:
            plugin_browser_ui_instance.save_plugin_browser_config()
        except Exception as e:
            this_plugin_logger.error(f"Error saving Plugin Browser settings via prefs_changed: {e}", exc_info=True)
    else:
        this_plugin_logger.warning("PluginBrowserUI instance not found during prefs_changed, cannot save settings.")
