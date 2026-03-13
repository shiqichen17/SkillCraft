# Task: Name Demographics (5 Names × 5 APIs) - H1

Analyze demographics of **5 international names** using 5 API endpoints per name.

## Objective

For each of the following **5 names**, collect:
1. **Gender**: predict gender
2. **Age**: predict age
3. **Nationality**: predict nationality
4. **Full Demographics**: comprehensive analysis
5. **Statistics**: statistical analysis

Create a **demographic profile** for each name.

## Names to Analyze

| # | Name | Expected Origin |
|---|------|----------------|
| 1 | Michael | Western/English |
| 2 | Yuki | Japanese |
| 3 | Hans | German |
| 4 | Maria | Hispanic/European |
| 5 | Chen | Chinese |

## Required Output

Save results to `name_demographics.json`:

```json
{
  "names": [
    {"name": "Michael", "gender": {"prediction": "male", "probability": 0.99}, "profile": {"cultural_origin": "Western"}}
  ],
  "summary": {"total_names": 5, "gender_distribution": {"male": 2, "female": 1}},
  "analysis_date": "2024-01-15"
}
```

## Tools Available

- `local-name_gender`: Gender
- `local-name_age`: Age
- `local-name_nationality`: Nationality
- `local-name_full_demographics`: Full Demographics
- `local-name_statistics`: Statistics

**File System:** `filesystem-write_file`, `filesystem-read_file`
**Completion:** `local-claim_done` (REQUIRED)

## Workflow

For each name (Michael, Yuki, Hans, Maria, Chen):
1. `local-name_gender`
2. `local-name_age`
3. `local-name_nationality`
4. `local-name_full_demographics`
5. `local-name_statistics`

## Age Groups

- **young_adult**: age < 30
- **adult**: 30 <= age < 45
- **middle_aged**: 45 <= age < 60
- **senior**: age >= 60

## Important

1. Process ALL 5 names completely
2. Include probability scores
3. Call `local-claim_done` to complete
