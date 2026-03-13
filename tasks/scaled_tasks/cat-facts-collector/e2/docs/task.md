# Task: Cat Breed Encyclopedia (3 Breeds × 3 APIs) - E2

Create encyclopedia entries for **3 cat breeds** using 3 API endpoints per breed.

## Objective

For each of the following **3 cat breeds**, collect:
1. **Breed Profile**: basic info and characteristics
2. **Facts Collection**: curated cat facts
3. **Encyclopedia**: full encyclopedia entry

Compile a **summary** with statistics across all breeds.

## Featured Breeds

| # | Breed | Country | Coat |
|---|-------|---------|------|
| 1 | Persian | Iran/USA/UK | Long |
| 2 | Siamese | Thailand | Short |
| 3 | Maine Coon | United States | Long |

## Required Output

Save results to `cat_encyclopedia.json`:

```json
{
  "breeds": [
    {"breed_name": "Persian", "profile": {}, "country_relatives": [], "facts": []}
  ],
  "summary": {"total_breeds_analyzed": 3, "countries_covered": ["Iran/USA/UK"]},
  "generation_date": "2024-01-15"
}
```

## Tools Available

- `local-catfacts_breed_profile`: Breed Profile
- `local-catfacts_breed_facts`: Facts Collection
- `local-catfacts_breed_encyclopedia`: Encyclopedia

**File System:** `filesystem-write_file`, `filesystem-read_file`
**Completion:** `local-claim_done` (REQUIRED)

## Workflow

For each breed (Persian, Siamese, Maine Coon):
1. `local-catfacts_breed_profile`
2. `local-catfacts_breed_facts`
3. `local-catfacts_breed_encyclopedia`

## Important

1. Process ALL 3 breeds completely
2. Summarize relatives and facts - counts and samples
3. Call `local-claim_done` to complete
