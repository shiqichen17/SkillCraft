# Task: GitLab Basic Project Analysis (Easy - 3 Projects × 3 APIs)

Perform a basic analysis of **3 GitLab repositories** by collecting key data points.

## Objective

For each of the following **3 GitLab projects**, collect:
1. **Project Info**: Stars, forks, description, default branch
2. **Contributors**: Top 5 contributors by commit count
3. **Issues**: Open and closed issues with labels

Then calculate an **activity score** and **health status** for each project.

## Projects to Analyze

1. `gitlab-org/gitlab-runner`
2. `gitlab-org/gitaly`
3. `gitlab-org/gitlab-pages`

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
      "issues": {
        "open_count": 45,
        "closed_count": 200,
        "top_labels": ["bug", "feature", "documentation"]
      },
      "activity_score": 85,
      "health_status": "healthy"
    }
  ],
  "summary": {
    "total_projects": 3,
    "avg_activity_score": 75.5,
    "healthiest_project": "gitlab-org/gitlab-runner",
    "total_stars": 5000,
    "total_forks": 2500
  },
  "analysis_date": "2024-01-15"
}
```

## Activity Score Calculation

Calculate activity score (0-100) based on:
- Recent commits (50%): 20+ commits = 50 points, scale down linearly
- Contributors (50%): 50+ contributors = 50 points, scale down

## Health Status

- **healthy**: activity_score >= 70
- **moderate**: 40 <= activity_score < 70
- **inactive**: activity_score < 40

## Tools Available

**Data Collection Tools:**
- `local-gitlab_get_project_info`: Get project details (stars, forks, description)
- `local-gitlab_get_contributors`: Get contributor list
- `local-gitlab_get_issues`: Get issues with labels and states

**File System Tools:**
- `filesystem-write_file`: Write output JSON to file (**USE THIS, NOT "write_file"**)
- `filesystem-read_file`: Read files from workspace

**Task Completion:**
- `local-claim_done`: Signal task completion (REQUIRED at the end)

## Workflow

For each project, you need to call 3 different API endpoints:
1. `local-gitlab_get_project_info` - Basic project details
2. `local-gitlab_get_contributors` - Top contributors
3. `local-gitlab_get_issues` - Issue tracking data

Process all 3 projects systematically and aggregate the results.

## Important Notes

1. Process ALL 3 projects completely - do NOT use placeholder data
2. Use skill mode to optimize repeated API calls
3. Handle API errors gracefully (mark as "unavailable" if project not found)
4. Calculate accurate statistics for the summary

## REQUIRED: Task Completion Protocol

**You MUST follow this exact sequence to complete the task:**

1. **FIRST**: Collect all data for all 3 projects
2. **SECOND**: Write the complete results to `gitlab_analysis_results.json` using `filesystem-write_file`
3. **THIRD**: Call `local-claim_done` to signal task completion

**CRITICAL WARNINGS:**
- **DO NOT stop after saving the file** - you MUST call `local-claim_done`!
- **The task is NOT complete until `claim_done` is called** - saving the file alone is insufficient
- **If you don't call `claim_done`, the task will be marked as FAILED** even if the results are correct
- Call `claim_done` with `{"status": "done"}` as the argument
