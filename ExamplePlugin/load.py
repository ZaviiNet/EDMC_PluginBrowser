"""
Example Plugin for EDMC
"""

import tkinter as tk
from tkinter import ttk

# Must be unique, and should be the name of the folder
plugin_name = "ExamplePlugin"

class ExamplePlugin:
    def __init__(self, parent):
        self.frame = parent
        self.label = tk.Label(self.frame, text="This is an example plugin.")
        self.label.pack()

def plugin_start3(plugin_dir):
    """
    EDMC calls this function when the plugin is loaded.
    """
    return plugin_name

def plugin_stop():
    """
    EDMC calls this function when the plugin is unloaded or EDMC is shutting down.
    """
    pass

def plugin_prefs(parent, cmdr, is_beta):
    """
    EDMC calls this function to get the plugin's preferences tab.
    """
    frame = nb.Frame(parent)
    ExamplePlugin(frame)
    return frame
