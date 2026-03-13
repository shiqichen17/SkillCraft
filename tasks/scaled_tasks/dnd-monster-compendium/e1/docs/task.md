# Task: D&D Monster Compendium (3 Monsters × 3 APIs) - E1

Create monster entries for **3 iconic D&D monsters** using 3 API endpoints per monster.

## Objective

For each of the following **3 monsters**, collect:
1. **Monster Info**: HP, AC, CR, abilities
2. **Spell Info**: spell details
3. **Class Info**: class data

Calculate **threat rating** and **recommended party level** for each monster.

## Monsters to Document

| # | Monster | Index |
|---|---------|-------|
| 1 | Adult Red Dragon | adult-red-dragon |
| 2 | Kraken | kraken |
| 3 | Aboleth | aboleth |

## Required Output

Save results to `monster_compendium.json`:

```json
{
  "monsters": [
    {"index": "adult-red-dragon", "name": "Adult Red Dragon", "challenge_rating": 17, "xp": 18000, "threat_rating": "Deadly", "recommended_party_level": 15}
  ],
  "summary": {"total_monsters": 3, "total_xp": 50000},
  "analysis_date": "2024-01-15"
}
```

## Tools Available

- `local-dnd_get_monster`: Monster Info
- `local-dnd_get_spell`: Spell Info
- `local-dnd_get_class`: Class Info

**File System:** `filesystem-write_file`, `filesystem-read_file`
**Completion:** `local-claim_done` (REQUIRED)

## Workflow

For each monster (Adult Red Dragon, Kraken, Aboleth):
1. `local-dnd_get_monster`
2. `local-dnd_get_spell`
3. `local-dnd_get_class`

## Threat Rating

- **Deadly**: CR >= 20
- **Legendary**: CR >= 15
- **Dangerous**: CR >= 10
- **Moderate**: CR >= 5
- **Easy**: CR < 5

## Important

1. Process ALL 3 monsters completely
2. Summarize combat data
3. Call `local-claim_done` to complete
