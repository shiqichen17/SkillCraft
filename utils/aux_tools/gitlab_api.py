"""
GitLab API Tools for WebArena Reuse Tasks

These tools provide access to public GitLab API for querying repository information.
Designed for skill mode scenarios where multiple similar queries are executed.
"""

import json
from typing import Any
from agents.tool import FunctionTool, RunContextWrapper
import requests
import urllib.parse

# Base URL for public GitLab
GITLAB_BASE_URL = "https://gitlab.com/api/v4"


# ============== Helper Functions ==============

def _parse_params_robust(params_str: str) -> dict:
    """
    Robustly parse parameters string that may have various format issues.
    
    Handles:
    - Normal JSON: {"key": "value"}
    - Double-encoded JSON: "{\"key\": \"value\"}"
    - Truncated JSON: {"key": "value (missing closing brace)
    """
    if not params_str:
        return {}
    
    # If params_str is already a dict (shouldn't happen, but just in case)
    if isinstance(params_str, dict):
        return params_str
    
    original_str = params_str
    
    # Step 1: Handle double-encoded JSON (starts and ends with quotes)
    if params_str.startswith('"') and params_str.endswith('"'):
        try:
            # Remove outer quotes and unescape
            params_str = json.loads(params_str)
        except json.JSONDecodeError:
            # If it fails, the string might be truncated
            pass
    
    # If after step 1, params_str is still a string starting with quote but not ending with it
    # it's likely truncated double-encoded JSON
    if isinstance(params_str, str) and params_str.startswith('"'):
        # Try to fix truncated double-encoded JSON
        # Remove leading quote and try to parse as JSON
        try:
            inner = params_str[1:]  # Remove leading quote
            # Try to fix common truncation issues
            if not inner.endswith('}'):
                # Find the last complete key-value pair
                inner = inner.rstrip('"')  # Remove trailing quote if any
                # Try to close the JSON properly
                if '"' in inner:
                    inner = inner + '"}'
                else:
                    inner = inner + '}'
            params_str = inner.replace('\\"', '"')
        except:
            pass
    
    # Step 2: Try to parse as JSON
    if isinstance(params_str, str):
        try:
            return json.loads(params_str)
        except json.JSONDecodeError:
            # Step 3: Try to fix truncated JSON
            fixed = params_str.rstrip()
            
            # Count braces to determine if truncated
            open_braces = fixed.count('{')
            close_braces = fixed.count('}')
            
            # Add missing closing braces
            while close_braces < open_braces:
                # Check if we need to close a string first
                # Count quotes (excluding escaped ones)
                quote_count = fixed.count('"') - fixed.count('\\"')
                if quote_count % 2 == 1:
                    fixed += '"'
                fixed += '}'
                close_braces += 1
            
            try:
                return json.loads(fixed)
            except json.JSONDecodeError:
                # Last resort: try to extract key-value pairs manually
                import re
                result = {}
                # Look for "key": "value" or "key": number patterns
                pattern = r'"([^"]+)"\s*:\s*(?:"([^"]*)"?|(\d+))'
                matches = re.findall(pattern, original_str)
                for key, str_val, num_val in matches:
                    if str_val:
                        result[key] = str_val
                    elif num_val:
                        result[key] = int(num_val)
                
                if result:
                    return result
                
                # If all else fails, return empty dict
                return {}
    
    return params_str if isinstance(params_str, dict) else {}


# ============== Core Functions ==============

def _gitlab_get_contributors(project_path: str, order_by: str = "commits") -> dict:
    """Get contributors list for a GitLab repository with detailed analysis."""
    try:
        project_encoded = urllib.parse.quote(project_path, safe='')
        url = f"{GITLAB_BASE_URL}/projects/{project_encoded}/repository/contributors"
        
        response = requests.get(url, timeout=30)
        
        if response.status_code == 200:
            contributors = response.json()
            if order_by == "commits":
                contributors = sorted(contributors, key=lambda x: -x.get('commits', 0))
            
            # Calculate statistics
            total_commits = sum(c.get('commits', 0) for c in contributors)
            total_additions = sum(c.get('additions', 0) for c in contributors)
            total_deletions = sum(c.get('deletions', 0) for c in contributors)
            
            # Top contributors analysis
            top_5 = contributors[:5] if len(contributors) >= 5 else contributors
            top_5_commits = sum(c.get('commits', 0) for c in top_5)
            top_contributor = contributors[0] if contributors else None
            
            # Contribution distribution analysis
            commit_counts = [c.get('commits', 0) for c in contributors]
            avg_commits = total_commits / len(contributors) if contributors else 0
            max_commits = max(commit_counts) if commit_counts else 0
            min_commits = min(commit_counts) if commit_counts else 0
            
            # Domain analysis (from emails)
            email_domains = {}
            for c in contributors:
                email = c.get('email', '')
                if '@' in email:
                    domain = email.split('@')[1]
                    email_domains[domain] = email_domains.get(domain, 0) + 1
            top_domains = sorted(email_domains.items(), key=lambda x: -x[1])[:10]
            
            # ============== TOP-LEVEL: Core fields for Pattern extraction ==============
            return {
                "success": True,
                "project_path": project_path,
                "total_count": len(contributors),
                "total_commits": total_commits,
                "top_contributor": {
                    "name": top_contributor.get('name') if top_contributor else None,
                    "commits": top_contributor.get('commits', 0) if top_contributor else 0,
                    "percentage": round(top_contributor.get('commits', 0) / total_commits * 100, 2) if top_contributor and total_commits > 0 else 0
                },
                "top_5_contributors": [{
                    "name": c.get('name'),
                    "email": c.get('email'),
                    "commits": c.get('commits', 0),
                    "additions": c.get('additions', 0),
                    "deletions": c.get('deletions', 0)
                } for c in top_5],
                "contribution_concentration": round(top_5_commits / total_commits * 100, 2) if total_commits > 0 else 0,
                
                # ============== DETAILED_ANALYSIS: Verbose data for Normal mode tokens ==============
                "detailed_analysis": {
                    "all_contributors": [{
                        "name": c.get('name'),
                        "email": c.get('email'),
                        "commits": c.get('commits', 0),
                        "additions": c.get('additions', 0),
                        "deletions": c.get('deletions', 0),
                        "commit_percentage": round(c.get('commits', 0) / total_commits * 100, 2) if total_commits > 0 else 0
                    } for c in contributors],
                    "statistics": {
                        "total_contributors": len(contributors),
                        "total_commits": total_commits,
                        "total_additions": total_additions,
                        "total_deletions": total_deletions,
                        "total_lines_changed": total_additions + total_deletions,
                        "avg_commits_per_contributor": round(avg_commits, 2),
                        "max_commits": max_commits,
                        "min_commits": min_commits,
                        "commit_range": max_commits - min_commits,
                        "median_commits": sorted(commit_counts)[len(commit_counts)//2] if commit_counts else 0
                    },
                    "distribution_analysis": {
                        "top_5_commit_share": round(top_5_commits / total_commits * 100, 2) if total_commits > 0 else 0,
                        "top_10_commit_share": round(sum(c.get('commits', 0) for c in contributors[:10]) / total_commits * 100, 2) if total_commits > 0 and len(contributors) >= 10 else 100,
                        "single_commit_contributors": sum(1 for c in contributors if c.get('commits', 0) == 1),
                        "prolific_contributors": sum(1 for c in contributors if c.get('commits', 0) >= 10),
                        "very_active_contributors": sum(1 for c in contributors if c.get('commits', 0) >= 50)
                    },
                    "email_domain_analysis": {
                        "unique_domains": len(email_domains),
                        "top_domains": [{"domain": d, "count": c, "percentage": round(c/len(contributors)*100, 2)} for d, c in top_domains],
                        "corporate_vs_personal": {
                            "gmail_users": email_domains.get('gmail.com', 0),
                            "outlook_users": email_domains.get('outlook.com', 0) + email_domains.get('hotmail.com', 0),
                            "corporate_users": len(contributors) - email_domains.get('gmail.com', 0) - email_domains.get('outlook.com', 0) - email_domains.get('hotmail.com', 0)
                        }
                    },
                    "code_churn_analysis": {
                        "avg_additions_per_contributor": round(total_additions / len(contributors), 2) if contributors else 0,
                        "avg_deletions_per_contributor": round(total_deletions / len(contributors), 2) if contributors else 0,
                        "addition_deletion_ratio": round(total_additions / total_deletions, 2) if total_deletions > 0 else float('inf'),
                        "contributors_with_more_additions": sum(1 for c in contributors if c.get('additions', 0) > c.get('deletions', 0)),
                        "contributors_with_more_deletions": sum(1 for c in contributors if c.get('deletions', 0) > c.get('additions', 0))
                    }
                }
            }
        elif response.status_code == 404:
            return {"success": False, "error": f"Repository '{project_path}' not found"}
        else:
            return {"success": False, "error": f"API error: {response.status_code}"}
    except requests.exceptions.Timeout:
        return {"success": False, "error": "Request timeout"}
    except Exception as e:
        return {"success": False, "error": str(e)}


def _gitlab_get_commits(project_path: str, since: str = None, until: str = None, 
                        author: str = None, per_page: int = 100) -> dict:
    """Get commits list for a GitLab repository with detailed analysis."""
    try:
        project_encoded = urllib.parse.quote(project_path, safe='')
        url = f"{GITLAB_BASE_URL}/projects/{project_encoded}/repository/commits"
        
        params = {"per_page": min(per_page, 100)}
        if since:
            params["since"] = since
        if until:
            params["until"] = until
        if author:
            params["author"] = author
            
        response = requests.get(url, params=params, timeout=30)
        
        if response.status_code == 200:
            commits = response.json()
            
            # Author analysis
            author_commits = {}
            author_emails = {}
            for c in commits:
                author_name = c.get('author_name', 'Unknown')
                author_commits[author_name] = author_commits.get(author_name, 0) + 1
                author_emails[author_name] = c.get('author_email', '')
            
            top_authors = sorted(author_commits.items(), key=lambda x: -x[1])[:10]
            most_active = top_authors[0] if top_authors else (None, 0)
            
            # Message analysis
            message_lengths = [len(c.get('message', '')) for c in commits]
            avg_message_length = sum(message_lengths) / len(message_lengths) if message_lengths else 0
            
            # Commit type analysis (based on message patterns)
            commit_types = {
                "feature": 0, "fix": 0, "refactor": 0, "docs": 0,
                "test": 0, "chore": 0, "style": 0, "merge": 0, "other": 0
            }
            for c in commits:
                msg = c.get('message', '').lower()
                title = c.get('title', '').lower()
                combined = msg + title
                if 'merge' in combined or 'merge request' in combined:
                    commit_types["merge"] += 1
                elif 'fix' in combined or 'bug' in combined or 'patch' in combined:
                    commit_types["fix"] += 1
                elif 'feat' in combined or 'add' in combined or 'new' in combined:
                    commit_types["feature"] += 1
                elif 'refactor' in combined or 'clean' in combined or 'improve' in combined:
                    commit_types["refactor"] += 1
                elif 'doc' in combined or 'readme' in combined:
                    commit_types["docs"] += 1
                elif 'test' in combined or 'spec' in combined:
                    commit_types["test"] += 1
                elif 'chore' in combined or 'build' in combined or 'ci' in combined:
                    commit_types["chore"] += 1
                elif 'style' in combined or 'format' in combined or 'lint' in combined:
                    commit_types["style"] += 1
                else:
                    commit_types["other"] += 1
            
            # Time analysis
            from datetime import datetime
            dates = []
            for c in commits:
                try:
                    date_str = c.get('created_at', '')[:10]
                    dates.append(date_str)
                except:
                    pass
            unique_dates = len(set(dates))
            
            # ============== TOP-LEVEL: Core fields for Pattern extraction ==============
            return {
                "success": True,
                "project_path": project_path,
                "count": len(commits),
                "most_active_author": most_active[0],
                "most_active_author_commits": most_active[1],
                "unique_authors": len(author_commits),
                "commits": [{
                    "id": c.get('id', '')[:12],
                    "short_id": c.get('short_id'),
                    "title": c.get('title'),
                    "author_name": c.get('author_name'),
                    "created_at": c.get('created_at')
                } for c in commits],
                
                # ============== DETAILED_ANALYSIS: Verbose data for Normal mode tokens ==============
                "detailed_analysis": {
                    "full_commits": [{
                        "id": c.get('id'),
                        "short_id": c.get('short_id'),
                        "title": c.get('title'),
                        "message": c.get('message'),
                        "author_name": c.get('author_name'),
                        "author_email": c.get('author_email'),
                        "committer_name": c.get('committer_name'),
                        "committer_email": c.get('committer_email'),
                        "created_at": c.get('created_at'),
                        "committed_date": c.get('committed_date'),
                        "parent_ids": c.get('parent_ids', []),
                        "web_url": c.get('web_url'),
                        "is_merge_commit": len(c.get('parent_ids', [])) > 1,
                        "message_length": len(c.get('message', ''))
                    } for c in commits],
                    "author_statistics": {
                        "total_unique_authors": len(author_commits),
                        "author_breakdown": [{
                            "name": name,
                            "email": author_emails.get(name, ''),
                            "commits": count,
                            "percentage": round(count / len(commits) * 100, 2) if commits else 0
                        } for name, count in top_authors],
                        "single_commit_authors": sum(1 for c in author_commits.values() if c == 1),
                        "prolific_authors": sum(1 for c in author_commits.values() if c >= 5)
                    },
                    "commit_type_analysis": {
                        "breakdown": commit_types,
                        "total_analyzed": len(commits),
                        "feature_percentage": round(commit_types["feature"] / len(commits) * 100, 2) if commits else 0,
                        "fix_percentage": round(commit_types["fix"] / len(commits) * 100, 2) if commits else 0,
                        "merge_percentage": round(commit_types["merge"] / len(commits) * 100, 2) if commits else 0,
                        "maintenance_ratio": round((commit_types["refactor"] + commit_types["chore"] + commit_types["style"]) / len(commits) * 100, 2) if commits else 0
                    },
                    "message_analysis": {
                        "avg_message_length": round(avg_message_length, 2),
                        "max_message_length": max(message_lengths) if message_lengths else 0,
                        "min_message_length": min(message_lengths) if message_lengths else 0,
                        "short_messages": sum(1 for l in message_lengths if l < 50),
                        "detailed_messages": sum(1 for l in message_lengths if l > 200)
                    },
                    "temporal_analysis": {
                        "unique_days": unique_dates,
                        "commits_per_day": round(len(commits) / unique_dates, 2) if unique_dates > 0 else 0,
                        "date_range": {
                            "earliest": min(dates) if dates else None,
                            "latest": max(dates) if dates else None
                        },
                        "merge_commits": sum(1 for c in commits if len(c.get('parent_ids', [])) > 1),
                        "regular_commits": sum(1 for c in commits if len(c.get('parent_ids', [])) <= 1)
                    }
                }
            }
        elif response.status_code == 404:
            return {"success": False, "error": f"Repository '{project_path}' not found"}
        else:
            return {"success": False, "error": f"API error: {response.status_code}"}
    except requests.exceptions.Timeout:
        return {"success": False, "error": "Request timeout"}
    except Exception as e:
        return {"success": False, "error": str(e)}


def _gitlab_search_projects(query: str, order_by: str = "updated_at", per_page: int = 20) -> dict:
    """Search for GitLab projects by name or description."""
    try:
        url = f"{GITLAB_BASE_URL}/projects"
        params = {
            "search": query,
            "order_by": order_by if order_by in ["id", "name", "path", "created_at", "updated_at", "last_activity_at"] else "updated_at",
            "per_page": min(per_page, 100),
            "visibility": "public"
        }
        
        response = requests.get(url, params=params, timeout=30)
        
        if response.status_code == 200:
            projects = response.json()
            simplified = [{
                "name": p.get("name"),
                "path_with_namespace": p.get("path_with_namespace"),
                "description": (p.get("description") or "")[:200],
                "stars": p.get("star_count", 0),
                "forks": p.get("forks_count", 0),
                "web_url": p.get("web_url")
            } for p in projects]
            return {
                "success": True,
                "projects": simplified,
                "count": len(simplified)
            }
        else:
            return {"success": False, "error": f"API error: {response.status_code}"}
    except Exception as e:
        return {"success": False, "error": str(e)}


def _gitlab_get_project_info(project_path: str) -> dict:
    """Get detailed information about a GitLab project with comprehensive analysis."""
    try:
        project_encoded = urllib.parse.quote(project_path, safe='')
        url = f"{GITLAB_BASE_URL}/projects/{project_encoded}"
        
        response = requests.get(url, timeout=30)
        
        if response.status_code == 200:
            p = response.json()
            
            # Calculate project age and activity metrics
            from datetime import datetime
            created_at = p.get("created_at", "")
            last_activity = p.get("last_activity_at", "")
            
            try:
                created_date = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
                last_date = datetime.fromisoformat(last_activity.replace('Z', '+00:00'))
                now = datetime.now(created_date.tzinfo) if created_date.tzinfo else datetime.now()
                
                age_days = (now - created_date).days
                days_since_activity = (now - last_date).days
                activity_ratio = round(1 - (days_since_activity / age_days), 4) if age_days > 0 else 0
            except:
                age_days = 0
                days_since_activity = 0
                activity_ratio = 0
            
            # Popularity score calculation
            stars = p.get("star_count", 0)
            forks = p.get("forks_count", 0)
            popularity_score = stars + (forks * 2)  # Forks weighted more
            
            # Activity level classification
            if days_since_activity <= 7:
                activity_level = "very_active"
            elif days_since_activity <= 30:
                activity_level = "active"
            elif days_since_activity <= 90:
                activity_level = "moderate"
            elif days_since_activity <= 365:
                activity_level = "low"
            else:
                activity_level = "inactive"
            
            # Project size classification
            if stars >= 10000:
                size_class = "large_popular"
            elif stars >= 1000:
                size_class = "medium_popular"
            elif stars >= 100:
                size_class = "small_popular"
            else:
                size_class = "emerging"
            
            # ============== TOP-LEVEL: Core fields for Pattern extraction ==============
            return {
                "success": True,
                "project": {
                    "name": p.get("name"),
                    "path_with_namespace": p.get("path_with_namespace"),
                    "description": p.get("description"),
                    "default_branch": p.get("default_branch"),
                    "visibility": p.get("visibility"),
                    "stars": stars,
                    "forks": forks,
                    "open_issues_count": p.get("open_issues_count", 0),
                    "created_at": created_at,
                    "last_activity_at": last_activity,
                    "web_url": p.get("web_url"),
                    "topics": p.get("topics", [])
                },
                "activity_level": activity_level,
                "popularity_score": popularity_score,
                "size_class": size_class,
                
                # ============== DETAILED_ANALYSIS: Verbose data for Normal mode tokens ==============
                "detailed_analysis": {
                    "full_project_data": {
                        "id": p.get("id"),
                        "name": p.get("name"),
                        "name_with_namespace": p.get("name_with_namespace"),
                        "path": p.get("path"),
                        "path_with_namespace": p.get("path_with_namespace"),
                        "description": p.get("description"),
                        "default_branch": p.get("default_branch"),
                        "visibility": p.get("visibility"),
                        "ssh_url_to_repo": p.get("ssh_url_to_repo"),
                        "http_url_to_repo": p.get("http_url_to_repo"),
                        "web_url": p.get("web_url"),
                        "readme_url": p.get("readme_url"),
                        "avatar_url": p.get("avatar_url"),
                        "forks_count": forks,
                        "star_count": stars,
                        "open_issues_count": p.get("open_issues_count", 0),
                        "topics": p.get("topics", []),
                        "created_at": created_at,
                        "last_activity_at": last_activity,
                        "archived": p.get("archived", False),
                        "empty_repo": p.get("empty_repo", False),
                        "issues_enabled": p.get("issues_enabled", True),
                        "merge_requests_enabled": p.get("merge_requests_enabled", True),
                        "wiki_enabled": p.get("wiki_enabled", True),
                        "jobs_enabled": p.get("jobs_enabled", True),
                        "snippets_enabled": p.get("snippets_enabled", True),
                        "container_registry_enabled": p.get("container_registry_enabled", False),
                        "creator_id": p.get("creator_id"),
                        "namespace": p.get("namespace", {}),
                        "import_status": p.get("import_status"),
                        "ci_config_path": p.get("ci_config_path"),
                        "shared_runners_enabled": p.get("shared_runners_enabled", True),
                        "lfs_enabled": p.get("lfs_enabled", False),
                        "request_access_enabled": p.get("request_access_enabled", True),
                        "only_allow_merge_if_pipeline_succeeds": p.get("only_allow_merge_if_pipeline_succeeds", False),
                        "only_allow_merge_if_all_discussions_are_resolved": p.get("only_allow_merge_if_all_discussions_are_resolved", False),
                        "remove_source_branch_after_merge": p.get("remove_source_branch_after_merge", False),
                        "printing_merge_request_link_enabled": p.get("printing_merge_request_link_enabled", True),
                        "auto_devops_enabled": p.get("auto_devops_enabled", False),
                        "auto_devops_deploy_strategy": p.get("auto_devops_deploy_strategy"),
                        "permissions": p.get("permissions", {}),
                        "allow_merge_on_skipped_pipeline": p.get("allow_merge_on_skipped_pipeline", False),
                        "squash_option": p.get("squash_option"),
                        "suggestion_commit_message": p.get("suggestion_commit_message"),
                        "merge_commit_template": p.get("merge_commit_template"),
                        "squash_commit_template": p.get("squash_commit_template")
                    },
                    "temporal_metrics": {
                        "age_days": age_days,
                        "age_months": round(age_days / 30, 1),
                        "age_years": round(age_days / 365, 2),
                        "days_since_last_activity": days_since_activity,
                        "activity_ratio": activity_ratio,
                        "activity_level": activity_level,
                        "created_date": created_at[:10] if created_at else None,
                        "last_activity_date": last_activity[:10] if last_activity else None
                    },
                    "popularity_metrics": {
                        "stars": stars,
                        "forks": forks,
                        "star_to_fork_ratio": round(stars / forks, 2) if forks > 0 else float('inf'),
                        "popularity_score": popularity_score,
                        "size_class": size_class,
                        "stars_per_year": round(stars / (age_days / 365), 2) if age_days > 365 else stars,
                        "forks_per_year": round(forks / (age_days / 365), 2) if age_days > 365 else forks
                    },
                    "feature_flags": {
                        "issues_enabled": p.get("issues_enabled", True),
                        "merge_requests_enabled": p.get("merge_requests_enabled", True),
                        "wiki_enabled": p.get("wiki_enabled", True),
                        "jobs_enabled": p.get("jobs_enabled", True),
                        "snippets_enabled": p.get("snippets_enabled", True),
                        "container_registry_enabled": p.get("container_registry_enabled", False),
                        "lfs_enabled": p.get("lfs_enabled", False),
                        "auto_devops_enabled": p.get("auto_devops_enabled", False),
                        "shared_runners_enabled": p.get("shared_runners_enabled", True)
                    },
                    "merge_settings": {
                        "only_allow_merge_if_pipeline_succeeds": p.get("only_allow_merge_if_pipeline_succeeds", False),
                        "only_allow_merge_if_all_discussions_are_resolved": p.get("only_allow_merge_if_all_discussions_are_resolved", False),
                        "remove_source_branch_after_merge": p.get("remove_source_branch_after_merge", False),
                        "squash_option": p.get("squash_option"),
                        "allow_merge_on_skipped_pipeline": p.get("allow_merge_on_skipped_pipeline", False)
                    },
                    "topics_analysis": {
                        "topics": p.get("topics", []),
                        "topic_count": len(p.get("topics", [])),
                        "has_topics": len(p.get("topics", [])) > 0,
                        "primary_topic": p.get("topics", [None])[0] if p.get("topics") else None
                    }
                }
            }
        elif response.status_code == 404:
            return {"success": False, "error": f"Repository '{project_path}' not found"}
        else:
            return {"success": False, "error": f"API error: {response.status_code}"}
    except Exception as e:
        return {"success": False, "error": str(e)}


def _gitlab_get_issues(project_path: str, labels: str = None, state: str = "opened", per_page: int = 20) -> dict:
    """Get issues list for a GitLab repository with detailed analysis."""
    try:
        project_encoded = urllib.parse.quote(project_path, safe='')
        url = f"{GITLAB_BASE_URL}/projects/{project_encoded}/issues"
        
        params = {"per_page": min(per_page, 100), "state": state}
        if labels:
            params["labels"] = labels
            
        response = requests.get(url, params=params, timeout=30)
        
        if response.status_code == 200:
            issues = response.json()
            
            # Label analysis
            all_labels = []
            for i in issues:
                all_labels.extend(i.get("labels", []))
            label_counts = {}
            for label in all_labels:
                label_counts[label] = label_counts.get(label, 0) + 1
            top_labels = sorted(label_counts.items(), key=lambda x: -x[1])[:15]
            
            # Author analysis
            author_issues = {}
            for i in issues:
                author = i.get("author", {}).get("username") if i.get("author") else "unknown"
                author_issues[author] = author_issues.get(author, 0) + 1
            top_authors = sorted(author_issues.items(), key=lambda x: -x[1])[:10]
            
            # State analysis
            open_count = sum(1 for i in issues if i.get("state") == "opened")
            closed_count = sum(1 for i in issues if i.get("state") == "closed")
            
            # Assignee analysis
            assigned_count = sum(1 for i in issues if i.get("assignees"))
            unassigned_count = len(issues) - assigned_count
            
            # Time analysis
            from datetime import datetime
            issue_ages = []
            for i in issues:
                try:
                    created = datetime.fromisoformat(i.get("created_at", "").replace('Z', '+00:00'))
                    now = datetime.now(created.tzinfo) if created.tzinfo else datetime.now()
                    age_days = (now - created).days
                    issue_ages.append(age_days)
                except:
                    pass
            
            avg_age = sum(issue_ages) / len(issue_ages) if issue_ages else 0
            
            # Priority/severity analysis (from labels)
            priority_issues = {
                "critical": sum(1 for i in issues if any('critical' in l.lower() or 'p0' in l.lower() or 'severity::1' in l.lower() for l in i.get("labels", []))),
                "high": sum(1 for i in issues if any('high' in l.lower() or 'p1' in l.lower() or 'severity::2' in l.lower() for l in i.get("labels", []))),
                "medium": sum(1 for i in issues if any('medium' in l.lower() or 'p2' in l.lower() or 'severity::3' in l.lower() for l in i.get("labels", []))),
                "low": sum(1 for i in issues if any('low' in l.lower() or 'p3' in l.lower() or 'severity::4' in l.lower() for l in i.get("labels", [])))
            }
            
            # Type analysis (from labels)
            type_issues = {
                "bug": sum(1 for i in issues if any('bug' in l.lower() for l in i.get("labels", []))),
                "feature": sum(1 for i in issues if any('feature' in l.lower() or 'enhancement' in l.lower() for l in i.get("labels", []))),
                "documentation": sum(1 for i in issues if any('doc' in l.lower() for l in i.get("labels", []))),
                "question": sum(1 for i in issues if any('question' in l.lower() or 'help' in l.lower() for l in i.get("labels", [])))
            }
            
            # ============== TOP-LEVEL: Core fields for Pattern extraction ==============
            return {
                "success": True,
                "project_path": project_path,
                "count": len(issues),
                "open_count": open_count,
                "closed_count": closed_count,
                "top_labels": [l for l, c in top_labels[:5]],
                "issues": [{
                    "iid": i.get("iid"),
                    "title": i.get("title"),
                    "state": i.get("state"),
                    "labels": i.get("labels", []),
                    "author": i.get("author", {}).get("username") if i.get("author") else None,
                    "created_at": i.get("created_at"),
                    "web_url": i.get("web_url")
                } for i in issues],
                
                # ============== DETAILED_ANALYSIS: Verbose data for Normal mode tokens ==============
                "detailed_analysis": {
                    "full_issues": [{
                        "iid": i.get("iid"),
                        "project_id": i.get("project_id"),
                        "title": i.get("title"),
                        "description": (i.get("description") or "")[:500],
                        "state": i.get("state"),
                        "labels": i.get("labels", []),
                        "milestone": i.get("milestone", {}).get("title") if i.get("milestone") else None,
                        "author": {
                            "username": i.get("author", {}).get("username"),
                            "name": i.get("author", {}).get("name"),
                            "avatar_url": i.get("author", {}).get("avatar_url")
                        } if i.get("author") else None,
                        "assignees": [{
                            "username": a.get("username"),
                            "name": a.get("name")
                        } for a in i.get("assignees", [])],
                        "assignee_count": len(i.get("assignees", [])),
                        "created_at": i.get("created_at"),
                        "updated_at": i.get("updated_at"),
                        "closed_at": i.get("closed_at"),
                        "closed_by": i.get("closed_by", {}).get("username") if i.get("closed_by") else None,
                        "upvotes": i.get("upvotes", 0),
                        "downvotes": i.get("downvotes", 0),
                        "merge_requests_count": i.get("merge_requests_count", 0),
                        "user_notes_count": i.get("user_notes_count", 0),
                        "due_date": i.get("due_date"),
                        "confidential": i.get("confidential", False),
                        "discussion_locked": i.get("discussion_locked"),
                        "weight": i.get("weight"),
                        "web_url": i.get("web_url"),
                        "has_description": bool(i.get("description")),
                        "description_length": len(i.get("description") or "")
                    } for i in issues],
                    "label_analysis": {
                        "unique_labels": len(label_counts),
                        "total_label_uses": len(all_labels),
                        "avg_labels_per_issue": round(len(all_labels) / len(issues), 2) if issues else 0,
                        "label_breakdown": [{
                            "label": label,
                            "count": count,
                            "percentage": round(count / len(issues) * 100, 2) if issues else 0
                        } for label, count in top_labels],
                        "issues_without_labels": sum(1 for i in issues if not i.get("labels"))
                    },
                    "author_analysis": {
                        "unique_authors": len(author_issues),
                        "author_breakdown": [{
                            "username": author,
                            "issue_count": count,
                            "percentage": round(count / len(issues) * 100, 2) if issues else 0
                        } for author, count in top_authors],
                        "top_reporter": top_authors[0][0] if top_authors else None,
                        "top_reporter_count": top_authors[0][1] if top_authors else 0
                    },
                    "state_analysis": {
                        "total": len(issues),
                        "opened": open_count,
                        "closed": closed_count,
                        "open_percentage": round(open_count / len(issues) * 100, 2) if issues else 0,
                        "close_rate": round(closed_count / len(issues) * 100, 2) if issues else 0
                    },
                    "assignment_analysis": {
                        "assigned": assigned_count,
                        "unassigned": unassigned_count,
                        "assignment_rate": round(assigned_count / len(issues) * 100, 2) if issues else 0
                    },
                    "priority_analysis": priority_issues,
                    "type_analysis": type_issues,
                    "temporal_analysis": {
                        "avg_age_days": round(avg_age, 2),
                        "oldest_issue_age": max(issue_ages) if issue_ages else 0,
                        "newest_issue_age": min(issue_ages) if issue_ages else 0,
                        "issues_older_than_30_days": sum(1 for a in issue_ages if a > 30),
                        "issues_older_than_90_days": sum(1 for a in issue_ages if a > 90),
                        "issues_older_than_year": sum(1 for a in issue_ages if a > 365)
                    },
                    "engagement_metrics": {
                        "total_upvotes": sum(i.get("upvotes", 0) for i in issues),
                        "total_downvotes": sum(i.get("downvotes", 0) for i in issues),
                        "total_comments": sum(i.get("user_notes_count", 0) for i in issues),
                        "avg_comments_per_issue": round(sum(i.get("user_notes_count", 0) for i in issues) / len(issues), 2) if issues else 0,
                        "issues_with_comments": sum(1 for i in issues if i.get("user_notes_count", 0) > 0),
                        "issues_with_linked_mr": sum(1 for i in issues if i.get("merge_requests_count", 0) > 0)
                    }
                }
            }
        elif response.status_code == 404:
            return {"success": False, "error": f"Repository '{project_path}' not found or issues disabled"}
        else:
            return {"success": False, "error": f"API error: {response.status_code}"}
    except requests.exceptions.Timeout:
        return {"success": False, "error": "Request timeout"}
    except Exception as e:
        return {"success": False, "error": str(e)}


def _gitlab_get_branches(project_path: str, per_page: int = 100) -> dict:
    """Get branches list for a GitLab repository with detailed analysis."""
    try:
        project_encoded = urllib.parse.quote(project_path, safe='')
        url = f"{GITLAB_BASE_URL}/projects/{project_encoded}/repository/branches"
        
        params = {"per_page": min(per_page, 100)}
        response = requests.get(url, params=params, timeout=30)
        
        if response.status_code == 200:
            branches = response.json()
            
            # Basic counts
            protected_count = sum(1 for b in branches if b.get("protected"))
            merged_count = sum(1 for b in branches if b.get("merged"))
            
            # Find default branch
            default_branch = next((b.get("name") for b in branches if b.get("default")), None)
            
            # Branch naming pattern analysis
            naming_patterns = {
                "feature": 0, "bugfix": 0, "hotfix": 0, "release": 0,
                "develop": 0, "main_master": 0, "stable": 0, "other": 0
            }
            for b in branches:
                name = b.get("name", "").lower()
                if "feature" in name or "feat" in name:
                    naming_patterns["feature"] += 1
                elif "bugfix" in name or "bug" in name or "fix" in name:
                    naming_patterns["bugfix"] += 1
                elif "hotfix" in name or "hot" in name:
                    naming_patterns["hotfix"] += 1
                elif "release" in name or "rel" in name:
                    naming_patterns["release"] += 1
                elif name in ["develop", "dev", "development"]:
                    naming_patterns["develop"] += 1
                elif name in ["main", "master"]:
                    naming_patterns["main_master"] += 1
                elif "stable" in name:
                    naming_patterns["stable"] += 1
                else:
                    naming_patterns["other"] += 1
            
            # Time analysis
            from datetime import datetime
            branch_ages = []
            recent_branches = []
            stale_branches = []
            
            for b in branches:
                try:
                    commit = b.get("commit", {})
                    date_str = commit.get("committed_date", "")
                    if date_str:
                        commit_date = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
                        now = datetime.now(commit_date.tzinfo) if commit_date.tzinfo else datetime.now()
                        age_days = (now - commit_date).days
                        branch_ages.append(age_days)
                        
                        if age_days <= 30:
                            recent_branches.append(b.get("name"))
                        elif age_days > 180:
                            stale_branches.append(b.get("name"))
                except:
                    pass
            
            avg_age = sum(branch_ages) / len(branch_ages) if branch_ages else 0
            
            # ============== TOP-LEVEL: Core fields for Pattern extraction ==============
            return {
                "success": True,
                "project_path": project_path,
                "count": len(branches),
                "default_branch": default_branch,
                "protected_count": protected_count,
                "merged_count": merged_count,
                "branches": [{
                    "name": b.get("name"),
                    "default": b.get("default", False),
                    "protected": b.get("protected", False),
                    "merged": b.get("merged", False),
                    "commit_date": b.get("commit", {}).get("committed_date") if b.get("commit") else None
                } for b in branches],
                
                # ============== DETAILED_ANALYSIS: Verbose data for Normal mode tokens ==============
                "detailed_analysis": {
                    "full_branches": [{
                        "name": b.get("name"),
                        "default": b.get("default", False),
                        "protected": b.get("protected", False),
                        "merged": b.get("merged", False),
                        "developers_can_push": b.get("developers_can_push", False),
                        "developers_can_merge": b.get("developers_can_merge", False),
                        "can_push": b.get("can_push", False),
                        "web_url": b.get("web_url"),
                        "commit": {
                            "id": b.get("commit", {}).get("id"),
                            "short_id": b.get("commit", {}).get("short_id"),
                            "title": b.get("commit", {}).get("title"),
                            "message": b.get("commit", {}).get("message"),
                            "author_name": b.get("commit", {}).get("author_name"),
                            "author_email": b.get("commit", {}).get("author_email"),
                            "authored_date": b.get("commit", {}).get("authored_date"),
                            "committer_name": b.get("commit", {}).get("committer_name"),
                            "committer_email": b.get("commit", {}).get("committer_email"),
                            "committed_date": b.get("commit", {}).get("committed_date"),
                            "parent_ids": b.get("commit", {}).get("parent_ids", []),
                            "web_url": b.get("commit", {}).get("web_url")
                        } if b.get("commit") else None
                    } for b in branches],
                    "protection_analysis": {
                        "total_branches": len(branches),
                        "protected_branches": protected_count,
                        "unprotected_branches": len(branches) - protected_count,
                        "protection_rate": round(protected_count / len(branches) * 100, 2) if branches else 0,
                        "protected_branch_names": [b.get("name") for b in branches if b.get("protected")],
                        "unprotected_important": [b.get("name") for b in branches if not b.get("protected") and b.get("name") in ["main", "master", "develop", "release"]]
                    },
                    "merge_status": {
                        "merged_branches": merged_count,
                        "unmerged_branches": len(branches) - merged_count,
                        "merge_rate": round(merged_count / len(branches) * 100, 2) if branches else 0,
                        "merged_branch_names": [b.get("name") for b in branches if b.get("merged")][:20]
                    },
                    "naming_pattern_analysis": {
                        "patterns": naming_patterns,
                        "feature_branches": naming_patterns["feature"],
                        "bugfix_branches": naming_patterns["bugfix"],
                        "release_branches": naming_patterns["release"],
                        "follows_gitflow": naming_patterns["feature"] > 0 or naming_patterns["release"] > 0 or naming_patterns["develop"] > 0
                    },
                    "temporal_analysis": {
                        "avg_branch_age_days": round(avg_age, 2),
                        "oldest_branch_age": max(branch_ages) if branch_ages else 0,
                        "newest_branch_age": min(branch_ages) if branch_ages else 0,
                        "recent_branches_count": len(recent_branches),
                        "recent_branches": recent_branches[:10],
                        "stale_branches_count": len(stale_branches),
                        "stale_branches": stale_branches[:10],
                        "branches_older_than_30_days": sum(1 for a in branch_ages if a > 30),
                        "branches_older_than_90_days": sum(1 for a in branch_ages if a > 90),
                        "branches_older_than_year": sum(1 for a in branch_ages if a > 365)
                    },
                    "health_indicators": {
                        "has_default_branch": default_branch is not None,
                        "default_is_protected": any(b.get("protected") and b.get("default") for b in branches),
                        "stale_branch_ratio": round(len(stale_branches) / len(branches) * 100, 2) if branches else 0,
                        "active_branch_ratio": round(len(recent_branches) / len(branches) * 100, 2) if branches else 0,
                        "cleanup_recommended": len(stale_branches) > len(branches) * 0.3,
                        "branches_needing_cleanup": stale_branches[:20] if len(stale_branches) > len(branches) * 0.3 else []
                    }
                }
            }
        elif response.status_code == 404:
            return {"success": False, "error": f"Repository '{project_path}' not found"}
        else:
            return {"success": False, "error": f"API error: {response.status_code}"}
    except requests.exceptions.Timeout:
        return {"success": False, "error": "Request timeout"}
    except Exception as e:
        return {"success": False, "error": str(e)}


# ============== Tool Handlers ==============

async def on_gitlab_get_contributors(context: RunContextWrapper, params_str: str) -> Any:
    params = _parse_params_robust(params_str)
    project_path = params.get("project_path", "")
    order_by = params.get("order_by", "commits")
    result = _gitlab_get_contributors(project_path, order_by)
    return result


async def on_gitlab_get_commits(context: RunContextWrapper, params_str: str) -> Any:
    params = _parse_params_robust(params_str)
    project_path = params.get("project_path", "")
    since = params.get("since")
    until = params.get("until")
    author = params.get("author")
    per_page = params.get("per_page", 100)
    result = _gitlab_get_commits(project_path, since, until, author, per_page)
    return result


async def on_gitlab_search_projects(context: RunContextWrapper, params_str: str) -> Any:
    params = _parse_params_robust(params_str)
    query = params.get("query", "")
    order_by = params.get("order_by", "updated_at")
    per_page = params.get("per_page", 20)
    result = _gitlab_search_projects(query, order_by, per_page)
    return result


async def on_gitlab_get_project_info(context: RunContextWrapper, params_str: str) -> Any:
    params = _parse_params_robust(params_str)
    project_path = params.get("project_path", "")
    result = _gitlab_get_project_info(project_path)
    return result


async def on_gitlab_get_issues(context: RunContextWrapper, params_str: str) -> Any:
    params = _parse_params_robust(params_str)
    project_path = params.get("project_path", "")
    labels = params.get("labels")
    state = params.get("state", "opened")
    per_page = params.get("per_page", 20)
    result = _gitlab_get_issues(project_path, labels, state, per_page)
    return result


async def on_gitlab_get_branches(context: RunContextWrapper, params_str: str) -> Any:
    params = _parse_params_robust(params_str)
    project_path = params.get("project_path", "")
    per_page = params.get("per_page", 100)
    result = _gitlab_get_branches(project_path, per_page)
    return result


# ============== Tool Definitions ==============

tool_gitlab_get_contributors = FunctionTool(
    name='local-gitlab_get_contributors',
    description='''Get the list of contributors for a GitLab repository, sorted by commit count.

**Input:** project_path (str), order_by (str, optional)

**Returns:** dict:
{
  "success": bool,
  "project_path": str,
  "total_count": int,
  "total_commits": int,
  "top_contributor": {"name": str, "commits": int, "percentage": float},
  "top_5_contributors": [{"name": str, "email": str, "commits": int, "additions": int, "deletions": int}],
  "contribution_concentration": float,
  "detailed_analysis": {...}
}''',
    params_json_schema={
        "type": "object",
        "properties": {
            "project_path": {
                "type": "string",
                "description": "Repository path in format 'owner/repo-name', e.g., 'gitlab-org/gitlab'"
            },
            "order_by": {
                "type": "string",
                "enum": ["commits", "name"],
                "description": "Sort order: 'commits' (most commits first) or 'name' (alphabetical)"
            }
        },
        "required": ["project_path"]
    },
    on_invoke_tool=on_gitlab_get_contributors
)

tool_gitlab_get_commits = FunctionTool(
    name='local-gitlab_get_commits',
    description='''Get commit history for a GitLab repository. Can filter by date range and author.

**Input:** project_path (str), since (str, optional), until (str, optional), author (str, optional)

**Returns:** dict:
{
  "success": bool,
  "project_path": str,
  "count": int,
  "most_active_author": str,
  "most_active_author_commits": int,
  "unique_authors": int,
  "commits": [{"id": str, "short_id": str, "title": str, "author_name": str, "created_at": str}],
  "detailed_analysis": {...}
}''',
    params_json_schema={
        "type": "object",
        "properties": {
            "project_path": {
                "type": "string",
                "description": "Repository path in format 'owner/repo-name'"
            },
            "since": {
                "type": "string",
                "description": "Get commits after this date (ISO 8601 format, e.g., '2024-01-01')"
            },
            "until": {
                "type": "string",
                "description": "Get commits before this date (ISO 8601 format)"
            },
            "author": {
                "type": "string",
                "description": "Filter by author name or email"
            },
            "per_page": {
                "type": "integer",
                "description": "Number of commits to return (max 100)"
            }
        },
        "required": ["project_path"]
    },
    on_invoke_tool=on_gitlab_get_commits
)

tool_gitlab_search_projects = FunctionTool(
    name='local-gitlab_search_projects',
    description='''Search for public GitLab projects by name or keyword.

**Input:** query (str), order_by (str, optional), per_page (int, optional)

**Returns:** dict:
{
  "success": bool,
  "projects": [{"name": str, "path_with_namespace": str, "description": str, "stars": int, "forks": int, "web_url": str}],
  "count": int
}''',
    params_json_schema={
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "Search query (project name or keyword)"
            },
            "order_by": {
                "type": "string",
                "enum": ["updated_at", "created_at", "name"],
                "description": "Sort order"
            },
            "per_page": {
                "type": "integer",
                "description": "Number of results to return"
            }
        },
        "required": ["query"]
    },
    on_invoke_tool=on_gitlab_search_projects
)

tool_gitlab_get_project_info = FunctionTool(
    name='local-gitlab_get_project_info',
    description='''Get detailed information about a GitLab project including stars, forks, issues count, and description.

**Input:** project_path (str)

**Returns:** dict:
{
  "success": bool,
  "project": {"name": str, "path_with_namespace": str, "description": str, "default_branch": str, "visibility": str, "stars": int, "forks": int, "open_issues_count": int, "created_at": str, "last_activity_at": str, "web_url": str, "topics": [str]},
  "activity_level": str,
  "popularity_score": int,
  "size_class": str,
  "detailed_analysis": {...}
}''',
    params_json_schema={
        "type": "object",
        "properties": {
            "project_path": {
                "type": "string",
                "description": "Repository path in format 'owner/repo-name'"
            }
        },
        "required": ["project_path"]
    },
    on_invoke_tool=on_gitlab_get_project_info
)

tool_gitlab_get_issues = FunctionTool(
    name='local-gitlab_get_issues',
    description='''Get the list of issues for a GitLab repository. Can filter by labels and state (opened/closed/all).

**Input:** project_path (str), labels (str, optional), state (str, optional)

**Returns:** dict:
{
  "success": bool,
  "project_path": str,
  "count": int,
  "open_count": int,
  "closed_count": int,
  "top_labels": [str],
  "issues": [{"iid": int, "title": str, "state": str, "labels": [str], "author": str, "created_at": str, "web_url": str}],
  "detailed_analysis": {...}
}''',
    params_json_schema={
        "type": "object",
        "properties": {
            "project_path": {
                "type": "string",
                "description": "Repository path in format 'owner/repo-name'"
            },
            "labels": {
                "type": "string",
                "description": "Comma-separated list of labels to filter by (e.g., 'bug,critical')"
            },
            "state": {
                "type": "string",
                "enum": ["opened", "closed", "all"],
                "description": "Filter issues by state (default: opened)"
            },
            "per_page": {
                "type": "integer",
                "description": "Number of issues to return (max 100)"
            }
        },
        "required": ["project_path"]
    },
    on_invoke_tool=on_gitlab_get_issues
)

tool_gitlab_get_branches = FunctionTool(
    name='local-gitlab_get_branches',
    description='''Get the list of branches for a GitLab repository, including information about default and protected branches.

**Input:** project_path (str), per_page (int, optional)

**Returns:** dict:
{
  "success": bool,
  "project_path": str,
  "count": int,
  "default_branch": str,
  "protected_count": int,
  "merged_count": int,
  "branches": [{"name": str, "default": bool, "protected": bool, "merged": bool, "commit_date": str}],
  "detailed_analysis": {...}
}''',
    params_json_schema={
        "type": "object",
        "properties": {
            "project_path": {
                "type": "string",
                "description": "Repository path in format 'owner/repo-name'"
            },
            "per_page": {
                "type": "integer",
                "description": "Number of branches to return (max 100)"
            }
        },
        "required": ["project_path"]
    },
    on_invoke_tool=on_gitlab_get_branches
)

# Export all tools as a list
gitlab_api_tools = [
    tool_gitlab_get_contributors,
    tool_gitlab_get_commits,
    tool_gitlab_search_projects,
    tool_gitlab_get_project_info,
    tool_gitlab_get_issues,
    tool_gitlab_get_branches,
]
