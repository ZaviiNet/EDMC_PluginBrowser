# **EDMC Plugin Browser**

Plugin Version: (Specify your plugin version here, e.g., 1.0.0)  
Compatible with EDMC: (Specify compatible EDMC versions, e.g., \>=5.0.0)

## **Description**

The EDMC Plugin Browser is a plugin for Elite Dangerous Market Connector (EDMC) that allows users to easily discover, install, manage, and remove other EDMC plugins directly from within the EDMC settings interface.

It fetches a list of available plugins from a configurable manifest URL, displays them alongside currently installed plugins, and provides simple actions for installation, removal, enabling, and disabling.

## **Features**

* **Browse Available Plugins:** View a list of plugins available for installation from a remote manifest.  
  * Displays plugin name, author, version, and description.  
  * Option to refresh the list of available plugins.  
  * Link to the plugin's repository (if provided in the manifest).  
* **Install Plugins:** Download and install plugins with a single click.  
  * Handles ZIP file extraction.  
  * Warns that EDMC needs a restart after installation.  
* **Manage Installed Plugins:**  
  * View a list of currently installed plugins and their status (enabled/disabled).  
  * Enable or disable installed plugins (requires EDMC restart).  
  * Remove installed plugins (requires EDMC restart).  
* **Configurable Manifest URL:** Users can change the URL from which the list of available plugins is fetched.  
* **Status Updates:** Provides feedback messages for all operations.

## **Installation**

1. **Download:**  
   * Go to the [releases page of this plugin's repository](http://docs.google.com/YOUR_PLUGIN_RELEASE_PAGE_URL_HERE).  
   * Download the latest .zip file for the Plugin Browser.  
2. **Install in EDMC:**  
   * Open EDMC.  
   * Go to File \-\> Settings \-\> Plugins tab.  
   * Click the Open Plugins Folder button. This will open the directory where EDMC stores user-installed plugins (usually %LOCALAPPDATA%\\EDMarketConnector\\plugins\\ on Windows).  
   * Extract the contents of the downloaded .zip file into this plugins directory. You should have a folder named PluginBrowser (or similar, depending on how the zip is structured) containing load.py and plugin\_manager\_module.py.  
3. **Restart EDMC:** Close and reopen EDMarketConnector for the new plugin to be loaded.

## **Usage**

1. Open EDMC.  
2. Go to File \-\> Settings.  
3. You will find a new tab labeled "**Plugin Browser**".  
4. **Manifest URL:**  
   * The first field allows you to set the URL for the plugin manifest file. By default, it points to \[YOUR\_DEFAULT\_MANIFEST\_URL\_HERE\_OR\_DESCRIBE\_IT\]. You can change this if you have an alternative manifest source.  
   * Changes to this URL are saved when you click "OK" on the main EDMC Settings window.  
5. **Available Plugins:**  
   * This section lists plugins fetched from the Manifest URL.  
   * Click **"Refresh List"** to update the list of available plugins.  
   * Select a plugin from the list to enable the "Install Selected" and "View Repository" buttons.  
   * Click **"Install Selected"** to download and install the chosen plugin. You will be prompted to confirm.  
   * Click **"View Repository"** to open the plugin's code repository in your web browser (if a URL is provided in the manifest).  
6. **Installed Plugins:**  
   * This section lists all plugins currently detected in your EDMC plugins folder.  
   * Select a plugin from this list to enable the "Enable/Disable" and "Remove Selected" buttons.  
   * Click **"Enable/Disable"** to toggle the selected plugin's status. This works by renaming the plugin's folder (adding/removing .disabled).  
   * Click **"Remove Selected"** to delete the plugin's folder. You will be prompted to confirm.  
7. **Restart EDMC:** After installing, removing, enabling, or disabling any plugin, you **must restart EDMC** for the changes to take full effect. The Plugin Browser will remind you of this.  
8. **Status Bar:** A status bar at the bottom of the tab provides feedback on ongoing operations and any errors encountered.

## **Configuration**

The main configuration option for the Plugin Browser itself is the **Manifest URL**, which can be set directly in its settings tab. This URL points to a JSON file that lists available plugins.

The default manifest URL is: \[YOUR\_DEFAULT\_MANIFEST\_URL\_HERE\_OR\_DESCRIBE\_IT\]

(If you are maintaining a community manifest, provide details or a link here.)

## **Troubleshooting**

* **"Failed to fetch plugin list"**:  
  * Check your internet connection.  
  * Ensure the Manifest URL in the settings is correct and accessible.  
  * The remote server hosting the manifest might be temporarily unavailable.  
* **Plugin installation fails**:  
  * Check the status messages for details. It could be a network error during download, a corrupted ZIP file, or a file permission issue in your plugins directory.  
  * Ensure you have write permissions to your EDMC plugins folder.  
* **Plugin doesn't appear after install/enable**:  
  * Make sure you have restarted EDMC.  
  * Verify the plugin folder structure is correct inside your main EDMC plugins directory (e.g., PluginBrowser/load.py).

For further issues, please check the EDMC logs (%TEMP%\\EDMarketConnector.log and %TEMP%\\EDMarketConnector\\EDMarketConnector-debug.log on Windows) and report issues on this plugin's repository: \[YOUR\_PLUGIN\_ISSUES\_URL\_HERE\]

## **For Plugin Developers (Wanting to be listed in a Manifest)**

To have your plugin listed by a Plugin Browser instance, your plugin needs to be included in the JSON manifest file that the browser is configured to use. The manifest typically requires information like:

* id: A unique machine-readable identifier for your plugin (e.g., my-cool-plugin).  
* name: The human-readable name of your plugin.  
* version: The current version of your plugin.  
* author: Your name or your organization's name.  
* description: A brief description of what your plugin does.  
* downloadUrl: A direct link to the .zip file of your plugin.  
* edmcCompatibility (optional): A string indicating EDMC version compatibility (e.g., \>=5.0.0).  
* repositoryUrl (optional): A link to your plugin's source code repository (e.g., GitHub).

Contact the maintainer of the specific plugin manifest you wish to be added to.

## **License**

This plugin (EDMC Plugin Browser) is licensed under the GNU General Public License v2.0 or later.  
(Or specify your chosen license if different)  
*This README is for the EDMC Plugin Browser plugin. For EDMarketConnector itself, please refer to its own documentation.*
