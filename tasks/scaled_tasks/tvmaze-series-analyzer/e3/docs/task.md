# Task: TV Series Analysis (3 Shows × 3 APIs) - E3

Perform analysis of **3 TV series** using 3 API endpoints per show.

## Objective

For each of the following **3 TV shows**, collect:
1. **Season Summary**: Season count, episodes per season stats
2. **Cast Summary**: Total count, lead actors
3. **Crew Summary**: Creator, director/writer counts

Then calculate a **binge rating** and **marathon hours** for each show.

## Shows to Analyze

| # | Title | TVMaze ID |
|---|-------|----------|
| 1 | Breaking Bad | 169 |
| 2 | Game of Thrones | 82 |
| 3 | The Office | 526 |


## Required Output

Save results to `tv_series_analysis.json`:

```json
{
  "shows": [
    {
      "id": 169,
      "name": "Breaking Bad",
      "seasons": {"count": 5, "avg_episodes_per_season": 12.4}, "cast": {"total_count": 50, "leads": [{"actor": "Bryan Cranston", "character": "Walter White"}]}, "crew": {"creator": "Vince Gilligan", "directors_count": 15},
      "marathon_hours": 46.5,
      "binge_rating": "A+"
    }
  ],
  "summary": {
    "total_shows": 3,
    "avg_rating": 8.7
  },
  "analysis_date": "2024-01-15"
}
```

## Tools Available

**Data Collection Tools:**
- `local-tvmaze_get_show_seasons`: Season Summary
- `local-tvmaze_get_show_cast`: Cast Summary
- `local-tvmaze_get_show_crew`: Crew Summary

**File System Tools:**
- `filesystem-write_file`: Write output JSON to file
- `filesystem-read_file`: Read files from workspace

**Task Completion:**
- `local-claim_done`: Signal task completion (REQUIRED at the end)

## Workflow

For each of the 3 shows (IDs: 169, 82, 526):
1. `local-tvmaze_get_show_seasons`
2. `local-tvmaze_get_show_cast`
3. `local-tvmaze_get_show_crew`

Calculate marathon hours and binge ratings, compile summary.

## Binge Rating Calculation

Based on marathon_hours and avg_rating:
- **A+**: marathon_hours < 50 AND avg_rating >= 9.0
- **A**: marathon_hours < 100 AND avg_rating >= 8.5
- **B+**: marathon_hours < 150 AND avg_rating >= 8.0
- **B**: marathon_hours < 200 AND avg_rating >= 7.5
- **C**: all others

## Important Notes

1. Process ALL 3 shows completely - do NOT use placeholder data
2. **Summarize data** - store counts, averages, and key items only
3. Calculate marathon_hours as `total_runtime_minutes / 60`
4. Handle API errors gracefully

## REQUIRED: Task Completion Protocol

1. **FIRST**: Collect all data for all 3 shows
2. **SECOND**: Calculate marathon hours and binge ratings
3. **THIRD**: Write the complete results to `tv_series_analysis.json` using `filesystem-write_file`
4. **FOURTH**: Call `local-claim_done` to signal task completion

**CRITICAL**: The task is NOT complete until `claim_done` is called!
