import hashlib
import json
from pathlib import Path
from folder_paths import folder_names_and_paths, models_dir

hashed = {}
def sha256sum(filename):
    global hashed
    hashstore = f'{models_dir}/hashes.json'
    if len(dict.keys(hashed)) == 0 and Path(hashstore).is_file():
        with open(hashstore) as f:
            hashed = json.load(f)
            print(hashed)
    if filename in hashed: return hashed[filename]
    h  = hashlib.sha256()
    b  = bytearray(128*1024)
    mv = memoryview(b)
    with open(filename, 'rb', buffering=0) as f:
        for n in iter(lambda : f.readinto(mv), 0):
            h.update(mv[:n])
    hashed[filename] = h.hexdigest()
    with open(hashstore, 'w', encoding='utf-8') as f:
        json.dump(hashed, f, ensure_ascii=False, indent=4)
    return hashed[filename]

def stripFileExtension(filename):
    if filename == None: return ''
    return str(filename).rsplit('.', 1)[0]

sampler_props_map = {
    'steps': 'Steps',
    'cfg': 'CFG scale',
    'seed': 'Seed',
    'denoise': 'Denoising strength',
    # handled by convSamplerA1111()
    'sampler_name': None,
    'scheduler': None }

def isSamplerNode(params):
    for param in sampler_props_map:
        if param not in params:
            return False
    return True

def convSamplerA1111(sampler, scheduler):
    sampler = sampler.replace('dpm', 'DPM').replace('pp', '++').replace('_ancestral', ' a').replace('DPM_2', 'DPM2').replace('_sde', ' SDE').replace('2m', '2M').replace('2s', '2S').replace('euler', 'Euler').replace('ddim', 'DDIM').replace('heun', 'Heun').replace('uni_pc', 'UniPC').replace('_', ' ')
    if scheduler == 'normal': return sampler
    scheduler = scheduler.title()
    return sampler+' '+scheduler

def automatic1111Format(prompt, image, add_hashes):
    positive_input = ''
    negative_input = ''
    gensampler = ''
    genmodel = ''
    hires = ''
    controlnet = ''
    ultimate_sd_upscale = ''
    hashes = {}
    loras = []

    for order in prompt:
        params = None
        if 'inputs' in prompt[order]:
            params = prompt[order]['inputs']
        if params != None and 'class_type' in prompt[order]:
            if prompt[order]['class_type'] == 'CLIPTextEncode':
                if 'text' in params and params['text'] != None:
                    if positive_input == '': positive_input = params['text']
                    elif negative_input == '': negative_input = '\nNegative prompt: '+params['text']
            if prompt[order]['class_type'] == 'LoraLoader':
                if 'lora_name' in params and params['lora_name'] != None:
                    loras.append({ "name": stripFileExtension(params['lora_name']), "weight_clip": params['strength_clip'], "weight_model": params['strength_model'] })
                    # calculate the sha256sum for this lora. TODO: store hashes in .txt file next to loras
                    if add_hashes:
                        hash = sha256sum(folder_names_and_paths['loras'][0][0]+'/'+params['lora_name'])
                        hashes[f'lora:{params["lora_name"]}'] = hash[0:10]
            if isSamplerNode(params) and gensampler == '':
                sampler = convSamplerA1111(params['sampler_name'], params['scheduler'])
                width, height = image.size
                gensampler = f'\nSteps: {params["steps"]}, Sampler: {sampler}, CFG scale: {params["cfg"]}, Seed: {params["seed"]}, Denoising strength: {params["denoise"]}, Size: {width}x{height}'
            if prompt[order]['class_type'] == 'UltimateSDUpscale' and ultimate_sd_upscale == '':
                if 'upscale_model' in params and params['upscale_model'] != None and params['upscale_model'][0] in prompt and prompt[params['upscale_model'][0]]['class_type'] == 'UpscaleModelLoader':
                    model = stripFileExtension(prompt[params['upscale_model'][0]]['inputs']['model_name'])
                ultimate_sd_upscale = f', Ultimate SD upscale upscaler: {model}'
                if 'tile_width' in params: ultimate_sd_upscale += f', Ultimate SD upscale tile_width: {params["tile_width"]}'
                if 'tile_height' in params: ultimate_sd_upscale += f', Ultimate SD upscale tile_height: {params["tile_height"]}'
                if 'mask_blur' in params: ultimate_sd_upscale += f', Ultimate SD upscale mask_blur: {params["mask_blur"]}'
                if 'tile_padding' in params: ultimate_sd_upscale += f', Ultimate SD upscale padding: {params["tile_padding"]}'
            if prompt[order]['class_type'] == 'CheckpointLoaderSimple':
                model = stripFileExtension(params['ckpt_name'])
                # first found model gets selected as creator
                if genmodel == '': genmodel = f', Model: {model}'
                # calculate the sha256sum for this model. TODO: store hashes in .txt file next to models
                if add_hashes:
                    hash = sha256sum(folder_names_and_paths['checkpoints'][0][0]+'/'+params['ckpt_name'])
                    hashes[f'model:{model}'] = hash[0:10]
            if prompt[order]['class_type'] == 'UpscaleModelLoader' and hires == '':
                model = stripFileExtension(params['model_name'])
                hires = f', Hires upscaler: {model}'
            if prompt[order]['class_type'] == 'ControlNetApply' and controlnet == '':
                if 'control_net' in params and params['control_net'] != None and params['control_net'][0] in prompt and prompt[params['control_net'][0]]['class_type'] == 'ControlNetLoader':
                    model = stripFileExtension(prompt[params['control_net'][0]]['inputs']['control_net_name'])
                    controlnet = f', ControlNet: "model: {model}, weight: {params["strength"]}"'

    lora_prompt_add = ''
    if len(loras) > 0:
        lora_prompt_add = ', <lora:'+'>, <lora:'.join(f'{l["name"]}:{l["weight_clip"]}' for l in loras)+'>'
    uc = positive_input + lora_prompt_add + negative_input + gensampler + genmodel + controlnet + hires + ultimate_sd_upscale + (', Hashes: ' + json.dumps(hashes) if add_hashes else '')
    return uc
