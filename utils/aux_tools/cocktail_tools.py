"""
TheCocktailDB API Tools

Provides tools to query cocktail recipes and ingredients.
Designed for skill mode scenarios with structured recipe data.

API Documentation: https://www.thecocktaildb.com/api.php
Free tier available with limited requests.
"""

import json
from typing import Any
from agents.tool import FunctionTool, RunContextWrapper
import requests

# Base URL for TheCocktailDB API
COCKTAIL_BASE_URL = "https://www.thecocktaildb.com/api/json/v1/1"


def _make_request(endpoint: str, params: dict = None) -> dict:
    """Make a request to TheCocktailDB API with error handling."""
    url = f"{COCKTAIL_BASE_URL}{endpoint}"
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


def _extract_ingredients(drink: dict) -> list:
    """Extract ingredients and measures from a drink."""
    ingredients = []
    for i in range(1, 16):
        ingredient = drink.get(f"strIngredient{i}")
        measure = drink.get(f"strMeasure{i}")
        if ingredient and ingredient.strip():
            ingredients.append({
                "ingredient": ingredient.strip(),
                "measure": measure.strip() if measure else "to taste"
            })
    return ingredients


# ============== Tool Implementation Functions ==============

def _search_cocktail_by_name(name: str) -> dict:
    """Search for cocktails by name with extended data."""
    data = _make_request("/search.php", {"s": name})
    
    if "error" in data:
        return data
    
    drinks = data.get("drinks") or []
    
    results = []
    category_counts = {}
    glass_counts = {}
    
    for drink in drinks[:8]:  # Limit to 8
        ingredients = _extract_ingredients(drink)
        category = drink.get("strCategory", "Unknown")
        glass = drink.get("strGlass", "Unknown")
        
        category_counts[category] = category_counts.get(category, 0) + 1
        glass_counts[glass] = glass_counts.get(glass, 0) + 1
        
        results.append({
            "id": drink.get("idDrink"),
            "name": drink.get("strDrink"),
            "category": category,
            "glass": glass,
            "alcoholic": drink.get("strAlcoholic"),
            "image": drink.get("strDrinkThumb"),
            "iba": drink.get("strIBA"),
            "tags": drink.get("strTags", "").split(",") if drink.get("strTags") else [],
            "ingredient_count": len(ingredients),
            "main_ingredients": [ing["ingredient"] for ing in ingredients[:3]],
            "instructions_preview": (drink.get("strInstructions") or "")[:150] + "..." if drink.get("strInstructions") and len(drink.get("strInstructions", "")) > 150 else drink.get("strInstructions"),
            "date_modified": drink.get("dateModified")
        })
    
    return {
        "success": True,
        "query": name,
        "summary": {
            "total_matches": len(drinks),
            "returned_count": len(results),
            "category_distribution": category_counts,
            "glass_distribution": glass_counts,
            "has_iba_cocktails": any(c.get("iba") for c in results)
        },
        "cocktails": results
    }


def _get_cocktail_details(cocktail_id: str) -> dict:
    """Get detailed information about a specific cocktail with VERBOSE data for skill mode."""
    data = _make_request("/lookup.php", {"i": cocktail_id})
    
    if "error" in data:
        return data
    
    drinks = data.get("drinks") or []
    if not drinks:
        return {"error": "Cocktail not found", "success": False}
    
    drink = drinks[0]
    ingredients = _extract_ingredients(drink)
    
    # Calculate complexity based on ingredients
    complexity = "Simple" if len(ingredients) <= 3 else "Moderate" if len(ingredients) <= 5 else "Complex"
    
    # Determine if it's a classic/standard cocktail
    is_iba = drink.get("strIBA") is not None and drink.get("strIBA") != ""
    
    # VERBOSE: Get detailed info for each ingredient
    ingredient_details = []
    for ing in ingredients:
        ing_name = ing.get("ingredient", "")
        if ing_name:
            ing_data = _make_request("/search.php", {"i": ing_name})
            ing_info = None
            if ing_data.get("ingredients"):
                ing_raw = ing_data["ingredients"][0]
                ing_info = {
                    "id": ing_raw.get("idIngredient"),
                    "name": ing_raw.get("strIngredient"),
                    "type": ing_raw.get("strType"),
                    "is_alcoholic": ing_raw.get("strAlcohol") == "Yes",
                    "abv": ing_raw.get("strABV"),
                    "description_preview": (ing_raw.get("strDescription") or "")[:200]
                }
            ingredient_details.append({
                "ingredient": ing.get("ingredient"),
                "measure": ing.get("measure"),
                "details": ing_info
            })
    
    # VERBOSE: Get similar cocktails using same primary ingredient
    similar_cocktails = []
    if ingredients:
        main_ing = ingredients[0].get("ingredient")
        if main_ing:
            similar_data = _make_request("/filter.php", {"i": main_ing})
            similar_drinks = similar_data.get("drinks") or []
            for sim in similar_drinks[:10]:
                if sim.get("idDrink") != cocktail_id:
                    similar_cocktails.append({
                        "id": sim.get("idDrink"),
                        "name": sim.get("strDrink"),
                        "image": sim.get("strDrinkThumb")
                    })
    
    return {
        "success": True,
        "cocktail": {
            "id": drink.get("idDrink"),
            "name": drink.get("strDrink"),
            "alternate_name": drink.get("strDrinkAlternate"),
            "category": drink.get("strCategory"),
            "alcoholic": drink.get("strAlcoholic"),
            "glass": drink.get("strGlass"),
            "iba": drink.get("strIBA"),
            "tags": drink.get("strTags", "").split(",") if drink.get("strTags") else [],
            "instructions": {
                "en": drink.get("strInstructions"),
                "es": drink.get("strInstructionsES"),
                "de": drink.get("strInstructionsDE"),
                "fr": drink.get("strInstructionsFR"),
                "it": drink.get("strInstructionsIT"),
                "zh-hans": drink.get("strInstructionsZH-HANS"),
                "zh-hant": drink.get("strInstructionsZH-HANT")
            },
            "ingredients": ingredients,
            "ingredient_details": ingredient_details,
            "media": {
                "image": drink.get("strDrinkThumb"),
                "image_preview": f"{drink.get('strDrinkThumb')}/preview" if drink.get("strDrinkThumb") else None,
                "video": drink.get("strVideo"),
                "creative_commons_confirmed": drink.get("strCreativeCommonsConfirmed"),
                "image_source": drink.get("strImageSource"),
                "image_attribution": drink.get("strImageAttribution")
            },
            "metadata": {
                "complexity": complexity,
                "ingredient_count": len(ingredients),
                "is_iba_official": is_iba,
                "date_modified": drink.get("dateModified"),
                "api_url": f"https://www.thecocktaildb.com/api/json/v1/1/lookup.php?i={cocktail_id}"
            },
            "similar_cocktails": similar_cocktails
        }
    }


def _get_cocktails_by_ingredient(ingredient: str) -> dict:
    """Get cocktails that use a specific ingredient with extended data."""
    data = _make_request("/filter.php", {"i": ingredient})
    
    if "error" in data:
        return data
    
    drinks = data.get("drinks") or []
    
    results = []
    for drink in drinks[:15]:  # Limit to 15
        results.append({
            "id": drink.get("idDrink"),
            "name": drink.get("strDrink"),
            "image": drink.get("strDrinkThumb"),
            "thumbnail_small": f"{drink.get('strDrinkThumb')}/preview" if drink.get("strDrinkThumb") else None
        })
    
    # Categorize by name patterns
    classic_patterns = ["Martini", "Daiquiri", "Margarita", "Manhattan", "Negroni", "Sour"]
    classics = [d for d in results if any(p.lower() in d["name"].lower() for p in classic_patterns)]
    
    return {
        "success": True,
        "ingredient": ingredient,
        "summary": {
            "total_cocktails": len(drinks),
            "returned_count": len(results),
            "is_popular_ingredient": len(drinks) > 20,
            "classics_featuring_ingredient": len(classics)
        },
        "classic_cocktails": [{"id": c["id"], "name": c["name"]} for c in classics],
        "cocktails": results
    }


def _get_cocktails_by_category(category: str) -> dict:
    """Get cocktails in a specific category with extended data."""
    data = _make_request("/filter.php", {"c": category})
    
    if "error" in data:
        return data
    
    drinks = data.get("drinks") or []
    
    results = []
    for drink in drinks[:15]:  # Limit to 15
        results.append({
            "id": drink.get("idDrink"),
            "name": drink.get("strDrink"),
            "image": drink.get("strDrinkThumb"),
            "thumbnail_small": f"{drink.get('strDrinkThumb')}/preview" if drink.get("strDrinkThumb") else None
        })
    
    # Determine category type
    category_types = {
        "Ordinary Drink": "standard",
        "Cocktail": "classic",
        "Shot": "shot",
        "Punch / Party Drink": "party",
        "Coffee / Tea": "hot",
        "Beer": "beer",
        "Soft Drink": "non-alcoholic"
    }
    
    return {
        "success": True,
        "category": category,
        "summary": {
            "total_in_category": len(drinks),
            "returned_count": len(results),
            "category_type": category_types.get(category, "other"),
            "is_large_category": len(drinks) > 50,
            "sample_names": [d["name"] for d in results[:5]]
        },
        "cocktails": results
    }


def _get_ingredient_info(ingredient: str) -> dict:
    """Get information about a specific ingredient with extended data."""
    data = _make_request("/search.php", {"i": ingredient})
    
    if "error" in data:
        return data
    
    ingredients = data.get("ingredients") or []
    if not ingredients:
        return {"error": "Ingredient not found", "success": False}
    
    ing = ingredients[0]
    
    # Get cocktails using this ingredient
    cocktails_data = _make_request("/filter.php", {"i": ingredient})
    cocktails_list = cocktails_data.get("drinks") or [] if "error" not in cocktails_data else []
    
    # Determine ingredient category
    ing_type = ing.get("strType", "")
    is_alcoholic = ing.get("strAlcohol") == "Yes"
    abv = ing.get("strABV")
    
    if is_alcoholic and abv:
        try:
            abv_val = float(abv.replace("%", ""))
            if abv_val >= 35:
                strength = "Strong Spirit"
            elif abv_val >= 15:
                strength = "Medium Strength"
            else:
                strength = "Light Alcohol"
        except:
            strength = "Alcoholic"
    elif is_alcoholic:
        strength = "Alcoholic"
    else:
        strength = "Non-Alcoholic"
    
    description = ing.get("strDescription", "") or ""
    
    return {
        "success": True,
        "ingredient": {
            "id": ing.get("idIngredient"),
            "name": ing.get("strIngredient"),
            "type": ing_type,
            "alcohol": {
                "is_alcoholic": is_alcoholic,
                "abv": abv,
                "strength_category": strength
            },
            "description": {
                "full": description[:800] if description else None,
                "preview": description[:200] + "..." if len(description) > 200 else description if description else None,
                "word_count": len(description.split()) if description else 0
            },
            "usage": {
                "total_cocktails": len(cocktails_list),
                "is_common_ingredient": len(cocktails_list) > 30,
                "sample_cocktails": [{"id": c.get("idDrink"), "name": c.get("strDrink")} for c in cocktails_list[:5]]
            },
            "metadata": {
                "image_url": f"https://www.thecocktaildb.com/images/ingredients/{ingredient}-Medium.png",
                "api_url": f"https://www.thecocktaildb.com/api/json/v1/1/search.php?i={ingredient}"
            }
        }
    }


# ============== Tool Handlers ==============

async def on_search_cocktail(context: RunContextWrapper, params_str: str) -> Any:
    """Handler for searching cocktails."""
    params = _parse_params(params_str)
    name = params.get("name")
    
    if not name:
        return {"error": "name is required", "success": False}
    
    result = _search_cocktail_by_name(name)
    return result


async def on_get_cocktail_details(context: RunContextWrapper, params_str: str) -> Any:
    """Handler for getting cocktail details."""
    params = _parse_params(params_str)
    cocktail_id = params.get("cocktail_id")
    
    if not cocktail_id:
        return {"error": "cocktail_id is required", "success": False}
    
    result = _get_cocktail_details(str(cocktail_id))
    return result


async def on_get_by_ingredient(context: RunContextWrapper, params_str: str) -> Any:
    """Handler for getting cocktails by ingredient."""
    params = _parse_params(params_str)
    ingredient = params.get("ingredient")
    
    if not ingredient:
        return {"error": "ingredient is required", "success": False}
    
    result = _get_cocktails_by_ingredient(ingredient)
    return result


async def on_get_by_category(context: RunContextWrapper, params_str: str) -> Any:
    """Handler for getting cocktails by category."""
    params = _parse_params(params_str)
    category = params.get("category")
    
    if not category:
        return {"error": "category is required", "success": False}
    
    result = _get_cocktails_by_category(category)
    return result


async def on_get_ingredient_info(context: RunContextWrapper, params_str: str) -> Any:
    """Handler for getting ingredient info."""
    params = _parse_params(params_str)
    ingredient = params.get("ingredient")
    
    if not ingredient:
        return {"error": "ingredient is required", "success": False}
    
    result = _get_ingredient_info(ingredient)
    return result


# ============== Tool Definitions ==============

tool_cocktail_search = FunctionTool(
    name='local-cocktail_search',
    description='''Search for cocktails by name with extended data.

**Returns:** dict:
{
  "success": bool,
  "query": str,
  "summary": {
    "total_matches": int,
    "returned_count": int,
    "category_distribution": {"Cocktail": int, "Ordinary Drink": int, ...},
    "glass_distribution": {"Cocktail glass": int, "Highball glass": int, ...},
    "has_iba_cocktails": bool
  },
  "cocktails": [
    {
      "id": str,
      "name": str,
      "category": str,
      "glass": str,
      "alcoholic": str,
      "image": str,
      "iba": str | null,
      "tags": [str],
      "ingredient_count": int,
      "main_ingredients": [str],
      "instructions_preview": str,
      "date_modified": str | null
    }
  ]
}''',
    params_json_schema={
        "type": "object",
        "properties": {
            "name": {
                "type": "string",
                "description": "The name of the cocktail to search for (e.g., 'margarita', 'mojito')"
            }
        },
        "required": ["name"]
    },
    on_invoke_tool=on_search_cocktail
)

tool_cocktail_details = FunctionTool(
    name='local-cocktail_details',
    description='''Get detailed information about a specific cocktail including full recipe with multilingual instructions.

**Returns:** dict:
{
  "success": bool,
  "cocktail": {
    "id": str,
    "name": str,
    "alternate_name": str | null,
    "category": str,
    "alcoholic": str,
    "glass": str,
    "iba": str | null,
    "tags": [str],
    "instructions": {
      "en": str,
      "es": str | null,
      "de": str | null,
      "fr": str | null,
      "it": str | null
    },
    "ingredients": [{"ingredient": str, "measure": str}],
    "media": {
      "image": str,
      "video": str | null,
      "creative_commons_confirmed": str | null
    },
    "metadata": {
      "complexity": str,           // "Simple", "Moderate", "Complex"
      "ingredient_count": int,
      "is_iba_official": bool,
      "date_modified": str | null,
      "api_url": str
    }
  }
}''',
    params_json_schema={
        "type": "object",
        "properties": {
            "cocktail_id": {
                "type": "string",
                "description": "The ID of the cocktail"
            }
        },
        "required": ["cocktail_id"]
    },
    on_invoke_tool=on_get_cocktail_details
)

tool_cocktail_by_ingredient = FunctionTool(
    name='local-cocktail_by_ingredient',
    description='''Get cocktails that use a specific ingredient with extended data.

**Returns:** dict:
{
  "success": bool,
  "ingredient": str,
  "summary": {
    "total_cocktails": int,
    "returned_count": int,
    "is_popular_ingredient": bool,
    "classics_featuring_ingredient": int
  },
  "classic_cocktails": [{"id": str, "name": str}],
  "cocktails": [
    {
      "id": str,
      "name": str,
      "image": str,
      "thumbnail_small": str | null
    }
  ]
}''',
    params_json_schema={
        "type": "object",
        "properties": {
            "ingredient": {
                "type": "string",
                "description": "The ingredient to search for"
            }
        },
        "required": ["ingredient"]
    },
    on_invoke_tool=on_get_by_ingredient
)

tool_cocktail_by_category = FunctionTool(
    name='local-cocktail_by_category',
    description='''Get cocktails in a specific category with extended data.

**Returns:** dict:
{
  "success": bool,
  "category": str,
  "summary": {
    "total_in_category": int,
    "returned_count": int,
    "category_type": str,            // "standard", "classic", "shot", "party", "hot", etc.
    "is_large_category": bool,
    "sample_names": [str]
  },
  "cocktails": [
    {
      "id": str,
      "name": str,
      "image": str,
      "thumbnail_small": str | null
    }
  ]
}''',
    params_json_schema={
        "type": "object",
        "properties": {
            "category": {
                "type": "string",
                "description": "The category (e.g., 'Ordinary Drink', 'Cocktail', 'Shot')"
            }
        },
        "required": ["category"]
    },
    on_invoke_tool=on_get_by_category
)

tool_ingredient_info = FunctionTool(
    name='local-cocktail_ingredient_info',
    description='''Get information about a specific cocktail ingredient with extended data.

**Returns:** dict:
{
  "success": bool,
  "ingredient": {
    "id": str,
    "name": str,
    "type": str,
    "alcohol": {
      "is_alcoholic": bool,
      "abv": str | null,
      "strength_category": str      // "Strong Spirit", "Medium Strength", "Light Alcohol", "Non-Alcoholic"
    },
    "description": {
      "full": str | null,
      "preview": str | null,
      "word_count": int
    },
    "usage": {
      "total_cocktails": int,
      "is_common_ingredient": bool,
      "sample_cocktails": [{"id": str, "name": str}]
    },
    "metadata": {
      "image_url": str,
      "api_url": str
    }
  }
}''',
    params_json_schema={
        "type": "object",
        "properties": {
            "ingredient": {
                "type": "string",
                "description": "The ingredient name (e.g., 'Vodka', 'Triple sec')"
            }
        },
        "required": ["ingredient"]
    },
    on_invoke_tool=on_get_ingredient_info
)


# Export all tools as a list
cocktail_tools = [
    tool_cocktail_search,
    tool_cocktail_details,
    tool_cocktail_by_ingredient,
    tool_cocktail_by_category,
    tool_ingredient_info,
]

