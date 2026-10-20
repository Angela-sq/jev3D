# mcbench env notes (probed 2026-10-19, MineStudio 1.1.6, amd64 container on Apple Silicon)

Facts measured with the env server (`docker/env_server.py`). Scoring rules in `src/mcbench/tasks.py` rely on them.

## Timing

- Full world reset (new `MinecraftSim`): 50–51 s.
- `/step` with n=40 no-ops: 2.6 s (about 15 steps/s including HTTP and PNG encoding).
- `/command`: 0.2 s.

## Seeding

| Reset | Spawn `player_pos` |
|---|---|
| seed 0 | x=-3009.5, y=71.0, z=-5572.5 |
| seed 0 again | x=-3009.5, y=71.0, z=-5572.5 |
| seed 1 | x=-5853.5, y=68.0, z=-3781.5 |

Same seed gives the same spawn and terrain. Mob AI and random ticks are not seeded.

## `info` keys

`break_item, craft_item, custom, damage_dealt, equipped_items, food_level, health, inventory, isGuiOpen, is_gui_open, kill_entity, location_stats, mine_block, mobs, pickup, player_pos, use_item` (plus `pov`/`voxels`, which the server drops).

- `health`: float, 20.0 = full. Updated every step.
- `player_pos`: `{"x", "y", "z", "pitch", "yaw"}`. Spawn faces yaw 0.
- `inventory`: `{"0": {"type": "oak_log", "quantity": 3}, ...}`; empty slots have `type: "none"`. Items given by a command can appear one step late.
- `mine_block`, `kill_entity`, `craft_item`, `pickup`, `use_item`, `damage_dealt`: dicts of `{item_or_entity: count}`, empty `{}` at the start of a fresh world.
- `mobs`: stayed `[]` with a zombie 3 blocks away. Not used.

## Behaviours that matter for scoring

- `/kill @e[type=zombie]` does **not** increase `kill_entity`. Only player kills count, so combat oracles must make the player land the blow.
- A zombie 3 blocks away took health from 20.0 to 15.5 in 40 steps (daytime, no armor).
- Holding `attack` for 60 steps mined 2 `spruce_leaves`, counted in `mine_block`.

## Runtime warnings that are harmless

`Failed to open OpenAL device` (no sound card), `Couldn't load Narrator library`, Realms authorization failure, missing OptiFine texture.

## Damage dealt

`damage_dealt` stayed `{}` in every episode, including the smoke-test episode where Fable killed a zombie (`kill_entity.zombie` = 1). `custom` stats held only `time_since_rest`, `play_one_minute`, `sprint_one_cm`, `walk_one_cm`, `time_since_death`. Damage dealt is therefore not used as a metric.
