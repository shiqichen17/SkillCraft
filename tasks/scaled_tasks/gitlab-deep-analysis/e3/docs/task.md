# Task: GitLab Repository Analysis - Development Activity (Easy - 3 Projects × 3 APIs)

Analyze **3 GitLab repositories** focusing on contributors, commits, and branches.

## Objective

For each of the following **3 projects**, collect:
1. **Contributors**: Top contributors with commit counts
2. **Commits**: Recent commit history and statistics
3. **Branches**: All branches with protection status

Then compile a development activity report.

## Projects to Analyze

| # | Project | GitLab Path |
|---|---------|-------------|
| 1 | GitLab Runner | gitlab-org/gitlab-runner |
| 2 | Gitaly | gitlab-org/gitaly |
| 3 | GitLab Pages | gitlab-org/gitlab-pages |

## Required Output

Save results to `gitlab_activity.json`:

```json
{
  "projects": [
    {
      "name": "GitLab Runner",
      "path": "gitlab-org/gitlab-runner",
      "contributors": {
        "total": 150,
        "top_contributors": [
          {"name": "John Doe", "commits": 500}
        ]
      },
      "commits": {
        "recent_count": 100,
        "recent_commits": [
          {"id": "abc123", "message": "Fix bug", "author": "John"}
        ]
      },
      "branches": {
        "total_count": 30,
        "protected_count": 3,
        "default_branch": "main"
      },
      "activity_score": 85.5
    }
  ],
  "summary": {
    "total_projects": 3,
    "total_contributors": 450,
    "total_commits": 300,
    "most_active_project": "GitLab Runner"
  },
  "analysis_date": "2024-01-15"
}
```

## Tools Available

**Data Collection Tools:**
- `local-gitlab_get_contributors`: Get top contributors with commit counts
- `local-gitlab_get_commits`: Get recent commits with authors
- `local-gitlab_get_branches`: Get branches with protection status

**File System Tools:**
- `filesystem-write_file`: Write output JSON to file
- `filesystem-read_file`: Read files from workspace

**Task Completion:**
- `local-claim_done`: Signal task completion (REQUIRED at the end)

## Workflow

For each project:
1. `local-gitlab_get_contributors` - Get contributor statistics
2. `local-gitlab_get_commits` - Get recent commit history
3. `local-gitlab_get_branches` - Get branch information

Process all 3 projects and compile summary.

## Important Notes

1. Process ALL 3 projects completely
2. Use skill mode to optimize repeated API calls
3. Calculate activity_score based on contributors and commits
4. Handle API errors gracefully

## REQUIRED: Task Completion Protocol

1. **FIRST**: Collect all data for all 3 projects
2. **SECOND**: Write results to `gitlab_activity.json` using `filesystem-write_file`
3. **THIRD**: Call `local-claim_done` to signal completion

**DO NOT stop without calling `claim_done`!**
