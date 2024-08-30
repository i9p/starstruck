from pathlib import Path
import tempfile
from datetime import datetime
import os
import io
import magic

DEFAULT_CACHE_FOLDER = Path(tempfile.gettempdir(), "Roblox", "http")

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
