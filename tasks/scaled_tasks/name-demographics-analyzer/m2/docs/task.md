# Task: Name Demographics (4 Names × 4 APIs) - M2

Analyze demographics of **4 international names** using 4 API endpoints per name.

## Objective

For each of the following **4 names**, collect:
1. **Gender**: predict gender
2. **Nationality**: predict nationality
3. **Full Demographics**: comprehensive analysis
4. **Statistics**: statistical analysis

Create a **demographic profile** for each name.

## Names to Analyze

| # | Name | Expected Origin |
|---|------|----------------|
| 1 | Michael | Western/English |
| 2 | Yuki | Japanese |
| 3 | Hans | German |
| 4 | Maria | Hispanic/European |

## Required Output

Save results to `name_demographics.json`:

```json
{
  "names": [
    {"name": "Michael", "gender": {"prediction": "male", "probability": 0.99}, "profile": {"cultural_origin": "Western"}}
  ],
  "summary": {"total_names": 4, "gender_distribution": {"male": 2, "female": 1}},
  "analysis_date": "2024-01-15"
}
```

## Tools Available

- `local-name_gender`: Gender
- `local-name_nationality`: Nationality
- `local-name_full_demographics`: Full Demographics
- `local-name_statistics`: Statistics

**File System:** `filesystem-write_file`, `filesystem-read_file`
**Completion:** `local-claim_done` (REQUIRED)

## Workflow

For each name (Michael, Yuki, Hans, Maria):
1. `local-name_gender`
2. `local-name_nationality`
3. `local-name_full_demographics`
4. `local-name_statistics`

## Age Groups

- **young_adult**: age < 30
- **adult**: 30 <= age < 45
- **middle_aged**: 45 <= age < 60
- **senior**: age >= 60

## Important

1. Process ALL 4 names completely
2. Include probability scores
3. Call `local-claim_done` to complete
