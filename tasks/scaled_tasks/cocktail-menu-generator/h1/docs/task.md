# Task: Cocktail Menu (5 Cocktails × 5 APIs) - H1

Create cocktail menu for **5 classic cocktails** using 5 API endpoints per cocktail.

## Objective

For each of the following **5 cocktails**, collect:
1. **Search**: find cocktail by name
2. **Details**: full recipe and instructions
3. **By Ingredient**: list cocktails using ingredient
4. **Ingredient Info**: spirit/ingredient details
5. **By Category**: list cocktails in category

Calculate **complexity rating** and **prep time** for each cocktail.

## Cocktails to Include

| # | Cocktail | Search Name |
|---|----------|-------------|
| 1 | Margarita | margarita |
| 2 | Mojito | mojito |
| 3 | Old Fashioned | old fashioned |
| 4 | Martini | martini |
| 5 | Cosmopolitan | cosmopolitan |

## Required Output

Save results to `cocktail_menu.json`:

```json
{
  "cocktails": [
    {"name": "Margarita", "category": "Ordinary Drink", "glass": "Cocktail glass", "ingredient_count": 4, "complexity_rating": "Medium", "estimated_prep_time_min": 5}
  ],
  "summary": {"total_cocktails": 5, "avg_ingredient_count": 4.5},
  "analysis_date": "2024-01-15"
}
```

## Tools Available

- `local-cocktail_search`: Search
- `local-cocktail_details`: Details
- `local-cocktail_by_ingredient`: By Ingredient
- `local-cocktail_ingredient_info`: Ingredient Info
- `local-cocktail_by_category`: By Category

**File System:** `filesystem-write_file`, `filesystem-read_file`
**Completion:** `local-claim_done` (REQUIRED)

## Workflow

For each cocktail (Margarita, Mojito, Old Fashioned, Martini, Cosmopolitan):
1. `local-cocktail_search`
2. `local-cocktail_details`
3. `local-cocktail_by_ingredient`
4. `local-cocktail_ingredient_info`
5. `local-cocktail_by_category`

## Complexity Rating

- **Easy**: <= 3 ingredients, no special technique
- **Medium**: 4-5 ingredients, basic mixing
- **Complex**: 6+ ingredients or special technique

## Summary Requirements

**⚠️ CRITICAL**: For similar cocktails, output only count and top 3!

## Important

1. Process ALL 5 cocktails completely
2. Summarize similar cocktails - count and top 3 only
3. Call `local-claim_done` to complete
