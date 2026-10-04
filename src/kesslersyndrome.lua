local Scheduler = require("utils.scheduler")
local Level = require("level")
local tableutils = require("utils.table")
local level = require("level")
local impacts = require("weapons.impacts")
local sounds = require("sounds")

local function satellite_impact(this, terrain, obj)
    this:destroy()
    if terrain == level.TER_LEVELBOUND then
        return
    end

    game.effect("MakeBigHole", { pos = this.pos, r = 8 })
    game.effect("AddParticle", {
        pos = this.pos,
        texture = textures.get("bigboom"),
    })
    impacts.make_shrapnell(36, this.pos, {
        color = 0xffff6666,
        texture = textures.get("pewpew"),
        state = {
            on_impact = impacts.bullet,
        },
    })

    sfx.explosion(sounds.small_explosion(), this.pos, 0.3)

    if obj and obj.state and obj.state.on_bullet_hit then
        obj.state.on_bullet_hit(obj, this, 30)
    end
end

-- Spawn out of control satellites outside the given safe zone
local function spawn_satellites(center, radius)
    local state = {
        on_impact = satellite_impact
    }
    local tex = textures.get("lvl_satellite")

    for i = 0, 12 do
        local point_on_circle = Vec2_for_angle(math.random(0, 360), 1)
        local tangent
        if math.random(0, 2) == 0 then
            tangent = Vec2(-point_on_circle.y, point_on_circle.x)
        else
            tangent = Vec2(point_on_circle.y, -point_on_circle.x)
        end
        game.effect("AddBullet", {
            pos = center + point_on_circle * radius + tangent * 1500,
            vel = tangent  * -2500,
            texture = tex,
            state = state,
        })
    end
end

local original_init_level = luola_init_level
function luola_init_level(settings)
    original_init_level(settings)
    local danger_zone = Level.to_world_coordinates(settings.danger_zone)
    local center = Vec2(danger_zone[1], danger_zone[2])
    local radius = danger_zone[3]
    Scheduler.add_global(1, function()
        spawn_satellites(center, radius)
        return 1
    end)
end
