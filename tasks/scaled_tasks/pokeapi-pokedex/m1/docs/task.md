# Task: Pokemon Pokedex (4 Pokemon × 4 APIs) - M1

Generate Pokedex entries for **4 Pokemon** using 4 API endpoints per Pokemon.

## Objective

For each of the following **4 Pokemon**, collect:
1. **Details**: basic info, types, stats
2. **Species**: genus, generation, legendary status
3. **Evolution**: evolution chain info
4. **Moves**: move list counts

Calculate **summary statistics** across all Pokemon.

## Pokemon to Analyze

| # | ID | Name | Type |
|---|-----|------|------|
| 1 | 25 | Pikachu | Electric |
| 2 | 6 | Charizard | Fire/Flying |
| 3 | 445 | Garchomp | Dragon/Ground |
| 4 | 94 | Gengar | Ghost/Poison |

## ⚠️ IMPORTANT: Tool Order Constraint

**`pokemon_get_species` MUST be called BEFORE `pokemon_get_evolution`** for each Pokemon.
The evolution endpoint requires the evolution_chain_id from species data.

## Required Output

Save results to `pokedex_entries.json`:

```json
{
  "pokemon": [
    {"id": 25, "name": "pikachu", "types": ["electric"], "stat_total": 320}
  ],
  "summary": {"total_pokemon": 4, "avg_base_stat_total": 500},
  "analysis_date": "2024-01-15"
}
```

## Tools Available

- `local-pokemon_get_details`: Details
- `local-pokemon_get_species`: Species
- `local-pokemon_get_evolution`: Evolution
- `local-pokemon_get_moves`: Moves

**File System:** `filesystem-write_file`, `filesystem-read_file`
**Completion:** `local-claim_done` (REQUIRED)

## Workflow

For each Pokemon (IDs: 25, 6, 445, 94):
1. `local-pokemon_get_details`
2. `local-pokemon_get_species`
3. `local-pokemon_get_evolution`
4. `local-pokemon_get_moves`

## Summary Requirements

**⚠️ CRITICAL**: Output ONLY summary statistics for moves, NOT full move lists!

## Important

1. Process ALL 4 Pokemon completely
2. Summarize move data - counts only
3. Call `local-claim_done` to complete
