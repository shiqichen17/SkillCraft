# Task: GitLab Repository Analysis - Branches & Issues (Easy - 3 Projects × 3 APIs)

Analyze **3 GitLab repositories** focusing on project info, branches, and issues.

## Objective

For each of the following **3 projects**, collect:
1. **Project Info**: Basic project details (stars, forks, description)
2. **Branches**: All branches with protection status
3. **Issues**: Recent issues with labels and states

Then compile an analysis report with comparative statistics.

## Projects to Analyze

| # | Project | GitLab Path |
|---|---------|-------------|
| 1 | GitLab Shell | gitlab-org/gitlab-shell |
| 2 | GitLab Runner | gitlab-org/gitlab-runner |
| 3 | GitLab Pages | gitlab-org/gitlab-pages |

## Required Output

Save results to `gitlab_analysis.json`:

```json
{
  "projects": [
    {
      "name": "GitLab Shell",
      "path": "gitlab-org/gitlab-shell",
      "info": {
        "stars": 600,
        "forks": 400,
        "description": "SSH access and repository management..."
      },
      "branches": {
        "total_count": 50,
        "protected_count": 5,
        "default_branch": "main",
        "recent_branches": ["main", "develop", "feature-x"]
      },
      "issues": {
        "total_count": 1000,
        "open_count": 500,
        "closed_count": 500,
        "recent_issues": [
          {"title": "Bug fix", "state": "open", "labels": ["bug"]}
        ]
      }
    }
  ],
  "summary": {
    "total_projects": 3,
    "total_branches": 150,
    "total_issues": 3000,
    "most_active_project": "GitLab Runner"
  },
  "analysis_date": "2024-01-15"
}
```

## Tools Available

**Data Collection Tools:**
- `local-gitlab_get_project_info`: Get project metadata (stars, forks, description)
- `local-gitlab_get_branches`: Get all branches with protection status
- `local-gitlab_get_issues`: Get issues with labels and states

**File System Tools:**
- `filesystem-write_file`: Write output JSON to file
- `filesystem-read_file`: Read files from workspace

**Task Completion:**
- `local-claim_done`: Signal task completion (REQUIRED at the end)

## Workflow

For each project:
1. `local-gitlab_get_project_info` - Get basic project information
2. `local-gitlab_get_branches` - Get branch information
3. `local-gitlab_get_issues` - Get issue statistics

Process all 3 projects and compile summary.

## Important Notes

1. Process ALL 3 projects completely
2. Use skill mode to optimize repeated API calls
3. Store summarized data, not full raw responses
4. Handle API errors gracefully

## REQUIRED: Task Completion Protocol

1. **FIRST**: Collect all data for all 3 projects
2. **SECOND**: Write results to `gitlab_analysis.json` using `filesystem-write_file`
3. **THIRD**: Call `local-claim_done` to signal completion

**DO NOT stop without calling `claim_done`!**
