# Task: Anime Analysis (4 Anime × 4 APIs) - M2

Analyze **4 anime series** using 4 API endpoints per anime.

## Objective

For each of the following **4 anime**, collect:
1. **Basic Info**: title, score, episodes, genres, studios
2. **Characters**: total count, main/supporting, top 3
3. **Episodes**: total count, avg score
4. **Recommendations**: count and top 3

Calculate a **quality score** and **popularity tier** for each anime.

## Anime to Analyze

| # | Title | MAL ID |
|---|-------|--------|
| 1 | Cowboy Bebop | 1 |
| 2 | Fullmetal Alchemist: Brotherhood | 5114 |
| 3 | Death Note | 1535 |
| 4 | Attack on Titan | 16498 |


## Required Output

Save results to `anime_analysis_results.json`:

```json
{
  "anime_list": [
    {
      "mal_id": 1,
      "title": "Cowboy Bebop",
      "score": 8.75,
      "quality_score": 92,
      "popularity_tier": "S"
    }
  ],
  "summary": {
    "total_anime": 4,
    "average_score": 8.65
  },
  "analysis_date": "2024-01-15"
}
```

## Tools Available

**Data Collection Tools:**
- `local-jikan_get_anime_details`: Basic Info
- `local-jikan_get_anime_characters`: Characters
- `local-jikan_get_anime_episodes`: Episodes
- `local-jikan_get_anime_recommendations`: Recommendations

**File System Tools:**
- `filesystem-write_file`: Write output JSON to file
- `filesystem-read_file`: Read files from workspace

**Task Completion:**
- `local-claim_done`: Signal task completion (REQUIRED at the end)

## Workflow

For each of the 4 anime (IDs: 1, 5114, 1535, 16498):
1. `local-jikan_get_anime_details`
2. `local-jikan_get_anime_characters`
3. `local-jikan_get_anime_episodes`
4. `local-jikan_get_anime_recommendations`

Calculate quality scores and compile summary.

## Quality Score (0-100)

- **MAL Score** (40%): `(score / 10) * 40`
- **Popularity** (30%): Based on total members
- **Completion Rate** (20%): `completed / (completed + dropped) * 20`
- **Other** (10%): Recommendations count

## Popularity Tier

- **S-tier**: quality_score >= 90
- **A-tier**: quality_score >= 80
- **B-tier**: quality_score >= 70
- **C-tier**: quality_score < 70

## Important Notes

1. Process ALL 4 anime completely
2. **Summarize large datasets** - counts and top items only
3. Handle API errors gracefully

## REQUIRED: Task Completion

1. Collect all data for all 4 anime
2. Calculate quality scores and tiers
3. Write results to `anime_analysis_results.json`
4. Call `local-claim_done` to complete

**CRITICAL**: Task is NOT complete until `claim_done` is called!
