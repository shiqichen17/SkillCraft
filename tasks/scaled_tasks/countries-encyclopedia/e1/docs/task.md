# Task: World Countries Encyclopedia (Easy - 3 Regions × 3 APIs)

Generate a comprehensive encyclopedia of world countries by analyzing **3 major regions**.

## Objective

For each of the following **3 regions**, collect and summarize:
1. **Region Summary**: Total countries, population, area
2. **Top 3 Countries**: Detailed info for the 3 most populous countries
3. **Border Summary**: Neighbor statistics, landlocked count

Then generate a global summary with regional comparisons.

## Regions to Analyze

| # | Region | Description |
|---|--------|-------------|
| 1 | Europe | Western civilization hub |
| 2 | Asia | Most populous continent |
| 3 | Americas | North & South America |

## Required Output

Save results to `countries_encyclopedia.json`:

```json
{
  "regions": [
    {
      "name": "Europe",
      "summary": {
        "country_count": 44,
        "total_population": 750000000,
        "total_area_km2": 10180000,
        "subregions": ["Northern Europe", "Western Europe", "Southern Europe", "Eastern Europe"]
      },
      "top_countries": [
        {
          "name": "Germany",
          "official_name": "Federal Republic of Germany",
          "capital": "Berlin",
          "population": 83200000,
          "area": 357114,
          "languages": ["German"],
          "currencies": [{"code": "EUR", "name": "Euro"}],
          "border_count": 9,
          "flag_emoji": "🇩🇪"
        }
      ],
      "border_analysis": {
        "total_borders": 100,
        "most_neighbors": {"country": "Germany", "count": 9},
        "landlocked_count": 5,
        "island_nations_count": 3
      }
    }
  ],
  "global_summary": {
    "total_regions": 3,
    "total_countries": 130,
    "total_world_population": 6500000000,
    "largest_region": {"name": "Asia", "countries": 48, "population": 4700000000}
  },
  "analysis_date": "2024-01-15"
}
```

## Tools Available

**Data Collection Tools:**
- `local-countries_get_region`: Get all countries in a region
- `local-countries_get_details`: Get comprehensive country details
- `local-countries_get_borders`: Get info about neighboring countries

**File System Tools:**
- `filesystem-write_file`: Write output JSON to file (**USE THIS, NOT "write_file"**)
- `filesystem-read_file`: Read files from workspace

**Task Completion:**
- `local-claim_done`: Signal task completion (REQUIRED at the end)

## Workflow

For each region:
1. `local-countries_get_region` - Count countries, sum population, select top 3
2. `local-countries_get_details` - Get details for top 3 countries
3. `local-countries_get_borders` - Count borders, find most neighbors

Process all 3 regions and compile global summary.

## Important Notes

1. Process ALL 3 regions completely - do NOT use placeholder data
2. Use skill mode to optimize repeated API calls
3. **Summarize country lists** - store counts and top 3 only
4. Handle API errors gracefully (mark as "unavailable" if region not found)

## REQUIRED: Task Completion Protocol

1. **FIRST**: Collect all data for all 3 regions
2. **SECOND**: Write results to `countries_encyclopedia.json` using `filesystem-write_file`
3. **THIRD**: Call `local-claim_done` to signal completion

**DO NOT stop without calling `claim_done`!**
