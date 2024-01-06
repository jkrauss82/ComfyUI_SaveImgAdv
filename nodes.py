import numpy as np
import pandas as pd
from PIL import Image, ImageDraw, ImageFont
from PIL.PngImagePlugin import PngInfo
import piexif
import piexif.helper
from . import helper
import folder_paths
import os
import json
from comfy.sd1_clip import escape_important, unescape_important, token_weights
import torch


class CLIPTextEncodeWithStats:
    def __init__(self):
        self.type = "output"

    @classmethod
    def INPUT_TYPES(s):
        return {
            "required": {
                "text": ("STRING", {"multiline": True}),
                "clip": ("CLIP", )
            }
        }

    # RETURN_TYPES = ("CONDITIONING", "STRING", )
    RETURN_TYPES = ("CONDITIONING", "STRING", "IMAGE",)
    FUNCTION = "encode"

    CATEGORY = "conditioning"

    OUTPUT_NODE = True

    embedding_identifier = "embedding:"

    def encode(self, clip, text):
        tokens = clip.tokenize(text, return_word_ids=True)
        print(f'org tokens {tokens}')
        words = self.getWords(text)
        stats = {}
        for clipn in tokens:
            print(f'clip name {clipn}')
            clip_name = f'clip_{clipn}'
            if not clip_name in stats: stats[clip_name] = { 'num_batches': len(tokens[clipn]), 'num_tokens': 0, 'batches': [] }
            for batch in tokens[clipn]:
                bat = { 'num_tokens': 0, 'words': {}, 'text': [] }
                for token in batch:
                    # exclude start and stop tokens or avoid index out of bounds (should never happen)
                    if token[2] == 0 or len(words) < token[2]: continue
                    bat['num_tokens'] += 1
                    if not f'word{token[2]}' in bat['words']:
                        bat['words'][f'word{token[2]}'] = { 'word': words[token[2] -1], 'num_tokens': 0, 'weight': 0 }
                    bat['words'][f'word{token[2]}']['num_tokens'] += 1
                    bat['words'][f'word{token[2]}']['weight'] += token[1]
                    stats[clip_name]['num_tokens'] += 1
                stats[clip_name]['batches'].append(bat)

        # build the stats dict for the dataframe
        dfdict = { 'batch': [], 'num_tokens': [], 'num_words': [], 'text': [] }
        for clipn in stats:
            bidx = 0
            for batch in stats[clipn]['batches']:
                bidx += 1
                for word_idx in batch['words']:
                    batch['words'][word_idx]['weight'] = batch['words'][word_idx]['weight'] / batch['words'][word_idx]['num_tokens']
                    batch['text'].append(batch['words'][word_idx]['word'])
                batch['text'] = " ".join(batch['text'])
                dfdict['batch'].append(str(bidx))
                dfdict['num_tokens'].append(batch['num_tokens'])
                dfdict['num_words'].append(len(dict.keys(batch['words'])))
                txt = batch['text'] if len(batch['text']) < 90 else str(batch['text'][:42]+" (..) "+batch['text'][-42:])
                dfdict['text'].append(txt)
            # create sum row
            dfdict['batch'].append('total')
            dfdict['num_tokens'].append(sum(dfdict['num_tokens']))
            dfdict['num_words'].append(sum(dfdict['num_words']))
            dfdict['text'].append(text if len(text) < 90 else str(text[:42]+" (..) "+text[-42:]))

        dfstr = pd.DataFrame.from_dict(dfdict).set_index('batch').to_string()
        # print(dfstr)
        lines = len(dfstr.splitlines())

        fnt = ImageFont.truetype("custom_nodes/ComfyUI_SaveImgAdv/font/RobotoMono.ttf", 14)

        out = Image.new("RGB", (1024, 20 * lines), (50, 50, 50))

        ImageDraw.Draw(
            out  # Image
        ).text(
            (6, 0),  # Coordinates
            dfstr,  # Text
            (255, 255, 255),  # Color
            fnt
        )

        # Convert the PIL image to Torch tensor
        img_tensor = np.array(out).astype(np.float32) / 255.0
        img_tensor = torch.from_numpy(img_tensor)[None,]

        cond, pooled = clip.encode_from_tokens(tokens, return_pooled=True)
        return ([[cond, {"pooled_output": pooled}]], json.dumps(stats, indent=3), img_tensor, )


    def getWords(self, text):
        words = []
        text = escape_important(text)
        parsed_weights = token_weights(text, 1.0)
        for weighted_segment, weight in parsed_weights:
            print(f'weighted_segment [{weighted_segment}] weight [{weight}]')
            to_tokenize = unescape_important(weighted_segment).replace("\n", " ").split(' ')
            to_tokenize = [x for x in to_tokenize if x != ""]
            print(f'len words {len(to_tokenize)}', to_tokenize)
            for word in to_tokenize:
                #if we find an embedding, deal with the embedding
                if word.startswith(self.embedding_identifier):
                    print(f'emdding {word}')
                words.append(word)

        return words


'''
by Kaharos94 and jkrauss82
forked from Kaharos94 / https://github.com/Kaharos94/ComfyUI-Saveaswebp
comfyUI node to save an image in webp, jpeg and png formats
'''
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
                "mode": (["lossy", "lossless"],),
                "format": ([ "webp", "jpg", "png" ], { "default": "webp" }),
                "compression": ("INT", {"default": 90, "min": 1, "max": 100, "step": 1},),
                "calc_model_hashes": ("BOOLEAN", {"default": False}),
                "add_automatic1111_meta": ("BOOLEAN", {"default": False}),
                "keywords": ("STRING", { "placeholder": "List of keywords to be added as exif tag, separated by commas" }),
            },
            "hidden": {
                "prompt": "PROMPT",
                "extra_pnginfo": "EXTRA_PNGINFO"
            }
        }

    INPUT_IS_LIST = True

    RETURN_TYPES = ()
    FUNCTION = "Save_as_format"

    OUTPUT_NODE = True

    CATEGORY = "image"


    def Save_as_format(self, mode, format, compression, images, calc_model_hashes, add_automatic1111_meta, filename_prefix="ComfyUI",
                       keywords=None, prompt=None, extra_pnginfo=None, ):

        # we have set INPUT_IS_LIST = True, need to map regular parameters from their lists
        images = images[0]
        mode = mode[0]
        format = format[0]
        compression = compression[0]
        calc_model_hashes = calc_model_hashes[0]
        add_automatic1111_meta = add_automatic1111_meta[0]
        filename_prefix = filename_prefix[0]
        prompt = prompt[0]
        extra_pnginfo = extra_pnginfo[0] if extra_pnginfo is not None else None

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

        results = list()

        filename_prefix = compute_vars(filename_prefix)

        subfolder = os.path.dirname(os.path.normpath(filename_prefix))
        filename = os.path.basename(os.path.normpath(filename_prefix))

        full_output_folder = os.path.join(self.output_dir, subfolder)

        if os.path.commonpath((self.output_dir, os.path.abspath(full_output_folder))) != self.output_dir:
            print("Saving image outside the output folder is not allowed.")
            return {}

        # sanitize mode option
        if format == 'jpg': mode = 'lossy'
        elif format == 'png': mode = 'lossless'

        # TODO: get rid of the trailing underscore
        try:
            counter = max(filter(lambda a: a[1][:-1] == filename and a[1][-1] == "_", map(map_filename, os.listdir(full_output_folder))))[0] + 1
        except ValueError:
            counter = 1
        except FileNotFoundError:
            os.makedirs(full_output_folder, exist_ok=True)
            counter = 1

        for idx in range(len(images)):
            i = 255. * images[idx].cpu().numpy()
            img = Image.fromarray(np.clip(i, 0, 255).astype(np.uint8))

            file = f"{filename}_{counter:05}_.{format}"

            # format webp or jpg
            if format != 'png':
                workflowmetadata = str()
                promptstr = str()

                if prompt is not None:
                    promptstr="".join(json.dumps(prompt)) #prepare prompt String
                if extra_pnginfo is not None:
                    for x in extra_pnginfo:
                        workflowmetadata += "".join(json.dumps(extra_pnginfo[x]))

                exifdict = {
                        "0th": {
                            piexif.ImageIFD.Make: promptstr,
                            piexif.ImageIFD.ImageDescription: workflowmetadata
                        }
                    }
                if add_automatic1111_meta:
                    exifdict['Exif'] = {
                            piexif.ExifIFD.UserComment: piexif.helper.UserComment.dump(helper.automatic1111Format(prompt, img, calc_model_hashes) or "", encoding="unicode")
                        }

                kidx = idx if keywords != None and len(keywords) > 1 else 0
                if keywords[kidx] != None and isinstance(keywords[kidx], str) and keywords[kidx] != '':
                    # keywords maxlength in iptc standard 64 characters
                    klist = keywords[kidx].split(",")
                    final_list = []
                    for word in klist:
                        if len(word) < 65: final_list.append(word.strip())
                    exifdict["0th"][piexif.ImageIFD.XPKeywords] = ", ".join(final_list).encode("utf-16le")

                exif_bytes = piexif.dump(exifdict)

                img.save(os.path.join(full_output_folder, file), method=6, exif=exif_bytes, lossless=(mode =="lossless"), quality=compression)

            # format png (method from ComfyUI SaveImage class)
            else:
                metadata = None
                metadata = PngInfo()
                if prompt is not None:
                    metadata.add_text("prompt", json.dumps(prompt))
                if extra_pnginfo is not None:
                    for x in extra_pnginfo:
                        metadata.add_text(x, json.dumps(extra_pnginfo[x]))

                img.save(os.path.join(full_output_folder, file), pnginfo=metadata, compress_level=4)

            results.append({
                "filename": file,
                "subfolder": subfolder,
                "type": self.type
            });
            counter += 1

        return { "ui": { "images": results } }
