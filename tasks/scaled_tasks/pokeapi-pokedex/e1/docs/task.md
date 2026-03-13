# Task: Pokemon Pokedex (3 Pokemon × 3 APIs) - E1

Generate Pokedex entries for **3 Pokemon** using 3 API endpoints per Pokemon.

## Objective

For each of the following **3 Pokemon**, collect:
1. **Details**: basic info, types, stats
2. **Moves**: move list counts
3. **Abilities**: ability info

Calculate **summary statistics** across all Pokemon.

## Pokemon to Analyze

| # | ID | Name | Type |
|---|-----|------|------|
| 1 | 25 | Pikachu | Electric |
| 2 | 6 | Charizard | Fire/Flying |
| 3 | 445 | Garchomp | Dragon/Ground |

## Required Output

Save results to `pokedex_entries.json`:

```json
{
  "pokemon": [
    {"id": 25, "name": "pikachu", "types": ["electric"], "stat_total": 320}
  ],
  "summary": {"total_pokemon": 3, "avg_base_stat_total": 500},
  "analysis_date": "2024-01-15"
}
```

## Tools Available

- `local-pokemon_get_details`: Details
- `local-pokemon_get_moves`: Moves
- `local-pokemon_get_abilities`: Abilities

**File System:** `filesystem-write_file`, `filesystem-read_file`
**Completion:** `local-claim_done` (REQUIRED)

## Workflow

For each Pokemon (IDs: 25, 6, 445):
1. `local-pokemon_get_details`
2. `local-pokemon_get_moves`
3. `local-pokemon_get_abilities`

## Summary Requirements

**⚠️ CRITICAL**: Output ONLY summary statistics for moves, NOT full move lists!

## Important

1. Process ALL 3 Pokemon completely
2. Summarize move data - counts only
3. Call `local-claim_done` to complete
