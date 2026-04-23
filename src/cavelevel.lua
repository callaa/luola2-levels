local Scheduler = require("utils.scheduler")
local Level = require("level")

local function create_drop(emitter)
	game.effect("AddTerrainParticle", {
		pos = emitter.pos + Vec2(0, 4),
		vel = Vec2(0, 0),
		imass = 10,
		drag = 0.0001,
		color = game.water_color,
		wind = false,
	})

	if game.terrain_at(emitter.pos) == 0 then
		emitter:destroy()
		return nil
	end
	return math.random(10, 100) / 10
end

local function create_drop_emitter(pos)
	game.effect("AddFixedObject", {
		id = 0,
		pos = pos,
		state = {
			scheduler = Scheduler:new():add(0.0, create_drop),
		},
		timer = math.random(1, 10),
	})
end

local original_init_level = luola_init_level
function luola_init_level(settings)
	original_init_level(settings)

	for _, pos in ipairs(settings.droppers) do
		create_drop_emitter(Level.to_world_coordinates(pos))
	end

end
