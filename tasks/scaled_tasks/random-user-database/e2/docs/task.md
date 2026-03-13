# Task: User Database Builder (3 Nationalities × 3 APIs) - E2

Build a user database from **3 nationalities** using 3 API endpoints per nationality.

## Objective

For each of the following **3 nationalities**, collect:
1. **By Nationality**: get users from specific nationality
2. **Get Users**: get multiple random users
3. **Detailed Stats**: get detailed statistics

Calculate **demographic statistics** and **regional distribution**.

## Nationalities

| # | Code | Name | Region |
|---|------|------|--------|
| 1 | US | United States | North America |
| 2 | GB | United Kingdom | Europe |
| 3 | DE | Germany | Europe |

## Required Output

Save results to `user_database.json`:

```json
{
  "nationalities": [
    {"nationality_code": "US", "nationality_name": "United States", "region": "North America", "user_count": 5, "users": [...], "statistics": {}}
  ],
  "summary": {"total_nationalities": 3, "total_users": 15},
  "generation_date": "2024-01-15"
}
```

## Tools Available

- `local-randomuser_by_nationality`: By Nationality
- `local-randomuser_get_users`: Get Users
- `local-randomuser_detailed`: Detailed Stats

**File System:** `filesystem-write_file`, `filesystem-read_file`
**Completion:** `local-claim_done` (REQUIRED)

## Workflow

For each nationality (US, GB, DE):
1. `local-randomuser_by_nationality`
2. `local-randomuser_get_users`
3. `local-randomuser_detailed`

## Age Groups

- **young_adult**: age < 30
- **adult**: 30 <= age < 45
- **middle_aged**: 45 <= age < 60
- **senior**: age >= 60

## Important

1. Process ALL 3 nationalities completely
2. Generate ~5 users per nationality (15 total)
3. Call `local-claim_done` to complete
