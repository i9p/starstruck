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
aud_path = os.path.join(tempfile.gettempdir(), "starstruck_audio.ogg")

os_name = platform.system()

if os_name == "Windows":
    CACHE_FOLDER = Path(tempfile.gettempdir(), "Roblox", "http")
elif os_name == "Linux":
    CACHE_FOLDER = Path.home() / Path(".var/app/org.vinegarhq.Sober/cache/sober/http")
else:
    logger.critical("Unsupported OS - %s", os)
    sys.exit()

logger.debug(CACHE_FOLDER)

cache_hashlist = os.listdir(CACHE_FOLDER)
curr = None

cache_files = []

asset_data = []
hash_data = {}


# ┏━╸┏━┓╻  ╻  ┏┓ ┏━┓┏━╸╻┏ ┏━┓
# ┃  ┣━┫┃  ┃  ┣┻┓┣━┫┃  ┣┻┓┗━┓
# ┗━╸╹ ╹┗━╸┗━╸┗━┛╹ ╹┗━╸╹ ╹┗━┛
def cache_file_drop_callback(sender, app_data):
    if os.path.isfile(CACHE_FOLDER / app_data):
        cache_file_callback(None, None, cache.File(CACHE_FOLDER / app_data))

def cache_file_callback(sender, app_data, user_data):
    if user_data.type == "": return

    global aud
    global curr
    curr = user_data

    logger.info("currently loading - %s", curr.name)
    dpg.set_item_label("asset_viewer", f"asset viewer: {curr.name}")
    dpg.set_value("status_text", f"currently viewing: {curr.name}")
    dpg.set_value("asset_text", curr.get_magic())

    dpg.configure_item('audio', show=True if curr.type == "ogg" else False)
    dpg.configure_item('texture', show=True if curr.type == "png" else False)

    if curr.type == "png":
        im = Image.open(curr.data)
        resized_im = im.convert('RGBA').resize((TEXTURE_RESOLUTION, TEXTURE_RESOLUTION))

        dpg.set_value("__asset_tex", np.frombuffer(resized_im.tobytes(), dtype=np.uint8) / 255.0)
    if curr.type == "ogg":
        with open(aud_path, 'wb') as file:
            file.write(curr.get_data())

        aud = openal.oalOpen(aud_path)
        file = pyogg.VorbisFile(aud_path)
        duration = file.buffer_length / file.frequency / file.channels / 2
        dpg.set_value("audio_duration", f"duration: {duration:.3f}s")

    dpg.configure_item("asset_viewer", width=-1, height=-1)

def export_callback():
    if curr is None: return

    try:
        with open(dpg.get_value('export_filename'), 'wb') as file:
            file.write(curr.get_data())
            dpg.set_value('export_status', f"successfully written to {dpg.get_value('export_filename')}")
    except Exception as e:
        logger.error(e)
        dpg.set_value('export_status', f"failed to write file: {e}")
        dpg.configure_item("asset_viewer", width=-1, height=-1)

def rescan_fleasion_callback():
    global cache_hashlist
    global hash_data
    hash_data.clear()
    dpg.delete_item("fleasion_asset_library", children_only=True)
    cache_hashlist = os.listdir(CACHE_FOLDER)
    dpg.set_item_label("fleasion_asset_library", f"fleasion asset library {asset_data['version']}")
    dpg.add_text("scans for hashes in cache folder, green if found, red if not found.", parent="fleasion_asset_library")
    for k, v in asset_data.items():
        process_element(k, v, "fleasion_asset_library")

    for k in hash_data:
        hash_data[k] = list(set(hash_data[k]))

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

# ╻ ╻┏━╸╻  ┏━┓┏━╸┏━┓   ┏━╸╻ ╻┏┓╻┏━╸╺┳╸╻┏━┓┏┓╻┏━┓
# ┣━┫┣╸ ┃  ┣━┛┣╸ ┣┳┛   ┣╸ ┃ ┃┃┗┫┃   ┃ ┃┃ ┃┃┗┫┗━┓
# ╹ ╹┗━╸┗━╸╹  ┗━╸╹┗╸   ╹  ┗━┛╹ ╹┗━╸ ╹ ╹┗━┛╹ ╹┗━┛
def in_hashlist(hash):
    """ return green if in cachelist, else red """
    return (0, 255, 0) if hash in cache_hashlist else (255, 0, 0)

def populate_cache_files():
    global cache_files
    global cache_hashlist
    cache_hashlist = os.listdir(CACHE_FOLDER)
    cache_files.clear()
    for file in os.listdir(CACHE_FOLDER):
        f = cache.File(CACHE_FOLDER / file)
        cache_files.append(f)
    cache_files.sort(key=lambda obj: obj.name)

def add_value_to_hash_data(key, value):
    global hash_data
    if key in hash_data:
        hash_data[key].append(value)
    else:
        hash_data[key] = [value]

def process_element(k, element, parent, path=None):
    """ recursive function to create GUI elements for each json elements """
    if path is None: path = [k]
    if isinstance(element, str):
        if k == 'version':
            with dpg.group(horizontal=True, parent=parent) as g:
                dpg.add_text(k + ": " + element)
                dpg.add_button(label="rescan", callback=rescan_fleasion_callback, parent=g)
        else:
            add_value_to_hash_data(element, "/".join(path[-2:]))
            dpg.add_text(k + ": " + element, color=in_hashlist(element), parent=parent)
            with dpg.drag_payload(parent=dpg.last_item(), drag_data=element, payload_type="hash"):
                dpg.add_text(element)
    elif isinstance(element, list):
        with dpg.tree_node(label=k + f" ({len(element)} elements)", parent=parent) as t:
            with dpg.drag_payload(parent=dpg.last_item(), drag_data='\n'.join(element), payload_type="hash"):
                dpg.add_text(f"list ({len(element)} hashes)")
            for item in element:
                add_value_to_hash_data(item, "/".join(path[-2:]))
                dpg.add_text(item, color=in_hashlist(item))  # Process each item in the list
                with dpg.drag_payload(parent=dpg.last_item(), drag_data=item, payload_type="hash"):
                    dpg.add_text(item)
    elif isinstance(element, dict):
        with dpg.tree_node(label=k + f" ({len(element)} elements)", parent=parent) as t:
            for key, value in element.items():
                process_element(key, value, t, path + [key])  # Recursively process each value in the dict

def _create_dynamic_tex():
    """ creates a gray placeholder image """
    tex_data = []
    for i in range(TEXTURE_RESOLUTION*TEXTURE_RESOLUTION):
        tex_data.append(100/255)
        tex_data.append(100/255)
        tex_data.append(100/255)
        tex_data.append(255/255)
    
    dpg.add_dynamic_texture(TEXTURE_RESOLUTION, TEXTURE_RESOLUTION, tex_data, parent="__asset_tex_container", tag="__asset_tex", label="Asset Viewer Texture")

populate_cache_files()

dpg.create_context()
dpg.add_texture_registry(label="Asset Viewer Texture Container", tag="__asset_tex_container")

_create_dynamic_tex()

dpg.create_viewport(title=f'starstruck v{VERSION}', width=1200, height=800)

# ┏━╸╻ ╻╻   ╻ ╻╻┏┓╻╺┳┓┏━┓╻ ╻┏━┓
# ┃╺┓┃ ┃┃   ┃╻┃┃┃┗┫ ┃┃┃ ┃┃╻┃┗━┓
# ┗━┛┗━┛╹   ┗┻┛╹╹ ╹╺┻┛┗━┛┗┻┛┗━┛
with dpg.window(label="cache list", width=650, height=450, no_close=True):
    dpg.add_text(f"deco says hello :3 ({len(cache_files)} found)", tag="cachelist_status")
    dpg.add_text(str(CACHE_FOLDER), label="cache folder", show_label=True)

    with dpg.collapsing_header(label="assets", default_open=True):
        _cache_controls_id = dpg.generate_uuid()
        _cache_table_id = dpg.generate_uuid()

        def rescan_cache_folder_callback():
            global cache_files
            global cache_hashlist
            for tag in dpg.get_item_children(_cache_table_id)[1]:
                dpg.delete_item(tag)

            populate_cache_files()

            for f in cache_files:
                data_list = [f.name, f.mtime, f.type, 'empty' if os.path.getsize(f.path) == 91 else str(os.path.getsize(f.path)), ", ".join(hash_data.get(f.name, ['nodesc']))]
                with dpg.table_row(filter_key=' '.join(data_list), parent=_cache_table_id):
                    dpg.add_button(label=f.name, user_data=f, callback=cache_file_callback)
                    dpg.add_text(f.mtime)
                    dpg.add_text(f.type)
                    dpg.add_text(os.path.getsize(f.path))
                    dpg.add_text(", ".join(hash_data.get(f.name, [])))

        dpg.add_text('-empty to hide empty files, -nodesc to hide files without a description')
        with dpg.group(horizontal=True, tag=_cache_controls_id):
            dpg.add_button(label="rescan (SLOW!)", callback=rescan_cache_folder_callback)
            dpg.add_input_text(label="filter", payload_type="hash", 
                user_data=_cache_table_id, callback=lambda s, a, u: dpg.set_value(u, dpg.get_value(s)), 
                drop_callback=lambda s, a: dpg.set_value(s, a))

        with dpg.table(header_row=True, no_host_extendX=True, delay_search=True, clipper=True,
                    borders_innerH=True, borders_outerH=True, borders_innerV=True,
                    borders_outerV=True, context_menu_in_body=True, row_background=True,
                    policy=dpg.mvTable_SizingFixedFit, height=-1, scrollY=True, tag=_cache_table_id):

            dpg.add_table_column(label="hash", tag="hash_col")
            dpg.add_table_column(label="last modified", tag="mtime_col")
            dpg.add_table_column(label="type", tag="type_col")
            dpg.add_table_column(label="size", tag="size_col")
            dpg.add_table_column(label="desc", tag="desc_col")

            for f in cache_files:
                data_list = [f.name, f.mtime, f.type, 'empty' if os.path.getsize(f.path) == 91 else str(os.path.getsize(f.path)), ", ".join(hash_data.get(f.name, ['nodesc']))]
                with dpg.table_row(filter_key=' '.join(data_list)):
                    dpg.add_button(label=f.name, user_data=f, callback=cache_file_callback)
                    dpg.add_text(f.mtime)
                    dpg.add_text(f.type)
                    dpg.add_text(os.path.getsize(f.path))
                    dpg.add_text(", ".join(hash_data.get(f.name, [])))

with dpg.window(label="asset viewer: <none>", tag="asset_viewer", height=-1, width=200, no_close=True, no_resize=True):
    dpg.add_text("currently viewing: <none>", tag="status_text", payload_type="hash", drop_callback=cache_file_drop_callback)

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

with dpg.window(label="fleasion asset library UNSCANNED", tag="fleasion_asset_library", width=500, height=300, no_close=True):
    dpg.add_text("scans for hashes in cache folder, green if found, red if not found.")
    dpg.add_button(label="download & scan", callback=download_fleasion_callback)

mods_dict = {}

def update_mods_left(_, app_data, user_data):
    mods_dict[user_data][0] = app_data 
    print(mods_dict)
def update_mods_right(_, app_data, user_data):
    mods_dict[user_data][1] = app_data 
    print(mods_dict)

def remove_mod_callback(_, app_data, user_data):
    del mods_dict[user_data]
    dpg.delete_item(user_data)

def add_mod_callback(_, app_data, user_data):
    tag = dpg.generate_uuid()
    mods_dict[tag] = ['', '']
    with dpg.group(horizontal=True, tag=tag, parent="mods_group"):
        dpg.add_input_text(callback=update_mods_left, user_data=tag, hexadecimal=True, width=240, payload_type="hash", drop_callback=lambda s, a: dpg.set_value(s, a))
        dpg.add_text('->')
        dpg.add_input_text(callback=update_mods_right, user_data=tag, multiline=True, width=244, height=30, payload_type="hash", drop_callback=lambda s, a: dpg.set_value(s, a))
        dpg.add_button(label='X', callback=remove_mod_callback, user_data=tag)

with dpg.window(label="the modificationator", width=555, height=300, no_close=True):
    with dpg.collapsing_header(label="modifications", default_open=True):
        dpg.add_button(label="add modification", callback=add_mod_callback)
        with dpg.group(tag="mods_group"):
            add_mod_callback(None, None, None)

        with dpg.group(horizontal=True):
            dpg.add_checkbox(label="no textures")
            dpg.add_checkbox(label="default skyboxes")

    with dpg.collapsing_header(label="controls", default_open=True):
        with dpg.group(horizontal=True):
            dpg.add_button(label="clear cache")
            dpg.add_button(label="apply modifications")

dpg.setup_dearpygui()
dpg.show_viewport()
dpg.start_dearpygui()
dpg.destroy_context()