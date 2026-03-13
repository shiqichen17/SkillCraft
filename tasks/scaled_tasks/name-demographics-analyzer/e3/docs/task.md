# Task: Name Demographics (3 Names × 3 APIs) - E3

Analyze demographics of **3 international names** using 3 API endpoints per name.

## Objective

For each of the following **3 names**, collect:
1. **Age**: predict age
2. **Nationality**: predict nationality
3. **Statistics**: statistical analysis

Create a **demographic profile** for each name.

## Names to Analyze

| # | Name | Expected Origin |
|---|------|----------------|
| 1 | Michael | Western/English |
| 2 | Yuki | Japanese |
| 3 | Hans | German |

## Required Output

Save results to `name_demographics.json`:

```json
{
  "names": [
    {"name": "Michael", "gender": {"prediction": "male", "probability": 0.99}, "profile": {"cultural_origin": "Western"}}
  ],
  "summary": {"total_names": 3, "gender_distribution": {"male": 2, "female": 1}},
  "analysis_date": "2024-01-15"
}
```

## Tools Available

- `local-name_age`: Age
- `local-name_nationality`: Nationality
- `local-name_statistics`: Statistics

**File System:** `filesystem-write_file`, `filesystem-read_file`
**Completion:** `local-claim_done` (REQUIRED)

## Workflow

For each name (Michael, Yuki, Hans):
1. `local-name_age`
2. `local-name_nationality`
3. `local-name_statistics`

## Age Groups

- **young_adult**: age < 30
- **adult**: 30 <= age < 45
- **middle_aged**: 45 <= age < 60
- **senior**: age >= 60

## Important

1. Process ALL 3 names completely
2. Include probability scores
3. Call `local-claim_done` to complete
