# Initial Workspace

This task does not require any input files.

All project information will be fetched directly from the GitLab API using the following tools:
- `local-gitlab_get_project_info`
- `local-gitlab_get_contributors`
- `local-gitlab_get_commits`
- `local-gitlab_get_branches`
- `local-gitlab_get_issues`

The agent should analyze these 5 projects:
1. `gitlab-org/gitlab-runner`
2. `gitlab-org/gitaly`
3. `gitlab-org/gitlab-pages`
4. `gitlab-org/gitlab-shell`
5. `gitlab-org/cli`

