# Task: User Database Builder (5 Nationalities × 5 APIs) - H1

Build a user database from **5 nationalities** using 5 API endpoints per nationality.

## Objective

For each of the following **5 nationalities**, collect:
1. **By Nationality**: get users from specific nationality
2. **Get Users**: get multiple random users
3. **Get User**: get a single user
4. **Profile**: get user profile with extended info
5. **Detailed Stats**: get detailed statistics

Calculate **demographic statistics** and **regional distribution**.

## Nationalities

| # | Code | Name | Region |
|---|------|------|--------|
| 1 | US | United States | North America |
| 2 | GB | United Kingdom | Europe |
| 3 | DE | Germany | Europe |
| 4 | FR | France | Europe |
| 5 | AU | Australia | Oceania |

## Required Output

Save results to `user_database.json`:

```json
{
  "nationalities": [
    {"nationality_code": "US", "nationality_name": "United States", "region": "North America", "user_count": 5, "users": [...], "statistics": {}}
  ],
  "summary": {"total_nationalities": 5, "total_users": 25},
  "generation_date": "2024-01-15"
}
```

## Tools Available

- `local-randomuser_by_nationality`: By Nationality
- `local-randomuser_get_users`: Get Users
- `local-randomuser_get_user`: Get User
- `local-randomuser_profile`: Profile
- `local-randomuser_detailed`: Detailed Stats

**File System:** `filesystem-write_file`, `filesystem-read_file`
**Completion:** `local-claim_done` (REQUIRED)

## Workflow

For each nationality (US, GB, DE, FR, AU):
1. `local-randomuser_by_nationality`
2. `local-randomuser_get_users`
3. `local-randomuser_get_user`
4. `local-randomuser_profile`
5. `local-randomuser_detailed`

## Age Groups

- **young_adult**: age < 30
- **adult**: 30 <= age < 45
- **middle_aged**: 45 <= age < 60
- **senior**: age >= 60

## Important

1. Process ALL 5 nationalities completely
2. Generate ~5 users per nationality (25 total)
3. Call `local-claim_done` to complete
