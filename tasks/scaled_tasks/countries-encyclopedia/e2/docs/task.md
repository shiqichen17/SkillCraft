# Task: World Countries Encyclopedia - Economic & Linguistic (Easy - 3 Regions × 3 APIs)

Generate a comprehensive encyclopedia focusing on **economic and linguistic** aspects of **3 major regions**.

## Objective

For each of the following **3 regions**, collect and summarize:
1. **Region Summary**: Total countries, population, area
2. **Currency Analysis**: Major currency usage and country counts
3. **Language Analysis**: Major language speakers and distribution

Then generate a global summary with regional comparisons.

## Regions to Analyze

| # | Region | Major Currency | Major Language |
|---|--------|---------------|----------------|
| 1 | Europe | EUR | english |
| 2 | Asia | CNY | arabic |
| 3 | Africa | XOF | french |

## Required Output

Save results to `countries_economic_linguistic.json`:

```json
{
  "regions": [
    {
      "name": "Europe",
      "summary": {
        "country_count": 44,
        "total_population": 750000000,
        "total_area_km2": 10180000
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
    "total_regions": 3,
    "most_used_currency": {"currency": "EUR", "countries": 19},
    "most_spoken_language": {"language": "english", "countries": 10}
  },
  "analysis_date": "2024-01-15"
}
```

## Tools Available

**Data Collection Tools:**
- `local-countries_get_region`: Get all countries in a region
- `local-countries_get_by_currency`: Get countries using a specific currency
- `local-countries_get_by_language`: Get countries speaking a specific language

**File System Tools:**
- `filesystem-write_file`: Write output JSON to file
- `filesystem-read_file`: Read files from workspace

**Task Completion:**
- `local-claim_done`: Signal task completion (REQUIRED at the end)

## Workflow

For each region:
1. `local-countries_get_region` - Get region summary and country list
2. `local-countries_get_by_currency` - Analyze currency usage
3. `local-countries_get_by_language` - Analyze language distribution

Process all 3 regions and compile global summary.

## Important Notes

1. Process ALL 3 regions completely
2. Use skill mode to optimize repeated API calls
3. **Summarize data** - store counts and statistics only
4. Handle API errors gracefully

## REQUIRED: Task Completion Protocol

1. **FIRST**: Collect all data for all 3 regions
2. **SECOND**: Write results to `countries_economic_linguistic.json` using `filesystem-write_file`
3. **THIRD**: Call `local-claim_done` to signal completion

**DO NOT stop without calling `claim_done`!**
