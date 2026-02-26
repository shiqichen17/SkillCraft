"""
Dog API Tools - Enhanced for 5x5 Skill Mode

Provides tools to query dog breed information and images.
Designed for skill mode scenarios with structured breed data.

API Documentation: https://dog.ceo/dog-api/
No authentication required.

5x5 Structure:
- 5 breeds: retriever, spaniel, bulldog, hound, terrier
- 5 tools per breed:
  1. dog_breed_info - Basic breed info + related breeds
  2. dog_breed_images - Sample images with metadata
  3. dog_sub_breed_images - Images for a specific sub-breed
  4. dog_breed_all_sub_breeds - All sub-breeds with samples
  5. dog_breed_gallery - Comprehensive gallery
"""

import json
from typing import Any
from agents.tool import FunctionTool, RunContextWrapper
import requests

# Base URL for Dog API
DOG_API_BASE_URL = "https://dog.ceo/api"

# Breed categories for enhanced data
BREED_CATEGORIES = {
    "retriever": {"category": "sporting", "origin": "Various", "size": "large", "temperament": "friendly"},
    "spaniel": {"category": "sporting", "origin": "Spain/UK", "size": "medium", "temperament": "gentle"},
    "bulldog": {"category": "non-sporting", "origin": "England", "size": "medium", "temperament": "calm"},
    "hound": {"category": "hound", "origin": "Various", "size": "varies", "temperament": "independent"},
    "terrier": {"category": "terrier", "origin": "British Isles", "size": "small-medium", "temperament": "energetic"},
    "poodle": {"category": "non-sporting", "origin": "Germany/France", "size": "varies", "temperament": "intelligent"},
    "shepherd": {"category": "herding", "origin": "Germany", "size": "large", "temperament": "loyal"},
    "boxer": {"category": "working", "origin": "Germany", "size": "large", "temperament": "playful"},
    "beagle": {"category": "hound", "origin": "England", "size": "small-medium", "temperament": "curious"},
    "husky": {"category": "working", "origin": "Siberia", "size": "medium-large", "temperament": "outgoing"},
}


def _make_request(endpoint: str) -> dict:
    """Make a request to Dog API with error handling."""
    url = f"{DOG_API_BASE_URL}{endpoint}"
    headers = {"User-Agent": "DikaNong-PatternReuse/1.0"}
    
    try:
        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.Timeout:
        return {"error": "Request timeout", "success": False}
    except requests.exceptions.RequestException as e:
        return {"error": str(e), "success": False}


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


def _analyze_image_url(url: str) -> dict:
    """Analyze an image URL to extract metadata."""
    parts = url.split("/")
    filename = parts[-1] if parts else ""
    breed_path = ""
    for i, part in enumerate(parts):
        if part == "breeds" and i + 1 < len(parts):
            breed_path = parts[i + 1]
            break
    
    return {
        "url": url,
        "filename": filename,
        "breed_path": breed_path,
        "extension": filename.split(".")[-1] if "." in filename else "unknown",
        "is_numbered": any(c.isdigit() for c in filename),
        "estimated_size": "medium" if "n0" in filename else "large",
        "source": "dog.ceo"
    }


def _get_breed_category_info(breed: str) -> dict:
    """Get category information for a breed."""
    breed_lower = breed.lower()
    if breed_lower in BREED_CATEGORIES:
        return BREED_CATEGORIES[breed_lower]
    return {"category": "unknown", "origin": "unknown", "size": "unknown", "temperament": "unknown"}


# ============== Tool Implementation Functions ==============

def _get_breed_info(breed: str) -> dict:
    """
    TOOL 1: Get comprehensive information about a specific breed.
    Enhanced with related breeds and detailed statistics.
    """
    breed_lower = breed.lower().replace(" ", "")
    
    # Get all sub-breeds
    sub_data = _make_request(f"/breed/{breed_lower}/list")
    
    # Get all images for count
    img_data = _make_request(f"/breed/{breed_lower}/images")
    
    if img_data.get("status") != "success":
        return {"error": f"Breed '{breed}' not found", "success": False}
    
    images = img_data.get("message", [])
    sub_breeds = sub_data.get("message", []) if sub_data.get("status") == "success" else []
    
    # VERBOSE: Get sample images with metadata
    sample_images = []
    for img_url in images[:10]:
        sample_images.append(_analyze_image_url(img_url))
    
    # VERBOSE: Get related breeds from same category
    category_info = _get_breed_category_info(breed)
    related_breeds = []
    
    # Fetch list of all breeds to find related ones
    all_breeds_data = _make_request("/breeds/list/all")
    if all_breeds_data.get("status") == "success":
        all_breeds = all_breeds_data.get("message", {})
        for b_name, b_subs in list(all_breeds.items())[:30]:  # Check first 30 breeds
            if b_name != breed_lower:
                b_info = _get_breed_category_info(b_name)
                if b_info.get("category") == category_info.get("category"):
                    # Get image count for related breed
                    related_img_data = _make_request(f"/breed/{b_name}/images")
                    related_img_count = len(related_img_data.get("message", [])) if related_img_data.get("status") == "success" else 0
                    related_breeds.append({
                        "breed": b_name,
                        "sub_breed_count": len(b_subs) if b_subs else 0,
                        "sub_breeds": b_subs[:5] if b_subs else [],
                        "image_count": related_img_count,
                        "category_info": b_info
                    })
                    if len(related_breeds) >= 5:
                        break
    
    # VERBOSE: Calculate statistics
    image_stats = {
        "total_images": len(images),
        "images_per_sub_breed": len(images) // max(len(sub_breeds), 1),
        "has_many_images": len(images) > 200,
        "diversity_score": len(sub_breeds) * 10 + min(len(images) // 10, 100),
        "popularity_tier": "Very Popular" if len(images) >= 300 else ("Popular" if len(images) >= 150 else ("Common" if len(images) >= 50 else "Rare"))
    }
    
    # VERBOSE: Sub-breed details
    sub_breed_details = []
    for sub in sub_breeds:
        sub_img_data = _make_request(f"/breed/{breed_lower}/{sub}/images")
        sub_img_count = len(sub_img_data.get("message", [])) if sub_img_data.get("status") == "success" else 0
        sub_sample = sub_img_data.get("message", [])[:3] if sub_img_data.get("status") == "success" else []
        sub_breed_details.append({
            "name": sub,
            "full_name": f"{sub} {breed}",
            "display_name": f"{sub.capitalize()} {breed.capitalize()}",
            "image_count": sub_img_count,
            "sample_images": [_analyze_image_url(url) for url in sub_sample],
            "has_unique_characteristics": True
        })
    
    return {
        "success": True,
        "breed": {
            "name": breed,
            "normalized_name": breed_lower,
            "display_name": breed.capitalize(),
            "sub_breeds": sub_breeds,
            "sub_breed_count": len(sub_breeds),
            "sub_breed_details": sub_breed_details,
            "total_images": len(images),
            "sample_images": sample_images
        },
        "category_info": category_info,
        "statistics": image_stats,
        "related_breeds": related_breeds,
        "api_info": {
            "endpoint": f"/breed/{breed_lower}",
            "api_version": "v1",
            "data_freshness": "live",
            "queries_made": 2 + len(sub_breeds) + len(related_breeds)
        }
    }


def _get_breed_images(breed: str, count: int = 10) -> dict:
    """
    TOOL 2: Get sample images for a breed with detailed metadata.
    Enhanced with image analysis and statistics.
    """
    breed_lower = breed.lower().replace(" ", "")
    
    # Get random images
    endpoint = f"/breed/{breed_lower}/images/random/{min(count, 20)}"
    data = _make_request(endpoint)
    
    if data.get("status") != "success":
        return {"error": f"Breed '{breed}' not found", "success": False}
    
    images = data.get("message", [])
    if isinstance(images, str):
        images = [images]
    
    # VERBOSE: Analyze each image
    analyzed_images = []
    filename_patterns = {}
    extensions = {}
    
    for img_url in images:
        analysis = _analyze_image_url(img_url)
        analyzed_images.append(analysis)
        
        # Track patterns
        ext = analysis.get("extension", "unknown")
        extensions[ext] = extensions.get(ext, 0) + 1
        
        prefix = analysis.get("filename", "")[:3]
        filename_patterns[prefix] = filename_patterns.get(prefix, 0) + 1
    
    # VERBOSE: Get all images for total count
    all_img_data = _make_request(f"/breed/{breed_lower}/images")
    total_available = len(all_img_data.get("message", [])) if all_img_data.get("status") == "success" else 0
    
    # VERBOSE: Get sub-breed info
    sub_data = _make_request(f"/breed/{breed_lower}/list")
    sub_breeds = sub_data.get("message", []) if sub_data.get("status") == "success" else []
    
    # VERBOSE: Get sample from each sub-breed
    sub_breed_samples = []
    for sub in sub_breeds[:5]:  # Limit to 5 sub-breeds
        sub_img = _make_request(f"/breed/{breed_lower}/{sub}/images/random/3")
        if sub_img.get("status") == "success":
            sub_images = sub_img.get("message", [])
            if isinstance(sub_images, str):
                sub_images = [sub_images]
            sub_breed_samples.append({
                "sub_breed": sub,
                "full_name": f"{sub} {breed}",
                "images": [_analyze_image_url(url) for url in sub_images]
            })
    
    return {
        "success": True,
        "breed": breed,
        "breed_normalized": breed_lower,
        "request_count": count,
        "image_count": len(analyzed_images),
        "images": analyzed_images,
        "image_statistics": {
            "total_available": total_available,
            "returned": len(analyzed_images),
            "coverage_percent": round(len(analyzed_images) / max(total_available, 1) * 100, 2),
            "extension_distribution": extensions,
            "filename_patterns": filename_patterns,
            "unique_sources": 1  # All from dog.ceo
        },
        "sub_breed_info": {
            "count": len(sub_breeds),
            "names": sub_breeds,
            "samples": sub_breed_samples
        },
        "category_info": _get_breed_category_info(breed),
        "api_info": {
            "endpoint": endpoint,
            "api_version": "v1",
            "queries_made": 2 + len(sub_breed_samples)
        }
    }


def _get_sub_breed_images(breed: str, sub_breed: str, count: int = 10) -> dict:
    """
    TOOL 3: Get images for a specific sub-breed with comprehensive data.
    Enhanced with sibling sub-breeds comparison.
    """
    breed_lower = breed.lower().replace(" ", "")
    sub_lower = sub_breed.lower()
    
    # Get images for this sub-breed
    endpoint = f"/breed/{breed_lower}/{sub_lower}/images/random/{min(count, 15)}"
    data = _make_request(endpoint)
    
    if data.get("status") != "success":
        return {"error": f"Sub-breed '{sub_breed} {breed}' not found", "success": False}
    
    images = data.get("message", [])
    if isinstance(images, str):
        images = [images]
    
    # VERBOSE: Analyze images
    analyzed_images = [_analyze_image_url(url) for url in images]
    
    # VERBOSE: Get all images for this sub-breed
    all_sub_img = _make_request(f"/breed/{breed_lower}/{sub_lower}/images")
    total_sub_images = len(all_sub_img.get("message", [])) if all_sub_img.get("status") == "success" else 0
    
    # VERBOSE: Get sibling sub-breeds info
    sub_data = _make_request(f"/breed/{breed_lower}/list")
    all_sub_breeds = sub_data.get("message", []) if sub_data.get("status") == "success" else []
    
    sibling_sub_breeds = []
    for sib in all_sub_breeds:
        if sib != sub_lower:
            sib_img = _make_request(f"/breed/{breed_lower}/{sib}/images")
            sib_count = len(sib_img.get("message", [])) if sib_img.get("status") == "success" else 0
            sib_sample = sib_img.get("message", [])[:2] if sib_img.get("status") == "success" else []
            sibling_sub_breeds.append({
                "name": sib,
                "full_name": f"{sib} {breed}",
                "display_name": f"{sib.capitalize()} {breed.capitalize()}",
                "image_count": sib_count,
                "sample_images": [_analyze_image_url(url) for url in sib_sample],
                "comparison_to_target": "more" if sib_count > total_sub_images else ("equal" if sib_count == total_sub_images else "less")
            })
    
    # VERBOSE: Calculate statistics
    all_sibling_counts = [s["image_count"] for s in sibling_sub_breeds]
    avg_sibling_count = sum(all_sibling_counts) / max(len(all_sibling_counts), 1) if all_sibling_counts else 0
    
    return {
        "success": True,
        "breed": breed,
        "sub_breed": sub_breed,
        "full_name": f"{sub_breed} {breed}",
        "display_name": f"{sub_breed.capitalize()} {breed.capitalize()}",
        "image_count": len(analyzed_images),
        "images": analyzed_images,
        "sub_breed_statistics": {
            "total_available": total_sub_images,
            "returned": len(analyzed_images),
            "rank_among_siblings": sum(1 for s in sibling_sub_breeds if s["image_count"] > total_sub_images) + 1,
            "total_siblings": len(sibling_sub_breeds),
            "average_sibling_count": round(avg_sibling_count, 1),
            "above_average": total_sub_images > avg_sibling_count
        },
        "sibling_sub_breeds": sibling_sub_breeds,
        "parent_breed_info": {
            "name": breed,
            "total_sub_breeds": len(all_sub_breeds),
            "category_info": _get_breed_category_info(breed)
        },
        "api_info": {
            "endpoint": endpoint,
            "api_version": "v1",
            "queries_made": 2 + len(sibling_sub_breeds)
        }
    }


def _get_breed_all_sub_breeds(breed: str) -> dict:
    """
    TOOL 4: Get detailed listing of ALL sub-breeds with sample images for each.
    This tool is designed to be called per-breed in a 5x5 pattern.
    """
    breed_lower = breed.lower().replace(" ", "")
    
    # Get all sub-breeds
    sub_data = _make_request(f"/breed/{breed_lower}/list")
    
    if sub_data.get("status") != "success":
        return {"error": f"Breed '{breed}' not found", "success": False}
    
    sub_breeds = sub_data.get("message", [])
    
    # VERBOSE: Get detailed info for each sub-breed
    sub_breed_details = []
    total_images_all_subs = 0
    
    for sub in sub_breeds:
        # Get all images for this sub-breed
        sub_img = _make_request(f"/breed/{breed_lower}/{sub}/images")
        sub_images = sub_img.get("message", []) if sub_img.get("status") == "success" else []
        
        total_images_all_subs += len(sub_images)
        
        # Analyze sample images
        sample_images = [_analyze_image_url(url) for url in sub_images[:5]]
        
        # Calculate characteristics
        characteristics = {
            "image_diversity": "high" if len(sub_images) > 100 else ("medium" if len(sub_images) > 30 else "low"),
            "has_sufficient_data": len(sub_images) >= 10,
            "recommended_for_training": len(sub_images) >= 50,
            "image_quality_estimate": "good" if any("n0" in url for url in sub_images[:5]) else "standard"
        }
        
        sub_breed_details.append({
            "name": sub,
            "full_name": f"{sub} {breed}",
            "display_name": f"{sub.capitalize()} {breed.capitalize()}",
            "total_images": len(sub_images),
            "sample_images": sample_images,
            "all_image_urls": sub_images[:15],  # Include more URLs
            "characteristics": characteristics,
            "api_endpoint": f"/breed/{breed_lower}/{sub}/images"
        })
    
    # VERBOSE: Sort by image count
    sub_breed_details.sort(key=lambda x: x["total_images"], reverse=True)
    
    # VERBOSE: Calculate breed-level statistics
    image_counts = [s["total_images"] for s in sub_breed_details]
    
    return {
        "success": True,
        "breed": breed,
        "breed_normalized": breed_lower,
        "display_name": breed.capitalize(),
        "sub_breed_count": len(sub_breeds),
        "sub_breeds": sub_breed_details,
        "statistics": {
            "total_images_all_sub_breeds": total_images_all_subs,
            "average_images_per_sub_breed": round(total_images_all_subs / max(len(sub_breeds), 1), 1),
            "max_images_sub_breed": max(image_counts) if image_counts else 0,
            "min_images_sub_breed": min(image_counts) if image_counts else 0,
            "most_popular_sub_breed": sub_breed_details[0]["name"] if sub_breed_details else None,
            "least_popular_sub_breed": sub_breed_details[-1]["name"] if sub_breed_details else None,
            "sub_breeds_with_100_plus_images": sum(1 for c in image_counts if c >= 100),
            "diversity_index": len(sub_breeds)
        },
        "category_info": _get_breed_category_info(breed),
        "api_info": {
            "endpoint": f"/breed/{breed_lower}/list",
            "api_version": "v1",
            "queries_made": 1 + len(sub_breeds)
        }
    }


def _get_breed_gallery(breed: str) -> dict:
    """
    TOOL 5: Get comprehensive gallery for a breed.
    Returns multiple images per sub-breed, organized for display.
    This tool is designed to be called per-breed in a 5x5 pattern.
    """
    breed_lower = breed.lower().replace(" ", "")
    
    # Get all images for the breed
    all_img_data = _make_request(f"/breed/{breed_lower}/images")
    
    if all_img_data.get("status") != "success":
        return {"error": f"Breed '{breed}' not found", "success": False}
    
    all_images = all_img_data.get("message", [])
    
    # Get sub-breeds
    sub_data = _make_request(f"/breed/{breed_lower}/list")
    sub_breeds = sub_data.get("message", []) if sub_data.get("status") == "success" else []
    
    # VERBOSE: Build gallery structure
    gallery_sections = []
    
    for sub in sub_breeds:
        # Get images for this sub-breed
        sub_img = _make_request(f"/breed/{breed_lower}/{sub}/images/random/8")
        images = sub_img.get("message", []) if sub_img.get("status") == "success" else []
        if isinstance(images, str):
            images = [images]
        
        # Analyze images
        analyzed = [_analyze_image_url(url) for url in images]
        
        # Get total count
        sub_all = _make_request(f"/breed/{breed_lower}/{sub}/images")
        total = len(sub_all.get("message", [])) if sub_all.get("status") == "success" else 0
        
        gallery_sections.append({
            "section_name": f"{sub.capitalize()} {breed.capitalize()}",
            "sub_breed": sub,
            "thumbnail": analyzed[0] if analyzed else None,
            "images": analyzed,
            "image_count": len(analyzed),
            "total_available": total,
            "display_priority": total,  # Higher count = higher priority
            "gallery_metadata": {
                "suggested_grid_size": "3x3" if len(analyzed) >= 9 else ("2x4" if len(analyzed) >= 8 else "2x3"),
                "has_hero_image": len(analyzed) > 0,
                "recommended_thumbnail_size": "200x200"
            }
        })
    
    # Sort by priority
    gallery_sections.sort(key=lambda x: x["display_priority"], reverse=True)
    
    # VERBOSE: Build main gallery images (from all breed images)
    main_gallery = []
    for img_url in all_images[:20]:
        analysis = _analyze_image_url(img_url)
        # Determine which sub-breed this belongs to
        for sub in sub_breeds:
            if sub in analysis.get("breed_path", ""):
                analysis["sub_breed"] = sub
                break
        else:
            analysis["sub_breed"] = "mixed"
        main_gallery.append(analysis)
    
    # VERBOSE: Calculate gallery statistics
    total_gallery_images = sum(s["image_count"] for s in gallery_sections)
    
    return {
        "success": True,
        "breed": breed,
        "breed_normalized": breed_lower,
        "display_name": breed.capitalize(),
        "gallery": {
            "main_images": main_gallery,
            "sections": gallery_sections,
            "total_sections": len(gallery_sections),
            "total_gallery_images": total_gallery_images
        },
        "gallery_statistics": {
            "total_breed_images": len(all_images),
            "images_in_gallery": total_gallery_images,
            "coverage_percent": round(total_gallery_images / max(len(all_images), 1) * 100, 2),
            "sub_breed_count": len(sub_breeds),
            "average_images_per_section": round(total_gallery_images / max(len(gallery_sections), 1), 1),
            "largest_section": gallery_sections[0]["section_name"] if gallery_sections else None,
            "smallest_section": gallery_sections[-1]["section_name"] if gallery_sections else None
        },
        "display_config": {
            "layout": "grid",
            "columns": 4,
            "image_size": "medium",
            "show_sub_breed_labels": True,
            "enable_lightbox": True,
            "lazy_loading": True
        },
        "category_info": _get_breed_category_info(breed),
        "api_info": {
            "endpoint": f"/breed/{breed_lower}/images",
            "api_version": "v1",
            "queries_made": 1 + len(sub_breeds) * 2
        }
    }


# ============== Tool Handlers ==============

async def on_get_breed_info(context: RunContextWrapper, params_str: str) -> Any:
    """Handler for getting breed info."""
    params = _parse_params(params_str)
    breed = params.get("breed")
    
    if not breed:
        return {"error": "breed is required", "success": False}
    
    result = _get_breed_info(breed)
    return result


async def on_get_breed_images(context: RunContextWrapper, params_str: str) -> Any:
    """Handler for getting breed images."""
    params = _parse_params(params_str)
    breed = params.get("breed")
    count = params.get("count", 10)
    
    if not breed:
        return {"error": "breed is required", "success": False}
    
    result = _get_breed_images(breed, int(count))
    return result


async def on_get_sub_breed_images(context: RunContextWrapper, params_str: str) -> Any:
    """Handler for getting sub-breed images."""
    params = _parse_params(params_str)
    breed = params.get("breed")
    sub_breed = params.get("sub_breed")
    count = params.get("count", 10)
    
    if not breed or not sub_breed:
        return {"error": "breed and sub_breed are required", "success": False}
    
    result = _get_sub_breed_images(breed, sub_breed, int(count))
    return result


async def on_get_breed_all_sub_breeds(context: RunContextWrapper, params_str: str) -> Any:
    """Handler for getting all sub-breeds for a breed."""
    params = _parse_params(params_str)
    breed = params.get("breed")
    
    if not breed:
        return {"error": "breed is required", "success": False}
    
    result = _get_breed_all_sub_breeds(breed)
    return result


async def on_get_breed_gallery(context: RunContextWrapper, params_str: str) -> Any:
    """Handler for getting breed gallery."""
    params = _parse_params(params_str)
    breed = params.get("breed")
    
    if not breed:
        return {"error": "breed is required", "success": False}
    
    result = _get_breed_gallery(breed)
    return result


# ============== Tool Definitions ==============

tool_dog_breed_info = FunctionTool(
    name='local-dog_breed_info',
    description='''Get comprehensive information about a dog breed including sub-breeds, statistics, and related breeds.

**Input**: breed (string) - The breed name (e.g., 'retriever', 'spaniel', 'bulldog')

**Returns:** dict with breed info, sub-breed details, category info, statistics, and related breeds.''',
    params_json_schema={
        "type": "object",
        "properties": {
            "breed": {
                "type": "string",
                "description": "The breed name (e.g., 'retriever', 'spaniel', 'bulldog', 'hound', 'terrier')"
            }
        },
        "required": ["breed"]
    },
    on_invoke_tool=on_get_breed_info
)

tool_dog_breed_images = FunctionTool(
    name='local-dog_breed_images',
    description='''Get sample images for a dog breed with detailed metadata and statistics.

**Input**: breed (string), count (int, optional, default: 10)

**Returns:** dict with analyzed images, image statistics, sub-breed samples, and category info.''',
    params_json_schema={
        "type": "object",
        "properties": {
            "breed": {
                "type": "string",
                "description": "The breed name (e.g., 'retriever', 'spaniel', 'bulldog')"
            },
            "count": {
                "type": "integer",
                "description": "Number of images to fetch (default: 10, max: 20)"
            }
        },
        "required": ["breed"]
    },
    on_invoke_tool=on_get_breed_images
)

tool_dog_sub_breed_images = FunctionTool(
    name='local-dog_sub_breed_images',
    description='''Get images for a specific sub-breed with comprehensive comparison data.

**Input**: breed (string), sub_breed (string), count (int, optional, default: 10)

**Returns:** dict with images, sibling sub-breeds comparison, and statistics.''',
    params_json_schema={
        "type": "object",
        "properties": {
            "breed": {
                "type": "string",
                "description": "The main breed (e.g., 'retriever', 'spaniel')"
            },
            "sub_breed": {
                "type": "string",
                "description": "The sub-breed (e.g., 'golden', 'cocker')"
            },
            "count": {
                "type": "integer",
                "description": "Number of images (default: 10)"
            }
        },
        "required": ["breed", "sub_breed"]
    },
    on_invoke_tool=on_get_sub_breed_images
)

tool_dog_breed_all_sub_breeds = FunctionTool(
    name='local-dog_breed_all_sub_breeds',
    description='''Get detailed listing of ALL sub-breeds for a breed with sample images for each.

**Input**: breed (string) - The breed name

**Returns:** dict with complete sub-breed listing, sample images per sub-breed, and statistics.''',
    params_json_schema={
        "type": "object",
        "properties": {
            "breed": {
                "type": "string",
                "description": "The breed name (e.g., 'retriever', 'spaniel', 'bulldog', 'hound', 'terrier')"
            }
        },
        "required": ["breed"]
    },
    on_invoke_tool=on_get_breed_all_sub_breeds
)

tool_dog_breed_gallery = FunctionTool(
    name='local-dog_breed_gallery',
    description='''Get comprehensive gallery for a breed with multiple images per sub-breed.

**Input**: breed (string) - The breed name

**Returns:** dict with organized gallery sections, display config, and statistics.''',
    params_json_schema={
        "type": "object",
        "properties": {
            "breed": {
                "type": "string",
                "description": "The breed name (e.g., 'retriever', 'spaniel', 'bulldog', 'hound', 'terrier')"
            }
        },
        "required": ["breed"]
    },
    on_invoke_tool=on_get_breed_gallery
)


# Export all tools as a list
dogapi_tools = [
    tool_dog_breed_info,
    tool_dog_breed_images,
    tool_dog_sub_breed_images,
    tool_dog_breed_all_sub_breeds,
    tool_dog_breed_gallery,
]
