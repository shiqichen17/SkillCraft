# Task: Pokemon Pokedex (5 Pokemon × 5 APIs) - H1

Generate Pokedex entries for **5 Pokemon** using 5 API endpoints per Pokemon.

## Objective

For each of the following **5 Pokemon**, collect:
1. **Details**: basic info, types, stats
2. **Species**: genus, generation, legendary status
3. **Evolution**: evolution chain info
4. **Moves**: move list counts
5. **Abilities**: ability info

Calculate **summary statistics** across all Pokemon.

## Pokemon to Analyze

| # | ID | Name | Type |
|---|-----|------|------|
| 1 | 25 | Pikachu | Electric |
| 2 | 6 | Charizard | Fire/Flying |
| 3 | 445 | Garchomp | Dragon/Ground |
| 4 | 94 | Gengar | Ghost/Poison |
| 5 | 150 | Mewtwo | Psychic |

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
  "summary": {"total_pokemon": 5, "avg_base_stat_total": 500},
  "analysis_date": "2024-01-15"
}
```

## Tools Available

- `local-pokemon_get_details`: Details
- `local-pokemon_get_species`: Species
- `local-pokemon_get_evolution`: Evolution
- `local-pokemon_get_moves`: Moves
- `local-pokemon_get_abilities`: Abilities

**File System:** `filesystem-write_file`, `filesystem-read_file`
**Completion:** `local-claim_done` (REQUIRED)

## Workflow

For each Pokemon (IDs: 25, 6, 445, 94, 150):
1. `local-pokemon_get_details`
2. `local-pokemon_get_species`
3. `local-pokemon_get_evolution`
4. `local-pokemon_get_moves`
5. `local-pokemon_get_abilities`

## Summary Requirements

**⚠️ CRITICAL**: Output ONLY summary statistics for moves, NOT full move lists!

## Important

1. Process ALL 5 Pokemon completely
2. Summarize move data - counts only
3. Call `local-claim_done` to complete
