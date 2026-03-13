# Task: GitLab Deep Project Analysis (Hard - 5 Projects)

Perform a comprehensive analysis of **5 GitLab repositories** by collecting and analyzing multiple data points for each project.

## Objective

For each of the following **5 GitLab projects**, collect:
1. **Project Info**: Stars, forks, description, default branch
2. **Contributors**: Top 5 contributors by commit count
3. **Recent Commits**: Last 20 commits with author info
4. **Branches**: All branches with protection status
5. **Issues**: Open issues count and recent issue titles

Then calculate an **activity score** and **health status** for each project.

## Projects to Analyze

1. `gitlab-org/gitlab-runner`
2. `gitlab-org/gitaly`
3. `gitlab-org/gitlab-pages`
4. `gitlab-org/gitlab-shell`
5. `gitlab-org/cli`

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
      "issues": {
        "open_count": 45,
        "recent_titles": ["Issue 1", "Issue 2", "Issue 3"]
      },
      "activity_score": 85,
      "health_status": "healthy"
    }
  ],
  "summary": {
    "total_projects": 5,
    "avg_activity_score": 72.5,
    "healthiest_project": "gitlab-org/gitlab-runner",
    "most_contributors": "gitlab-org/gitlab-runner",
    "total_stars": 8000,
    "total_forks": 4000
  },
  "analysis_date": "2024-01-15"
}
```

## Activity Score Calculation

Calculate activity score (0-100) based on:
- Recent commits (40%): 20+ commits = 40 points, scale down linearly
- Contributors (30%): 50+ contributors = 30 points, scale down
- Open issues engagement (20%): Having active issues = positive
- Branch activity (10%): Multiple active branches = positive

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
- `local-gitlab_get_issues`: Get issue list

**File System Tools:**
- `filesystem-write_file`: Write output JSON to file (**USE THIS, NOT "write_file"**)
- `filesystem-read_file`: Read files from workspace

**Task Completion:**
- `local-claim_done`: Signal task completion (REQUIRED at the end)


## Workflow

For each project, you need to call 5 different API endpoints to collect complete information:
1. `local-gitlab_get_project_info` - Basic project details
2. `local-gitlab_get_contributors` - Top contributors
3. `local-gitlab_get_commits` - Recent commit activity
4. `local-gitlab_get_branches` - Branch information
5. `local-gitlab_get_issues` - Open issues

Process all 5 projects systematically and aggregate the results.

## Important Notes

1. Process ALL 5 projects completely - do NOT use placeholder data
2. Use skill mode to optimize repeated API calls
3. Handle API errors gracefully (mark as "unavailable" if project not found)
4. Calculate accurate statistics for the summary

## REQUIRED: Task Completion Protocol

**You MUST follow this exact sequence to complete the task:**

1. **FIRST**: Collect all data for all 5 projects
2. **SECOND**: Write the complete results to `gitlab_analysis_results.json` using `filesystem-write_file`
3. **THIRD**: Call `local-claim_done` to signal task completion

**CRITICAL WARNINGS:**
- **DO NOT stop after saving the file** - you MUST call `local-claim_done`!
- **The task is NOT complete until `claim_done` is called** - saving the file alone is insufficient
- **If you don't call `claim_done`, the task will be marked as FAILED** even if the results are correct
- Call `claim_done` with `{"status": "done"}` as the argument
