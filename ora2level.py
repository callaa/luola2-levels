#!/usr/bin/env -S uv run --script
#
# /// script
# dependencies = ["pyora", "tomlkit"]
# ///

import PIL
import numpy
import itertools
from os import path

import tomlkit
import pyora
import sys
import re

# Where to put output files (relative to working directory)
TARGET_DIR = "luola2"

# This matches everything that looks like a terrain type string, even if its not actually
# supported by the game engine itself.
TERRAIN_TYPE_RE = re.compile('^(?:[a-z]+)(?:-(?:uw|i))*$')

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
        is_terrain = bool(TERRAIN_TYPE_RE.match(layer.name))
        if TERRAIN_TYPE_RE.match(layer.name):
            # Terrain groups are rendered as-is
            continue

        if layer.type == pyora.TYPE_GROUP:
            hide_non_terrain_layers(layer.children)
        else:
            layer.visible = False


def intersect_map_bounds(map_w, map_h, x, y, w, h):
    x0 = max(0, x)
    y0 = max(0, y)
    x1 = min(x+w, map_w)
    y1 = min(y+h, map_h)

    return (x0, y0, x1, y1)


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

        color_idx = get_terrain_color(layer.name)

        mask = numpy.array(image.getdata(3)).reshape(h, w) > 0

        # The game uses the palette's water color to replace destroyed underwater pixels
        # This color can be overridden in the TOML file.
        global WATER_COLOR_SET
        if layer.name == "water" and not WATER_COLOR_SET:
            nonzero = numpy.where(mask == True)
            pixelindex = (nonzero[0][0], nonzero[1][0])
            watercolor = image.getpixel((nonzero[0][0], nonzero[1][0]))
            PALETTE[colormap["water"]] = watercolor[0:3]
            print(f"Water color (#{colormap['water']}) set to {PALETTE[colormap['water']]}")
            WATER_COLOR_SET = True

        imagedata[y:y2, x:x2] = imagedata[y:y2, x:x2] * ~mask + color_idx * mask

    def paint(stack, prefix=''):
        for layer in reversed(list(stack.children)):
            if not layer.visible:
                continue
            if isinstance(layer, pyora.Group):
                print(prefix, layer.name)
                paint(layer, prefix + '  ')
            elif TERRAIN_TYPE_RE.match(layer.name):
                print(prefix, "paint", layer.name)
                paint_layer(layer)

    paint(project.root)

    image = PIL.Image.fromarray(imagedata, 'P')
    image.putpalette(list(itertools.chain(*PALETTE[:len(colormap)])))
    return image, colormap


def get_parallax(project):
    for layer in project.root:
        if layer.name in ("Parallax", "Parallax.jpeg"):
            fmt = 'jpeg' if layer.name.endswith('jpeg') else 'png'
            return layer.get_image_data(), fmt
    return None, None


def make_thumbnail(src, target):
    with PIL.Image.open(src) as im:
        im = im.convert("RGB")
        im.thumbnail((256, 256))
        im.save(target)


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
    thumb_filename = basename + "-thumb.jpeg"
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
    parallax, parallax_fmt = get_parallax(project)
    if parallax:
        if parallax_fmt == 'jpeg':
            parallax = parallax.convert("RGB")
        background_filename = f"{basename}-bg.{parallax_fmt}"
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

    # Make thumbnail (from original ORA mergedimage)
    print("Saving thumbnail:", thumb_filename)
    thumbnail = project.get_image_data(use_original=True).convert("RGB")
    thumbnail.thumbnail((256, 256))
    thumbnail.save(path.join(TARGET_DIR, thumb_filename))

    # Write TOML file with all the additions (most importantly the terrain palette)
    print("Writing TOML file:", toml_filename)
    with open(path.join(TARGET_DIR, toml_filename), 'w') as tf:
        tomlkit.dump(levelinfo, tf)


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: ora2level.py <filename.toml>")
    else:
        main(sys.argv[1])
