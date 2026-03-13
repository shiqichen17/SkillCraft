# Task: D&D Monster Compendium (4 Monsters × 4 APIs) - M2

Create monster entries for **4 iconic D&D monsters** using 4 API endpoints per monster.

## Objective

For each of the following **4 monsters**, collect:
1. **Monster Info**: HP, AC, CR, abilities
2. **Class Info**: class data
3. **Race Info**: race data
4. **Equipment**: gear categories

Calculate **threat rating** and **recommended party level** for each monster.

## Monsters to Document

| # | Monster | Index |
|---|---------|-------|
| 1 | Adult Red Dragon | adult-red-dragon |
| 2 | Kraken | kraken |
| 3 | Aboleth | aboleth |
| 4 | Lich | lich |

## Required Output

Save results to `monster_compendium.json`:

```json
{
  "monsters": [
    {"index": "adult-red-dragon", "name": "Adult Red Dragon", "challenge_rating": 17, "xp": 18000, "threat_rating": "Deadly", "recommended_party_level": 15}
  ],
  "summary": {"total_monsters": 4, "total_xp": 50000},
  "analysis_date": "2024-01-15"
}
```

## Tools Available

- `local-dnd_get_monster`: Monster Info
- `local-dnd_get_class`: Class Info
- `local-dnd_get_race`: Race Info
- `local-dnd_get_equipment_category`: Equipment

**File System:** `filesystem-write_file`, `filesystem-read_file`
**Completion:** `local-claim_done` (REQUIRED)

## Workflow

For each monster (Adult Red Dragon, Kraken, Aboleth, Lich):
1. `local-dnd_get_monster`
2. `local-dnd_get_class`
3. `local-dnd_get_race`
4. `local-dnd_get_equipment_category`

## Threat Rating

- **Deadly**: CR >= 20
- **Legendary**: CR >= 15
- **Dangerous**: CR >= 10
- **Moderate**: CR >= 5
- **Easy**: CR < 5

## Important

1. Process ALL 4 monsters completely
2. Summarize combat data
3. Call `local-claim_done` to complete
