"""
Open Trivia Database API Tools

Provides tools to generate trivia quizzes from various categories.
Designed for skill mode scenarios with quiz generation.

API Documentation: https://opentdb.com/api_config.php
No authentication required.
"""

import json
import html
import time
from typing import Any
from agents.tool import FunctionTool, RunContextWrapper
import requests

# Base URL for Open Trivia Database API
TRIVIA_BASE_URL = "https://opentdb.com"

# Rate limiting configuration
# Open Trivia DB has a rate limit of approximately 1 request per 5 seconds
API_RETRY_COUNT = 3
API_BASE_DELAY = 5  # Base delay in seconds between retries
API_REQUEST_DELAY = 1  # Delay before each request to avoid hitting rate limits

# Category mappings
CATEGORIES = {
    "general": 9,
    "books": 10,
    "film": 11,
    "music": 12,
    "television": 14,
    "video_games": 15,
    "science_nature": 17,
    "computers": 18,
    "mathematics": 19,
    "mythology": 20,
    "sports": 21,
    "geography": 22,
    "history": 23,
    "politics": 24,
    "art": 25,
    "celebrities": 26,
    "animals": 27,
    "vehicles": 28,
    "comics": 29,
    "anime": 31,
    "cartoons": 32
}


def _make_request(endpoint: str, params: dict = None, max_retries: int = API_RETRY_COUNT) -> dict:
    """Make a request to Open Trivia DB API with error handling and automatic retry.
    
    Implements exponential backoff for rate limiting (429) errors.
    The Open Trivia Database has strict rate limits (~1 request per 5 seconds).
    """
    url = f"{TRIVIA_BASE_URL}{endpoint}"
    headers = {"User-Agent": "DikaNong-PatternReuse/1.0"}
    
    # Add a small delay before each request to avoid hitting rate limits
    time.sleep(API_REQUEST_DELAY)
    
    last_error = None
    
    for attempt in range(max_retries):
        try:
            response = requests.get(url, headers=headers, params=params, timeout=30)
            
            # Handle rate limiting (429 Too Many Requests)
            if response.status_code == 429:
                # Calculate delay with exponential backoff
                delay = API_BASE_DELAY * (2 ** attempt)
                print(f"[trivia_tools] Rate limited (429), waiting {delay}s before retry {attempt + 1}/{max_retries}")
                time.sleep(delay)
                last_error = f"429 Too Many Requests (attempt {attempt + 1})"
                continue
            
            response.raise_for_status()
            return response.json()
            
        except requests.exceptions.Timeout:
            last_error = "Request timeout"
            # For timeout, retry with shorter delay
            if attempt < max_retries - 1:
                time.sleep(API_BASE_DELAY)
                continue
                
        except requests.exceptions.RequestException as e:
            last_error = str(e)
            # For other request errors, check if we should retry
            if "429" in str(e) and attempt < max_retries - 1:
                delay = API_BASE_DELAY * (2 ** attempt)
                print(f"[trivia_tools] Rate limit error, waiting {delay}s before retry {attempt + 1}/{max_retries}")
                time.sleep(delay)
                continue
            break
    
    return {"error": last_error or "Unknown error after retries", "success": False}


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


def _decode_html(text: str) -> str:
    """Decode HTML entities in text."""
    return html.unescape(text) if text else text


# ============== Tool Implementation Functions ==============

def _get_trivia_questions(category: str = None, difficulty: str = None, 
                          amount: int = 10, question_type: str = None) -> dict:
    """Get trivia questions with optional filters."""
    params = {"amount": min(amount, 50)}  # Max 50 questions
    
    if category and category.lower() in CATEGORIES:
        params["category"] = CATEGORIES[category.lower()]
    
    if difficulty and difficulty.lower() in ["easy", "medium", "hard"]:
        params["difficulty"] = difficulty.lower()
    
    if question_type and question_type.lower() in ["multiple", "boolean"]:
        params["type"] = question_type.lower()
    
    data = _make_request("/api.php", params)
    
    if "error" in data:
        return data
    
    response_code = data.get("response_code", -1)
    if response_code != 0:
        error_messages = {
            1: "Not enough questions available for this query",
            2: "Invalid parameter",
            3: "Token not found",
            4: "Token exhausted"
        }
        return {"error": error_messages.get(response_code, "Unknown error"), "success": False}
    
    results = data.get("results", [])
    
    questions = []
    for i, q in enumerate(results, 1):
        all_answers = q.get("incorrect_answers", []) + [q.get("correct_answer")]
        # Shuffle answers (simple rotation based on index)
        shuffled = all_answers[i % len(all_answers):] + all_answers[:i % len(all_answers)]
        
        questions.append({
            "question_number": i,
            "category": _decode_html(q.get("category")),
            "difficulty": q.get("difficulty"),
            "type": q.get("type"),
            "question": _decode_html(q.get("question")),
            "correct_answer": _decode_html(q.get("correct_answer")),
            "all_answers": [_decode_html(a) for a in shuffled],
            "incorrect_answers": [_decode_html(a) for a in q.get("incorrect_answers", [])]
        })
    
    return {
        "success": True,
        "query": {
            "category": category,
            "difficulty": difficulty,
            "amount": amount,
            "type": question_type
        },
        "count": len(questions),
        "questions": questions
    }


def _get_category_question_count(category: str) -> dict:
    """Get the number of questions available in a category."""
    if category.lower() not in CATEGORIES:
        return {"error": f"Unknown category: {category}", "success": False}
    
    cat_id = CATEGORIES[category.lower()]
    data = _make_request("/api_count.php", {"category": cat_id})
    
    if "error" in data:
        return data
    
    counts = data.get("category_question_count", {})
    
    return {
        "success": True,
        "category": category,
        "category_id": cat_id,
        "question_counts": {
            "total": counts.get("total_question_count", 0),
            "easy": counts.get("total_easy_question_count", 0),
            "medium": counts.get("total_medium_question_count", 0),
            "hard": counts.get("total_hard_question_count", 0)
        }
    }


def _list_categories() -> dict:
    """List all available trivia categories."""
    data = _make_request("/api_category.php")
    
    if "error" in data:
        return data
    
    categories = data.get("trivia_categories", [])
    
    results = []
    for cat in categories:
        cat_id = cat.get("id")
        cat_name = cat.get("name")
        # Find our shorthand if available
        shorthand = None
        for key, val in CATEGORIES.items():
            if val == cat_id:
                shorthand = key
                break
        
        results.append({
            "id": cat_id,
            "name": cat_name,
            "shorthand": shorthand
        })
    
    return {
        "success": True,
        "count": len(categories),
        "categories": results
    }


def _get_global_question_count() -> dict:
    """Get global question count statistics."""
    data = _make_request("/api_count_global.php")
    
    if "error" in data:
        return data
    
    overall = data.get("overall", {})
    categories = data.get("categories", {})
    
    # Get top 5 categories by question count
    cat_list = []
    for cat_id, counts in categories.items():
        cat_list.append({
            "id": int(cat_id),
            "total": counts.get("total_num_of_questions", 0)
        })
    cat_list.sort(key=lambda x: x["total"], reverse=True)
    
    return {
        "success": True,
        "overall": {
            "total": overall.get("total_num_of_questions", 0),
            "pending": overall.get("total_num_of_pending_questions", 0),
            "verified": overall.get("total_num_of_verified_questions", 0),
            "rejected": overall.get("total_num_of_rejected_questions", 0)
        },
        "top_categories": cat_list[:10],
        "total_categories": len(categories)
    }


def _get_category_difficulty_analysis(category: str) -> dict:
    """Get detailed difficulty analysis for a category with sample questions.
    
    Note: This function makes multiple API calls, so it includes additional
    delays between requests to avoid rate limiting.
    """
    if category.lower() not in CATEGORIES:
        return {"error": f"Unknown category: {category}", "success": False}
    
    cat_id = CATEGORIES[category.lower()]
    
    # Get category counts
    count_data = _make_request("/api_count.php", {"category": cat_id})
    if "error" in count_data:
        return count_data
    
    counts = count_data.get("category_question_count", {})
    
    # Get sample questions for each difficulty
    # Add extra delay between requests to avoid rate limiting
    difficulty_samples = {}
    for i, diff in enumerate(["easy", "medium", "hard"]):
        # Add delay between difficulty requests (skip first one as _make_request already adds delay)
        if i > 0:
            time.sleep(API_BASE_DELAY)
        
        q_data = _make_request("/api.php", {
            "amount": 3,
            "category": cat_id,
            "difficulty": diff
        })
        if q_data.get("response_code") == 0:
            samples = []
            for q in q_data.get("results", []):
                samples.append({
                    "question": _decode_html(q.get("question"))[:100],
                    "type": q.get("type"),
                    "answer": _decode_html(q.get("correct_answer"))
                })
            difficulty_samples[diff] = {
                "count": counts.get(f"total_{diff}_question_count", 0),
                "samples": samples
            }
        else:
            difficulty_samples[diff] = {
                "count": counts.get(f"total_{diff}_question_count", 0),
                "samples": []
            }
    
    total = counts.get("total_question_count", 0)
    
    return {
        "success": True,
        "category": category,
        "category_id": cat_id,
        "total_questions": total,
        "difficulty_breakdown": difficulty_samples,
        "difficulty_distribution": {
            "easy_percent": round(difficulty_samples["easy"]["count"] / max(total, 1) * 100, 1),
            "medium_percent": round(difficulty_samples["medium"]["count"] / max(total, 1) * 100, 1),
            "hard_percent": round(difficulty_samples["hard"]["count"] / max(total, 1) * 100, 1)
        },
        "recommended_quiz_config": {
            "balanced": {"easy": 2, "medium": 5, "hard": 3},
            "beginner": {"easy": 7, "medium": 3, "hard": 0},
            "expert": {"easy": 0, "medium": 3, "hard": 7}
        }
    }


# ============== Tool Handlers ==============

async def on_get_trivia_questions(context: RunContextWrapper, params_str: str) -> Any:
    """Handler for getting trivia questions."""
    params = _parse_params(params_str)
    
    result = _get_trivia_questions(
        category=params.get("category"),
        difficulty=params.get("difficulty"),
        amount=params.get("amount", 10),
        question_type=params.get("type")
    )
    return result


async def on_get_category_count(context: RunContextWrapper, params_str: str) -> Any:
    """Handler for getting category question count."""
    params = _parse_params(params_str)
    category = params.get("category")
    
    if not category:
        return {"error": "category is required", "success": False}
    
    result = _get_category_question_count(category)
    return result


async def on_list_categories(context: RunContextWrapper, params_str: str) -> Any:
    """Handler for listing categories."""
    result = _list_categories()
    return result


async def on_get_global_count(context: RunContextWrapper, params_str: str) -> Any:
    """Handler for getting global question count."""
    result = _get_global_question_count()
    return result


async def on_category_difficulty_analysis(context: RunContextWrapper, params_str: str) -> Any:
    """Handler for category difficulty analysis."""
    params = _parse_params(params_str)
    category = params.get("category")
    
    if not category:
        return {"error": "category is required", "success": False}
    
    result = _get_category_difficulty_analysis(category)
    return result


# ============== Tool Definitions ==============

tool_trivia_get_questions = FunctionTool(
    name='local-trivia_get_questions',
    description='''Get trivia questions with optional category, difficulty, and type filters.

**Returns:** dict:
{
  "success": bool,
  "query": {"category": str | null, "difficulty": str | null, "amount": int, "type": str | null},
  "count": int,
  "questions": [
    {
      "question_number": int,
      "category": str,
      "difficulty": str,
      "type": str,
      "question": str,
      "correct_answer": str,
      "all_answers": [str],
      "incorrect_answers": [str]
    }
  ]
}''',
    params_json_schema={
        "type": "object",
        "properties": {
            "category": {
                "type": "string",
                "description": "Category name (e.g., 'general', 'science_nature', 'history', 'geography', 'sports', 'music', 'film', 'video_games', 'anime', 'computers')"
            },
            "difficulty": {
                "type": "string",
                "description": "Difficulty level: 'easy', 'medium', or 'hard'"
            },
            "amount": {
                "type": "integer",
                "description": "Number of questions (1-50, default: 10)"
            },
            "type": {
                "type": "string",
                "description": "Question type: 'multiple' (multiple choice) or 'boolean' (true/false)"
            }
        }
    },
    on_invoke_tool=on_get_trivia_questions
)

tool_trivia_category_count = FunctionTool(
    name='local-trivia_category_count',
    description='''Get the number of questions available in a category by difficulty.

**Returns:** dict:
{
  "success": bool,
  "category": str,
  "category_id": int,
  "question_counts": {"total": int, "easy": int, "medium": int, "hard": int}
}''',
    params_json_schema={
        "type": "object",
        "properties": {
            "category": {
                "type": "string",
                "description": "Category name (e.g., 'history', 'science_nature')"
            }
        },
        "required": ["category"]
    },
    on_invoke_tool=on_get_category_count
)

tool_trivia_list_categories = FunctionTool(
    name='local-trivia_list_categories',
    description='''List all available trivia categories.

**Returns:** dict:
{
  "success": bool,
  "count": int,
  "categories": [{"id": int, "name": str, "shorthand": str | null}]
}''',
    params_json_schema={
        "type": "object",
        "properties": {}
    },
    on_invoke_tool=on_list_categories
)

tool_trivia_global_stats = FunctionTool(
    name='local-trivia_global_stats',
    description='''Get global trivia database statistics.

**Returns:** dict:
{
  "success": bool,
  "overall": {"total": int, "pending": int, "verified": int, "rejected": int},
  "top_categories": [{"id": int, "total": int}],
  "total_categories": int
}''',
    params_json_schema={
        "type": "object",
        "properties": {}
    },
    on_invoke_tool=on_get_global_count
)

tool_trivia_difficulty_analysis = FunctionTool(
    name='local-trivia_difficulty_analysis',
    description='''Get detailed difficulty analysis for a category with sample questions and quiz recommendations.

**Returns:** dict:
{
  "success": bool,
  "category": str,                    # Category name
  "category_id": int,                 # Category ID
  "total_questions": int,             # Total questions in category
  "difficulty_breakdown": {           # Breakdown by difficulty
    "easy": {
      "count": int,                   # Number of easy questions
      "samples": [                    # Sample easy questions
        {"question": str, "type": str, "answer": str}
      ]
    },
    "medium": {"count": int, "samples": [...]},
    "hard": {"count": int, "samples": [...]}
  },
  "difficulty_distribution": {        # Percentage distribution
    "easy_percent": float,
    "medium_percent": float,
    "hard_percent": float
  },
  "recommended_quiz_config": {        # Recommended configurations
    "balanced": {"easy": int, "medium": int, "hard": int},
    "beginner": {"easy": int, "medium": int, "hard": int},
    "expert": {"easy": int, "medium": int, "hard": int}
  }
}''',
    params_json_schema={
        "type": "object",
        "properties": {
            "category": {
                "type": "string",
                "description": "Category name (e.g., 'history', 'science_nature', 'geography')"
            }
        },
        "required": ["category"]
    },
    on_invoke_tool=on_category_difficulty_analysis
)


# Export all tools as a list
trivia_tools = [
    tool_trivia_get_questions,
    tool_trivia_category_count,
    tool_trivia_list_categories,
    tool_trivia_global_stats,
    tool_trivia_difficulty_analysis,
]

