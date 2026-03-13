# Task: Cocktail Menu (4 Cocktails × 4 APIs) - M2

Create cocktail menu for **4 classic cocktails** using 4 API endpoints per cocktail.

## Objective

For each of the following **4 cocktails**, collect:
1. **Details**: full recipe and instructions
2. **By Ingredient**: list cocktails using ingredient
3. **Ingredient Info**: spirit/ingredient details
4. **By Category**: list cocktails in category

Calculate **complexity rating** and **prep time** for each cocktail.

## Cocktails to Include

| # | Cocktail | Search Name |
|---|----------|-------------|
| 1 | Margarita | margarita |
| 2 | Mojito | mojito |
| 3 | Old Fashioned | old fashioned |
| 4 | Martini | martini |

## Required Output

Save results to `cocktail_menu.json`:

```json
{
  "cocktails": [
    {"name": "Margarita", "category": "Ordinary Drink", "glass": "Cocktail glass", "ingredient_count": 4, "complexity_rating": "Medium", "estimated_prep_time_min": 5}
  ],
  "summary": {"total_cocktails": 4, "avg_ingredient_count": 4.5},
  "analysis_date": "2024-01-15"
}
```

## Tools Available

- `local-cocktail_details`: Details
- `local-cocktail_by_ingredient`: By Ingredient
- `local-cocktail_ingredient_info`: Ingredient Info
- `local-cocktail_by_category`: By Category

**File System:** `filesystem-write_file`, `filesystem-read_file`
**Completion:** `local-claim_done` (REQUIRED)

## Workflow

For each cocktail (Margarita, Mojito, Old Fashioned, Martini):
1. `local-cocktail_details`
2. `local-cocktail_by_ingredient`
3. `local-cocktail_ingredient_info`
4. `local-cocktail_by_category`

## Complexity Rating

- **Easy**: <= 3 ingredients, no special technique
- **Medium**: 4-5 ingredients, basic mixing
- **Complex**: 6+ ingredients or special technique

## Summary Requirements

**⚠️ CRITICAL**: For similar cocktails, output only count and top 3!

## Important

1. Process ALL 4 cocktails completely
2. Summarize similar cocktails - count and top 3 only
3. Call `local-claim_done` to complete
