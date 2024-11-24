# ▞▀▖▀▛▘▞▀▖▛▀▖▞▀▖▀▛▘▛▀▖▌ ▌▞▀▖▌ ▌ ▌        ▌            ▞▀▖
# ▚▄  ▌ ▙▄▌▙▄▘▚▄  ▌ ▙▄▘▌ ▌▌  ▙▞  ▛▀▖▌ ▌ ▞▀▌▞▀▖▞▀▖▞▀▖ ▐▌ ▄▘
# ▖ ▌ ▌ ▌ ▌▌▚ ▖ ▌ ▌ ▌▚ ▌ ▌▌ ▖▌▝▖ ▌ ▌▚▄▌ ▌ ▌▛▀ ▌ ▖▌ ▌ ▗▖▖ ▌
# ▝▀  ▘ ▘ ▘▘ ▘▝▀  ▘ ▘ ▘▝▀ ▝▀ ▘ ▘ ▀▀ ▗▄▘ ▝▀▘▝▀▘▝▀ ▝▀  ▝▘▝▀ 
import os
import io
import platform
import sys
import tempfile
import logging
import re
import shutil

import openal
import pygame.mixer as m
import pyogg
import magic
import numpy as np
import requests
from PIL import Image
import dearpygui.dearpygui as dpg

from mutagen.oggvorbis import OggVorbis
from datetime import datetime
from pathlib import Path

VERSION = 1.6

TEXTURE_RESOLUTION = 256
ASSET_URL = 'https://raw.githubusercontent.com/CroppingFlea479/Fleasion/main/assets.json'

MD5_PATTERN = re.compile(r'^[a-f0-9]{32}$', re.I)

logging.basicConfig(
    level=logging.DEBUG,  # Set the logging level to DEBUG
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',  # Log message format
)

logger = logging.getLogger()

m.init()

aud_buffer = None
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

cache_hashlist = os.listdir(CACHE_FOLDER)
curr = None

cache_files = []

asset_data = []
hash_data = {}

class File:
    def __init__(self, path: Path):
        self.path = path
        self.name = path.name
        self.mtime = datetime.fromtimestamp(os.path.getmtime(self.path)).strftime("%Y-%m-%d %H:%M:%S")

        self.type = ''
        self.metadata = {}

        self.data_pos = None
        self.data = None
        self.magic = None

        try:
            with open(self.path, 'rb') as file:
                for line_number in range(256):
                    tell = file.tell()
                    line = file.readline()
                    if line_number == 0:
                        continue
                    if not line:
                        break
                    if b': ' in line:
                        l = line.decode('utf-8', errors='ignore').replace('\n', '').replace('\r', '').split(": ")
                        self.metadata[l[0]] = l[1]
                    else:
                        self.data_pos = tell
                        header = line[:12]
                        if header.startswith(b'\x89PNG\r\n'):
                            self.type = 'png'
                        elif header.startswith(b'\xabKTX 11\xbb\r\n'):
                            self.type = 'ktx2'
                        elif header.startswith(b'<roblox!'):
                            self.type = 'rbxl'
                        elif header.startswith(b'OggS'):
                            self.type = 'ogg'
                        elif header.startswith(b'version '):
                            self.type = 'v' + str(header).split()[1][:-1]
                        break
        except FileNotFoundError:
            print(f"The file {self.path} was not found.")
        except Exception as e:
            print(path.name, f"An error occurred: {e}")

    def get_magic(self):
        if self.magic is not None: return self.magic
        self.magic = magic.from_buffer(self.get_data())
        return self.magic
    
    def get_data(self):
        if self.data is not None: return self.data.getvalue()
        if self.data_pos is None: return False

        with open(self.path, 'rb') as file:
            file.seek(self.data_pos)
            self.data = io.BytesIO(file.read())
            return self.data.getvalue()

# ┏━╸┏━┓╻  ╻  ┏┓ ┏━┓┏━╸╻┏ ┏━┓
# ┃  ┣━┫┃  ┃  ┣┻┓┣━┫┃  ┣┻┓┗━┓
# ┗━╸╹ ╹┗━╸┗━╸┗━┛╹ ╹┗━╸╹ ╹┗━┛
def cache_file_drop_callback(sender, app_data):
    if os.path.isfile(CACHE_FOLDER / app_data):
        cache_file_callback(None, None, File(CACHE_FOLDER / app_data))

def cache_file_callback(sender, app_data, user_data):
    if user_data.type == "": return

    global aud, aud_buffer
    global curr
    curr = user_data

    logger.info("currently loading - %s", curr.name)
    dpg.set_item_label("asset_viewer", f"asset viewer: {curr.name}")
    dpg.set_value("status_text", f"currently viewing: {curr.name}")
    dpg.set_value("asset_magic", curr.get_magic())

    dpg.configure_item('audio', show=True if curr.type == "ogg" else False)
    dpg.configure_item('texture', show=True if curr.type == "png" else False)

    if curr.type == "png":
        im = Image.open(curr.data)
        resized_im = im.convert('RGBA').resize((TEXTURE_RESOLUTION, TEXTURE_RESOLUTION))

        dpg.set_value("__asset_tex", np.frombuffer(resized_im.tobytes(), dtype=np.uint8) / 255.0)
    if curr.type == "ogg":
        orig_data = curr.data.getvalue()
        file = OggVorbis(io.BytesIO(orig_data))
        aud = m.Sound(io.BytesIO(orig_data))
        dpg.set_value("audio_duration", f"duration: {file.info.length:.3f}s")

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
        if asset_data == []:
            dpg.add_button(label='remove textures', parent="add_mods", user_data=('delete', '\n'.join(response.json()['textures']), ''), callback=add_mod_callback)
            dpg.add_button(label='default skyboxes', parent="add_mods", user_data=('delete', '\n'.join(response.json()['skyboxes']), ''), callback=add_mod_callback)
        asset_data = response.json()
    else:
        logger.error(f"Failed to retrieve data: {response.status_code}")
    rescan_fleasion_callback()

def clear_cache_callback():
    for file in os.listdir(CACHE_FOLDER):
        if MD5_PATTERN.match(file):
            os.remove(CACHE_FOLDER / file)
    dpg.configure_item("clearcache_modal", show=False)

def apply_mods_callback():
    for v in mods_dict.values():
        if v[1] == 'delete':
            src = CACHE_FOLDER / 'd625adff6a3d75081d11b3407b0b417c'
        elif v[1] == 'replace':
            src = CACHE_FOLDER / v[3]
        else:
            continue

        for h in v[2].strip().split('\n'):
            if MD5_PATTERN.match(h):
                shutil.copyfile(src, CACHE_FOLDER / h)
                logger.info(f'{h} has been replaced with {src}')

    dpg.configure_item("applymods_modal", show=False)

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
    for file in cache_hashlist:
        f = File(CACHE_FOLDER / file)
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
                dpg.add_button(label="rescan", callback=download_fleasion_callback, parent=g)
        else:
            add_value_to_hash_data(element, "/".join(path[-2:]))
            dpg.add_text(k + ": " + element, color=in_hashlist(element), parent=parent)
            with dpg.drag_payload(parent=dpg.last_item(), drag_data=element, payload_type="hash"):
                dpg.add_text(element)
    elif isinstance(element, list):
        with dpg.tree_node(label=k + f" ({len(element)} elements)", parent=parent) as t:
            dpg.add_text(f'list containing {len(element)} hashes')
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
with dpg.window(label="cache list", width=800, height=500, no_close=True):
    dpg.add_text(f"LAUNCHING MY TECH LIKE IM FUCKING APPLE BITCH #SAVEPFMOVEMENT ({len(cache_files)} found)", tag="cachelist_status")
    dpg.add_text(str(CACHE_FOLDER), label="cache folder", show_label=True)

    _cache_controls_id = dpg.generate_uuid()
    _cache_table_id = dpg.generate_uuid()

    def format_number(num):
        if num < 1000:
            return str(num)
        elif num < 1_000_000:
            return f"{num / 1000:.2f}k"
        elif num < 1_000_000_000:
            return f"{num / 1_000_000:.2f}M"
        else:
            return f"{num / 1_000_000_000:.2f}B"

    def populate_cache_table(files):
        for f in files:
            fsize = os.path.getsize(f.path)
            data_list = [f.name, f.mtime, f.type, 'empty' if fsize == 91 else str(fsize), ", ".join(hash_data.get(f.name, ['nodesc']))]
            with dpg.table_row(filter_key=' '.join(data_list), parent=_cache_table_id):
                dpg.add_button(label=f.name, user_data=f, callback=cache_file_callback)
                with dpg.drag_payload(parent=dpg.last_item(), drag_data=f.name, payload_type="hash"):
                    dpg.add_text(f.name)
                dpg.add_text(f.mtime)
                dpg.add_text(f.type)
                dpg.add_text(format_number(fsize))
                dpg.add_text(", ".join(hash_data.get(f.name, [])))

    def rescan_cache_folder_callback():
        global cache_files
        global cache_hashlist

        populate_cache_files()

        dpg.set_value("cachelist_status", f"LAUNCHING MY TECH LIKE IM FUCKING APPLE BITCH #SAVEPFMOVEMENT ({len(cache_files)} found)")

        dpg.delete_item(_cache_table_id, children_only=True)
        dpg.add_table_column(label="hash", tag="hash_col", parent=_cache_table_id)
        dpg.add_table_column(label="last modified", tag="mtime_col", parent=_cache_table_id)
        dpg.add_table_column(label="type", tag="type_col", parent=_cache_table_id)
        dpg.add_table_column(label="size", tag="size_col", parent=_cache_table_id)
        dpg.add_table_column(label="desc", tag="desc_col", parent=_cache_table_id)

        populate_cache_table(cache_files)

    dpg.add_text('-empty to hide empty files, -nodesc to hide files without a description')
    with dpg.group(horizontal=True, tag=_cache_controls_id):
        dpg.add_button(label="rescan", callback=rescan_cache_folder_callback)
        dpg.add_input_text(label="filter", payload_type="hash", 
            user_data=_cache_table_id, callback=lambda s, a, u: dpg.set_value(u, dpg.get_value(s)), 
            drop_callback=lambda s, a: dpg.set_value(s, a))

    def _sort_callback(sender, sort_specs):
        # sort_specs scenarios:
        #   1. no sorting -> sort_specs == None
        #   2. single sorting -> sort_specs == [[column_id, direction]]
        #   3. multi sorting -> sort_specs == [[column_id, direction], [column_id, direction], ...]
        #
        # notes:
        #   1. direction is ascending if == 1
        #   2. direction is ascending if == -1

        # no sorting case
        _sorters = {
            'hash': lambda obj: obj.name,
            'last modified': lambda obj: obj.mtime,
            'type': lambda obj: obj.type,
            'size': lambda obj: os.path.getsize(obj.path),
            'desc': lambda obj: ", ".join(hash_data.get(obj.name, []))
        }

        if sort_specs is None: return
        print(sender, sort_specs )
        try:
            sort_by = dpg.get_item_label(sort_specs[0][0])
        except SystemError as e:
            print(f'GATED: {e}')
            return

        def _sorter(e):
            return _sorters[sort_by](e)

        sorted_files = cache_files
        sorted_files.sort(key=_sorter, reverse=sort_specs[0][1] < 0)

        dpg.delete_item(_cache_table_id, children_only=True)
        dpg.add_table_column(label="hash", tag="hash_col", parent=_cache_table_id)
        dpg.add_table_column(label="last modified", tag="mtime_col", parent=_cache_table_id)
        dpg.add_table_column(label="type", tag="type_col", parent=_cache_table_id)
        dpg.add_table_column(label="size", tag="size_col", parent=_cache_table_id)
        dpg.add_table_column(label="desc", tag="desc_col", parent=_cache_table_id)

        populate_cache_table(sorted_files)

    with dpg.table(header_row=True, no_host_extendX=True, delay_search=True, clipper=True, sortable=True, sort_tristate=True, callback=_sort_callback,
                borders_innerH=True, borders_outerH=True, borders_innerV=True,
                borders_outerV=True, context_menu_in_body=True, row_background=True,
                policy=dpg.mvTable_SizingFixedFit, height=-1, scrollX=True, scrollY=True, tag=_cache_table_id):

        dpg.add_table_column(label="hash", tag="hash_col")
        dpg.add_table_column(label="last modified", tag="mtime_col")
        dpg.add_table_column(label="type", tag="type_col")
        dpg.add_table_column(label="size", tag="size_col")
        dpg.add_table_column(label="desc", tag="desc_col")

        populate_cache_table(cache_files)

with dpg.window(label="asset viewer: <none>", tag="asset_viewer", height=-1, width=200, no_close=True, no_resize=True):
    dpg.add_text("currently viewing: <none>", tag="status_text", payload_type="hash", drop_callback=cache_file_drop_callback)

    with dpg.group(tag="audio", show=False):
        dpg.add_slider_float(label='volume', callback=lambda s, a: aud.set_volume(a), min_value=0, max_value=1, clamped=True, default_value=1, tag="audio_volume")
        with dpg.group(horizontal=True):
            dpg.add_button(label="play", callback=lambda x: aud.play())
            dpg.add_button(label="stop", callback=lambda x: aud.stop())
            dpg.add_text("duration", tag="audio_duration")
    with dpg.group(tag="texture", show=False):
        dpg.add_image("__asset_tex")

    dpg.add_text("magic", tag="asset_magic")

    with dpg.collapsing_header(label="exporting", default_open=True):
        dpg.add_input_text(label='filename', tag="export_filename")
        with dpg.group(horizontal=True):
            dpg.add_button(label="export", callback=export_callback)
            dpg.add_text('', tag="export_status")

with dpg.window(label="fleasion asset library UNSCANNED", tag="fleasion_asset_library", width=500, height=300, no_close=True):
    dpg.add_text("scans for hashes in cache folder, green if found, red if not found.")
    dpg.add_button(label="download & scan", callback=download_fleasion_callback)

mods_dict = {}

def update_mods(_, app_data, user_data):
    mods_dict[user_data[0]][user_data[1]] = app_data 
    print(mods_dict)

def drop_update_callback(s, a):
    user_data = dpg.get_item_user_data(s)
    if user_data[1] == 2: value = dpg.get_value(s) + a + '\n'
    elif user_data[1] == 3: value = a
    dpg.set_value(s, value)
    update_mods(s, value, dpg.get_item_user_data(s))

def remove_mod_callback(_, app_data, user_data):
    del mods_dict[user_data]
    dpg.delete_item(user_data)

def add_mod_callback(_, app_data, user_data):
    tag = dpg.generate_uuid()
    tag2 = dpg.generate_uuid()
    mods_dict[tag] = [tag2, user_data[0], user_data[1], user_data[2]]
    with dpg.group(horizontal=True, tag=tag, parent="mods_group"):
        if user_data[0] == 'replace':
            with dpg.group(horizontal=True, xoffset=60):
                dpg.add_text('replace', tag=tag2)
                dpg.add_input_text(default_value=user_data[1], callback=update_mods, user_data=(tag, 2), multiline=True, width=244, height=30, payload_type="hash", drop_callback=drop_update_callback)
            with dpg.group(horizontal=True, xoffset=35):
                dpg.add_text('with')
                dpg.add_input_text(default_value=user_data[2], callback=update_mods, user_data=(tag, 3), hexadecimal=True, width=240, payload_type="hash", drop_callback=drop_update_callback)
        elif user_data[0] == 'delete':
            with dpg.group(horizontal=True, xoffset=60):
                dpg.add_text('delete', tag=tag2)
                dpg.add_input_text(default_value=user_data[1], callback=update_mods, user_data=(tag, 2), multiline=True, width=527, height=30, payload_type="hash", drop_callback=drop_update_callback)
        dpg.add_button(label=' X ', callback=remove_mod_callback, user_data=tag)

def validate_mods_callback():
    regex_valid = True
    for k, v in mods_dict.items():
        hashes = v[2].strip().split('\n')
        if v[3] != '': hashes.append(v[3])

        re_valid = True
        file_valid = True
        for h in hashes:
            if not MD5_PATTERN.match(h): re_valid = False
            elif not os.path.isfile(CACHE_FOLDER / h):
                file_valid = False

        if not re_valid:
            # red, because you are doing something wrong
            regex_valid = False
            dpg.configure_item(v[0], color=(255, 0, 0))
        elif not file_valid:
            # yellow, because its okay if a file you are replacing doesnt exist
            dpg.configure_item(v[0], color=(255, 255, 0))
        else:
            dpg.configure_item(v[0], color=(0, 255, 0))
    
    return regex_valid

with dpg.window(label="the modificationator", width=650, height=300, no_close=True):
    with dpg.collapsing_header(label="modifications", default_open=True):
        with dpg.group(horizontal=True, tag="add_mods"):
            dpg.add_button(label="add replacement", user_data=('replace', '', ''), callback=add_mod_callback)
            dpg.add_button(label="add removal", user_data=('delete', '', ''), callback=add_mod_callback)
        with dpg.group(tag="mods_group"):
            add_mod_callback(None, None, ('replace', '', ''))

    with dpg.collapsing_header(label="controls", default_open=True):
        with dpg.group(horizontal=True):
            dpg.add_button(label="clear cache")
            with dpg.popup(dpg.last_item(), modal=True, mousebutton=dpg.mvMouseButton_Left, tag="clearcache_modal"):
                dpg.add_text("Are you sure you want to delete everything in cache?")
                dpg.add_separator()
                with dpg.group(horizontal=True):
                    dpg.add_button(label="OK", width=75, callback=clear_cache_callback)
                    dpg.add_button(label="Cancel", width=75, callback=lambda: dpg.configure_item("clearcache_modal", show=False))

            dpg.add_button(label="apply mods", callback=apply_mods_callback)
            with dpg.popup(dpg.last_item(), modal=True, mousebutton=dpg.mvMouseButton_Left, tag="applymods_modal"):
                dpg.add_text("Are you sure you want to apply changes?")
                dpg.add_separator()
                with dpg.group(horizontal=True):
                    dpg.add_button(label="OK", width=75, callback=apply_mods_callback)
                    dpg.add_button(label="Cancel", width=75, callback=lambda: dpg.configure_item("applymods_modal", show=False))

            dpg.add_button(label="validate mods", callback=validate_mods_callback)

dpg.setup_dearpygui()
dpg.show_viewport()
dpg.start_dearpygui()
dpg.destroy_context()