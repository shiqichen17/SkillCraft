# Task: Earthquake Analysis (3 Regions × 3 APIs) - E3

Analyze earthquake activity in **3 seismically active regions** using 3 API endpoints per region.

## Objective

For each of the following **3 regions**, collect:
1. **Region Stats**: get statistical analysis
2. **Historical Trends**: 90-day trends
3. **Tectonic Info**: plate boundary info

Calculate **risk level** and compile global summary.

## Regions to Analyze

| # | Region | Latitude | Longitude |
|---|--------|----------|----------|
| 1 | Tokyo, Japan | 35.6895 | 139.6917 |
| 2 | Los Angeles, USA | 34.0522 | -118.2437 |
| 3 | Jakarta, Indonesia | -6.2088 | 106.8456 |

## Required Output

Save results to `earthquake_analysis_results.json`:

```json
{
  "regions": [
    {"name": "Tokyo, Japan", "coordinates": {"latitude": 35.6895, "longitude": 139.6917}, "earthquakes": {"total_count": 156}, "risk_level": "High"}
  ],
  "summary": {"total_regions": 3, "total_earthquakes": 500, "most_active_region": {"name": "Tokyo, Japan"}},
  "analysis_date": "2024-01-15"
}
```

## Tools Available

- `local-usgs_get_region_stats`: Region Stats
- `local-usgs_get_historical_trends`: Historical Trends
- `local-usgs_get_tectonic_info`: Tectonic Info

**File System:** `filesystem-write_file`, `filesystem-read_file`
**Completion:** `local-claim_done` (REQUIRED)

## Workflow

For each region (Tokyo, Los Angeles, Jakarta):
1. `local-usgs_get_region_stats`
2. `local-usgs_get_historical_trends`
3. `local-usgs_get_tectonic_info`

## Risk Level

- **High**: max_magnitude >= 6.0 OR total_count > 100
- **Moderate**: max_magnitude >= 5.0 OR total_count > 50
- **Low**: max_magnitude >= 4.0 OR total_count > 20
- **Minimal**: all others

## Summary Requirements

**⚠️ CRITICAL**: Output ONLY summary statistics, NOT full earthquake lists!

## Important

1. Process ALL 3 regions completely
2. Summarize earthquake data - counts only
3. Call `local-claim_done` to complete
