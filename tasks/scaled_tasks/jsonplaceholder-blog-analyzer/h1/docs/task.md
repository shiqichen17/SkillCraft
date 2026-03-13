# Task: Blog User Analysis (5 Users × 5 APIs) - H1

Analyze blog activity for **5 users** using 5 API endpoints per user.

## Objective

For each of the following **5 users**, collect:
1. **User Profile**: name, email, company, address
2. **Posts**: all posts with content
3. **Todos**: all todos with completion status
4. **Comments**: all comments received
5. **Full Profile**: comprehensive user profile

Calculate **productivity score** and **engagement tier** for each user.

## Users to Analyze

| # | User ID | Name |
|---|---------|------|
| 1 | 1 | Leanne Graham |
| 2 | 2 | Ervin Howell |
| 3 | 3 | Clementine Bauch |
| 4 | 4 | Patricia Lebsack |
| 5 | 5 | Chelsey Dietrich |

## Required Output

Save results to `blog_analysis.json`:

```json
{
  "users": [
    {"user_id": 1, "profile": {"name": "Leanne Graham"}, "activity": {"post_count": 10, "todo_count": 20}, "metrics": {"productivity_score": 75, "engagement_tier": "Active"}}
  ],
  "summary": {"total_users": 5, "total_posts": 50},
  "generation_date": "2024-01-15"
}
```

## Tools Available

- `local-jsonplaceholder_get_user`: User Profile
- `local-jsonplaceholder_get_posts`: Posts
- `local-jsonplaceholder_get_todos`: Todos
- `local-jsonplaceholder_get_comments`: Comments
- `local-jsonplaceholder_user_profile`: Full Profile

**File System:** `filesystem-write_file`, `filesystem-read_file`
**Completion:** `local-claim_done` (REQUIRED)

## Workflow

For each user ID (1, 2, 3, 4, 5):
1. `local-jsonplaceholder_get_user`
2. `local-jsonplaceholder_get_posts`
3. `local-jsonplaceholder_get_todos`
4. `local-jsonplaceholder_get_comments`
5. `local-jsonplaceholder_user_profile`

## Productivity Score (0-100)

- **Post Activity** (50%): (post_count / 10) * 50
- **Todo Completion** (50%): completion_rate * 0.5

## Engagement Tier

- **Very Active**: score >= 80
- **Active**: score >= 60
- **Moderate**: score >= 40
- **Low**: score < 40

## Important

1. Process ALL 5 users completely
2. Use ALL 5 tools per user
3. Call `local-claim_done` to complete
