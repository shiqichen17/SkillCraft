# Task: Recipe Cookbook (3 Dishes × 3 APIs) - E1

Create cookbook with **3 international dishes** using 3 API endpoints per dish.

## Objective

For each of the following **3 dishes**, collect:
1. **Search**: find meal by name
2. **By Category**: list meals in category
3. **By Area**: list meals by cuisine

Calculate **difficulty rating** and **cooking time** for each dish.

## Dishes to Include

| # | Dish | Search Name | Cuisine |
|---|------|-------------|---------|
| 1 | Spaghetti Carbonara | carbonara | Italian |
| 2 | Tandoori Chicken | tandoori | Indian |
| 3 | Pad Thai | pad thai | Thai |

## Required Output

Save results to `recipe_cookbook.json`:

```json
{
  "recipes": [
    {"name": "Spaghetti Carbonara", "category": "Pasta", "cuisine": "Italian", "ingredient_count": 8, "difficulty_rating": "Medium", "estimated_cooking_time_min": 30}
  ],
  "summary": {"total_recipes": 3, "cuisines_covered": ['Italian', 'Indian', 'Thai']},
  "analysis_date": "2024-01-15"
}
```

## Tools Available

- `local-meal_search`: Search
- `local-meal_by_category`: By Category
- `local-meal_by_area`: By Area

**File System:** `filesystem-write_file`, `filesystem-read_file`
**Completion:** `local-claim_done` (REQUIRED)

## Workflow

For each dish (Spaghetti Carbonara, Tandoori Chicken, Pad Thai):
1. `local-meal_search`
2. `local-meal_by_category`
3. `local-meal_by_area`

## Difficulty Rating

- **Easy**: <= 5 ingredients, basic cooking
- **Medium**: 6-10 ingredients, moderate technique
- **Hard**: 10+ ingredients or advanced technique

## Important

1. Process ALL 3 dishes completely
2. Summarize related dishes - count and top 3 only
3. Call `local-claim_done` to complete
