# ComfyUI-SaveImgAdv

*Forked from Kaharos94 / https://github.com/Kaharos94/ComfyUI-Saveaswebp*

Save a picture as Webp or Jpeg file in ComfyUI + Workflow loading and basic support of automatic1111 prompt embedding. Also supported are CivitAI model hashes.

## Description:

This adds a custom node to save a picture as a Webp or Jpeg file and also adds a script to Comfy to drag and drop generated images into the UI to load the workflow.

PNG images saved by default from the node shipped with ComfyUI are lossless, thus occupy more space compared to lossy formats.

Options: format (webp/jpeg), compression slider, and lossy/lossless (lossless supported for webp format only).

The compression slider is a bit misleading: In lossless mode, it only affects the "effort" taken to compress where 100 is the smallest possible size and 1 is the biggest possible size, it's a tradeoff for saving speed.

In lossy mode, that's the other way around, where 100 is the biggest possible size with the least compression and 1 is the smallest possible size with maximum compression.

On default it's set to lossy with a compression of 80.

The workflow JSON is embedded in the EXIF metadata of the images, sections ImageIFD/Make for prompt and ImageIFD/ImageDescription for workflow meta. Automatic1111 prompt info is added at field ExifIFD/UserComment.

## Installation:

In your terminal/console, navigate to your ComfyUI custom nodes directory and clone this repo:

`git clone https://github.com/jkrauss82/ComfyUI_SaveImgAdv.git`

Restart ComfyUI.

## Warning:

Some of the code is pretty hacky, so this can definitely break.

Also, Webp only supports files up to 16383 x 16383. Jpeg max resolution is untested.

Prompt compatibility with automatic1111 is very basic and hacky and will surely break for more advanced workflows. It works reasonably well only for basic txt2img.

CivitAI model hashes require the SHA256sum of the models used in the workflow which takes a while to calculate on the first execution. Hashes are cashed in a simple JSON file.

### Known issues:

Import of Webpfiles breaks if import a workflow that has }Prompt:{ in a Node that has dynamic wildcards disabled.

Node doesn't resize on Save - image is in there, just needs to be resized to be visible.

Automatic1111 compatibility is broken for more advanced workflow including multiple prompts. Positive and negative prompts might be wrongly assigned if negative prompt widget was created before the positive one.

Images posted on CivitAI created with this node will only use the automatic1111 compatibility metadata, not the workflow as with original ComfyUI PNG files.

The filename index appending only works with an additional underscore being added.
