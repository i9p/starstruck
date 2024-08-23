import os
import platform
import sys
import tempfile
import logging

import openal
import pyogg
import numpy as np
import requests
from PIL import Image
import dearpygui.dearpygui as dpg

import cache
from pathlib import Path

TEXTURE_RESOLUTION = 256
ASSET_URL = 'https://raw.githubusercontent.com/CroppingFlea479/Fleasion/main/assets.json'

VERSION = 1
logging.basicConfig(
    level=logging.DEBUG,  # Set the logging level to DEBUG
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',  # Log message format
)

logger = logging.getLogger()

aud = None

os_name = platform.system()

if os_name == "Windows":
    CACHE_FOLDER = Path(tempfile.gettempdir(), "Roblox", "http")
elif os_name == "Linux":
    CACHE_FOLDER = Path.home() / Path(".var/app/org.vinegarhq.Sober/cache/sober/http")
else:
    logger.critical("Unsupported OS - %s", os)
    sys.exit()
logger.debug(CACHE_FOLDER)

cache_files = []
cache_hashlist = os.listdir(CACHE_FOLDER)

asset_data = []

for file in cache_hashlist:
    f = cache.File(CACHE_FOLDER / file)
    cache_files.append(f)

def _create_dynamic_tex():
    tex_data = []
    for i in range(TEXTURE_RESOLUTION*TEXTURE_RESOLUTION):
        tex_data.append(100/255)
        tex_data.append(100/255)
        tex_data.append(100/255)
        tex_data.append(255/255)
    
    dpg.add_dynamic_texture(TEXTURE_RESOLUTION, TEXTURE_RESOLUTION, tex_data, parent="__asset_tex_container", tag="__asset_tex", label="Asset Viewer Texture")

dpg.create_context()
dpg.add_texture_registry(label="Asset Viewer Texture Container", tag="__asset_tex_container")

_create_dynamic_tex()

dpg.create_viewport(title=f'starstruck v{VERSION}', width=1200, height=800, clear_color=(170,229,164,255))

curr = None
def cache_file_callback(sender, app_data, user_data):
    global aud
    global curr
    curr = user_data
    dpg.set_item_label("asset_viewer", f"asset viewer: {user_data.name}")
    dpg.set_value("status_text", f"currently viewing: {user_data.name}")
    dpg.set_value("asset_text", user_data.get_magic())

    dpg.configure_item('audio', show=True if user_data.type == "ogg" else False)
    dpg.configure_item('texture', show=True if user_data.type == "png" else False)

    if user_data.type == "png":
        im = Image.open(user_data.data)
        resized_im = im.convert('RGBA').resize((TEXTURE_RESOLUTION, TEXTURE_RESOLUTION))

        dpg.set_value("__asset_tex", np.frombuffer(resized_im.tobytes(), dtype=np.uint8) / 255.0)
    if user_data.type == "ogg":
        with open("starstruck_audio.ogg", 'wb') as file:
            file.write(user_data.get_data())

        aud = openal.oalOpen("starstruck_audio.ogg")
        file = pyogg.VorbisFile("starstruck_audio.ogg")
        duration = file.buffer_length / file.frequency / file.channels / 2
        dpg.set_value("audio_duration", f"duration: {duration:.3f}s")

    dpg.configure_item("asset_viewer", width=-1, height=-1)

def export_callback():
    if curr is None:
        return
    try:
        with open(dpg.get_value('export_filename'), 'wb') as file:
            file.write(curr.get_data())
            dpg.set_value('export_status', f"successfully written to {dpg.get_value('export_filename')}")
    except Exception as e:
        logger.error(e)
        dpg.set_value('export_status', f"failed to write file: {e}")

def rescan_fleasion_callback():
    global cache_hashlist
    dpg.delete_item("fleasion_asset_library", children_only=True)
    cache_hashlist = os.listdir(CACHE_FOLDER)
    dpg.set_item_label("fleasion_asset_library", f"fleasion asset library {asset_data['version']}")
    dpg.add_text("scans for hashes in cache folder, green if found, red if not found.", parent="fleasion_asset_library")
    for k, v in asset_data.items():
        process_element(k, v, "fleasion_asset_library")

def download_fleasion_callback():
    global asset_data
    response = requests.get(ASSET_URL)
    if response.status_code == 200:
        asset_data = response.json()
    else:
        logger.error(f"Failed to retrieve data: {response.status_code}")
    rescan_fleasion_callback()

def audio_play_callback():
    aud.set_gain(dpg.get_value("audio_volume"))
    aud.play()

def audio_stop_callback():
    aud.stop()

with dpg.window(label="cache list", width=650, height=450, no_close=True):
    dpg.add_text(f"deco says hello :3 ({len(cache_files)} found)")
    dpg.add_text(str(CACHE_FOLDER), label="cache folder", show_label=True)
    with dpg.group(horizontal=True):
        dpg.add_button(label="scan")

    with dpg.collapsing_header(label="assets", default_open=True):
        def _sort_callback(sender, sort_specs):
            # sort_specs scenarios:
            #   1. no sorting -> sort_specs == None
            #   2. single sorting -> sort_specs == [[column_id, direction]]
            #   3. multi sorting -> sort_specs == [[column_id, direction], [column_id, direction], ...]
            #
            # notes:
            #   1. direction is ascending if == 1
            #   2. direction is ascending if == -1
            pass

        _asset_table_id = dpg.generate_uuid()
        dpg.add_input_text(label="hash", hexadecimal=True, payload_type="hash", 
            user_data=_asset_table_id, callback=lambda s, a, u: dpg.set_value(u, dpg.get_value(s)), 
            drop_callback=lambda s, a: dpg.set_value(s, a))

        with dpg.table(header_row=True, no_host_extendX=True, delay_search=True,
                    borders_innerH=True, borders_outerH=True, borders_innerV=True,
                    borders_outerV=True, context_menu_in_body=True, row_background=True, sort_tristate=True,
                    policy=dpg.mvTable_SizingFixedFit, height=-1, sortable=True, callback=_sort_callback,
                    scrollY=True, tag=_asset_table_id) as table_id:

            dpg.add_table_column(label="hash")
            dpg.add_table_column(label="last modified")
            dpg.add_table_column(label="type")
            dpg.add_table_column(label="size")
            dpg.add_table_column(label="desc")

            for f in cache_files:
                with dpg.table_row(filter_key=f.name):
                    dpg.add_button(label=f.name, user_data=f, callback=cache_file_callback)
                    dpg.add_text(f.mtime_formatted())
                    dpg.add_text(f.type)
                    dpg.add_text(os.path.getsize(f.path))
                    dpg.add_text('')

with dpg.window(label="asset viewer: <none>", tag="asset_viewer", height=-1, width=200, no_close=True, no_resize=True):
    dpg.add_text("currently viewing: <none>", tag="status_text", payload_type="hash", drop_callback=lambda s, a: cache_file_callback(None, None, cache.File(CACHE_FOLDER / a)))

    with dpg.group(tag="audio", show=False):
        dpg.add_slider_float(label='volume', min_value=0, max_value=1, clamped=True, default_value=1, tag="audio_volume")
        with dpg.group(horizontal=True):
            dpg.add_button(label="play", callback=audio_play_callback)
            dpg.add_button(label="stop", callback=audio_stop_callback)
            dpg.add_text("duration", tag="audio_duration")
    with dpg.group(tag="texture", show=False):
        dpg.add_image("__asset_tex")

    dpg.add_text("magic", tag="asset_text")

    with dpg.collapsing_header(label="exporting", default_open=True):
        dpg.add_input_text(label='filename', tag="export_filename")
        with dpg.group(horizontal=True):
            dpg.add_button(label="export", callback=export_callback)
            dpg.add_text('', tag="export_status")

def in_hashlist(hash):
    if hash in cache_hashlist: return (0, 255, 0)
    if hash not in cache_hashlist: return (255, 0, 0)

def process_element(k, element, parent=None):
    if isinstance(element, str):
        if k == 'version':
            with dpg.group(horizontal=True, parent=parent) as g:
                dpg.add_text(k + ": " + element, parent=g)
                dpg.add_button(label="rescan", callback=rescan_fleasion_callback, parent=g)
        else:
            dpg.add_text(k + ": " + element, color=in_hashlist(element), parent=parent)
            with dpg.drag_payload(parent=dpg.last_item(), drag_data=element, payload_type="hash"):
                dpg.add_text(element)
    elif isinstance(element, list):
        with dpg.tree_node(label=k + f" [list ({len(element)} elements)]", parent=parent) as t:
            for item in element:
                dpg.add_text(item, color=in_hashlist(item), parent=t)  # Process each item in the list
                with dpg.drag_payload(parent=dpg.last_item(), drag_data=item, payload_type="hash"):
                    dpg.add_text(item)
    elif isinstance(element, dict):
        with dpg.tree_node(label=k + f" [object ({len(element)} elements)]", parent=parent) as t:
            for key, value in element.items():
                process_element(key, value, parent=t)  # Recursively process each value in the dict

with dpg.window(label="fleasion asset library UNSCANED", tag="fleasion_asset_library", width=500, height=300, no_close=True):
    dpg.add_text("scans for hashes in cache folder, green if found, red if not found.")
    dpg.add_button(label="download & scan", callback=download_fleasion_callback)
    #for k, v in asset_data.items():
    #    process_element(k, v, "fleasion_asset_library")

with dpg.window(label="asset changer", height=-1, width=-1, no_close=True):
    with dpg.collapsing_header(label="modifications", default_open=True):
        dpg.add_text("hi")

dpg.setup_dearpygui()
dpg.show_viewport()
dpg.start_dearpygui()
dpg.destroy_context()