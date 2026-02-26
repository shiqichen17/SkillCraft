"""
TheMealDB API Tools

Provides tools to query meal recipes and ingredients.
Designed for skill mode scenarios with structured recipe data.

API Documentation: https://www.themealdb.com/api.php
Free tier available.
"""

import json
from typing import Any
from agents.tool import FunctionTool, RunContextWrapper
import requests

# Base URL for TheMealDB API
MEALDB_BASE_URL = "https://www.themealdb.com/api/json/v1/1"


def _make_request(endpoint: str, params: dict = None) -> dict:
    """Make a request to TheMealDB API with error handling."""
    url = f"{MEALDB_BASE_URL}{endpoint}"
    headers = {"User-Agent": "DikaNong-PatternReuse/1.0"}
    
    try:
        response = requests.get(url, headers=headers, params=params, timeout=30)
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


def _extract_ingredients(meal: dict) -> list:
    """Extract ingredients and measures from a meal - ENHANCED VERBOSE V2."""
    ingredients = []
    
    # Categorization keywords
    protein_keywords = ['chicken', 'beef', 'pork', 'fish', 'shrimp', 'egg', 'tofu', 'lamb', 'duck', 'turkey', 'salmon', 'tuna', 'prawn']
    veggie_keywords = ['onion', 'garlic', 'tomato', 'pepper', 'carrot', 'celery', 'potato', 'mushroom', 'lettuce', 'spinach', 'broccoli', 'zucchini']
    dairy_keywords = ['milk', 'cheese', 'butter', 'cream', 'yogurt', 'parmesan', 'mozzarella', 'cheddar']
    spice_keywords = ['salt', 'pepper', 'cumin', 'paprika', 'oregano', 'basil', 'thyme', 'coriander', 'chili', 'cinnamon', 'ginger']
    grain_keywords = ['rice', 'pasta', 'flour', 'bread', 'noodle', 'wheat', 'oat']
    liquid_keywords = ['water', 'stock', 'broth', 'wine', 'oil', 'vinegar', 'sauce', 'juice']
    
    for i in range(1, 21):
        ingredient = meal.get(f"strIngredient{i}")
        measure = meal.get(f"strMeasure{i}")
        if ingredient and ingredient.strip():
            ing_name = ingredient.strip()
            ing_lower = ing_name.lower()
            meas = measure.strip() if measure else ""
            
            # Determine category
            category = "other"
            if any(k in ing_lower for k in protein_keywords):
                category = "protein"
            elif any(k in ing_lower for k in veggie_keywords):
                category = "vegetable"
            elif any(k in ing_lower for k in dairy_keywords):
                category = "dairy"
            elif any(k in ing_lower for k in spice_keywords):
                category = "spice"
            elif any(k in ing_lower for k in grain_keywords):
                category = "grain"
            elif any(k in ing_lower for k in liquid_keywords):
                category = "liquid"
            
            # Parse measure for numeric value
            numeric_value = None
            unit = None
            if meas:
                import re
                match = re.match(r'([\d./]+)\s*(.+)?', meas)
                if match:
                    try:
                        numeric_value = float(match.group(1).replace('/', '.'))
                    except:
                        pass
                    unit = match.group(2).strip() if match.group(2) else None
            
            ingredients.append({
                "ingredient": ing_name,
                "ingredient_lower": ing_lower,
                "measure": meas,
                "measure_numeric": numeric_value,
                "measure_unit": unit,
                "ingredient_words": len(ing_name.split()),
                "ingredient_char_count": len(ing_name),
                "has_measure": bool(meas),
                "measure_words": len(meas.split()) if meas else 0,
                "position": i,
                "category": category,
                "is_primary": i <= 5,
                "ingredient_image_url": f"https://www.themealdb.com/images/ingredients/{ing_name}.png",
                "ingredient_thumbnail": f"https://www.themealdb.com/images/ingredients/{ing_name}-Small.png",
                "ingredient_preview_url": f"https://www.themealdb.com/images/ingredients/{ing_name}-Medium.png"
            })
    return ingredients


# ============== Tool Implementation Functions ==============

def _search_meal_by_name(name: str) -> dict:
    """Search for meals by name - ENHANCED VERBOSE."""
    data = _make_request("/search.php", {"s": name})
    
    if "error" in data:
        return data
    
    meals = data.get("meals") or []
    
    results = []
    categories = {}
    areas = {}
    
    for meal in meals[:10]:  # VERBOSE: Increased to 10
        meal_name = meal.get("strMeal", "")
        category = meal.get("strCategory", "")
        area = meal.get("strArea", "")
        tags = meal.get("strTags", "")
        
        # Track statistics
        categories[category] = categories.get(category, 0) + 1
        areas[area] = areas.get(area, 0) + 1
        
        results.append({
            "id": meal.get("idMeal"),
            "name": meal_name,
            "name_length": len(meal_name),
            "name_words": len(meal_name.split()),
            "category": category,
            "area": area,
            "tags": tags.split(",") if tags else [],
            "tag_count": len(tags.split(",")) if tags else 0,
            "image": meal.get("strMealThumb"),
            "youtube": meal.get("strYoutube"),
            "has_youtube": bool(meal.get("strYoutube")),
            "source": meal.get("strSource"),
            "has_source": bool(meal.get("strSource")),
            "instructions_preview": (meal.get("strInstructions") or "")[:300],
            "instructions_length": len(meal.get("strInstructions") or "")
        })
    
    return {
        "success": True,
        "query": name,
        "query_length": len(name),
        "total_matches": len(meals),
        "returned_count": len(results),
        "meals": results,
        "statistics": {
            "categories_found": categories,
            "areas_found": areas,
            "unique_categories": len(categories),
            "unique_areas": len(areas)
        },
        "api_info": {
            "endpoint": "/search.php",
            "api_version": "v1"
        }
    }


def _get_meal_details(meal_id: str) -> dict:
    """Get detailed information about a specific meal - ENHANCED VERBOSE V2."""
    data = _make_request("/lookup.php", {"i": meal_id})
    
    if "error" in data:
        return data
    
    meals = data.get("meals") or []
    if not meals:
        return {"error": "Meal not found", "success": False}
    
    meal = meals[0]
    
    # Parse instructions into steps - VERBOSE: return all steps
    instructions = meal.get("strInstructions", "")
    steps = [s.strip() for s in instructions.split("\r\n") if s.strip()]
    if len(steps) <= 1:
        steps = [s.strip() for s in instructions.split(". ") if s.strip()]
    
    # VERBOSE V2: Create detailed step analysis with cooking techniques
    cooking_techniques = ['fry', 'bake', 'boil', 'steam', 'grill', 'roast', 'saute', 'simmer', 'braise', 'poach', 'stir', 'mix', 'chop', 'slice', 'dice']
    step_details = []
    for i, step in enumerate(steps[:20], 1):  # VERBOSE V2: up to 20 steps
        techniques_found = [t for t in cooking_techniques if t in step.lower()]
        step_details.append({
            "step_number": i,
            "instruction": step,
            "word_count": len(step.split()),
            "char_count": len(step),
            "has_temperature": any(word in step.lower() for word in ['°c', '°f', 'degrees', 'heat', 'oven', 'boil', 'simmer', 'preheat']),
            "has_time": any(word in step.lower() for word in ['minute', 'hour', 'second', 'min', 'hr']),
            "cooking_techniques": techniques_found,
            "technique_count": len(techniques_found),
            "is_prep_step": any(word in step.lower() for word in ['chop', 'slice', 'dice', 'cut', 'prepare', 'wash', 'peel']),
            "is_cooking_step": any(word in step.lower() for word in ['cook', 'fry', 'bake', 'heat', 'boil'])
        })
    
    # Extract ingredients with enhanced info
    ingredients = _extract_ingredients(meal)
    
    # VERBOSE V2: Detailed ingredient analysis by category
    ingredient_by_category = {"protein": [], "vegetable": [], "dairy": [], "spice": [], "grain": [], "liquid": [], "other": []}
    for ing in ingredients:
        cat = ing.get('category', 'other')
        ingredient_by_category[cat].append({
            "name": ing['ingredient'],
            "measure": ing['measure'],
            "position": ing['position']
        })
    
    meal_name = meal.get("strMeal", "")
    category = meal.get("strCategory", "")
    area = meal.get("strArea", "")
    tags = meal.get("strTags", "").split(",") if meal.get("strTags") else []
    
    # VERBOSE V2: Fetch related meals from same category (up to 8)
    related_by_category = []
    if category:
        cat_data = _make_request("/filter.php", {"c": category})
        if "meals" in cat_data and cat_data["meals"]:
            for m in cat_data["meals"][:8]:
                if m.get("idMeal") != meal_id:
                    related_by_category.append({
                        "id": m.get("idMeal"),
                        "name": m.get("strMeal"),
                        "image": m.get("strMealThumb"),
                        "relation": f"same_category_{category}"
                    })
    
    # VERBOSE V2: Fetch related meals from same area/cuisine (up to 8)
    related_by_area = []
    if area:
        area_data = _make_request("/filter.php", {"a": area})
        if "meals" in area_data and area_data["meals"]:
            for m in area_data["meals"][:8]:
                if m.get("idMeal") != meal_id:
                    related_by_area.append({
                        "id": m.get("idMeal"),
                        "name": m.get("strMeal"),
                        "image": m.get("strMealThumb"),
                        "relation": f"same_cuisine_{area}"
                    })
    
    # Calculate nutrition estimate based on ingredients
    nutrition_estimate = {
        "has_protein": len(ingredient_by_category['protein']) > 0,
        "protein_sources": [i['name'] for i in ingredient_by_category['protein']],
        "has_vegetables": len(ingredient_by_category['vegetable']) > 0,
        "vegetable_count": len(ingredient_by_category['vegetable']),
        "has_dairy": len(ingredient_by_category['dairy']) > 0,
        "dairy_items": [i['name'] for i in ingredient_by_category['dairy']],
        "spice_count": len(ingredient_by_category['spice']),
        "estimated_calories_range": "300-500" if len(ingredients) <= 8 else ("500-800" if len(ingredients) <= 15 else "800+"),
        "dietary_notes": []
    }
    
    if not ingredient_by_category['protein']:
        nutrition_estimate['dietary_notes'].append("Vegetarian-friendly")
    if not ingredient_by_category['dairy']:
        nutrition_estimate['dietary_notes'].append("Dairy-free")
    
    return {
        "success": True,
        "meal": {
            "id": meal.get("idMeal"),
            "name": meal_name,
            "name_length": len(meal_name),
            "name_words": len(meal_name.split()),
            "category": category,
            "area": area,
            "cuisine": area,
            "instructions": instructions,
            "instructions_length": len(instructions),
            "instructions_word_count": len(instructions.split()),
            "instruction_steps": steps[:20],
            "step_count": len(steps),
            "step_details": step_details,
            "ingredients": ingredients,
            "ingredient_count": len(ingredients),
            "ingredients_by_category": ingredient_by_category,
            "primary_ingredients": [i['ingredient'] for i in ingredients if i.get('is_primary')],
            "image": meal.get("strMealThumb"),
            "image_preview": meal.get("strMealThumb") + "/preview" if meal.get("strMealThumb") else None,
            "image_small": meal.get("strMealThumb") + "/small" if meal.get("strMealThumb") else None,
            "tags": tags,
            "tag_count": len(tags),
            "youtube": meal.get("strYoutube"),
            "has_youtube": bool(meal.get("strYoutube")),
            "source": meal.get("strSource"),
            "has_source": bool(meal.get("strSource")),
            "drink_alternate": meal.get("strDrinkAlternate"),
            "date_modified": meal.get("dateModified"),
            "creative_commons_confirmed": meal.get("strCreativeCommonsConfirmed"),
            "image_source": meal.get("strImageSource")
        },
        "related_meals": {
            "by_category": related_by_category[:8],
            "by_area": related_by_area[:8],
            "total_related": len(related_by_category) + len(related_by_area)
        },
        "analysis": {
            "complexity_score": len(ingredients) + len(steps),
            "estimated_difficulty": "Easy" if len(ingredients) <= 6 else ("Medium" if len(ingredients) <= 12 else "Hard"),
            "estimated_prep_time_minutes": len([s for s in step_details if s.get('is_prep_step')]) * 3,
            "estimated_cook_time_minutes": len([s for s in step_details if s.get('is_cooking_step')]) * 8,
            "estimated_total_time_minutes": len(steps) * 5,
            "unique_techniques": list(set(t for s in step_details for t in s.get('cooking_techniques', []))),
            "technique_count": len(set(t for s in step_details for t in s.get('cooking_techniques', [])))
        },
        "nutrition_estimate": nutrition_estimate,
        "api_info": {
            "meal_id": meal_id,
            "endpoint": "/lookup.php",
            "api_version": "v1",
            "related_queries": 2
        }
    }


def _get_meals_by_category(category: str) -> dict:
    """Get meals in a specific category - ENHANCED VERBOSE V2."""
    data = _make_request("/filter.php", {"c": category})
    
    if "error" in data:
        return data
    
    meals = data.get("meals") or []
    
    results = []
    name_lengths = []
    first_words = {}
    name_words_dist = {}
    
    for meal in meals[:35]:  # VERBOSE V2: Increased to 35
        meal_name = meal.get("strMeal", "")
        meal_id = meal.get("idMeal", "")
        name_lengths.append(len(meal_name))
        
        # Track first words for analysis
        first_word = meal_name.split()[0] if meal_name else ""
        first_words[first_word] = first_words.get(first_word, 0) + 1
        
        # Track word count distribution
        word_count = len(meal_name.split())
        name_words_dist[word_count] = name_words_dist.get(word_count, 0) + 1
        
        results.append({
            "id": meal_id,
            "name": meal_name,
            "name_length": len(meal_name),
            "name_words": word_count,
            "name_first_word": first_word,
            "name_last_word": meal_name.split()[-1] if meal_name else "",
            "image": meal.get("strMealThumb"),
            "thumbnail": meal.get("strMealThumb") + "/preview" if meal.get("strMealThumb") else None,
            "image_small": meal.get("strMealThumb") + "/small" if meal.get("strMealThumb") else None,
            "lookup_url": f"https://www.themealdb.com/api/json/v1/1/lookup.php?i={meal_id}",
            "meal_page_url": f"https://www.themealdb.com/meal/{meal_id}",
            "category": category,
            "category_lower": category.lower()
        })
    
    # Get top first words
    top_first_words = dict(sorted(first_words.items(), key=lambda x: x[1], reverse=True)[:10])
    
    return {
        "success": True,
        "category": category,
        "category_lower": category.lower(),
        "category_description": f"Meals in the {category} category",
        "total_in_category": len(meals),
        "returned_count": len(results),
        "meals": results,
        "statistics": {
            "avg_name_length": round(sum(name_lengths) / len(name_lengths), 1) if name_lengths else 0,
            "min_name_length": min(name_lengths) if name_lengths else 0,
            "max_name_length": max(name_lengths) if name_lengths else 0,
            "total_meals_available": len(meals),
            "common_name_prefixes": top_first_words,
            "unique_first_words": len(first_words),
            "name_word_count_distribution": name_words_dist
        },
        "api_info": {
            "endpoint": "/filter.php",
            "filter_type": "category",
            "api_version": "v1",
            "category_param": category
        }
    }


def _get_meals_by_area(area: str) -> dict:
    """Get meals from a specific cuisine/area - ENHANCED VERBOSE V2."""
    data = _make_request("/filter.php", {"a": area})
    
    if "error" in data:
        return data
    
    meals = data.get("meals") or []
    
    results = []
    name_lengths = []
    first_words = {}
    name_words_dist = {}
    
    for meal in meals[:35]:  # VERBOSE V2: Increased to 35
        meal_name = meal.get("strMeal", "")
        meal_id = meal.get("idMeal", "")
        name_lengths.append(len(meal_name))
        
        # Track first words for analysis
        first_word = meal_name.split()[0] if meal_name else ""
        first_words[first_word] = first_words.get(first_word, 0) + 1
        
        # Track word count distribution
        word_count = len(meal_name.split())
        name_words_dist[word_count] = name_words_dist.get(word_count, 0) + 1
        
        results.append({
            "id": meal_id,
            "name": meal_name,
            "name_length": len(meal_name),
            "name_words": word_count,
            "name_first_word": first_word,
            "name_last_word": meal_name.split()[-1] if meal_name else "",
            "image": meal.get("strMealThumb"),
            "thumbnail": meal.get("strMealThumb") + "/preview" if meal.get("strMealThumb") else None,
            "image_small": meal.get("strMealThumb") + "/small" if meal.get("strMealThumb") else None,
            "lookup_url": f"https://www.themealdb.com/api/json/v1/1/lookup.php?i={meal_id}",
            "meal_page_url": f"https://www.themealdb.com/meal/{meal_id}",
            "cuisine": area,
            "area": area,
            "cuisine_region": area
        })
    
    # Get top first words
    top_first_words = dict(sorted(first_words.items(), key=lambda x: x[1], reverse=True)[:10])
    
    # Cuisine info mapping
    cuisine_info = {
        "Italian": {"region": "Europe", "famous_for": "pasta, pizza, risotto"},
        "French": {"region": "Europe", "famous_for": "sauces, pastries, wine"},
        "Japanese": {"region": "Asia", "famous_for": "sushi, ramen, tempura"},
        "Thai": {"region": "Asia", "famous_for": "curries, pad thai, tom yum"},
        "Indian": {"region": "Asia", "famous_for": "curries, tandoori, biryani"},
        "Mexican": {"region": "Americas", "famous_for": "tacos, burritos, enchiladas"},
        "Chinese": {"region": "Asia", "famous_for": "dim sum, stir-fry, noodles"},
        "British": {"region": "Europe", "famous_for": "fish and chips, pies, roasts"},
        "American": {"region": "Americas", "famous_for": "burgers, bbq, fried chicken"}
    }
    
    info = cuisine_info.get(area, {"region": "Unknown", "famous_for": "various dishes"})
    
    return {
        "success": True,
        "area": area,
        "area_lower": area.lower(),
        "cuisine_region": area,
        "geographic_region": info["region"],
        "cuisine_famous_for": info["famous_for"],
        "total_in_cuisine": len(meals),
        "returned_count": len(results),
        "meals": results,
        "statistics": {
            "avg_name_length": round(sum(name_lengths) / len(name_lengths), 1) if name_lengths else 0,
            "min_name_length": min(name_lengths) if name_lengths else 0,
            "max_name_length": max(name_lengths) if name_lengths else 0,
            "total_meals_available": len(meals),
            "common_name_prefixes": top_first_words,
            "unique_first_words": len(first_words),
            "name_word_count_distribution": name_words_dist
        },
        "api_info": {
            "endpoint": "/filter.php",
            "filter_type": "area",
            "api_version": "v1",
            "area_param": area
        }
    }


def _get_meals_by_ingredient(ingredient: str) -> dict:
    """Get meals that use a specific ingredient - ENHANCED VERBOSE."""
    data = _make_request("/filter.php", {"i": ingredient})
    
    if "error" in data:
        return data
    
    meals = data.get("meals") or []
    
    results = []
    name_lengths = []
    
    for meal in meals[:20]:  # VERBOSE: Increased to 20
        meal_name = meal.get("strMeal", "")
        meal_id = meal.get("idMeal", "")
        name_lengths.append(len(meal_name))
        
        # Check if ingredient appears in name
        ing_in_name = ingredient.lower() in meal_name.lower()
        
        results.append({
            "id": meal_id,
            "name": meal_name,
            "name_length": len(meal_name),
            "name_words": len(meal_name.split()),
            "ingredient_in_name": ing_in_name,
            "image": meal.get("strMealThumb"),
            "thumbnail": meal.get("strMealThumb") + "/preview" if meal.get("strMealThumb") else None,
            "lookup_url": f"https://www.themealdb.com/api/json/v1/1/lookup.php?i={meal_id}",
            "meal_page_url": f"https://www.themealdb.com/meal/{meal_id}",
            "main_ingredient": ingredient
        })
    
    # Count how many have ingredient in name
    ing_in_name_count = sum(1 for m in results if m.get('ingredient_in_name'))
    
    return {
        "success": True,
        "ingredient": ingredient,
        "ingredient_lower": ingredient.lower(),
        "ingredient_image": f"https://www.themealdb.com/images/ingredients/{ingredient}.png",
        "ingredient_thumbnail": f"https://www.themealdb.com/images/ingredients/{ingredient}-Small.png",
        "total_with_ingredient": len(meals),
        "returned_count": len(results),
        "meals": results,
        "statistics": {
            "avg_name_length": round(sum(name_lengths) / len(name_lengths), 1) if name_lengths else 0,
            "min_name_length": min(name_lengths) if name_lengths else 0,
            "max_name_length": max(name_lengths) if name_lengths else 0,
            "total_meals_available": len(meals),
            "meals_with_ingredient_in_name": ing_in_name_count,
            "name_match_ratio": round(ing_in_name_count / len(results), 2) if results else 0
        },
        "api_info": {
            "endpoint": "/filter.php",
            "filter_type": "ingredient",
            "api_version": "v1"
        }
    }


def _list_categories() -> dict:
    """List all meal categories - ENHANCED VERBOSE V2."""
    data = _make_request("/categories.php")
    
    if "error" in data:
        return data
    
    categories = data.get("categories") or []
    
    results = []
    total_desc_length = 0
    
    for cat in categories:
        cat_name = cat.get("strCategory", "")
        desc = cat.get("strCategoryDescription", "")
        total_desc_length += len(desc)
        
        # Get sample meals for this category (up to 5)
        sample_meals = []
        cat_data = _make_request("/filter.php", {"c": cat_name})
        if "meals" in cat_data and cat_data["meals"]:
            for m in cat_data["meals"][:5]:
                sample_meals.append({
                    "id": m.get("idMeal"),
                    "name": m.get("strMeal"),
                    "image": m.get("strMealThumb")
                })
        
        results.append({
            "id": cat.get("idCategory"),
            "name": cat_name,
            "name_lower": cat_name.lower(),
            "description": desc,
            "description_length": len(desc),
            "description_word_count": len(desc.split()),
            "description_preview": desc[:150] + "..." if len(desc) > 150 else desc,
            "image": cat.get("strCategoryThumb"),
            "thumbnail": cat.get("strCategoryThumb") + "/preview" if cat.get("strCategoryThumb") else None,
            "sample_meals": sample_meals,
            "sample_meal_count": len(sample_meals),
            "filter_url": f"https://www.themealdb.com/api/json/v1/1/filter.php?c={cat_name}"
        })
    
    return {
        "success": True,
        "count": len(categories),
        "total_categories": len(categories),
        "categories": results,
        "statistics": {
            "avg_description_length": round(total_desc_length / len(categories), 1) if categories else 0,
            "categories_with_samples": sum(1 for c in results if c.get('sample_meals')),
            "total_sample_meals": sum(len(c.get('sample_meals', [])) for c in results)
        },
        "api_info": {
            "endpoint": "/categories.php",
            "api_version": "v1"
        }
    }


# ============== Tool Handlers ==============

async def on_search_meal(context: RunContextWrapper, params_str: str) -> Any:
    """Handler for searching meals."""
    params = _parse_params(params_str)
    name = params.get("name")
    
    if not name:
        return {"error": "name is required", "success": False}
    
    result = _search_meal_by_name(name)
    return result


async def on_get_meal_details(context: RunContextWrapper, params_str: str) -> Any:
    """Handler for getting meal details."""
    params = _parse_params(params_str)
    meal_id = params.get("meal_id")
    
    if not meal_id:
        return {"error": "meal_id is required", "success": False}
    
    result = _get_meal_details(str(meal_id))
    return result


async def on_get_by_category(context: RunContextWrapper, params_str: str) -> Any:
    """Handler for getting meals by category."""
    params = _parse_params(params_str)
    category = params.get("category")
    
    if not category:
        return {"error": "category is required", "success": False}
    
    result = _get_meals_by_category(category)
    return result


async def on_get_by_area(context: RunContextWrapper, params_str: str) -> Any:
    """Handler for getting meals by area."""
    params = _parse_params(params_str)
    area = params.get("area")
    
    if not area:
        return {"error": "area is required", "success": False}
    
    result = _get_meals_by_area(area)
    return result


async def on_get_by_ingredient(context: RunContextWrapper, params_str: str) -> Any:
    """Handler for getting meals by ingredient."""
    params = _parse_params(params_str)
    ingredient = params.get("ingredient")
    
    if not ingredient:
        return {"error": "ingredient is required", "success": False}
    
    result = _get_meals_by_ingredient(ingredient)
    return result


async def on_list_categories(context: RunContextWrapper, params_str: str) -> Any:
    """Handler for listing categories."""
    result = _list_categories()
    return result


# ============== Tool Definitions ==============

tool_meal_search = FunctionTool(
    name='local-meal_search',
    description='''Search for meals by name.

**Returns:** dict:
{
  "success": bool,
  "query": str,
  "count": int,
  "meals": [{"id": str, "name": str, "category": str, "area": str, "image": str}]
}''',
    params_json_schema={
        "type": "object",
        "properties": {
            "name": {
                "type": "string",
                "description": "The name of the meal to search for (e.g., 'chicken', 'pasta')"
            }
        },
        "required": ["name"]
    },
    on_invoke_tool=on_search_meal
)

tool_meal_details = FunctionTool(
    name='local-meal_details',
    description='''Get detailed information about a specific meal including full recipe.

**Returns:** dict:
{
  "success": bool,
  "meal": {
    "id": str,
    "name": str,
    "category": str,
    "area": str,
    "instructions": str,
    "instruction_steps": [str],
    "ingredients": [{"ingredient": str, "measure": str}],
    "image": str,
    "tags": [str],
    "youtube": str | null,
    "source": str | null
  }
}''',
    params_json_schema={
        "type": "object",
        "properties": {
            "meal_id": {
                "type": "string",
                "description": "The ID of the meal"
            }
        },
        "required": ["meal_id"]
    },
    on_invoke_tool=on_get_meal_details
)

tool_meal_by_category = FunctionTool(
    name='local-meal_by_category',
    description='''Get meals in a specific category.

**Returns:** dict:
{
  "success": bool,
  "category": str,
  "count": int,
  "meals": [{"id": str, "name": str, "image": str}]
}''',
    params_json_schema={
        "type": "object",
        "properties": {
            "category": {
                "type": "string",
                "description": "The category (e.g., 'Beef', 'Chicken', 'Seafood', 'Vegetarian')"
            }
        },
        "required": ["category"]
    },
    on_invoke_tool=on_get_by_category
)

tool_meal_by_area = FunctionTool(
    name='local-meal_by_area',
    description='''Get meals from a specific cuisine/area.

**Returns:** dict:
{
  "success": bool,
  "area": str,
  "count": int,
  "meals": [{"id": str, "name": str, "image": str}]
}''',
    params_json_schema={
        "type": "object",
        "properties": {
            "area": {
                "type": "string",
                "description": "The cuisine area (e.g., 'Italian', 'Mexican', 'Japanese', 'Chinese')"
            }
        },
        "required": ["area"]
    },
    on_invoke_tool=on_get_by_area
)

tool_meal_by_ingredient = FunctionTool(
    name='local-meal_by_ingredient',
    description='''Get meals that use a specific main ingredient.

**Returns:** dict:
{
  "success": bool,
  "ingredient": str,
  "count": int,
  "meals": [{"id": str, "name": str, "image": str}]
}''',
    params_json_schema={
        "type": "object",
        "properties": {
            "ingredient": {
                "type": "string",
                "description": "The main ingredient (e.g., 'chicken', 'beef', 'salmon')"
            }
        },
        "required": ["ingredient"]
    },
    on_invoke_tool=on_get_by_ingredient
)

tool_meal_categories = FunctionTool(
    name='local-meal_list_categories',
    description='''List all available meal categories with descriptions.

**Returns:** dict:
{
  "success": bool,
  "count": int,
  "categories": [{"id": str, "name": str, "description": str, "image": str}]
}''',
    params_json_schema={
        "type": "object",
        "properties": {}
    },
    on_invoke_tool=on_list_categories
)


# Export all tools as a list
mealdb_tools = [
    tool_meal_search,
    tool_meal_details,
    tool_meal_by_category,
    tool_meal_by_area,
    tool_meal_by_ingredient,
    tool_meal_categories,
]

