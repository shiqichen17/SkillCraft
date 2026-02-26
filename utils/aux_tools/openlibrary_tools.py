"""
OpenLibrary Tools for library-book-analysis task
Based on Open Library API - completely free, no API key required.

Open Library API Documentation: https://openlibrary.org/developers/api
"""

import json
from typing import Any, Dict, List
from agents.tool import FunctionTool, RunContextWrapper
import requests

# Base URLs for Open Library APIs
OPENLIBRARY_URL = "https://openlibrary.org"
SEARCH_URL = f"{OPENLIBRARY_URL}/search.json"


# ============== Subjects for Task ==============
# 8 diverse book subjects for library analysis
SUBJECTS = [
    {"name": "science_fiction", "display": "Science Fiction"},
    {"name": "fantasy", "display": "Fantasy"},
    {"name": "mystery", "display": "Mystery"},
    {"name": "history", "display": "History"},
    {"name": "biography", "display": "Biography"},
    {"name": "philosophy", "display": "Philosophy"},
    {"name": "psychology", "display": "Psychology"},
    {"name": "programming", "display": "Programming"},
]


# ============== Tool 1: Search Books by Subject ==============

async def on_search_by_subject(context: RunContextWrapper, params_str: str) -> Any:
    """Search for books in a specific subject category."""
    try:
        params = json.loads(params_str) if params_str else {}
    except json.JSONDecodeError:
        return {"success": False, "error": "Invalid JSON parameters"}
    
    subject = params.get("subject", "")
    limit = params.get("limit", 50)
    
    if not subject:
        return {"success": False, "error": "subject is required"}
    
    try:
        response = requests.get(
            SEARCH_URL,
            params={
                "subject": subject,
                "limit": limit,
                "fields": "key,title,author_name,author_key,first_publish_year,edition_count,cover_i,language,subject,publisher,isbn,number_of_pages_median,ratings_average,ratings_count,want_to_read_count,currently_reading_count,already_read_count"
            },
            timeout=30
        )
        response.raise_for_status()
        data = response.json()
        
        books = []
        for doc in data.get("docs", []):
            # Extract work key (remove /works/ prefix)
            work_key = doc.get("key", "")
            if work_key.startswith("/works/"):
                work_key = work_key[7:]
            
            books.append({
                "work_key": work_key,
                "title": doc.get("title"),
                "authors": doc.get("author_name", []),
                "author_keys": doc.get("author_key", []),
                "first_publish_year": doc.get("first_publish_year"),
                "edition_count": doc.get("edition_count"),
                "cover_id": doc.get("cover_i"),
                "languages": doc.get("language", []),
                "subjects": doc.get("subject", [])[:10],  # Limit subjects
                "publishers": doc.get("publisher", [])[:5],  # Limit publishers
                "isbn": doc.get("isbn", [])[:3],  # Limit ISBNs
                "pages_median": doc.get("number_of_pages_median"),
                "ratings": {
                    "average": doc.get("ratings_average"),
                    "count": doc.get("ratings_count", 0)
                },
                "reading_stats": {
                    "want_to_read": doc.get("want_to_read_count", 0),
                    "currently_reading": doc.get("currently_reading_count", 0),
                    "already_read": doc.get("already_read_count", 0)
                }
            })
        
        # Calculate summary statistics
        years = [b["first_publish_year"] for b in books if b.get("first_publish_year")]
        editions = [b["edition_count"] for b in books if b.get("edition_count")]
        ratings = [b["ratings"]["average"] for b in books if b["ratings"].get("average")]
        
        return {
            "success": True,
            "subject": subject,
            "total_found": data.get("numFound", 0),
            "returned_count": len(books),
            "summary": {
                "oldest_year": min(years) if years else None,
                "newest_year": max(years) if years else None,
                "avg_editions": round(sum(editions) / len(editions), 1) if editions else None,
                "max_editions": max(editions) if editions else None,
                "avg_rating": round(sum(ratings) / len(ratings), 2) if ratings else None,
                "total_want_to_read": sum(b["reading_stats"]["want_to_read"] for b in books),
                "unique_authors": len(set(a for b in books for a in b.get("authors", [])))
            },
            "books": books
        }
        
    except requests.RequestException as e:
        return {"success": False, "error": f"API error: {str(e)}"}


tool_search_by_subject = FunctionTool(
    name='local-library_search_subject',
    description='''Search for books in a subject category. Returns book titles, authors, publication years, and reading statistics.

**Input:** subject (str), limit (int, optional, default: 50)

**Returns:** dict:
{
  "success": bool,
  "subject": str,
  "work_count": int,
  "books": [{"title": str, "authors": [str], "first_publish_year": int, "work_key": str, ...}]
}''',
    params_json_schema={
        "type": "object",
        "properties": {
            "subject": {"type": "string", "description": "Subject to search (e.g., 'science_fiction', 'history', 'programming')"},
            "limit": {"type": "integer", "description": "Maximum number of books to return (default: 50)"},
        },
        "required": ["subject"]
    },
    on_invoke_tool=on_search_by_subject
)


# ============== Tool 2: Get Book/Work Details ==============

async def on_get_work_details(context: RunContextWrapper, params_str: str) -> Any:
    """Get detailed information about a specific book/work."""
    try:
        params = json.loads(params_str) if params_str else {}
    except json.JSONDecodeError:
        return {"success": False, "error": "Invalid JSON parameters"}
    
    work_key = params.get("work_key", "")
    
    if not work_key:
        return {"success": False, "error": "work_key is required"}
    
    # Ensure proper format
    if not work_key.startswith("OL"):
        work_key = f"OL{work_key}"
    if not work_key.endswith("W"):
        work_key = f"{work_key}W"
    
    try:
        response = requests.get(
            f"{OPENLIBRARY_URL}/works/{work_key}.json",
            timeout=30
        )
        response.raise_for_status()
        data = response.json()
        
        # Extract description
        description = data.get("description")
        if isinstance(description, dict):
            description = description.get("value", "")
        
        # Extract first sentence
        first_sentence = data.get("first_sentence")
        if isinstance(first_sentence, dict):
            first_sentence = first_sentence.get("value", "")
        
        # Extract subjects and subject places
        subjects = data.get("subjects", [])
        subject_places = data.get("subject_places", [])
        subject_times = data.get("subject_times", [])
        subject_people = data.get("subject_people", [])
        
        # Extract links
        links = []
        for link in data.get("links", []):
            links.append({
                "title": link.get("title"),
                "url": link.get("url")
            })
        
        # Extract cover IDs
        covers = data.get("covers", [])
        
        # Get author references
        authors = []
        for author_ref in data.get("authors", []):
            author_data = author_ref.get("author", {})
            author_key = author_data.get("key", "")
            if author_key.startswith("/authors/"):
                author_key = author_key[9:]
            authors.append({
                "key": author_key,
                "type": author_ref.get("type", {}).get("key", "")
            })
        
        # Get excerpts
        excerpts = []
        for excerpt in data.get("excerpts", []):
            excerpts.append({
                "text": excerpt.get("excerpt"),
                "comment": excerpt.get("comment")
            })
        
        return {
            "success": True,
            "work": {
                "key": work_key,
                "title": data.get("title"),
                "subtitle": data.get("subtitle"),
                "description": description,
                "first_sentence": first_sentence,
                "authors": authors,
                "subjects": subjects[:20],
                "subject_places": subject_places,
                "subject_times": subject_times,
                "subject_people": subject_people,
                "covers": covers[:5],
                "cover_url": f"https://covers.openlibrary.org/b/id/{covers[0]}-L.jpg" if covers else None,
                "links": links,
                "excerpts": excerpts[:3],
                "first_publish_date": data.get("first_publish_date"),
                "revision": data.get("revision"),
                "latest_revision": data.get("latest_revision"),
                "created": data.get("created", {}).get("value"),
                "last_modified": data.get("last_modified", {}).get("value")
            }
        }
        
    except requests.RequestException as e:
        return {"success": False, "error": f"API error: {str(e)}"}


tool_get_work_details = FunctionTool(
    name='local-library_get_work',
    description='''Get detailed information about a specific book/work including description, subjects, and excerpts.

**Input:** work_key (str) - e.g., 'OL45883W' or just '45883'

**Returns:** dict:
{
  "success": bool,
  "work": {"title": str, "description": str, "subjects": [str], "authors": [...], "first_publish_date": str, ...}
}''',
    params_json_schema={
        "type": "object",
        "properties": {
            "work_key": {"type": "string", "description": "Work key (e.g., 'OL45883W' or just '45883')"},
        },
        "required": ["work_key"]
    },
    on_invoke_tool=on_get_work_details
)


# ============== Tool 3: Get Book Editions ==============

async def on_get_editions(context: RunContextWrapper, params_str: str) -> Any:
    """Get all editions of a specific book/work."""
    try:
        params = json.loads(params_str) if params_str else {}
    except json.JSONDecodeError:
        return {"success": False, "error": "Invalid JSON parameters"}
    
    work_key = params.get("work_key", "")
    limit = params.get("limit", 20)
    
    if not work_key:
        return {"success": False, "error": "work_key is required"}
    
    # Ensure proper format
    if not work_key.startswith("OL"):
        work_key = f"OL{work_key}"
    if not work_key.endswith("W"):
        work_key = f"{work_key}W"
    
    try:
        response = requests.get(
            f"{OPENLIBRARY_URL}/works/{work_key}/editions.json",
            params={"limit": limit},
            timeout=30
        )
        response.raise_for_status()
        data = response.json()
        
        editions = []
        for entry in data.get("entries", []):
            # Extract edition key
            edition_key = entry.get("key", "")
            if edition_key.startswith("/books/"):
                edition_key = edition_key[7:]
            
            editions.append({
                "edition_key": edition_key,
                "title": entry.get("title"),
                "subtitle": entry.get("subtitle"),
                "publishers": entry.get("publishers", []),
                "publish_date": entry.get("publish_date"),
                "publish_places": entry.get("publish_places", []),
                "number_of_pages": entry.get("number_of_pages"),
                "pagination": entry.get("pagination"),
                "languages": [lang.get("key", "").replace("/languages/", "") for lang in entry.get("languages", [])],
                "isbn_10": entry.get("isbn_10", []),
                "isbn_13": entry.get("isbn_13", []),
                "lccn": entry.get("lccn", []),
                "oclc_numbers": entry.get("oclc_numbers", []),
                "physical_format": entry.get("physical_format"),
                "covers": entry.get("covers", [])[:3],
                "contributors": entry.get("contributors", []),
                "series": entry.get("series", []),
                "weight": entry.get("weight"),
                "physical_dimensions": entry.get("physical_dimensions")
            })
        
        # Calculate summary
        publishers = list(set(p for e in editions for p in e.get("publishers", [])))
        languages = list(set(l for e in editions for l in e.get("languages", [])))
        years = []
        for e in editions:
            pd = e.get("publish_date", "")
            if pd and len(pd) >= 4:
                try:
                    year = int(pd[-4:]) if pd[-4:].isdigit() else int(pd[:4])
                    if 1400 < year < 2100:
                        years.append(year)
                except ValueError:
                    pass
        
        return {
            "success": True,
            "work_key": work_key,
            "total_editions": data.get("size", len(editions)),
            "returned_count": len(editions),
            "summary": {
                "unique_publishers": publishers[:20],
                "publisher_count": len(publishers),
                "languages": languages,
                "language_count": len(languages),
                "earliest_edition": min(years) if years else None,
                "latest_edition": max(years) if years else None,
                "editions_with_isbn": sum(1 for e in editions if e.get("isbn_10") or e.get("isbn_13"))
            },
            "editions": editions
        }
        
    except requests.RequestException as e:
        return {"success": False, "error": f"API error: {str(e)}"}


tool_get_editions = FunctionTool(
    name='local-library_get_editions',
    description='''Get all editions of a specific book/work including publishers, languages, and ISBNs.

**Input:** work_key (str), limit (int, optional, default: 20)

**Returns:** dict:
{
  "success": bool,
  "work_key": str,
  "edition_count": int,
  "editions": [{"title": str, "publishers": [str], "publish_date": str, "isbn_13": str, "language": str, ...}]
}''',
    params_json_schema={
        "type": "object",
        "properties": {
            "work_key": {"type": "string", "description": "Work key (e.g., 'OL45883W' or just '45883')"},
            "limit": {"type": "integer", "description": "Maximum number of editions to return (default: 20)"},
        },
        "required": ["work_key"]
    },
    on_invoke_tool=on_get_editions
)


# ============== Tool 4: Get Author Details ==============

async def on_get_author(context: RunContextWrapper, params_str: str) -> Any:
    """Get detailed information about an author."""
    try:
        params = json.loads(params_str) if params_str else {}
    except json.JSONDecodeError:
        return {"success": False, "error": "Invalid JSON parameters"}
    
    author_key = params.get("author_key", "")
    
    if not author_key:
        return {"success": False, "error": "author_key is required"}
    
    # Ensure proper format
    if not author_key.startswith("OL"):
        author_key = f"OL{author_key}"
    if not author_key.endswith("A"):
        author_key = f"{author_key}A"
    
    try:
        response = requests.get(
            f"{OPENLIBRARY_URL}/authors/{author_key}.json",
            timeout=30
        )
        response.raise_for_status()
        data = response.json()
        
        # Extract bio
        bio = data.get("bio")
        if isinstance(bio, dict):
            bio = bio.get("value", "")
        
        # Extract links
        links = []
        for link in data.get("links", []):
            links.append({
                "title": link.get("title"),
                "url": link.get("url")
            })
        
        # Get photos
        photos = data.get("photos", [])
        
        return {
            "success": True,
            "author": {
                "key": author_key,
                "name": data.get("name"),
                "personal_name": data.get("personal_name"),
                "alternate_names": data.get("alternate_names", []),
                "birth_date": data.get("birth_date"),
                "death_date": data.get("death_date"),
                "bio": bio,
                "photos": photos[:5],
                "photo_url": f"https://covers.openlibrary.org/a/id/{photos[0]}-L.jpg" if photos else None,
                "links": links,
                "wikipedia": data.get("wikipedia"),
                "source_records": data.get("source_records", []),
                "revision": data.get("revision"),
                "created": data.get("created", {}).get("value"),
                "last_modified": data.get("last_modified", {}).get("value")
            }
        }
        
    except requests.RequestException as e:
        return {"success": False, "error": f"API error: {str(e)}"}


tool_get_author = FunctionTool(
    name='local-library_get_author',
    description='''Get detailed information about an author including biography, photos, and links.

**Input:** author_key (str) - e.g., 'OL23919A' or just '23919'

**Returns:** dict:
{
  "success": bool,
  "author": {"name": str, "bio": str, "birth_date": str, "death_date": str, "photos": [str], ...}
}''',
    params_json_schema={
        "type": "object",
        "properties": {
            "author_key": {"type": "string", "description": "Author key (e.g., 'OL23919A' or just '23919')"},
        },
        "required": ["author_key"]
    },
    on_invoke_tool=on_get_author
)


# ============== Tool 5: Get Author Works ==============

async def on_get_author_works(context: RunContextWrapper, params_str: str) -> Any:
    """Get all works by a specific author."""
    try:
        params = json.loads(params_str) if params_str else {}
    except json.JSONDecodeError:
        return {"success": False, "error": "Invalid JSON parameters"}
    
    author_key = params.get("author_key", "")
    limit = params.get("limit", 30)
    
    if not author_key:
        return {"success": False, "error": "author_key is required"}
    
    # Ensure proper format
    if not author_key.startswith("OL"):
        author_key = f"OL{author_key}"
    if not author_key.endswith("A"):
        author_key = f"{author_key}A"
    
    try:
        response = requests.get(
            f"{OPENLIBRARY_URL}/authors/{author_key}/works.json",
            params={"limit": limit},
            timeout=30
        )
        response.raise_for_status()
        data = response.json()
        
        works = []
        for entry in data.get("entries", []):
            # Extract work key
            work_key = entry.get("key", "")
            if work_key.startswith("/works/"):
                work_key = work_key[7:]
            
            # Extract description
            description = entry.get("description")
            if isinstance(description, dict):
                description = description.get("value", "")
            elif isinstance(description, str):
                description = description[:500]  # Limit length
            
            works.append({
                "work_key": work_key,
                "title": entry.get("title"),
                "subtitle": entry.get("subtitle"),
                "description": description,
                "subjects": entry.get("subjects", [])[:10],
                "covers": entry.get("covers", [])[:3],
                "first_publish_date": entry.get("first_publish_date"),
                "revision": entry.get("revision")
            })
        
        # Calculate summary
        all_subjects = {}
        for w in works:
            for s in w.get("subjects", []):
                all_subjects[s] = all_subjects.get(s, 0) + 1
        
        # Sort subjects by frequency
        top_subjects = sorted(all_subjects.items(), key=lambda x: x[1], reverse=True)[:15]
        
        return {
            "success": True,
            "author_key": author_key,
            "total_works": data.get("size", len(works)),
            "returned_count": len(works),
            "summary": {
                "works_with_covers": sum(1 for w in works if w.get("covers")),
                "works_with_descriptions": sum(1 for w in works if w.get("description")),
                "top_subjects": [{"subject": s, "count": c} for s, c in top_subjects],
                "unique_subjects": len(all_subjects)
            },
            "works": works
        }
        
    except requests.RequestException as e:
        return {"success": False, "error": f"API error: {str(e)}"}


tool_get_author_works = FunctionTool(
    name='local-library_get_author_works',
    description='''Get all works by a specific author with subjects and descriptions.

**Input:** author_key (str), limit (int, optional, default: 30)

**Returns:** dict:
{
  "success": bool,
  "author": str,
  "work_count": int,
  "works": [{"title": str, "work_key": str, "subjects": [str], "first_publish_year": int, ...}]
}''',
    params_json_schema={
        "type": "object",
        "properties": {
            "author_key": {"type": "string", "description": "Author key (e.g., 'OL23919A' or just '23919')"},
            "limit": {"type": "integer", "description": "Maximum number of works to return (default: 30)"},
        },
        "required": ["author_key"]
    },
    on_invoke_tool=on_get_author_works
)


# ============== Tool 6: Search Books by Title ==============

async def on_search_by_title(context: RunContextWrapper, params_str: str) -> Any:
    """Search for books by title."""
    try:
        params = json.loads(params_str) if params_str else {}
    except json.JSONDecodeError:
        return {"success": False, "error": "Invalid JSON parameters"}
    
    title = params.get("title", "")
    limit = params.get("limit", 10)
    
    if not title:
        return {"success": False, "error": "title is required"}
    
    try:
        response = requests.get(
            SEARCH_URL,
            params={
                "title": title,
                "limit": limit,
                "fields": "key,title,author_name,author_key,first_publish_year,edition_count,cover_i,language,subject,publisher,isbn,number_of_pages_median,ratings_average,ratings_count"
            },
            timeout=30
        )
        response.raise_for_status()
        data = response.json()
        
        books = []
        for doc in data.get("docs", []):
            # Extract work key (remove /works/ prefix)
            work_key = doc.get("key", "")
            if work_key.startswith("/works/"):
                work_key = work_key[7:]
            
            books.append({
                "work_key": work_key,
                "title": doc.get("title"),
                "authors": doc.get("author_name", []),
                "author_keys": doc.get("author_key", []),
                "first_publish_year": doc.get("first_publish_year"),
                "edition_count": doc.get("edition_count"),
                "cover_id": doc.get("cover_i"),
                "languages": doc.get("language", []),
                "subjects": doc.get("subject", [])[:10],
                "pages_median": doc.get("number_of_pages_median"),
                "ratings": {
                    "average": doc.get("ratings_average"),
                    "count": doc.get("ratings_count", 0)
                }
            })
        
        return {
            "success": True,
            "search_query": title,
            "total_found": data.get("numFound", 0),
            "returned_count": len(books),
            "books": books
        }
        
    except requests.RequestException as e:
        return {"success": False, "error": f"API error: {str(e)}"}


tool_search_by_title = FunctionTool(
    name='local-library_search_books',
    description='''Search for books by title. Returns matching books with details.

**Input:** title (str), limit (int, optional, default: 10)

**Returns:** dict:
{
  "success": bool,
  "search_query": str,
  "total_found": int,
  "books": [{"title": str, "authors": [str], "first_publish_year": int, "work_key": str, "author_keys": [str], ...}]
}''',
    params_json_schema={
        "type": "object",
        "properties": {
            "title": {"type": "string", "description": "Book title to search for"},
            "limit": {"type": "integer", "description": "Maximum number of results (default: 10)"},
        },
        "required": ["title"]
    },
    on_invoke_tool=on_search_by_title
)


# ============== Export all tools ==============

openlibrary_tools = [
    tool_search_by_subject,     # Step 1: Search books by subject
    tool_search_by_title,       # Step 1b: Search books by title
    tool_get_work_details,      # Step 2: Get work details
    tool_get_editions,          # Step 3: Get book editions
    tool_get_author,            # Step 4: Get author details
    tool_get_author_works,      # Step 5: Get author's other works
]

