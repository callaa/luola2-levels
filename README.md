Luola II official level pack
----------------------------

This is the official level pack to [Luola II](https://github.com/callaa/luola2/).

To install, copy or symlink the `luola2/` folder into the game's `data/levels/` folder.


## Level structure

A Luola2 level is made up of at least the following parts:

 * A TOML file for the level's metadata
 * A terrain map image
 * An Artwork image (may be the same as the terrain map)
 * A thumbnail image to be shown in the level selection screen

A level may also include:

 * Lua scripts to customize the game
 * A parallax background image
 * Foreground and background billboard elements (not yet implemented)
 * Background music (not yet implemented)

Levels are grouped into level packs, where each level pack is a subfolder inside the game's `data/levels/` folder.


## Level converter

There are two ways to create Luola2 levels: the old-school 8-bit palette way (see the demo levels for an example) or modern true color way with separate artwork and terrain map files.
The included `ora2level.py` script makes level authoring in the latter style easier by allowing you to put each terrain type into its own layer and group those layers however you like.

The script performs the following tasks automatically:

 * Exports the OpenRaster file into a merged artwork PNG
 * Merges all terrain layers: non-transparent pixels are assigned a palette index based on the layer's type
 * Discovers the level's water color (game uses this for destructible underwater terrain)
 * Generates a thumbnail image
 * Adds filenames and the terrain type map to the TOML file

The converter determines the type of the layer based on its name:

 * Anything that looks like a terrain type (e.g. "ground" or "base-uw-i") is interpreted to contain terrain of that type. (The script does not validate that the type is actually supported by the game engine.)
 * Layers not named accordingly will be hidden
 * Layer group names are ignored. Layer groups may be arbitrarily nested.

To convert an OpenRaster file:

1. Ensure you have a TOML metadata file in the `src/` folder, paired with the image file. (E.g. "my-level.toml" and "my-level.ora")
2. Run `./ora2level.py src/my-level.toml`. This will write the level files to `luola2/` folder.

You need to have Python and uv installed to run the script.


## License

Luola II Levels © 2025 by Calle Laakkonen is licensed under CC BY-SA 4.0. To view a copy of this license, visit https://creativecommons.org/licenses/by-sa/4.0/ 
