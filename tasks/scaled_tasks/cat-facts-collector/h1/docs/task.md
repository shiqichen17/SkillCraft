# Task: Cat Breed Encyclopedia (5 Breeds × 5 APIs) - H1

Create encyclopedia entries for **5 cat breeds** using 5 API endpoints per breed.

## Objective

For each of the following **5 cat breeds**, collect:
1. **Breed Profile**: basic info and characteristics
2. **Country Relatives**: breeds from same country
3. **Coat Family**: breeds with similar coat
4. **Facts Collection**: curated cat facts
5. **Encyclopedia**: full encyclopedia entry

Compile a **summary** with statistics across all breeds.

## Featured Breeds

| # | Breed | Country | Coat |
|---|-------|---------|------|
| 1 | Persian | Iran/USA/UK | Long |
| 2 | Siamese | Thailand | Short |
| 3 | Maine Coon | United States | Long |
| 4 | Ragdoll | United States | Long |
| 5 | Bengal | United States | Short |

## Required Output

Save results to `cat_encyclopedia.json`:

```json
{
  "breeds": [
    {"breed_name": "Persian", "profile": {}, "country_relatives": [], "facts": []}
  ],
  "summary": {"total_breeds_analyzed": 5, "countries_covered": ["Iran/USA/UK"]},
  "generation_date": "2024-01-15"
}
```

## Tools Available

- `local-catfacts_breed_profile`: Breed Profile
- `local-catfacts_breed_relatives`: Country Relatives
- `local-catfacts_breed_coat_family`: Coat Family
- `local-catfacts_breed_facts`: Facts Collection
- `local-catfacts_breed_encyclopedia`: Encyclopedia

**File System:** `filesystem-write_file`, `filesystem-read_file`
**Completion:** `local-claim_done` (REQUIRED)

## Workflow

For each breed (Persian, Siamese, Maine Coon, Ragdoll, Bengal):
1. `local-catfacts_breed_profile`
2. `local-catfacts_breed_relatives`
3. `local-catfacts_breed_coat_family`
4. `local-catfacts_breed_facts`
5. `local-catfacts_breed_encyclopedia`

## Important

1. Process ALL 5 breeds completely
2. Summarize relatives and facts - counts and samples
3. Call `local-claim_done` to complete
