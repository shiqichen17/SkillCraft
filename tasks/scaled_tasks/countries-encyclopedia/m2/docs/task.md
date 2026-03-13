# Task: World Countries Encyclopedia - Linguistic Focus (Medium - 4 Regions × 4 APIs)

Generate a comprehensive encyclopedia of world countries by analyzing **4 major regions** with linguistic focus.

## Objective

For each of the following **4 regions**, collect and summarize:
1. **Region Summary**: Total countries, population, area
2. **Top 3 Countries**: Detailed info for the 3 most populous countries
3. **Border Summary**: Neighbor statistics, landlocked count
4. **Language Summary**: Major language speakers and distribution

Then generate a global summary with regional comparisons.

## Regions to Analyze

| # | Region | Major Language |
|---|--------|----------------|
| 1 | Europe | english |
| 2 | Asia | arabic |
| 3 | Africa | french |
| 4 | Americas | spanish |

## Required Output

Save results to `countries_encyclopedia_linguistic.json`:

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
          "capital": "Berlin",
          "population": 83200000,
          "area": 357114,
          "languages": ["German"]
        }
      ],
      "border_analysis": {
        "total_borders": 100,
        "most_neighbors": {"country": "Germany", "count": 9},
        "landlocked_count": 5
      },
      "language_analysis": {
        "language": "english",
        "countries_speaking": 5,
        "total_speakers": 70000000
      }
    }
  ],
  "global_summary": {
    "total_regions": 4,
    "total_countries": 180,
    "most_spoken_language": {"language": "english", "countries": 10}
  },
  "analysis_date": "2024-01-15"
}
```

## Tools Available

**Data Collection Tools:**
- `local-countries_get_region`: Get all countries in a region
- `local-countries_get_details`: Get comprehensive country details
- `local-countries_get_borders`: Get info about neighboring countries
- `local-countries_get_by_language`: Get countries speaking a specific language

**File System Tools:**
- `filesystem-write_file`: Write output JSON to file
- `filesystem-read_file`: Read files from workspace

**Task Completion:**
- `local-claim_done`: Signal task completion (REQUIRED at the end)

## Workflow

For each region:
1. `local-countries_get_region` - Count countries, sum population, select top 3
2. `local-countries_get_details` - Get details for top 3 countries
3. `local-countries_get_borders` - Count borders, find most neighbors
4. `local-countries_get_by_language` - Count countries speaking major language

Process all 4 regions and compile global summary.

## Important Notes

1. Process ALL 4 regions completely
2. Use skill mode to optimize repeated API calls
3. **Summarize country lists** - store counts and top 3 only
4. Handle API errors gracefully

## REQUIRED: Task Completion Protocol

1. **FIRST**: Collect all data for all 4 regions
2. **SECOND**: Write results to `countries_encyclopedia_linguistic.json` using `filesystem-write_file`
3. **THIRD**: Call `local-claim_done` to signal completion

**DO NOT stop without calling `claim_done`!**
