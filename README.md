
# Readme
This is a little Rouge Like im working on in my free time. The premise is simple,
it's an RPG with mechanics I feel like adding. It currently is a big playground of 
ideas. 

## Premise
The premise is a lone survivor going up a tower built from flesh and viscera.

![Main Menu](Res/screenshots/main_menu.png)


### Info how to play

The Keybinds are a bit convoluted thus there is a screen to inform the player.

![Keybinds](Res/screenshots/keybinds.png)

This also works from in game:

![Keybinds in game](Res/screenshots/keybinds_in_game.png)

## Level Editor

The game offers a level Editor, accessable from the Main Menu.

![Level Editor](Res/screenshots/editor.png)

Levels can be createt and edited from the menu:

![Level Editor List](Res/screenshots/level_select.png)

The level editor offers simple level creation.

- Brushes: wall, floor, stairs and player start (1–4); palettes (5, [ ] to switch, Tab for the next palette); select/edit (6); area trigger (7).
- Painting: left click draws, right click erases, R is rectangle mode, the mouse wheel scrolls or picks.
- Validation check if level is completable or missing flags and such



![Validation](Res/screenshots/editor_check_level.png)

Tiles can have logic, such as chests, doors or pressure plates.

| Chest | Lever |  
| --- | --- |
| ![Chest Closed](Res/screenshots/chest_closed.png)| ![Lever off](Res/screenshots/lever_off.png)|
| ![Chest open](Res/screenshots/chest_opened.png) | ![Lever on](Res/screenshots/lever_on.png)


### Properties

The editor can change Properties of entities or tiles paced in game:

![Chest Properties](Res/screenshots/editor_chest_properties.png)

Chests can have Loot tables assigned.

![Event Properties](Res/screenshots/editor_event_properties.png)

Events can be linked to Levers, death triggers and such. These will trigger if link is called. Events then can trigger many things:

- message
- lore
- spawn
- teleport
- give item
- fire signal
- set flag
- end level

NPC's can also be configured.

![NPC](Res/screenshots/editor_npc_properties.png)

NPC's can have custom dialogue attatched. This is in form of .twee files. Theese files can be produced via Twine.

![Twine](Res/screenshots/Twine.png)

This is an example dialogue. The dialogue can have behaviours assigned to the passages:

| Kind | Tag|
| --- | --- |
|Show the passage only when the condition holds | requires:<item>, if:<flag>, ifnot:<flag>|
|Effects, run once per NPC	| gives:, takes:, item:, organs:, signal:, flag:, unflag:, die|
|Opening passage| start: the first passage tagged start whose conditions hold is where the conversation opens|
## Game

The game starts in a small room. The Player by default is a Rouge called `Whisperbound`.
By consuming one of two corpses in the starting room the player permanently switches class to

- **Fighter**: Gorebound
- **Mage**: Helixbound
- **Rouge**: Whisperbound *Default*

![Game start](<Res/ClassSelect.png>)

The player has a stats panel with various stats.

![alt text](<Res/Stats.png>)

The player can hover over various things in the world and get a hover over text. Depending on length
its displayed at cursor or one of the corners.

![alt text](<Res/hover over text.png>)

![alt text](<Res/hover over at mouse.png>)

### Classes

The Whisperbound (Rouge) has a stamina bar. This bar allows the player to move
and press shift to "sprint". Now instead of 1 tile the player moves in a two tile
pattern.

![alt text](Res/Stamina.png)

The Gorebound (Fighter), has the Mass bar. While consuming various things in the tower
the mass gets accumulated. This mass 

![alt text](Res/MassBar.png)

Gaining a mass level influences max HP by a mod of Mass_Level * 4 and
damage_reduction =+ Mass_Level

```python
self.max_hp += self.mass_level * 4
self.damage_reduction += self.mass_level
```

The Helixbound (Mage), gains mana. This mana can be spent by casting spells. The mage
starts with no spells but can by consuming spell scrolls learn them and use them permanently.
(These values for learning need tweaking and don't feal good at this moment.)

![alt text](Res/mana_bar.png)


### Equipments

If the player equips some stuff there is a separat Equipment screen where all slots and equipped items with corresponding stat changes are displayed. 

![alt text](Res/Equipments.png)