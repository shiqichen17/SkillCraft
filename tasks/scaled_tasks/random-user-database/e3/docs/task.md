# Task: User Database Builder (3 Nationalities × 3 APIs) - E3

Build a user database from **3 nationalities** using 3 API endpoints per nationality.

## Objective

For each of the following **3 nationalities**, collect:
1. **Get Users**: get multiple random users
2. **Profile**: get user profile with extended info
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

- `local-randomuser_get_users`: Get Users
- `local-randomuser_profile`: Profile
- `local-randomuser_detailed`: Detailed Stats

**File System:** `filesystem-write_file`, `filesystem-read_file`
**Completion:** `local-claim_done` (REQUIRED)

## Workflow

For each nationality (US, GB, DE):
1. `local-randomuser_get_users`
2. `local-randomuser_profile`
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
