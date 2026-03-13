# Task: Blog User Analysis (3 Users × 3 APIs) - E2

Analyze blog activity for **3 users** using 3 API endpoints per user.

## Objective

For each of the following **3 users**, collect:
1. **User Profile**: name, email, company, address
2. **Posts**: all posts with content
3. **Comments**: all comments received

Calculate **productivity score** and **engagement tier** for each user.

## Users to Analyze

| # | User ID | Name |
|---|---------|------|
| 1 | 1 | Leanne Graham |
| 2 | 2 | Ervin Howell |
| 3 | 3 | Clementine Bauch |

## Required Output

Save results to `blog_analysis.json`:

```json
{
  "users": [
    {"user_id": 1, "profile": {"name": "Leanne Graham"}, "activity": {"post_count": 10, "todo_count": 20}, "metrics": {"productivity_score": 75, "engagement_tier": "Active"}}
  ],
  "summary": {"total_users": 3, "total_posts": 30},
  "generation_date": "2024-01-15"
}
```

## Tools Available

- `local-jsonplaceholder_get_user`: User Profile
- `local-jsonplaceholder_get_posts`: Posts
- `local-jsonplaceholder_get_comments`: Comments

**File System:** `filesystem-write_file`, `filesystem-read_file`
**Completion:** `local-claim_done` (REQUIRED)

## Workflow

For each user ID (1, 2, 3):
1. `local-jsonplaceholder_get_user`
2. `local-jsonplaceholder_get_posts`
3. `local-jsonplaceholder_get_comments`

## Productivity Score (0-100)

- **Post Activity** (50%): (post_count / 10) * 50
- **Todo Completion** (50%): completion_rate * 0.5

## Engagement Tier

- **Very Active**: score >= 80
- **Active**: score >= 60
- **Moderate**: score >= 40
- **Low**: score < 40

## Important

1. Process ALL 3 users completely
2. Use ALL 3 tools per user
3. Call `local-claim_done` to complete
