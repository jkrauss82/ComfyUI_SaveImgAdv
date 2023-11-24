import shutil
import folder_paths
import os

class colors:
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'

comfy_path = os.path.dirname(folder_paths.__file__)

def setup_js():
  imgadv_path = os.path.dirname(__file__)
  js_dest_path = os.path.join(comfy_path, "web", "extensions", "imginfo")
  js_files = ["imginfo.js", "exif-reader.js"]

  ## Creating folder if it's not present, then Copy.
  if not os.path.isdir(js_dest_path):
    os.mkdir(js_dest_path)
  for js in js_files:
    if not os.path.isfile(f"{js_dest_path}/{js}"):
      print(f"{colors.BLUE}SaveImgAdv:{colors.ENDC} Copying JS files for Workflow loading")
      shutil.copy(os.path.join(imgadv_path, "imginfo", js), js_dest_path)

  print(f"{colors.BLUE}SaveImgAdv: {colors.GREEN}Loaded{colors.ENDC}")

setup_js()

from .SaveImgAdv import NODE_CLASS_MAPPINGS

__all__ = ['NODE_CLASS_MAPPINGS']
