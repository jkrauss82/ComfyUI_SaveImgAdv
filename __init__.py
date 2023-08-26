import shutil
import folder_paths
import os

print("### Loading: SaveImgAdv")

comfy_path = os.path.dirname(folder_paths.__file__)

def setup_js():
    imgadv_path = os.path.dirname(__file__)
    js_dest_path = os.path.join(comfy_path, "web", "extensions", "imginfo")
    js_files = ["imginfo.js", "exif-reader.js"]

    ## Creating folder if it's not present, then Copy.
    print("Copying JS files for Workflow loading")
    if (os.path.isdir(js_dest_path)==False):
      os.mkdir(js_dest_path)
    for js in js_files:
      shutil.copy(os.path.join(imgadv_path, "imginfo", js), js_dest_path)


setup_js()

from .SaveImgAdv import NODE_CLASS_MAPPINGS

__all__ = ['NODE_CLASS_MAPPINGS']
