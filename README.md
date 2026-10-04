Luola II official level pack
----------------------------

This is the official level pack to [Luola II](https://github.com/callaa/luola2/).

To install, run `make.sh` and copy or symlink the `luola2/` folder into the game's `data/levels/` folder.


## Level structure

A Luola2 level is made up of at least the following parts:

 * A TOML file for the level's metadata
 * A terrain map image
 * An artwork image (may be the same as the terrain map)
 * A thumbnail image to be shown in the level selection screen

A level may also include:

 * Lua scripts to customize the game
 * A parallax background image
 * Background music
 * Custom textures for use in level scripts or to override standard ones

Levels are grouped into level packs, where each level pack is a subfolder inside the game's `data/levels/` folder.


## Level metadata

The schema for the metadata file is defined in [src/game/level/levelinfo.rs](https://github.com/callaa/luola2/blob/main/src/game/level/levelinfo.rs), `struct LevelInfoToml`.

At a minimum, the `title` property should be set. The lever converter script will assign the other required properties.

Level specific textures are given in the same format as in [Luola's main texture declaration file](https://github.com/callaa/luola2/blob/main/data/textures/textures.toml).

Custom scripts will typically override the `luola_init_level` function. The script is loaded into the same context as the rest of the game's scripts and may arbitrarily extend the game.
See the included lua files for examples.


## Level converter

There are two ways to create Luola2 levels: the old-school 8-bit palette way (see the demo levels for an example) or modern true color way with separate artwork and terrain map files.
The included `ora2level.py` script makes level authoring in the latter style easier by allowing you to put each terrain type into its own layer and group those layers however you like. The script will generate the terrain map for you.

The script performs the following tasks automatically:

 * Exports the OpenRaster file into a merged artwork PNG
 * Merges all terrain layers: non-transparent pixels are assigned a palette index based on the layer's name
 * Discovers the level's water color (game uses this for destructible underwater terrain)
 * Generates a thumbnail image
 * Extracts the parallax background (if included)
 * Adds filenames and the terrain type map to the TOML file

The converter determines the type of the layer based on its name:

 * Anything that looks like a terrain type (e.g. "ground" or "base-uw-i") is interpreted to contain terrain of that type. (The script does not validate that the type is actually supported by the game engine.)
 * Layers not named accordingly will be hidden
 * Layer group names are ignored. Layer groups may be arbitrarily nested.
 * Layer or group named "Parallax" will be extracted as the parallax background image

To convert an OpenRaster file:

1. Ensure you have a TOML metadata file in the `src/` folder, paired with the image file. (E.g. "my-level.toml" and "my-level.ora")
2. Run `./ora2level.py src/my-level.toml`. This will write the level files to `luola2/` folder.

You need to have Python and uv installed to run the script.


## License

Luola II Levels © 2025, 2026 by Calle Laakkonen is licensed under CC BY-SA 4.0. To view a copy of this license, visit https://creativecommons.org/licenses/by-sa/4.0/
