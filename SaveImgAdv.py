import numpy as np
from PIL import Image
import piexif
import piexif.helper
from . import helper
import folder_paths
import os
import json

# by Kaharos94 and jkrauss82
# forked from Kaharos94 / https://github.com/Kaharos94/ComfyUI-Saveaswebp
# comfyUI node to save an image in webp and jpeg formats

class SaveImgAdv:
    def __init__(self):
        self.output_dir = folder_paths.get_output_directory()
        self.type = "output"

    @classmethod
    def INPUT_TYPES(s):
        return {
            "required": {
                "images": ("IMAGE", ),
                "filename_prefix": ("STRING", {"default": "ComfyUI"}),
                "mode":(["lossy","lossless"],),
                "format":([ "jpg", "webp" ], { "default": "webp" }),
                "compression":("INT", {"default": 80, "min": 1, "max": 100, "step": 1},)
            },
            "hidden": {
                "prompt": "PROMPT", "extra_pnginfo": "EXTRA_PNGINFO"
            }
        }

    RETURN_TYPES = ()
    FUNCTION = "Save_as_format"

    OUTPUT_NODE = True

    CATEGORY = "image"

    def Save_as_format(self, mode, format, compression, images, filename_prefix="ComfyUI", prompt=None, extra_pnginfo=None, ):
        def map_filename(filename):
            prefix_len = len(os.path.basename(filename_prefix))
            prefix = filename[:prefix_len + 1]
            try:
                digits = int(filename[prefix_len + 1:].split('_')[0])
            except:
                digits = 0
            return (digits, prefix)

        def compute_vars(input):
            input = input.replace("%width%", str(images[0].shape[1]))
            input = input.replace("%height%", str(images[0].shape[0]))
            return input

        filename_prefix = compute_vars(filename_prefix)

        subfolder = os.path.dirname(os.path.normpath(filename_prefix))
        filename = os.path.basename(os.path.normpath(filename_prefix))

        full_output_folder = os.path.join(self.output_dir, subfolder)

        if os.path.commonpath((self.output_dir, os.path.abspath(full_output_folder))) != self.output_dir:
            print("Saving image outside the output folder is not allowed.")
            return {}

        try:
            counter = max(filter(lambda a: a[1][:-1] == filename and a[1][-1] == "_", map(map_filename, os.listdir(full_output_folder))))[0] + 1
        except ValueError:
            counter = 1
        except FileNotFoundError:
            os.makedirs(full_output_folder, exist_ok=True)
            counter = 1

        results = list()
        for image in images:
            i = 255. * image.cpu().numpy()
            img = Image.fromarray(np.clip(i, 0, 255).astype(np.uint8))
            workflowmetadata = str()
            promptstr = str()

            if prompt is not None:
                promptstr="".join(json.dumps(prompt)) #prepare prompt String
            if extra_pnginfo is not None:
                for x in extra_pnginfo:
                    workflowmetadata += "".join(json.dumps(extra_pnginfo[x]))
            file = f"{filename}_{counter:05}_.{format}"

            exif_bytes = piexif.dump({
                "0th": {
                    piexif.ImageIFD.Make: promptstr,
                    piexif.ImageIFD.ImageDescription: workflowmetadata
                },
                "Exif": {
                    piexif.ExifIFD.UserComment: piexif.helper.UserComment.dump(helper.automatic1111Format(prompt, img) or "", encoding="unicode")
                }
            })

            img.save(os.path.join(full_output_folder, file), method=6, exif=exif_bytes, lossless=(mode =="lossless"), quality=compression)

            # webp format saving
            #if format == 'webp':
                #if mode =="lossless":
                #    boolloss = True
                #if mode =="lossy":
                #    boolloss = False
                #img.save(os.path.join(full_output_folder, file), method=6, exif=exif_bytes, lossless=boolloss, quality=compression) #Save as webp - options to be determined
            # jpg saving
            #else:
                #img.save(os.path.join(full_output_folder, file), exif=exif_bytes, quality=compression)

            results.append({
                "filename": file,
                "subfolder": subfolder,
                "type": self.type
            });
            counter += 1

        return { "ui": { "images": results } }

NODE_CLASS_MAPPINGS = {
    "SaveImgAdv": SaveImgAdv
}
