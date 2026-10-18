#!/usr/bin/env -S uv run --script
#
# /// script
# dependencies = ["pyora", "tomlkit"]
# ///

from PIL import Image, ImageDraw
import numpy
import itertools
import shutil
from os import path
import sys
import re

import tomlkit
import pyora


# Where to put output files (relative to working directory)
TARGET_DIR = "luola2"

# This matches everything that looks like a terrain type string, even if its not actually
# supported by the game engine itself.
TERRAIN_TYPE_RE = re.compile(r'^([a-z]+(?:-(?:uw|i|dyn))*)(\+nocolor)?$')

PALETTE = [
    (0, 0, 0),
    (255, 255, 255),
    (0, 0, 255),
    (255, 255, 0),
    (255, 0, 0),
    (0, 255, 0),
    (255, 0, 255),
    (127, 0, 0),
    (0, 127, 0),
    (0, 0, 127),
    (127, 127, 0),
    (127, 0, 127),
    (127, 127, 127),
    (64, 0, 0),
    (0, 64, 0),
    (0, 0, 64),
    (64, 64, 0),
    (64, 0, 64),
    (64, 64, 64),
]

WATER_COLOR_SET = False

def hide_non_terrain_layers(stack):
    for layer in stack:
        terrain_name = TERRAIN_TYPE_RE.match(layer.name)

        if layer.type == pyora.TYPE_GROUP and not terrain_name:
            hide_non_terrain_layers(layer.children)
        else:
            layer.visible = bool(terrain_name) and terrain_name.group(2) != '+nocolor'


def intersect_map_bounds(map_w, map_h, x, y, w, h):
    x0 = max(0, x)
    y0 = max(0, y)
    x1 = min(x+w, map_w)
    y1 = min(y+h, map_h)

    return (x0, y0, x1, y1)


def get_terrain_name_part(layer_name):
    terrain_name = TERRAIN_TYPE_RE.match(layer_name)
    if not terrain_name:
        raise ValueError(f"Layer name {layer_name} does not match terrain name regex!")

    return terrain_name.group(1)


def render_collisionmap(project):
    map_w, map_h = project.dimensions
    imagedata = numpy.zeros((map_h, map_w), dtype=numpy.uint8)
    colormap = {'space': 0, 'ground': 1, 'water': 2} # terrain type name -> palette index

    def get_terrain_color(name):
        try:
            return colormap[name]
        except KeyError:
            idx = len(colormap)
            colormap[name] = idx
            return idx

    def paint_layer(layer):
        image = layer.get_image_data(raw=True)
        x, y = layer.offsets
        w, h = image.size

        x, y, x2, y2 = intersect_map_bounds(map_w, map_h, x, y, w, h)

        if w != x2-x or h != y2-y:
            image = image.crop((x - layer.offsets[0], y - layer.offsets[1], x2 - layer.offsets[0], y2 - layer.offsets[1]))
            w, h = image.size

        terrain_name = get_terrain_name_part(layer.name)
        color_idx = get_terrain_color(terrain_name)

        mask = numpy.array(image.get_flattened_data(3)).reshape(h, w) > 0

        # The game uses the palette's water color to replace destroyed underwater pixels
        # This color can be overridden in the TOML file.
        global WATER_COLOR_SET
        if terrain_name == "water" and not WATER_COLOR_SET:
            nonzero = numpy.where(mask == True)
            pixelindex = (nonzero[1][0], nonzero[0][0])
            watercolor = image.getpixel(pixelindex)
            PALETTE[colormap["water"]] = watercolor[0:3]
            print(f"Water color (#{colormap['water']}) set to {PALETTE[colormap['water']]}")
            WATER_COLOR_SET = True

        imagedata[y:y2, x:x2] = imagedata[y:y2, x:x2] * ~mask + color_idx * mask

    def paint(stack, prefix=''):
        for layer in reversed(list(stack.children)):
            if not layer.visible:
                print(prefix, "not visible:", layer.name)
                continue

            if TERRAIN_TYPE_RE.match(layer.name):
                print(prefix, "paint:", layer.name)
                paint_layer(layer)
            elif isinstance(layer, pyora.Group):
                print(prefix, "group:", layer.name)
                paint(layer, prefix + '  ')
            else:
                print(prefix, "skip", layer.name)

    paint(project.root)

    image = Image.fromarray(imagedata, 'P')
    image.putpalette(list(itertools.chain(*PALETTE[:len(colormap)])))
    return image, colormap


def extract_billboards(project, basename):
    billboard_layers = []
    # TODO: pack images efficiently (doesn't need to be optimal, as that's NP-complete)
    # TODO deduplicate identical billboards
    max_w = 0
    sum_h = 0
    def walk(stack, x, y):
        nonlocal max_w
        nonlocal sum_h
        for layer in stack:
            offx = x + layer.offsets[0]
            offy = y + layer.offsets[1]
            if layer.name == "Billboard":
                billboard_layers.append((offx, offy, layer))
                w, h = layer.dimensions
                max_w = max(max_w, w)
                sum_h = sum_h + h
            elif layer.type == pyora.TYPE_GROUP:
                walk(layer.children, offx, offy)

    walk(project.root, 0, 0)

    if not billboard_layers:
        print("No billboards.")
        return [], []

    billboard_toml = []
    texture_toml = {}
    texture_filename = f"{basename}-billboards.png"

    image = Image.new("RGBA", (max_w, sum_h), color=(0, 0, 0, 0))
    y_offset = 0
    for idx, (x, y, layer) in enumerate(billboard_layers):
        print(f"Adding billboard layer at ({x}, {y})")
        image.paste(layer.get_image_data(raw=True), (0, y_offset))
        texture_name = f"lvl_billboard_{idx}"
        billboard_toml.append({
            "pos": [x, y],
            "texture": texture_name,
        })
        texture_toml[texture_name] = {
            "file": texture_filename,
            "subrect": [0, y_offset, *layer.dimensions],
        }
        y_offset += layer.dimensions[1]

    print("Saving billboard texture:", texture_filename)
    image.save(path.join(TARGET_DIR, texture_filename))
    return billboard_toml, texture_toml


def get_parallax(project):
    for layer in project.root:
        if layer.name in ("Parallax", "Parallax.jpeg"):
            image = layer.get_image_data(raw=False)
            if layer.opacity < 1.0:
                dark = Image.new("RGBA", image.size, (0, 0, 0, int((1-layer.opacity) * 255)))
                image = Image.alpha_composite(image, dark)
            return image
    return None


def make_thumbnail(image):
    # TODO add parallax background?
    im = image.convert("RGB")
    im.thumbnail((image.size[0], 512))

    # Add rounded edges
    mask = Image.new("RGBA", im.size, color=(0, 0, 0, 0))
    draw = ImageDraw.Draw(mask)
    draw.rounded_rectangle(((0, 0), im.size), 32, fill=(255, 255, 255, 255))

    thumbnail = Image.new("RGBA", im.size, color=0)
    thumbnail.paste(im, mask=mask)

    return thumbnail


def main(input_path):
    root, _ = path.splitext(input_path)
    basename = path.basename(root)
    toml_path = root + ".toml"
    ora_path = root + ".ora"

    # First, load the level description TOML file
    with open(toml_path, 'r') as tf:
        levelinfo = tomlkit.load(tf)

    # Output file names
    artwork_filename = basename + "-art.png"
    terrain_filename = basename + "-terrain.png"
    thumb_filename = basename + "-thumb.png"
    toml_filename = basename + ".toml"

    levelinfo["artwork"] = artwork_filename
    levelinfo["terrain"] = terrain_filename
    levelinfo["thumbnail"] = thumb_filename

    # Load OpenRaster file
    project = pyora.Project.load(ora_path)
    print("Level size is", project.dimensions)

    # Make collisionmap
    print("Rendering collisionmap...")
    cmap, colormap = render_collisionmap(project)
    levelinfo["terrain-palette"] = colormap

    print("Saving collisionmap:", terrain_filename)
    cmap.save(path.join(TARGET_DIR, terrain_filename))

    # Extract parallax background image (if any)
    print("Extracting background image...")
    parallax = get_parallax(project)
    if parallax:
        background_filename = f"{basename}-bg.png"
        print("Saving background:", background_filename)
        parallax.save(path.join(TARGET_DIR, background_filename))
        levelinfo["background"] = background_filename
    else:
        print("No parallax background.")

    # Save artwork with non-terrain layers hidden
    print("Rendering artwork...")
    hide_non_terrain_layers(project.children)
    artwork = pyora.Renderer(project).render()
    print("Saving artwork:", artwork_filename)
    artwork.save(path.join(TARGET_DIR, artwork_filename))

    # Save billboards
    print("Extracting billboards...")
    billboard_toml, billboard_textures_toml = extract_billboards(project, basename)
    if billboard_toml:
        textures = levelinfo.get("textures")
        if textures is None:
            textures = levelinfo["textures"] = tomlkit.table()

        for k, v in billboard_textures_toml.items():
            it = tomlkit.inline_table()
            it |= v
            textures[k] = it

        levelinfo["billboard"] = billboard_toml

    # Make thumbnail (from original ORA mergedimage)
    print("Saving thumbnail:", thumb_filename)
    make_thumbnail(project.get_image_data(use_original=True)).save(path.join(TARGET_DIR, thumb_filename))

    # Copy script (if set)
    if 'script' in levelinfo:
        scriptpath = path.join(path.dirname(toml_path), levelinfo['script'])
        print("Copying script:", scriptpath)
        shutil.copyfile(scriptpath, path.join(TARGET_DIR, levelinfo['script']))

    # Write TOML file with all the additions (most importantly the terrain palette)
    print("Writing TOML file:", toml_filename)
    with open(path.join(TARGET_DIR, toml_filename), 'w') as tf:
        tomlkit.dump(levelinfo, tf)


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: ora2level.py <filename.toml>")
    else:
        main(sys.argv[1])
