# Task: Rick and Morty Character Analysis (3 Characters × 3 APIs) - E2

Analyze **3 characters** from Rick and Morty using 3 API endpoints per character.

## Objective

For each of the following **3 characters**, collect:
1. **Character Info**: name, status, species, origin
2. **Search Characters**: find related characters
3. **Episode List**: all episodes for character

Calculate **significance score** and **tier** for each character.

## Characters to Analyze

| # | Character | ID |
|---|-----------|----|
| 1 | Rick Sanchez | 1 |
| 2 | Morty Smith | 2 |
| 3 | Summer Smith | 3 |

## Required Output

Save results to `rickmorty_analysis.json`:

```json
{
  "characters": [
    {"id": 1, "name": "Rick Sanchez", "status": "Alive", "species": "Human", "significance_score": 100, "significance_tier": "Main"}
  ],
  "summary": {"total_characters": 3, "species_distribution": {"Human": 3}},
  "analysis_date": "2024-01-15"
}
```

## Tools Available

- `local-rickmorty_get_character`: Character Info
- `local-rickmorty_search_characters`: Search Characters
- `local-rickmorty_get_character_episodes`: Episode List

**File System:** `filesystem-write_file`, `filesystem-read_file`
**Completion:** `local-claim_done` (REQUIRED)

## Workflow

For each of the 3 characters (IDs: 1, 2, 3):
1. `local-rickmorty_get_character`
2. `local-rickmorty_search_characters`
3. `local-rickmorty_get_character_episodes`

## Significance Score (0-100)

- **Episode Count** (60%): `(char_episodes / max_episodes) * 60`
- **Status** (20%): Alive=20, unknown=10, Dead=5
- **Location** (20%): Main Earth/Citadel=20, Other=10

## Tier

- **Main**: score >= 80
- **Recurring**: score >= 50
- **Supporting**: score >= 30
- **Minor**: score < 30

## Important

1. Process ALL 3 characters completely
2. **Summarize episode data** - counts only
3. Call `local-claim_done` to complete
