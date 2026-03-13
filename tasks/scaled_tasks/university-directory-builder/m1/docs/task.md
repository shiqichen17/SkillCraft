# Task: University Directory (4 Countries × 4 APIs) - M1

Build a university directory from **4 countries** using 4 API endpoints per country.

## Objective

For each of the following **4 countries**, collect:
1. **By Country**: get universities in a country
2. **By Name**: search by university name
3. **Details**: detailed university info
4. **By Domain**: search by domain

Calculate **education rank** and **tier** for each country.

## Countries to Include

| # | Country | Code | Expected |
|---|---------|------|----------|
| 1 | Canada | CA | 150+ |
| 2 | United Kingdom | GB | 190+ |
| 3 | France | FR | 290+ |
| 4 | Germany | DE | 300+ |

## Required Output

Save results to `university_directory.json`:

```json
{
  "countries": [
    {"country": "Canada", "alpha_code": "CA", "statistics": {"total_universities": 150}, "education_rank": 1, "tier": "Major"}
  ],
  "summary": {"total_countries": 4, "total_universities": 500, "largest_system": {"country": "Canada"}},
  "analysis_date": "2024-01-15"
}
```

## Tools Available

- `local-university_by_country`: By Country
- `local-university_by_name`: By Name
- `local-university_details`: Details
- `local-university_by_domain`: By Domain

**File System:** `filesystem-write_file`, `filesystem-read_file`
**Completion:** `local-claim_done` (REQUIRED)

## Workflow

For each country (Canada, United Kingdom, France, Germany):
1. `local-university_by_country`
2. `local-university_by_name`
3. `local-university_details`
4. `local-university_by_domain`

## Education Tier

- **World Leader**: 400+ universities
- **Major**: 150-400 universities
- **Established**: 50-150 universities
- **Developing**: < 50 universities

## Summary Requirements

**⚠️ CRITICAL**: Output ONLY summary statistics, NOT full university lists!

## Important

1. Process ALL 4 countries completely
2. Summarize university data - counts only
3. Call `local-claim_done` to complete
