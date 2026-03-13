# Task: Cocktail Menu (3 Cocktails × 3 APIs) - E1

Create cocktail menu for **3 classic cocktails** using 3 API endpoints per cocktail.

## Objective

For each of the following **3 cocktails**, collect:
1. **Search**: find cocktail by name
2. **By Ingredient**: list cocktails using ingredient
3. **Ingredient Info**: spirit/ingredient details

Calculate **complexity rating** and **prep time** for each cocktail.

## Cocktails to Include

| # | Cocktail | Search Name |
|---|----------|-------------|
| 1 | Margarita | margarita |
| 2 | Mojito | mojito |
| 3 | Old Fashioned | old fashioned |

## Required Output

Save results to `cocktail_menu.json`:

```json
{
  "cocktails": [
    {"name": "Margarita", "category": "Ordinary Drink", "glass": "Cocktail glass", "ingredient_count": 4, "complexity_rating": "Medium", "estimated_prep_time_min": 5}
  ],
  "summary": {"total_cocktails": 3, "avg_ingredient_count": 4.5},
  "analysis_date": "2024-01-15"
}
```

## Tools Available

- `local-cocktail_search`: Search
- `local-cocktail_by_ingredient`: By Ingredient
- `local-cocktail_ingredient_info`: Ingredient Info

**File System:** `filesystem-write_file`, `filesystem-read_file`
**Completion:** `local-claim_done` (REQUIRED)

## Workflow

For each cocktail (Margarita, Mojito, Old Fashioned):
1. `local-cocktail_search`
2. `local-cocktail_by_ingredient`
3. `local-cocktail_ingredient_info`

## Complexity Rating

- **Easy**: <= 3 ingredients, no special technique
- **Medium**: 4-5 ingredients, basic mixing
- **Complex**: 6+ ingredients or special technique

## Summary Requirements

**⚠️ CRITICAL**: For similar cocktails, output only count and top 3!

## Important

1. Process ALL 3 cocktails completely
2. Summarize similar cocktails - count and top 3 only
3. Call `local-claim_done` to complete
