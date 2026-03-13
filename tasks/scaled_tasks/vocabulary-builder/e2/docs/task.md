# Task: Vocabulary Builder (3 Words × 3 APIs) - E2

Build vocabulary cards for **3 English words** using 3 API endpoints per word.

## Objective

For each of the following **3 words**, collect:
1. **Details**: comprehensive word info
2. **Synonyms**: related words
3. **Phonetics**: pronunciation info

Create a **vocabulary profile** with complexity and usage metrics.

## Words to Define

| # | Word | Expected Difficulty |
|---|------|---------------------|
| 1 | ephemeral | Advanced |
| 2 | ubiquitous | Advanced |
| 3 | pragmatic | Intermediate |

## Required Output

Save results to `vocabulary_cards.json`:

```json
{
  "words": [
    {"word": "ephemeral", "phonetic": "/ɪˈfem(ə)rəl/", "meanings": [], "synonyms": [], "vocabulary_profile": {"complexity": "complex", "difficulty_level": "advanced"}}
  ],
  "summary": {"total_words": 3, "total_definitions": 10, "total_synonyms": 20},
  "analysis_date": "2024-01-15"
}
```

## Tools Available

- `local-dictionary_word_details`: Details
- `local-dictionary_synonyms`: Synonyms
- `local-dictionary_phonetics`: Phonetics

**File System:** `filesystem-write_file`, `filesystem-read_file`
**Completion:** `local-claim_done` (REQUIRED)

## Workflow

For each word (ephemeral, ubiquitous, pragmatic):
1. `local-dictionary_word_details`
2. `local-dictionary_synonyms`
3. `local-dictionary_phonetics`

## Complexity Rating

- **Simple**: 1-2 syllables, common usage
- **Moderate**: 3 syllables, intermediate usage
- **Complex**: 4+ syllables, advanced usage

## Important

1. Process ALL 3 words completely
2. Include all parts of speech
3. Call `local-claim_done` to complete
