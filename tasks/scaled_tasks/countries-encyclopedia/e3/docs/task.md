# Task: Country Profiles - Details & Economics (Easy - 3 Countries × 3 APIs)

Generate detailed profiles for **3 major countries** focusing on details, borders, and currency.

## Objective

For each of the following **3 countries**, collect:
1. **Country Details**: Population, area, languages, capitals
2. **Border Analysis**: Neighboring countries and statistics
3. **Currency Analysis**: Countries sharing the same currency

Then compile a comparative report.

## Countries to Analyze

| # | Country | Currency |
|---|---------|----------|
| 1 | Germany | EUR |
| 2 | China | CNY |
| 3 | Brazil | BRL |

## Required Output

Save results to `country_profiles.json`:

```json
{
  "countries": [
    {
      "name": "Germany",
      "details": {
        "official_name": "Federal Republic of Germany",
        "capital": "Berlin",
        "population": 83200000,
        "area": 357114,
        "languages": ["German"],
        "currencies": [{"code": "EUR", "name": "Euro"}],
        "flag_emoji": "🇩🇪"
      },
      "border_analysis": {
        "border_countries": ["Austria", "Belgium", "Czech Republic", "Denmark", "France", "Luxembourg", "Netherlands", "Poland", "Switzerland"],
        "total_neighbors": 9,
        "is_landlocked": false
      },
      "currency_analysis": {
        "currency": "EUR",
        "countries_using": 19,
        "major_economies": ["Germany", "France", "Italy"]
      }
    }
  ],
  "summary": {
    "total_countries": 3,
    "total_borders": 25,
    "most_neighbors": {"country": "Germany", "count": 9}
  },
  "analysis_date": "2024-01-15"
}
```

## Tools Available

**Data Collection Tools:**
- `local-countries_get_details`: Get comprehensive country details
- `local-countries_get_borders`: Get info about neighboring countries
- `local-countries_get_by_currency`: Get countries using a specific currency

**File System Tools:**
- `filesystem-write_file`: Write output JSON to file
- `filesystem-read_file`: Read files from workspace

**Task Completion:**
- `local-claim_done`: Signal task completion (REQUIRED at the end)

## Workflow

For each country:
1. `local-countries_get_details` - Get comprehensive country info
2. `local-countries_get_borders` - Get neighboring countries
3. `local-countries_get_by_currency` - Get currency usage analysis

Process all 3 countries and compile summary.

## Important Notes

1. Process ALL 3 countries completely
2. Use skill mode to optimize repeated API calls
3. Handle API errors gracefully

## REQUIRED: Task Completion Protocol

1. **FIRST**: Collect all data for all 3 countries
2. **SECOND**: Write results to `country_profiles.json` using `filesystem-write_file`
3. **THIRD**: Call `local-claim_done` to signal completion

**DO NOT stop without calling `claim_done`!**
