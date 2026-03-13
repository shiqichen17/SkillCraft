# Task: DNA Analysis (3 Sequences × 3 APIs) - E2

Perform DNA sequence analysis for **3 sequences** using 3 API endpoints per sequence.

## Objective

For each of the following **3 DNA sequences**, perform:
1. **Validation**: check if DNA is valid
2. **Nucleotide Count**: count A, C, G, T
3. **Transcription**: DNA to mRNA

Calculate **GC content** and **sequence characteristics** for each.

## DNA Sequences to Analyze

```
SEQ_01: ATGCGATCGATCGATCGATCGATCGATCGATCGATCGATC...
SEQ_02: GCTAGCTAGCTAGCTAGCTAGCTAGCTAGCTAGCTAGCTA...
SEQ_03: AAATTTGGGCCCAAATTTGGGCCCAAATTTGGGCCCAAAT...
```

## Required Output

Save results to `dna_analysis_results.json`:

```json
{
  "sequences": [
    {"id": "SEQ_01", "length": 60, "is_valid": true, "nucleotide_counts": {"A": 15}, "gc_content": 50.0}
  ],
  "summary": {"total_sequences": 3, "valid_sequences": 3, "avg_gc_content": 50.0},
  "analysis_date": "2024-01-15"
}
```

## Tools Available

- `local-dna_is_valid`: Validation
- `local-dna_count_nucleotides`: Nucleotide Count
- `local-dna_transcribe_to_mrna`: Transcription

**File System:** `filesystem-write_file`, `filesystem-read_file`
**Completion:** `local-claim_done` (REQUIRED)

## Workflow

For each sequence (SEQ_01, SEQ_02, SEQ_03):
1. `local-dna_is_valid`
2. `local-dna_count_nucleotides`
3. `local-dna_transcribe_to_mrna`

## GC Content Classification

- **high**: GC content >= 60%
- **medium**: 40% <= GC < 60%
- **low**: GC content < 40%

## Important

1. Process ALL 3 sequences completely
2. Calculate GC content from nucleotide counts
3. Call `local-claim_done` to complete
