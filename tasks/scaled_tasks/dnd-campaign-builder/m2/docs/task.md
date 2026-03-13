# Task: D&D Character Builder (4 Characters × 4 APIs) - M2

Create character templates for **4 D&D character builds** using 4 API endpoints per character.

## Objective

For each of the following **4 character builds**, collect:
1. **Class Info**: hit die, proficiencies, saving throws
2. **Race Info**: ability bonuses, speed, traits
3. **Class Spells**: available spell list
4. **Spell Details**: specific spell info

Calculate **combat rating** and **versatility score** for each build.

## Characters to Create

| # | Build Name | Class | Race |
|---|------------|-------|------|
| 1 | Human Fighter | Fighter | Human |
| 2 | Elf Wizard | Wizard | Elf |
| 3 | Dwarf Cleric | Cleric | Dwarf |
| 4 | Halfling Rogue | Rogue | Halfling |

## Required Output

Save results to `dnd_character_templates.json`:

```json
{
  "characters": [
    {"build_name": "Human Fighter", "class": {"name": "Fighter"}, "race": {"name": "Human"}, "combat_rating": 85, "versatility_score": 70}
  ],
  "summary": {"total_characters": 4, "avg_combat_rating": 80},
  "analysis_date": "2024-01-15"
}
```

## Tools Available

- `local-dnd_get_class`: Class Info
- `local-dnd_get_race`: Race Info
- `local-dnd_get_class_spells`: Class Spells
- `local-dnd_get_spell`: Spell Details

**File System:** `filesystem-write_file`, `filesystem-read_file`
**Completion:** `local-claim_done` (REQUIRED)

## Workflow

For each character (Human Fighter, Elf Wizard, Dwarf Cleric, Halfling Rogue):
1. `local-dnd_get_class`
2. `local-dnd_get_race`
3. `local-dnd_get_class_spells`
4. `local-dnd_get_spell`

## Combat Rating (0-100)

- **Hit Die** (30%): d12=30, d10=25, d8=20, d6=15
- **Armor Proficiency** (40%): Heavy=40, Medium=30, Light=20, None=10
- **Weapon Proficiency** (30%): Martial+Simple=30, Simple=15

## Important

1. Process ALL 4 characters completely
2. Summarize spell lists - counts only
3. Call `local-claim_done` to complete
