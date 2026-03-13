# Task: Dog Breeds Encyclopedia (3 Breeds × 3 APIs) - E1

Create encyclopedia entries for **3 dog breeds** using 3 API endpoints per breed.

## Objective

For each of the following **3 dog breeds**, collect:
1. **Breed Info**: basic breed information
2. **Breed Images**: sample images for breed
3. **All Sub-breeds**: complete sub-breed list

Calculate **diversity index** and **popularity tier** for each breed.

## Breeds to Document

| # | Breed | Has Sub-breeds |
|---|-------|----------------|
| 1 | Retriever | Yes |
| 2 | Spaniel | Yes |
| 3 | Bulldog | Yes |

## Required Output

Save results to `dog_encyclopedia.json`:

```json
{
  "breeds": [
    {"breed": "retriever", "display_name": "Retriever", "sub_breed_count": 4, "diversity_index": 4, "popularity_tier": "Very Popular"}
  ],
  "summary": {"total_breeds": 3, "total_sub_breeds": 30},
  "analysis_date": "2024-01-15"
}
```

## Tools Available

- `local-dog_breed_info`: Breed Info
- `local-dog_breed_images`: Breed Images
- `local-dog_breed_all_sub_breeds`: All Sub-breeds

**File System:** `filesystem-write_file`, `filesystem-read_file`
**Completion:** `local-claim_done` (REQUIRED)

## Workflow

For each breed (Retriever, Spaniel, Bulldog):
1. `local-dog_breed_info`
2. `local-dog_breed_images`
3. `local-dog_breed_all_sub_breeds`

## Popularity Tier

- **Very Popular**: > 500 images
- **Popular**: 200-500 images
- **Common**: 50-200 images
- **Rare**: < 50 images

## Important

1. Process ALL 3 breeds completely
2. Summarize image lists - counts and samples only
3. Call `local-claim_done` to complete
