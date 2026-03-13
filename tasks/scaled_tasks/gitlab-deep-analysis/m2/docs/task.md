# Task: GitLab Repository Analysis - Comprehensive (Medium - 4 Projects × 4 APIs)

Analyze **4 GitLab repositories** with comprehensive metrics including project info, contributors, branches, and issues.

## Objective

For each of the following **4 projects**, collect:
1. **Project Info**: Basic project details (stars, forks, description)
2. **Contributors**: Top contributors with commit counts
3. **Branches**: All branches with protection status
4. **Issues**: Recent issues with labels and states

Then compile a comprehensive analysis report.

## Projects to Analyze

| # | Project | GitLab Path |
|---|---------|-------------|
| 1 | GitLab CE | gitlab-org/gitlab |
| 2 | GitLab Runner | gitlab-org/gitlab-runner |
| 3 | Gitaly | gitlab-org/gitaly |
| 4 | GitLab Pages | gitlab-org/gitlab-pages |

## Required Output

Save results to `gitlab_comprehensive.json`:

```json
{
  "projects": [
    {
      "name": "GitLab CE",
      "path": "gitlab-org/gitlab",
      "info": {
        "stars": 24000,
        "forks": 6000,
        "description": "GitLab is a DevOps platform..."
      },
      "contributors": {
        "total": 3000,
        "top_contributors": [
          {"name": "John Doe", "commits": 5000}
        ]
      },
      "branches": {
        "total_count": 100,
        "protected_count": 10,
        "default_branch": "main"
      },
      "issues": {
        "total_count": 50000,
        "open_count": 25000,
        "closed_count": 25000
      },
      "health_score": 92.5
    }
  ],
  "summary": {
    "total_projects": 4,
    "total_stars": 30000,
    "total_contributors": 4000,
    "total_issues": 60000,
    "healthiest_project": "GitLab CE"
  },
  "analysis_date": "2024-01-15"
}
```

## Tools Available

**Data Collection Tools:**
- `local-gitlab_get_project_info`: Get project metadata (stars, forks, description)
- `local-gitlab_get_contributors`: Get top contributors with commit counts
- `local-gitlab_get_branches`: Get branches with protection status
- `local-gitlab_get_issues`: Get issues with labels and states

**File System Tools:**
- `filesystem-write_file`: Write output JSON to file
- `filesystem-read_file`: Read files from workspace

**Task Completion:**
- `local-claim_done`: Signal task completion (REQUIRED at the end)

## Workflow

For each project:
1. `local-gitlab_get_project_info` - Get basic project information
2. `local-gitlab_get_contributors` - Get contributor statistics
3. `local-gitlab_get_branches` - Get branch information
4. `local-gitlab_get_issues` - Get issue statistics

Process all 4 projects and compile summary.

## Important Notes

1. Process ALL 4 projects completely
2. Use skill mode to optimize repeated API calls
3. Calculate health_score based on all metrics
4. Handle API errors gracefully

## REQUIRED: Task Completion Protocol

1. **FIRST**: Collect all data for all 4 projects
2. **SECOND**: Write results to `gitlab_comprehensive.json` using `filesystem-write_file`
3. **THIRD**: Call `local-claim_done` to signal completion

**DO NOT stop without calling `claim_done`!**
