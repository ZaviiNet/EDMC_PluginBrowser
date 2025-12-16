"""
plugin_manager_module.py - Handles fetching, installing, and removing EDMC plugins.
This is a module for the PluginBrowser plugin.

Copyright (c) EDCD, All Rights Reserved
Licensed under the GNU General Public License.
See LICENSE file.
"""
from __future__ import annotations

import json
import logging
import pathlib
import shutil
import zipfile
from typing import Callable, List, TypedDict, Optional

import requests

# Standard EDMC plugin imports
from EDMCLogging import get_main_logger

# Logger for this specific module
logger = get_main_logger()

# --- Constants ---
DEFAULT_PLUGIN_BROWSER_MANIFEST_URL = "https://raw.githubusercontent.com/ZaviiNet/edmc_plugins/main/plugin_manifest.json"
REQUEST_TIMEOUT = 15  # seconds

# --- Globals ---
# We store the root plugins directory here, set by load.py
_PLUGIN_ROOT: Optional[pathlib.Path] = None


def set_plugin_root(path: pathlib.Path) -> None:
    """Sets the root directory where plugins are stored."""
    global _PLUGIN_ROOT
    _PLUGIN_ROOT = path


# Define a type for the plugin information dictionary
class PluginInfo(TypedDict):
    id: str
    name: str
    version: str
    author: str
    description: str
    downloadUrl: str
    edmcCompatibility: Optional[str]
    repositoryUrl: Optional[str]


class InstalledPluginInfo(TypedDict):
    name: str  # Folder name
    status: str  # 'enabled' or 'disabled'
    path: pathlib.Path


# --- Helper Functions ---
def _status_update(callback: Optional[Callable[[str, Optional[str]], None]], message: str,
                   msg_type: Optional[str] = "info") -> None:
    """Helper to call the status callback if provided."""
    if callback:
        try:
            callback(message, msg_type)
        except Exception as e:
            logger.error(f"Error in status callback: {e}")
    else:
        if msg_type == "error":
            logger.error(message)
        elif msg_type == "warning":
            logger.warning(message)
        else:
            logger.info(message)


# --- Core Plugin Management Functions ---

def fetch_available_plugins(
        manifest_url: str,
        status_callback: Optional[Callable[[str, Optional[str]], None]] = None
) -> List[PluginInfo]:
    """Fetches the list of available plugins from the manifest URL."""
    if not manifest_url:
        _status_update(status_callback, "Plugin manifest URL is not configured.", "error")
        return []

    _status_update(status_callback, f"Fetching plugin manifest from {manifest_url}...", "info")
    try:
        response = requests.get(manifest_url, timeout=REQUEST_TIMEOUT)
        response.raise_for_status()
        plugins_data = response.json()

        if not isinstance(plugins_data, list):
            _status_update(status_callback, "Plugin manifest is not a valid list.", "error")
            return []

        valid_plugins: List[PluginInfo] = []
        for plugin_entry in plugins_data:
            if all(key in plugin_entry for key in ["id", "name", "version", "author", "description", "downloadUrl"]):
                plugin_entry.setdefault("edmcCompatibility", None)
                plugin_entry.setdefault("repositoryUrl", None)
                valid_plugins.append(plugin_entry)  # type: ignore
            else:
                logger.warning(f"Skipping invalid plugin entry in manifest: {plugin_entry.get('id', 'Unknown ID')}")

        _status_update(status_callback, f"Successfully fetched {len(valid_plugins)} plugins.", "info")
        return valid_plugins
    except requests.exceptions.RequestException as e:
        _status_update(status_callback, f"Network error fetching plugin manifest: {e}", "error")
    except json.JSONDecodeError as e:
        _status_update(status_callback, f"Error decoding plugin manifest JSON: {e}", "error")
    except Exception as e:
        _status_update(status_callback, f"An unexpected error occurred while fetching plugins: {e}", "error")
    return []


def get_installed_plugins() -> List[InstalledPluginInfo]:
    """Scans the plugin directory and returns a list of installed plugins."""
    if _PLUGIN_ROOT is None:
        logger.error("Plugin root directory not set. Cannot list installed plugins.")
        return []

    plugin_dir = _PLUGIN_ROOT
    installed_plugins: List[InstalledPluginInfo] = []

    if not plugin_dir.is_dir():
        logger.warning(f"Plugin directory not found: {plugin_dir}")
        return []

    for item in plugin_dir.iterdir():
        if item.is_dir():
            name = item.name
            status = "enabled"
            if name.endswith(".disabled"):
                name = name[:-len(".disabled")]
                status = "disabled"

            # Check for load.py to confirm it's a plugin
            if (item / "load.py").is_file():
                installed_plugins.append({
                    "name": name,
                    "status": status,
                    "path": item
                })  # type: ignore
            else:
                logger.debug(f"Directory '{item.name}' in plugins folder does not contain a load.py, skipping.")
    return installed_plugins


def install_plugin(
        plugin_info: PluginInfo,
        status_callback: Optional[Callable[[str, Optional[str]], None]] = None
) -> bool:
    """Downloads and installs a plugin into EDMC's plugin directory."""
    if _PLUGIN_ROOT is None:
        _status_update(status_callback, "Plugin root directory not configured.", "error")
        return False

    plugin_dir = _PLUGIN_ROOT
    plugin_id = plugin_info["id"]
    install_path = plugin_dir / plugin_id
    download_url = plugin_info["downloadUrl"]

    _status_update(status_callback, f"Installing plugin '{plugin_info['name']}' from {download_url}...", "info")

    if install_path.exists() or (install_path.with_suffix(install_path.suffix + ".disabled")).exists():
        _status_update(status_callback,
                       f"Plugin '{plugin_info['name']}' (folder: {plugin_id}) already exists or is disabled. Please remove it first.",
                       "error")
        return False

    temp_zip_path = plugin_dir / f"{plugin_id}_temp.zip"
    try:
        _status_update(status_callback, f"Downloading {download_url}...", "info")
        response = requests.get(download_url, timeout=REQUEST_TIMEOUT, stream=True)
        response.raise_for_status()

        with open(temp_zip_path, "wb") as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
        _status_update(status_callback, "Download complete.", "info")

        _status_update(status_callback, f"Extracting to {install_path}...", "info")
        with zipfile.ZipFile(temp_zip_path, "r") as zip_ref:
            top_level_members = list(set(member.split('/', 1)[0] for member in zip_ref.namelist()))

            if len(top_level_members) == 1 and top_level_members[0].rstrip('/') == plugin_id:
                temp_extract_path = plugin_dir / f"{plugin_id}_temp_extract"
                temp_extract_path.mkdir(parents=True, exist_ok=True)
                zip_ref.extractall(temp_extract_path)
                shutil.move(str(temp_extract_path / plugin_id), str(install_path))
                shutil.rmtree(temp_extract_path)
            else:
                install_path.mkdir(parents=True, exist_ok=True)
                zip_ref.extractall(install_path)

        _status_update(status_callback, f"Plugin '{plugin_info['name']}' installed successfully to {install_path}.",
                       "info")
        _status_update(status_callback, "Please restart EDMC for the new plugin to be loaded.", "warning")
        return True
    except Exception as e:
        _status_update(status_callback, f"Error installing plugin: {e}", "error")
        # Cleanup code ...
    finally:
        if temp_zip_path.exists():
            temp_zip_path.unlink()
    return False


def remove_plugin(
        plugin_folder_name: str,
        status_callback: Optional[Callable[[str, Optional[str]], None]] = None
) -> bool:
    if _PLUGIN_ROOT is None: return False
    plugin_dir = _PLUGIN_ROOT
    path_to_remove = plugin_dir / plugin_folder_name

    _status_update(status_callback, f"Removing plugin folder '{plugin_folder_name}'...", "info")

    if not path_to_remove.is_dir():
        _status_update(status_callback, f"Plugin folder '{plugin_folder_name}' not found.", "error")
        return False
    try:
        shutil.rmtree(path_to_remove)
        _status_update(status_callback, f"Plugin '{plugin_folder_name}' removed successfully.", "info")
        _status_update(status_callback, "Please restart EDMC for changes to take effect.", "warning")
        return True
    except Exception as e:
        _status_update(status_callback, f"Error removing plugin '{plugin_folder_name}': {e}", "error")
    return False


def enable_plugin(
        plugin_base_name: str,
        status_callback: Optional[Callable[[str, Optional[str]], None]] = None
) -> bool:
    if _PLUGIN_ROOT is None: return False
    plugin_dir = _PLUGIN_ROOT
    disabled_path = plugin_dir / f"{plugin_base_name}.disabled"
    enabled_path = plugin_dir / plugin_base_name

    _status_update(status_callback, f"Enabling plugin '{plugin_base_name}'...", "info")

    if not disabled_path.is_dir():
        _status_update(status_callback, f"Disabled plugin folder '{disabled_path.name}' not found.", "error")
        return False
    if enabled_path.exists():
        _status_update(status_callback, f"Enabled plugin folder '{enabled_path.name}' already exists.", "error")
        return False
    try:
        disabled_path.rename(enabled_path)
        _status_update(status_callback, f"Plugin '{plugin_base_name}' enabled successfully.", "info")
        _status_update(status_callback, "Please restart EDMC for changes to take effect.", "warning")
        return True
    except OSError as e:
        _status_update(status_callback, f"Error enabling plugin '{plugin_base_name}': {e}", "error")
    return False


def disable_plugin(
        plugin_base_name: str,
        status_callback: Optional[Callable[[str, Optional[str]], None]] = None
) -> bool:
    if _PLUGIN_ROOT is None: return False
    plugin_dir = _PLUGIN_ROOT
    enabled_path = plugin_dir / plugin_base_name
    disabled_path = plugin_dir / f"{plugin_base_name}.disabled"

    _status_update(status_callback, f"Disabling plugin '{plugin_base_name}'...", "info")

    if not enabled_path.is_dir():
        _status_update(status_callback, f"Plugin folder '{enabled_path.name}' not found.", "error")
        return False
    if disabled_path.exists():
        _status_update(status_callback, f"Disabled plugin folder '{disabled_path.name}' already exists.", "error")
        return False
    try:
        enabled_path.rename(disabled_path)
        _status_update(status_callback, f"Plugin '{plugin_base_name}' disabled successfully.", "info")
        _status_update(status_callback, "Please restart EDMC for changes to take effect.", "warning")
        return True
    except OSError as e:
        _status_update(status_callback, f"Error disabling plugin '{plugin_base_name}': {e}", "error")
    return False