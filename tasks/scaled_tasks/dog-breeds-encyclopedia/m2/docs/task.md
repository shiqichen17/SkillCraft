# Task: Dog Breeds Encyclopedia (4 Breeds × 4 APIs) - M2

Create encyclopedia entries for **4 dog breeds** using 4 API endpoints per breed.

## Objective

For each of the following **4 dog breeds**, collect:
1. **Breed Images**: sample images for breed
2. **Sub-breed Images**: images for sub-breeds
3. **All Sub-breeds**: complete sub-breed list
4. **Gallery**: comprehensive image gallery

Calculate **diversity index** and **popularity tier** for each breed.

## Breeds to Document

| # | Breed | Has Sub-breeds |
|---|-------|----------------|
| 1 | Retriever | Yes |
| 2 | Spaniel | Yes |
| 3 | Bulldog | Yes |
| 4 | Hound | Yes |

## Required Output

Save results to `dog_encyclopedia.json`:

```json
{
  "breeds": [
    {"breed": "retriever", "display_name": "Retriever", "sub_breed_count": 4, "diversity_index": 4, "popularity_tier": "Very Popular"}
  ],
  "summary": {"total_breeds": 4, "total_sub_breeds": 30},
  "analysis_date": "2024-01-15"
}
```

## Tools Available

- `local-dog_breed_images`: Breed Images
- `local-dog_sub_breed_images`: Sub-breed Images
- `local-dog_breed_all_sub_breeds`: All Sub-breeds
- `local-dog_breed_gallery`: Gallery

**File System:** `filesystem-write_file`, `filesystem-read_file`
**Completion:** `local-claim_done` (REQUIRED)

## Workflow

For each breed (Retriever, Spaniel, Bulldog, Hound):
1. `local-dog_breed_images`
2. `local-dog_sub_breed_images`
3. `local-dog_breed_all_sub_breeds`
4. `local-dog_breed_gallery`

## Popularity Tier

- **Very Popular**: > 500 images
- **Popular**: 200-500 images
- **Common**: 50-200 images
- **Rare**: < 50 images

## Important

1. Process ALL 4 breeds completely
2. Summarize image lists - counts and samples only
3. Call `local-claim_done` to complete
