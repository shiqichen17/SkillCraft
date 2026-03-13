# Task: GitLab Project Analysis (Medium - 4 Projects × 4 APIs)

Perform an analysis of **4 GitLab repositories** by collecting multiple data points for each project.

## Objective

For each of the following **4 GitLab projects**, collect:
1. **Project Info**: Stars, forks, description, default branch
2. **Contributors**: Top 5 contributors by commit count
3. **Recent Commits**: Last 20 commits with author info
4. **Branches**: All branches with protection status

Then calculate an **activity score** and **health status** for each project.

## Projects to Analyze

| # | Project | GitLab Path |
|---|---------|-------------|
| 1 | GitLab Runner | gitlab-org/gitlab-runner |
| 2 | Gitaly | gitlab-org/gitaly |
| 3 | GitLab Pages | gitlab-org/gitlab-pages |
| 4 | GitLab Shell | gitlab-org/gitlab-shell |

## Required Output

Save results to `gitlab_analysis_results.json`:

```json
{
  "projects": [
    {
      "path": "gitlab-org/gitlab-runner",
      "name": "GitLab Runner",
      "description": "...",
      "stars": 1234,
      "forks": 567,
      "default_branch": "main",
      "contributors": {
        "total": 150,
        "top_5": [
          {"name": "alice", "commits": 500},
          {"name": "bob", "commits": 300}
        ]
      },
      "commits": {
        "recent_count": 20,
        "authors_in_recent": 8,
        "most_active_author": "alice"
      },
      "branches": {
        "total": 25,
        "default": "main",
        "protected_count": 3
      },
      "activity_score": 85,
      "health_status": "healthy"
    }
  ],
  "summary": {
    "total_projects": 4,
    "avg_activity_score": 75.5,
    "healthiest_project": "gitlab-org/gitlab-runner",
    "most_contributors": "gitlab-org/gitlab-runner",
    "total_stars": 5000,
    "total_forks": 2500
  },
  "analysis_date": "2024-01-15"
}
```

## Activity Score Calculation

Calculate activity score (0-100) based on:
- Recent commits (40%): 20+ commits = 40 points, scale down linearly
- Contributors (30%): 50+ contributors = 30 points, scale down
- Branch activity (30%): Multiple active branches = positive

## Health Status

- **healthy**: activity_score >= 70
- **moderate**: 40 <= activity_score < 70
- **inactive**: activity_score < 40

## Tools Available

**Data Collection Tools:**
- `local-gitlab_get_project_info`: Get project details (stars, forks, description)
- `local-gitlab_get_contributors`: Get contributor list
- `local-gitlab_get_commits`: Get commit history
- `local-gitlab_get_branches`: Get branch information

**File System Tools:**
- `filesystem-write_file`: Write output JSON to file
- `filesystem-read_file`: Read files from workspace

**Task Completion:**
- `local-claim_done`: Signal task completion (REQUIRED at the end)

## Workflow

For each project, you need to call 4 different API endpoints:
1. `local-gitlab_get_project_info` - Basic project details
2. `local-gitlab_get_contributors` - Top contributors
3. `local-gitlab_get_commits` - Recent commit activity
4. `local-gitlab_get_branches` - Branch information

Process all 4 projects systematically and aggregate the results.

## Important Notes

1. Process ALL 4 projects completely - do NOT use placeholder data
2. Use skill mode to optimize repeated API calls
3. Handle API errors gracefully
4. Calculate accurate statistics for the summary

## REQUIRED: Task Completion Protocol

1. **FIRST**: Collect all data for all 4 projects
2. **SECOND**: Write results to `gitlab_analysis_results.json` using `filesystem-write_file`
3. **THIRD**: Call `local-claim_done` to signal completion

**DO NOT stop without calling `claim_done`!**
