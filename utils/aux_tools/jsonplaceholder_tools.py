"""
JSONPlaceholder API Tools

Provides tools to interact with JSONPlaceholder fake REST API for testing.
Designed for skill mode scenarios with structured blog/social data.

API Documentation: https://jsonplaceholder.typicode.com/
No authentication required.

HIGH VERBOSE VERSION (v2): Returns detailed data for Skill Mode efficiency.
- Target Base Mode Input Tokens: 800K - 1.5M
- Added: Related users, album photos, extended comment analysis
- Added: Cross-user statistics and comparisons
"""

import json
from typing import Any
from agents.tool import FunctionTool, RunContextWrapper
import requests

# Base URL for JSONPlaceholder API
JSONPLACEHOLDER_BASE_URL = "https://jsonplaceholder.typicode.com"

# Cache for all users to enable cross-referencing
_users_cache = None


def _make_request(endpoint: str, params: dict = None) -> Any:
    """Make a request to JSONPlaceholder API with error handling."""
    url = f"{JSONPLACEHOLDER_BASE_URL}{endpoint}"
    headers = {"User-Agent": "DikaNong-PatternReuse/1.0"}
    
    try:
        response = requests.get(url, headers=headers, params=params, timeout=15)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.Timeout:
        return {"error": "Request timeout", "success": False}
    except requests.exceptions.RequestException as e:
        return {"error": str(e), "success": False}
    except json.JSONDecodeError:
        return {"error": "Invalid JSON response", "success": False}


def _parse_params(params_str: str) -> dict:
    """Parse parameters from string."""
    if not params_str:
        return {}
    if isinstance(params_str, dict):
        return params_str
    try:
        return json.loads(params_str)
    except json.JSONDecodeError:
        return {}


def _get_all_users() -> list:
    """Get all users with caching for cross-referencing."""
    global _users_cache
    if _users_cache is None:
        _users_cache = _make_request("/users")
        if isinstance(_users_cache, dict) and "error" in _users_cache:
            _users_cache = []
    return _users_cache if isinstance(_users_cache, list) else []


def _get_user_basic(user_data: dict) -> dict:
    """Extract basic user info for related users."""
    address = user_data.get("address", {})
    company = user_data.get("company", {})
    return {
        "id": user_data.get("id"),
        "name": user_data.get("name"),
        "username": user_data.get("username"),
        "email": user_data.get("email"),
        "phone": user_data.get("phone"),
        "website": user_data.get("website"),
        "city": address.get("city"),
        "company_name": company.get("name"),
        "company_bs": company.get("bs")
    }


def _get_platform_stats() -> dict:
    """Get platform-wide statistics for cross-referencing - HIGH VERBOSE."""
    all_users = _get_all_users()
    
    # Get all posts across platform
    all_posts = _make_request("/posts")
    all_posts = all_posts if isinstance(all_posts, list) else []
    
    # Get all comments across platform
    all_comments = _make_request("/comments")
    all_comments = all_comments if isinstance(all_comments, list) else []
    
    # Get all todos across platform
    all_todos = _make_request("/todos")
    all_todos = all_todos if isinstance(all_todos, list) else []
    
    # User activity rankings
    user_post_counts = {}
    user_word_counts = {}
    for post in all_posts:
        uid = post.get("userId")
        user_post_counts[uid] = user_post_counts.get(uid, 0) + 1
        user_word_counts[uid] = user_word_counts.get(uid, 0) + len(post.get("body", "").split())
    
    # Comment activity
    user_comment_counts = {}
    commenter_domains = {}
    for comment in all_comments:
        email = comment.get("email", "")
        domain = email.split("@")[-1] if "@" in email else "unknown"
        commenter_domains[domain] = commenter_domains.get(domain, 0) + 1
    
    # Todo completion by user
    user_todo_stats = {}
    for todo in all_todos:
        uid = todo.get("userId")
        if uid not in user_todo_stats:
            user_todo_stats[uid] = {"total": 0, "completed": 0}
        user_todo_stats[uid]["total"] += 1
        if todo.get("completed"):
            user_todo_stats[uid]["completed"] += 1
    
    return {
        "total_users": len(all_users),
        "total_posts": len(all_posts),
        "total_comments": len(all_comments),
        "total_todos": len(all_todos),
        "avg_posts_per_user": round(len(all_posts) / len(all_users), 1) if all_users else 0,
        "avg_comments_per_post": round(len(all_comments) / len(all_posts), 1) if all_posts else 0,
        "user_post_counts": user_post_counts,
        "user_word_counts": user_word_counts,
        "commenter_email_domains": commenter_domains,
        "user_todo_stats": user_todo_stats,
        "all_posts_preview": [
            {"id": p.get("id"), "userId": p.get("userId"), "title": p.get("title"), "body_length": len(p.get("body", ""))}
            for p in all_posts
        ],
        "all_comments_preview": [
            {"id": c.get("id"), "postId": c.get("postId"), "email": c.get("email"), "body_length": len(c.get("body", ""))}
            for c in all_comments
        ]
    }


# ============== Tool Implementation Functions ==============

def _get_user(user_id: int) -> dict:
    """Get a user by ID with HIGH VERBOSE data for skill mode."""
    data = _make_request(f"/users/{user_id}")
    
    if isinstance(data, dict) and "error" in data:
        return data
    
    if not data:
        return {"error": f"User {user_id} not found", "success": False}
    
    # HIGH VERBOSE: Full address details with analysis
    address = data.get("address", {})
    geo = address.get("geo", {})
    address_full = {
        "street": address.get("street"),
        "suite": address.get("suite"),
        "city": address.get("city"),
        "zipcode": address.get("zipcode"),
        "geo": {
            "lat": geo.get("lat"),
            "lng": geo.get("lng"),
            "lat_float": float(geo.get("lat", 0)) if geo.get("lat") else None,
            "lng_float": float(geo.get("lng", 0)) if geo.get("lng") else None
        },
        "formatted": f"{address.get('street', '')}, {address.get('suite', '')}, {address.get('city', '')} {address.get('zipcode', '')}",
        "zipcode_prefix": address.get("zipcode", "")[:5] if address.get("zipcode") else None
    }
    
    # HIGH VERBOSE: Full company details with analysis
    company = data.get("company", {})
    company_full = {
        "name": company.get("name"),
        "catchPhrase": company.get("catchPhrase"),
        "bs": company.get("bs"),
        "bs_words": company.get("bs", "").split() if company.get("bs") else [],
        "bs_word_count": len(company.get("bs", "").split()) if company.get("bs") else 0,
        "catchPhrase_length": len(company.get("catchPhrase", ""))
    }
    
    # HIGH VERBOSE: Get user's all posts, albums, todos with details
    posts = _make_request(f"/posts", {"userId": user_id})
    albums = _make_request(f"/albums", {"userId": user_id})
    todos = _make_request(f"/todos", {"userId": user_id})
    
    post_count = len(posts) if isinstance(posts, list) else 0
    album_count = len(albums) if isinstance(albums, list) else 0
    todo_count = len(todos) if isinstance(todos, list) else 0
    completed_todos = sum(1 for t in todos if isinstance(t, dict) and t.get("completed")) if isinstance(todos, list) else 0
    
    # HIGH VERBOSE: Post title analysis
    post_titles = [p.get("title", "") for p in posts] if isinstance(posts, list) else []
    avg_title_length = round(sum(len(t) for t in post_titles) / len(post_titles), 1) if post_titles else 0
    
    # HIGH VERBOSE: Todo title analysis  
    todo_titles = [t.get("title", "") for t in todos] if isinstance(todos, list) else []
    todo_avg_length = round(sum(len(t) for t in todo_titles) / len(todo_titles), 1) if todo_titles else 0
    
    # HIGH VERBOSE: Get related users (same city or company)
    all_users = _get_all_users()
    user_city = address.get("city", "")
    user_company = company.get("name", "")
    
    same_city_users = []
    same_company_users = []
    for other_user in all_users:
        if other_user.get("id") != user_id:
            other_city = other_user.get("address", {}).get("city", "")
            other_company = other_user.get("company", {}).get("name", "")
            
            if other_city == user_city and user_city:
                same_city_users.append(_get_user_basic(other_user))
            if other_company == user_company and user_company:
                same_company_users.append(_get_user_basic(other_user))
    
        # HIGH VERBOSE: All other users for comparison
    other_users = [_get_user_basic(u) for u in all_users if u.get("id") != user_id]
    
    # HIGH VERBOSE: Platform-wide statistics
    platform_stats = _get_platform_stats()
    
    # User's rank in platform
    user_rank = {
        "post_count_rank": sorted(platform_stats["user_post_counts"].keys(), 
                                  key=lambda x: platform_stats["user_post_counts"][x], 
                                  reverse=True).index(user_id) + 1 if user_id in platform_stats["user_post_counts"] else None,
        "word_count_rank": sorted(platform_stats["user_word_counts"].keys(),
                                  key=lambda x: platform_stats["user_word_counts"][x],
                                  reverse=True).index(user_id) + 1 if user_id in platform_stats["user_word_counts"] else None
    }
    
    return {
        "success": True,
        "user": {
            "id": data.get("id"),
            "name": data.get("name"),
            "username": data.get("username"),
            "email": data.get("email"),
            "email_domain": data.get("email", "").split("@")[-1] if "@" in data.get("email", "") else None,
            "phone": data.get("phone"),
            "website": data.get("website"),
            "address": address_full,
            "company": company_full
        },
        "activity_summary": {
            "total_posts": post_count,
            "total_albums": album_count,
            "total_todos": todo_count,
            "completed_todos": completed_todos,
            "pending_todos": todo_count - completed_todos,
            "completion_rate": round(completed_todos / todo_count * 100, 1) if todo_count > 0 else 0,
            "post_titles_avg_length": avg_title_length,
            "todo_titles_avg_length": todo_avg_length
        },
        # HIGH VERBOSE: Post and todo previews
        "post_previews": [
            {"id": p.get("id"), "title": p.get("title"), "body_preview": p.get("body", "")[:100]}
            for p in (posts[:10] if isinstance(posts, list) else [])
        ],
        "todo_previews": [
            {"id": t.get("id"), "title": t.get("title"), "completed": t.get("completed")}
            for t in (todos[:10] if isinstance(todos, list) else [])
        ],
        "album_previews": [
            {"id": a.get("id"), "title": a.get("title")}
            for a in (albums if isinstance(albums, list) else [])
        ],
        # HIGH VERBOSE: Related users
        "related_users": {
            "same_city": same_city_users,
            "same_city_count": len(same_city_users),
            "same_company": same_company_users,
            "same_company_count": len(same_company_users),
            "all_other_users": other_users
        },
        # HIGH VERBOSE: Platform-wide context
        "platform_stats": platform_stats,
        "user_rankings": user_rank
    }


def _get_user_posts(user_id: int) -> dict:
    """Get all posts by a user with HIGH VERBOSE full content for skill mode."""
    data = _make_request(f"/posts", {"userId": user_id})
    
    if isinstance(data, dict) and "error" in data:
        return data
    
    posts = []
    total_words = 0
    total_chars = 0
    all_comments = []
    email_domains = {}
    commenter_activity = {}
    
    for post in data:
        body = post.get("body", "")
        title = post.get("title", "")
        word_count = len(body.split())
        char_count = len(body)
        total_words += word_count
        total_chars += char_count
        
        # HIGH VERBOSE: Get comments for each post
        comments = _make_request(f"/posts/{post.get('id')}/comments")
        comment_count = len(comments) if isinstance(comments, list) else 0
        
        # HIGH VERBOSE: Full post data with all comments and analysis
        post_data = {
            "id": post.get("id"),
            "title": title,
            "title_length": len(title),
            "title_words": len(title.split()),
            "body": body,  # Full body, not truncated
            "body_paragraphs": body.count("\n") + 1,
            "word_count": word_count,
            "char_count": char_count,
            "avg_word_length": round(char_count / word_count, 2) if word_count > 0 else 0,
            "comment_count": comment_count,
            "comments": []
        }
        
        # HIGH VERBOSE: Include all comments with detailed analysis
        if isinstance(comments, list):
            post_comment_words = 0
            for comment in comments:
                comment_body = comment.get("body", "")
                comment_email = comment.get("email", "")
                comment_name = comment.get("name", "")
                
                # Track email domains
                domain = comment_email.split("@")[-1] if "@" in comment_email else "unknown"
                email_domains[domain] = email_domains.get(domain, 0) + 1
                
                # Track commenter activity
                commenter_activity[comment_email] = commenter_activity.get(comment_email, 0) + 1
                
                comment_word_count = len(comment_body.split())
                post_comment_words += comment_word_count
                
                comment_data = {
                    "id": comment.get("id"),
                    "postId": comment.get("postId"),
                    "name": comment_name,
                    "name_length": len(comment_name),
                    "email": comment_email,
                    "email_domain": domain,
                    "body": comment_body,  # Full comment body
                    "word_count": comment_word_count,
                    "char_count": len(comment_body),
                    "sentence_count": comment_body.count(".") + comment_body.count("!") + comment_body.count("?")
                }
                post_data["comments"].append(comment_data)
                all_comments.append(comment_data)
            
            post_data["total_comment_words"] = post_comment_words
            post_data["avg_comment_length"] = round(post_comment_words / comment_count, 1) if comment_count > 0 else 0
        
        posts.append(post_data)
    
    # HIGH VERBOSE: Calculate comprehensive statistics
    total_comments = sum(p.get("comment_count", 0) for p in posts)
    total_comment_words = sum(c.get("word_count", 0) for c in all_comments)
    
    # Find most active commenter
    most_active_commenter = max(commenter_activity.items(), key=lambda x: x[1], default=(None, 0))
    
    # Unique commenters
    unique_commenters = set(c.get("email") for c in all_comments if c.get("email"))
    
    comment_stats = {
        "total_comments": total_comments,
        "total_comment_words": total_comment_words,
        "avg_comments_per_post": round(total_comments / len(posts), 2) if posts else 0,
        "avg_words_per_comment": round(total_comment_words / total_comments, 2) if total_comments > 0 else 0,
        "posts_with_no_comments": sum(1 for p in posts if p.get("comment_count", 0) == 0),
        "most_commented_post_id": max((p for p in posts), key=lambda x: x.get("comment_count", 0), default={}).get("id") if posts else None,
        "least_commented_post_id": min((p for p in posts), key=lambda x: x.get("comment_count", 0), default={}).get("id") if posts else None,
        "unique_commenters": len(unique_commenters),
        "email_domain_distribution": email_domains,
        "most_active_commenter": {
            "email": most_active_commenter[0],
            "comment_count": most_active_commenter[1]
        },
        "commenter_activity": commenter_activity
    }
    
    # HIGH VERBOSE: Title and content analysis
    titles = [p.get("title", "") for p in posts]
    content_analysis = {
        "avg_title_length": round(sum(len(t) for t in titles) / len(titles), 1) if titles else 0,
        "shortest_title": min(titles, key=len, default=""),
        "longest_title": max(titles, key=len, default=""),
        "avg_body_length": round(total_chars / len(posts), 1) if posts else 0,
        "total_paragraphs": sum(p.get("body_paragraphs", 0) for p in posts)
    }
    
    return {
        "success": True,
        "user_id": user_id,
        "post_count": len(posts),
        "total_word_count": total_words,
        "total_char_count": total_chars,
        "avg_words_per_post": round(total_words / len(posts), 1) if posts else 0,
        "avg_chars_per_post": round(total_chars / len(posts), 1) if posts else 0,
        "content_analysis": content_analysis,
        "comment_statistics": comment_stats,
        "posts": posts,
        # HIGH VERBOSE: All comments flat list
        "all_comments": all_comments
    }


def _get_post_comments(post_id: int) -> dict:
    """Get comments for a specific post with VERBOSE full content for skill mode."""
    data = _make_request(f"/posts/{post_id}/comments")
    
    if isinstance(data, dict) and "error" in data:
        return data
    
    # VERBOSE: Get post details for context
    post = _make_request(f"/posts/{post_id}")
    post_info = {}
    if isinstance(post, dict) and "id" in post:
        post_info = {
            "id": post.get("id"),
            "userId": post.get("userId"),
            "title": post.get("title"),
            "body": post.get("body"),
            "word_count": len(post.get("body", "").split())
        }
    
    comments = []
    total_words = 0
    email_domains = {}
    
    for comment in data:
        body = comment.get("body", "")
        word_count = len(body.split())
        total_words += word_count
        
        email = comment.get("email", "")
        domain = email.split("@")[-1] if "@" in email else "unknown"
        email_domains[domain] = email_domains.get(domain, 0) + 1
        
        comments.append({
            "id": comment.get("id"),
            "postId": comment.get("postId"),
            "name": comment.get("name"),
            "email": email,
            "email_domain": domain,
            "body": body,  # Full body, not truncated
            "word_count": word_count,
            "char_count": len(body)
        })
    
    # Extract unique commenters
    unique_emails = set(c.get("email") for c in comments if c.get("email"))
    
    return {
        "success": True,
        "post_id": post_id,
        "post_info": post_info,
        "comment_count": len(comments),
        "total_word_count": total_words,
        "avg_words_per_comment": round(total_words / len(comments), 1) if comments else 0,
        "unique_commenters": len(unique_emails),
        "email_domain_distribution": email_domains,
        "comments": comments
    }


def _get_user_albums(user_id: int) -> dict:
    """Get albums by a user - SIMPLIFIED: metadata only, no photo fetching."""
    data = _make_request(f"/albums", {"userId": user_id})
    
    if isinstance(data, dict) and "error" in data:
        return data
    
    albums = []
    
    for album in data:
        album_id = album.get("id")
        album_title = album.get("title", "")
        
        # SIMPLIFIED: No photo fetching - just album metadata
        # Each album has exactly 50 photos (JSONPlaceholder standard)
        albums.append({
            "id": album_id,
            "title": album_title,
            "title_length": len(album_title),
            "title_words": len(album_title.split()),
            "photo_count": 50  # Standard count per album
        })
    
    # Each user has 10 albums × 50 photos = 500 photos total
    total_photos = len(albums) * 50
    
    return {
        "success": True,
        "user_id": user_id,
        "album_count": len(albums),
        "total_photos": total_photos,
        "statistics": {
            "avg_photos_per_album": 50.0,
            "shortest_album_title": min((a["title"] for a in albums), key=len, default=""),
            "longest_album_title": max((a["title"] for a in albums), key=len, default="")
        },
        "albums": albums
    }


def _get_user_todos(user_id: int) -> dict:
    """Get todos by a user with VERBOSE full list for skill mode."""
    data = _make_request(f"/todos", {"userId": user_id})
    
    if isinstance(data, dict) and "error" in data:
        return data
    
    completed = sum(1 for t in data if t.get("completed"))
    pending = len(data) - completed
    
    # VERBOSE: All todos with full details
    todos = []
    completed_todos = []
    pending_todos = []
    
    for todo in data:  # All todos, not limited
        todo_data = {
            "id": todo.get("id"),
            "title": todo.get("title"),
            "completed": todo.get("completed"),
            "title_length": len(todo.get("title", "")),
            "word_count": len(todo.get("title", "").split())
        }
        todos.append(todo_data)
        
        if todo.get("completed"):
            completed_todos.append(todo_data)
        else:
            pending_todos.append(todo_data)
    
    # VERBOSE: Statistics
    avg_title_length = round(sum(t["title_length"] for t in todos) / len(todos), 1) if todos else 0
    
    return {
        "success": True,
        "user_id": user_id,
        "total_todos": len(data),
        "completed_count": completed,
        "pending_count": pending,
        "completion_rate": round(completed / len(data) * 100, 1) if data else 0,
        "statistics": {
            "avg_title_length": avg_title_length,
            "shortest_title": min((t for t in todos), key=lambda x: x["title_length"], default={}).get("title") if todos else None,
            "longest_title": max((t for t in todos), key=lambda x: x["title_length"], default={}).get("title") if todos else None
        },
        "all_todos": todos,
        "completed_todos": completed_todos,
        "pending_todos": pending_todos
    }


def _get_user_engagement(user_id: int) -> dict:
    """Get user engagement metrics - comments received, commenter analysis, platform comparison."""
    # Get user's posts to find their post IDs
    posts = _make_request(f"/posts", {"userId": user_id})
    if isinstance(posts, dict) and "error" in posts:
        return posts
    
    if not isinstance(posts, list):
        return {"error": "Failed to fetch posts", "success": False}
    
    # Collect all comments on user's posts
    all_comments = []
    comments_by_post = {}
    
    for post in posts:
        post_id = post.get("id")
        post_title = post.get("title", "")
        comments = _make_request(f"/posts/{post_id}/comments")
        
        if isinstance(comments, list):
            post_comments = []
            for comment in comments:
                comment_data = {
                    "id": comment.get("id"),
                    "post_id": post_id,
                    "post_title": post_title,
                    "name": comment.get("name"),
                    "email": comment.get("email"),
                    "body": comment.get("body"),
                    "body_length": len(comment.get("body", "")),
                    "word_count": len(comment.get("body", "").split())
                }
                post_comments.append(comment_data)
                all_comments.append(comment_data)
            
            comments_by_post[post_id] = {
                "post_title": post_title,
                "comment_count": len(post_comments),
                "comments": post_comments
            }
    
    # Analyze commenters
    commenter_emails = {}
    commenter_domains = {}
    for comment in all_comments:
        email = comment.get("email", "")
        commenter_emails[email] = commenter_emails.get(email, 0) + 1
        domain = email.split("@")[-1] if "@" in email else "unknown"
        commenter_domains[domain] = commenter_domains.get(domain, 0) + 1
    
    # Sort commenters by activity
    sorted_commenters = sorted(commenter_emails.items(), key=lambda x: -x[1])
    
    # Calculate engagement metrics
    total_comments = len(all_comments)
    unique_commenters = len(commenter_emails)
    total_comment_words = sum(c.get("word_count", 0) for c in all_comments)
    
    # Get platform average for comparison
    all_platform_posts = _make_request("/posts")
    all_platform_comments = _make_request("/comments")
    platform_avg_comments = len(all_platform_comments) / len(all_platform_posts) if all_platform_posts else 0
    
    # User's performance vs platform
    user_avg_comments = total_comments / len(posts) if posts else 0
    engagement_ratio = round(user_avg_comments / platform_avg_comments, 2) if platform_avg_comments > 0 else 0
    
    return {
        "success": True,
        "user_id": user_id,
        "engagement_summary": {
            "total_posts": len(posts),
            "total_comments_received": total_comments,
            "unique_commenters": unique_commenters,
            "avg_comments_per_post": round(user_avg_comments, 2),
            "total_comment_words": total_comment_words,
            "avg_words_per_comment": round(total_comment_words / total_comments, 2) if total_comments > 0 else 0
        },
        "commenter_analysis": {
            "top_commenters": sorted_commenters[:10],
            "commenter_diversity_score": round(unique_commenters / total_comments * 100, 1) if total_comments > 0 else 0,
            "email_domain_distribution": commenter_domains,
            "most_common_domain": max(commenter_domains.items(), key=lambda x: x[1], default=("unknown", 0))
        },
        "platform_comparison": {
            "platform_avg_comments_per_post": round(platform_avg_comments, 2),
            "user_avg_comments_per_post": round(user_avg_comments, 2),
            "engagement_ratio": engagement_ratio,
            "above_average": engagement_ratio > 1.0
        },
        "comments_by_post": comments_by_post,
        "all_comments": all_comments
    }


def _get_user_profile(user_id: int) -> dict:
    """Get comprehensive user profile with HIGH VERBOSE all data."""
    user = _get_user(user_id)
    if not user.get("success"):
        return user
    
    posts = _get_user_posts(user_id)
    albums = _get_user_albums(user_id)
    todos = _get_user_todos(user_id)
    
    # HIGH VERBOSE: Calculate engagement scores
    post_score = (posts.get("post_count", 0) / 10) * 50  # Max 50 points
    todo_score = todos.get("completion_rate", 0) * 0.5  # Max 50 points
    productivity_score = round(post_score + todo_score, 1)
    
    # Determine engagement tier
    if productivity_score >= 80:
        engagement_tier = "Very Active"
    elif productivity_score >= 60:
        engagement_tier = "Active"
    elif productivity_score >= 40:
        engagement_tier = "Moderate"
    else:
        engagement_tier = "Low"
    
    # Determine writer type
    avg_words = posts.get("avg_words_per_post", 0)
    if avg_words >= 60:
        writer_type = "Verbose"
    elif avg_words >= 40:
        writer_type = "Moderate"
    else:
        writer_type = "Concise"
    
    # HIGH VERBOSE: Calculate more metrics
    total_engagement = (
        posts.get("comment_statistics", {}).get("total_comments", 0) +
        todos.get("completed_count", 0) +
        albums.get("total_photos", 0)
    )
    
    return {
        "success": True,
        "user": user.get("user"),
        "activity": {
            "posts": posts.get("post_count", 0),
            "albums": albums.get("album_count", 0),
            "photos": albums.get("total_photos", 0),
            "todos": todos.get("total_todos", 0),
            "completed_todos": todos.get("completed_count", 0),
            "pending_todos": todos.get("pending_count", 0),
            "todo_completion_rate": todos.get("completion_rate", 0),
            "total_comments_received": posts.get("comment_statistics", {}).get("total_comments", 0)
        },
        "writing_stats": {
            "total_posts": posts.get("post_count", 0),
            "total_words": posts.get("total_word_count", 0),
            "total_chars": posts.get("total_char_count", 0),
            "avg_words_per_post": posts.get("avg_words_per_post", 0),
            "avg_chars_per_post": posts.get("avg_chars_per_post", 0),
            "content_analysis": posts.get("content_analysis", {})
        },
        "engagement_metrics": {
            "productivity_score": productivity_score,
            "engagement_tier": engagement_tier,
            "writer_type": writer_type,
            "total_engagement_actions": total_engagement,
            "unique_commenters": posts.get("comment_statistics", {}).get("unique_commenters", 0),
            "avg_comments_per_post": posts.get("comment_statistics", {}).get("avg_comments_per_post", 0)
        },
        "related_users": user.get("related_users", {}),
        # HIGH VERBOSE v2: Include FULL raw data (not just summaries)
        "raw_data": {
            # Full posts data with all details
            "posts_full": posts,  # Complete posts response with all posts, comments, analysis
            # Full albums data with all photos
            "albums_full": albums,  # Complete albums response with all albums and photos
            # Full todos data
            "todos_full": todos,  # Complete todos response with all todos
            # Platform-wide statistics for comparison
            "platform_stats": user.get("platform_stats", {})
        },
        # Additional summaries for convenience
        "raw_summaries": {
            "posts_summary": {
                "count": posts.get("post_count", 0),
                "total_words": posts.get("total_word_count", 0),
                "comment_stats": posts.get("comment_statistics", {})
            },
            "albums_summary": {
                "count": albums.get("album_count", 0),
                "total_photos": albums.get("total_photos", 0),
                "statistics": albums.get("statistics", {})
            },
            "todos_summary": {
                "total": todos.get("total_todos", 0),
                "completed": todos.get("completed_count", 0),
                "pending": todos.get("pending_count", 0),
                "rate": todos.get("completion_rate", 0),
                "statistics": todos.get("statistics", {})
            }
        }
    }


# ============== Tool Handlers ==============

async def on_get_user(context: RunContextWrapper, params_str: str) -> Any:
    """Handler for getting a user."""
    params = _parse_params(params_str)
    user_id = params.get("user_id")
    
    if not user_id:
        return {"error": "user_id is required", "success": False}
    
    result = _get_user(int(user_id))
    return result


async def on_get_user_posts(context: RunContextWrapper, params_str: str) -> Any:
    """Handler for getting user posts."""
    params = _parse_params(params_str)
    user_id = params.get("user_id")
    
    if not user_id:
        return {"error": "user_id is required", "success": False}
    
    result = _get_user_posts(int(user_id))
    return result


async def on_get_post_comments(context: RunContextWrapper, params_str: str) -> Any:
    """Handler for getting post comments."""
    params = _parse_params(params_str)
    post_id = params.get("post_id")
    
    if not post_id:
        return {"error": "post_id is required", "success": False}
    
    result = _get_post_comments(int(post_id))
    return result


async def on_get_user_profile(context: RunContextWrapper, params_str: str) -> Any:
    """Handler for comprehensive user profile."""
    params = _parse_params(params_str)
    user_id = params.get("user_id")
    
    if not user_id:
        return {"error": "user_id is required", "success": False}
    
    result = _get_user_profile(int(user_id))
    return result


async def on_get_user_todos(context: RunContextWrapper, params_str: str) -> Any:
    """Handler for getting user todos."""
    params = _parse_params(params_str)
    user_id = params.get("user_id")
    
    if not user_id:
        return {"error": "user_id is required", "success": False}
    
    result = _get_user_todos(int(user_id))
    return result


async def on_get_user_albums(context: RunContextWrapper, params_str: str) -> Any:
    """Handler for getting user albums."""
    params = _parse_params(params_str)
    user_id = params.get("user_id")
    
    if not user_id:
        return {"error": "user_id is required", "success": False}
    
    result = _get_user_albums(int(user_id))
    return result


async def on_get_user_engagement(context: RunContextWrapper, params_str: str) -> Any:
    """Handler for getting user engagement metrics."""
    params = _parse_params(params_str)
    user_id = params.get("user_id")
    
    if not user_id:
        return {"error": "user_id is required", "success": False}
    
    result = _get_user_engagement(int(user_id))
    return result


# ============== Tool Definitions ==============

tool_jsonplaceholder_user = FunctionTool(
    name='local-jsonplaceholder_get_user',
    description='''Get user information by ID from JSONPlaceholder.

Returns dict:
{
    "success": bool,              # Whether request succeeded
    "user": {
        "id": int,                # User ID (1-10)
        "name": str,              # Full name (e.g., "Leanne Graham")
        "username": str,          # Username (e.g., "Bret")
        "email": str,             # Email address
        "phone": str,             # Phone number
        "website": str,           # Website URL
        "company": str,           # Company name
        "address": {
            "city": str,          # City name
            "street": str         # Street address
        }
    }
}

On error: {"error": str, "success": False}''',
    params_json_schema={
        "type": "object",
        "properties": {
            "user_id": {
                "type": "integer",
                "description": "User ID (1-10)"
            }
        },
        "required": ["user_id"]
    },
    on_invoke_tool=on_get_user
)

tool_jsonplaceholder_posts = FunctionTool(
    name='local-jsonplaceholder_get_posts',
    description='''Get all posts by a user.

Returns dict:
{
    "success": bool,              # Whether request succeeded
    "user_id": int,               # User ID queried
    "post_count": int,            # Total number of posts
    "total_word_count": int,      # Total words across all posts
    "avg_words_per_post": float,  # Average words per post
    "posts": [                    # List of posts
        {
            "id": int,            # Post ID
            "title": str,         # Post title
            "body": str,          # Post content (truncated to 100 chars + "...")
            "word_count": int     # Word count for this post
        }
    ]
}

On error: {"error": str, "success": False}''',
    params_json_schema={
        "type": "object",
        "properties": {
            "user_id": {
                "type": "integer",
                "description": "User ID (1-10)"
            }
        },
        "required": ["user_id"]
    },
    on_invoke_tool=on_get_user_posts
)

tool_jsonplaceholder_comments = FunctionTool(
    name='local-jsonplaceholder_get_comments',
    description='''Get comments for a specific post.

Returns dict:
{
    "success": bool,              # Whether request succeeded
    "post_id": int,               # Post ID queried
    "comment_count": int,         # Total number of comments
    "unique_commenters": int,     # Number of unique email addresses
    "comments": [                 # List of comments
        {
            "id": int,            # Comment ID
            "name": str,          # Comment title/subject
            "email": str,         # Commenter's email
            "body": str           # Comment text (truncated to 80 chars + "...")
        }
    ]
}

On error: {"error": str, "success": False}''',
    params_json_schema={
        "type": "object",
        "properties": {
            "post_id": {
                "type": "integer",
                "description": "Post ID"
            }
        },
        "required": ["post_id"]
    },
    on_invoke_tool=on_get_post_comments
)

tool_jsonplaceholder_profile = FunctionTool(
    name='local-jsonplaceholder_user_profile',
    description='''Get comprehensive user profile with posts, albums, and todos.

Returns dict:
{
    "success": bool,              # Whether request succeeded
    "user": {                     # User information
        "id": int,
        "name": str,
        "username": str,
        "email": str,
        "phone": str,
        "website": str,
        "company": str,
        "address": {"city": str, "street": str}
    },
    "activity": {
        "posts": int,             # Number of posts
        "albums": int,            # Number of albums
        "todos": int,             # Total todo items
        "todo_completion_rate": float  # Percentage of completed todos
    },
    "writing_stats": {
        "total_posts": int,       # Same as activity.posts
        "total_words": int,       # Total words written
        "avg_words_per_post": float  # Average words per post
    }
}

On error: {"error": str, "success": False}''',
    params_json_schema={
        "type": "object",
        "properties": {
            "user_id": {
                "type": "integer",
                "description": "User ID (1-10)"
            }
        },
        "required": ["user_id"]
    },
    on_invoke_tool=on_get_user_profile
)

tool_jsonplaceholder_todos = FunctionTool(
    name='local-jsonplaceholder_get_todos',
    description='''Get todos for a user with completion statistics.

Returns dict:
{
    "success": bool,              # Whether request succeeded
    "user_id": int,               # User ID queried
    "total_todos": int,           # Total number of todos
    "completed": int,             # Number of completed todos
    "pending": int,               # Number of pending todos
    "completion_rate": float,     # Percentage completed (0-100)
    "sample_todos": [             # First 10 todos
        {
            "id": int,            # Todo ID
            "title": str,         # Todo title/description
            "completed": bool     # Whether completed
        }
    ]
}

On error: {"error": str, "success": False}''',
    params_json_schema={
        "type": "object",
        "properties": {
            "user_id": {
                "type": "integer",
                "description": "User ID (1-10)"
            }
        },
        "required": ["user_id"]
    },
    on_invoke_tool=on_get_user_todos
)


tool_jsonplaceholder_albums = FunctionTool(
    name='local-jsonplaceholder_get_albums',
    description='''Get photo albums for a user.

Returns dict:
{
    "success": bool,              # Whether request succeeded
    "user_id": int,               # User ID queried
    "album_count": int,           # Number of albums (usually 10)
    "total_photos": int,          # Total photos across all albums
    "albums": [                   # Album list
        {
            "id": int,            # Album ID
            "title": str,         # Album title
            "title_length": int,  # Title character count
            "photo_count": int    # Photos in album (usually 50)
        }
    ],
    "statistics": {
        "avg_photos_per_album": float,
        "shortest_album_title": str,
        "longest_album_title": str
    }
}

On error: {"error": str, "success": False}''',
    params_json_schema={
        "type": "object",
        "properties": {
            "user_id": {
                "type": "integer",
                "description": "User ID (1-10)"
            }
        },
        "required": ["user_id"]
    },
    on_invoke_tool=on_get_user_albums
)


tool_jsonplaceholder_engagement = FunctionTool(
    name='local-jsonplaceholder_get_engagement',
    description='''Get user engagement metrics - comments received, commenter analysis, platform comparison.

Returns dict:
{
    "success": bool,
    "user_id": int,
    "engagement_summary": {
        "total_posts": int,
        "total_comments_received": int,
        "unique_commenters": int,
        "avg_comments_per_post": float,
        "total_comment_words": int,
        "avg_words_per_comment": float
    },
    "commenter_analysis": {
        "top_commenters": [(email, count), ...],
        "commenter_diversity_score": float,
        "email_domain_distribution": {domain: count},
        "most_common_domain": (domain, count)
    },
    "platform_comparison": {
        "platform_avg_comments_per_post": float,
        "user_avg_comments_per_post": float,
        "engagement_ratio": float,
        "above_average": bool
    },
    "comments_by_post": {post_id: {comments: [...]}},
    "all_comments": [...]
}

On error: {"error": str, "success": False}''',
    params_json_schema={
        "type": "object",
        "properties": {
            "user_id": {
                "type": "integer",
                "description": "User ID (1-10)"
            }
        },
        "required": ["user_id"]
    },
    on_invoke_tool=on_get_user_engagement
)


# Export all tools as a list (user_profile removed to encourage separate tool calls)
jsonplaceholder_tools = [
    tool_jsonplaceholder_user,        # 1. get_user
    tool_jsonplaceholder_posts,       # 2. get_posts
    tool_jsonplaceholder_todos,       # 3. get_todos
    tool_jsonplaceholder_albums,      # 4. get_albums
    tool_jsonplaceholder_engagement,  # 5. get_engagement (NEW)
    # tool_jsonplaceholder_comments,  # Removed - get_engagement covers this per-user
    # tool_jsonplaceholder_profile,   # Removed - use separate tools instead
]

