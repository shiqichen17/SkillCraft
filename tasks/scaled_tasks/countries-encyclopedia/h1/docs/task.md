# Task: World Countries Encyclopedia (Hard - 5 Regions × 5 APIs)

Generate a comprehensive encyclopedia of world countries by analyzing **5 major regions** and **summarizing** their key statistics.

## Objective

For each of the following **5 regions**, collect and **summarize**:
1. **Region Summary**: Total countries, population, area (NOT full country list)
2. **Top 3 Countries**: Detailed info for the 3 most populous countries only
3. **Border Summary**: Neighbor statistics, landlocked count
4. **Currency Summary**: Main currencies and country counts
5. **Language Summary**: Major languages and speaker counts

Then generate a global summary with regional comparisons.

## Regions to Analyze

| # | Region | Major Currency | Major Language |
|---|--------|---------------|----------------|
| 1 | Europe | EUR | english |
| 2 | Asia | CNY | arabic |
| 3 | Africa | XOF | french |
| 4 | Americas | USD | spanish |
| 5 | Oceania | AUD | english |

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
        "un_members": 43,
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
      },
      "currency_analysis": {
        "currency": "EUR",
        "countries_using": 19,
        "total_population_using": 340000000
      },
      "language_analysis": {
        "language": "english",
        "countries_speaking": 5,
        "total_speakers": 70000000
      }
    }
  ],
  "global_summary": {
    "total_regions": 5,
    "total_countries": 195,
    "total_world_population": 8000000000,
    "largest_region": {"name": "Asia", "countries": 48, "population": 4700000000},
    "smallest_region": {"name": "Oceania", "countries": 14, "population": 45000000},
    "most_populous_country": {"name": "China", "population": 1400000000}
  },
  "analysis_date": "2024-01-15"
}
```

## Summary Requirements

**⚠️ CRITICAL**: Output ONLY summaries and top countries, NOT full country lists!

| Data Type | Tool Returns | Required Output |
|-----------|-------------|-----------------|
| Countries | 14-54 per region | country_count, population sum, top 3 only |
| Borders | All border relationships | total count, most_neighbors, landlocked_count |
| Currencies | Countries per currency | count of countries using target currency |

## Tools Available

**Data Collection Tools:**
- `local-countries_get_region`: Get all countries in a region (returns 14-54 countries)
- `local-countries_get_details`: Get comprehensive country details
- `local-countries_get_borders`: Get info about neighboring countries
- `local-countries_get_by_currency`: Get countries using a currency
- `local-countries_get_by_language`: Get countries speaking a language

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
4. `local-countries_get_by_currency` - Count countries using major currency
5. `local-countries_get_by_language` - Count countries speaking major language

Process all 5 regions and compile global summary.

## Important Notes

1. Process ALL 5 regions completely - do NOT use placeholder data
2. Use skill mode to optimize repeated API calls
3. **Summarize country lists** - store counts and top 3 only
4. Sort countries by population when selecting "top countries"
5. Handle API errors gracefully (mark as "unavailable" if region not found)

## REQUIRED: Task Completion Protocol

**You MUST follow this exact sequence to complete the task:**

1. **FIRST**: Collect all data for all 5 regions
2. **SECOND**: Write the complete results to `countries_encyclopedia.json` using `filesystem-write_file`
3. **THIRD**: Call `local-claim_done` to signal task completion

**CRITICAL WARNINGS:**
- **DO NOT stop after saving the file** - you MUST call `local-claim_done`!
- **The task is NOT complete until `claim_done` is called**
- **If you don't call `claim_done`, the task will be marked as FAILED**
