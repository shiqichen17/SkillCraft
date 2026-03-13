# Task: Vocabulary Builder (5 Words × 5 APIs) - H1

Build vocabulary cards for **5 English words** using 5 API endpoints per word.

## Objective

For each of the following **5 words**, collect:
1. **Lookup**: basic word lookup
2. **Details**: comprehensive word info
3. **Synonyms**: related words
4. **Definitions**: all meanings
5. **Phonetics**: pronunciation info

Create a **vocabulary profile** with complexity and usage metrics.

## Words to Define

| # | Word | Expected Difficulty |
|---|------|---------------------|
| 1 | ephemeral | Advanced |
| 2 | ubiquitous | Advanced |
| 3 | pragmatic | Intermediate |
| 4 | eloquent | Intermediate |
| 5 | resilient | Intermediate |

## Required Output

Save results to `vocabulary_cards.json`:

```json
{
  "words": [
    {"word": "ephemeral", "phonetic": "/ɪˈfem(ə)rəl/", "meanings": [], "synonyms": [], "vocabulary_profile": {"complexity": "complex", "difficulty_level": "advanced"}}
  ],
  "summary": {"total_words": 5, "total_definitions": 10, "total_synonyms": 20},
  "analysis_date": "2024-01-15"
}
```

## Tools Available

- `local-dictionary_lookup`: Lookup
- `local-dictionary_word_details`: Details
- `local-dictionary_synonyms`: Synonyms
- `local-dictionary_definitions`: Definitions
- `local-dictionary_phonetics`: Phonetics

**File System:** `filesystem-write_file`, `filesystem-read_file`
**Completion:** `local-claim_done` (REQUIRED)

## Workflow

For each word (ephemeral, ubiquitous, pragmatic, eloquent, resilient):
1. `local-dictionary_lookup`
2. `local-dictionary_word_details`
3. `local-dictionary_synonyms`
4. `local-dictionary_definitions`
5. `local-dictionary_phonetics`

## Complexity Rating

- **Simple**: 1-2 syllables, common usage
- **Moderate**: 3 syllables, intermediate usage
- **Complex**: 4+ syllables, advanced usage

## Important

1. Process ALL 5 words completely
2. Include all parts of speech
3. Call `local-claim_done` to complete
