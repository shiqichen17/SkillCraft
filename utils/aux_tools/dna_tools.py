# dna_tools.py
# DNA sequence analysis tools based on M3ToolEval
# Enhanced version with larger, more detailed outputs for Skill Mode efficiency
import json
from typing import Any, Dict, List
from agents.tool import FunctionTool, RunContextWrapper
from collections import Counter


# ============== Enhanced DNA Analysis Functions ==============

CODON_MAP = {
        'AUG': 'Methionine', 'UUU': 'Phenylalanine', 'UUC': 'Phenylalanine',
        'UUA': 'Leucine', 'UUG': 'Leucine', 'CUU': 'Leucine', 'CUC': 'Leucine',
        'CUA': 'Leucine', 'CUG': 'Leucine', 'AUU': 'Isoleucine', 'AUC': 'Isoleucine',
        'AUA': 'Isoleucine', 'GUU': 'Valine', 'GUC': 'Valine', 'GUA': 'Valine',
        'GUG': 'Valine', 'UCU': 'Serine', 'UCC': 'Serine', 'UCA': 'Serine',
        'UCG': 'Serine', 'CCU': 'Proline', 'CCC': 'Proline', 'CCA': 'Proline',
        'CCG': 'Proline', 'ACU': 'Threonine', 'ACC': 'Threonine', 'ACA': 'Threonine',
        'ACG': 'Threonine', 'GCU': 'Alanine', 'GCC': 'Alanine', 'GCA': 'Alanine',
        'GCG': 'Alanine', 'UAU': 'Tyrosine', 'UAC': 'Tyrosine', 'CAU': 'Histidine',
        'CAC': 'Histidine', 'CAA': 'Glutamine', 'CAG': 'Glutamine', 'AAU': 'Asparagine',
        'AAC': 'Asparagine', 'AAA': 'Lysine', 'AAG': 'Lysine', 'GAU': 'Aspartate',
        'GAC': 'Aspartate', 'GAA': 'Glutamate', 'GAG': 'Glutamate', 'UGU': 'Cysteine',
        'UGC': 'Cysteine', 'UGG': 'Tryptophan', 'CGU': 'Arginine', 'CGC': 'Arginine',
        'CGA': 'Arginine', 'CGG': 'Arginine', 'AGU': 'Serine', 'AGC': 'Serine',
        'AGA': 'Arginine', 'AGG': 'Arginine', 'GGU': 'Glycine', 'GGC': 'Glycine',
        'GGA': 'Glycine', 'GGG': 'Glycine', 'UAA': 'Stop', 'UAG': 'Stop', 'UGA': 'Stop'
    }

# Amino acid properties for detailed analysis
AMINO_ACID_PROPERTIES = {
    'Methionine': {'abbreviation': 'Met', 'code': 'M', 'type': 'hydrophobic', 'polarity': 'nonpolar', 'molecular_weight': 149.21, 'pI': 5.74},
    'Phenylalanine': {'abbreviation': 'Phe', 'code': 'F', 'type': 'hydrophobic', 'polarity': 'nonpolar', 'molecular_weight': 165.19, 'pI': 5.48},
    'Leucine': {'abbreviation': 'Leu', 'code': 'L', 'type': 'hydrophobic', 'polarity': 'nonpolar', 'molecular_weight': 131.17, 'pI': 5.98},
    'Isoleucine': {'abbreviation': 'Ile', 'code': 'I', 'type': 'hydrophobic', 'polarity': 'nonpolar', 'molecular_weight': 131.17, 'pI': 6.02},
    'Valine': {'abbreviation': 'Val', 'code': 'V', 'type': 'hydrophobic', 'polarity': 'nonpolar', 'molecular_weight': 117.15, 'pI': 5.96},
    'Serine': {'abbreviation': 'Ser', 'code': 'S', 'type': 'hydrophilic', 'polarity': 'polar', 'molecular_weight': 105.09, 'pI': 5.68},
    'Proline': {'abbreviation': 'Pro', 'code': 'P', 'type': 'hydrophobic', 'polarity': 'nonpolar', 'molecular_weight': 115.13, 'pI': 6.30},
    'Threonine': {'abbreviation': 'Thr', 'code': 'T', 'type': 'hydrophilic', 'polarity': 'polar', 'molecular_weight': 119.12, 'pI': 5.60},
    'Alanine': {'abbreviation': 'Ala', 'code': 'A', 'type': 'hydrophobic', 'polarity': 'nonpolar', 'molecular_weight': 89.09, 'pI': 6.00},
    'Tyrosine': {'abbreviation': 'Tyr', 'code': 'Y', 'type': 'hydrophilic', 'polarity': 'polar', 'molecular_weight': 181.19, 'pI': 5.66},
    'Histidine': {'abbreviation': 'His', 'code': 'H', 'type': 'hydrophilic', 'polarity': 'positive', 'molecular_weight': 155.16, 'pI': 7.59},
    'Glutamine': {'abbreviation': 'Gln', 'code': 'Q', 'type': 'hydrophilic', 'polarity': 'polar', 'molecular_weight': 146.15, 'pI': 5.65},
    'Asparagine': {'abbreviation': 'Asn', 'code': 'N', 'type': 'hydrophilic', 'polarity': 'polar', 'molecular_weight': 132.12, 'pI': 5.41},
    'Lysine': {'abbreviation': 'Lys', 'code': 'K', 'type': 'hydrophilic', 'polarity': 'positive', 'molecular_weight': 146.19, 'pI': 9.74},
    'Aspartate': {'abbreviation': 'Asp', 'code': 'D', 'type': 'hydrophilic', 'polarity': 'negative', 'molecular_weight': 133.10, 'pI': 2.77},
    'Glutamate': {'abbreviation': 'Glu', 'code': 'E', 'type': 'hydrophilic', 'polarity': 'negative', 'molecular_weight': 147.13, 'pI': 3.22},
    'Cysteine': {'abbreviation': 'Cys', 'code': 'C', 'type': 'hydrophilic', 'polarity': 'polar', 'molecular_weight': 121.16, 'pI': 5.07},
    'Tryptophan': {'abbreviation': 'Trp', 'code': 'W', 'type': 'hydrophobic', 'polarity': 'nonpolar', 'molecular_weight': 204.23, 'pI': 5.89},
    'Arginine': {'abbreviation': 'Arg', 'code': 'R', 'type': 'hydrophilic', 'polarity': 'positive', 'molecular_weight': 174.20, 'pI': 10.76},
    'Glycine': {'abbreviation': 'Gly', 'code': 'G', 'type': 'hydrophobic', 'polarity': 'nonpolar', 'molecular_weight': 75.07, 'pI': 5.97},
    'Stop': {'abbreviation': 'Stop', 'code': '*', 'type': 'termination', 'polarity': 'none', 'molecular_weight': 0, 'pI': 0},
}


def validate_and_analyze_dna(dna_sequence: str) -> Dict:
    """Validate DNA sequence and provide comprehensive analysis."""
    seq = dna_sequence.upper().strip()
    is_valid = set(seq).issubset(set('ACGT'))
    
    if not is_valid:
        invalid_chars = set(seq) - set('ACGT')
        return {
            "is_valid": False,
            "error": f"Invalid characters found: {invalid_chars}",
            "sequence_length": len(seq)
        }
    
    # Count nucleotides
    counts = dict(Counter(seq))
    # Ensure all nucleotides are present
    for nuc in 'ATGC':
        if nuc not in counts:
            counts[nuc] = 0
    total = len(seq)
    
    # Calculate GC content
    gc_count = counts.get('G', 0) + counts.get('C', 0)
    at_count = counts.get('A', 0) + counts.get('T', 0)
    gc_content = (gc_count / total * 100) if total > 0 else 0
    
    # Calculate ALL dinucleotide frequencies (16 possible)
    all_dinucleotides = ['AA', 'AT', 'AG', 'AC', 'TA', 'TT', 'TG', 'TC', 
                         'GA', 'GT', 'GG', 'GC', 'CA', 'CT', 'CG', 'CC']
    dinucleotides = {di: 0 for di in all_dinucleotides}
    for i in range(len(seq) - 1):
        di = seq[i:i+2]
        dinucleotides[di] = dinucleotides.get(di, 0) + 1
    
    # Calculate dinucleotide percentages
    total_di = sum(dinucleotides.values())
    dinucleotide_percentages = {di: round(c / total_di * 100, 3) if total_di > 0 else 0 
                                 for di, c in dinucleotides.items()}
    
    # Calculate trinucleotide frequencies (64 possible codons)
    trinucleotides = {}
    for i in range(len(seq) - 2):
        tri = seq[i:i+3]
        trinucleotides[tri] = trinucleotides.get(tri, 0) + 1
    total_tri = sum(trinucleotides.values())
    
    # Find repeat patterns (2-6 bases)
    repeat_patterns = []
    for pattern_len in [2, 3, 4, 5, 6]:
        for i in range(len(seq) - pattern_len * 2 + 1):
            pattern = seq[i:i+pattern_len]
            repeat_count = 1
            pos = i + pattern_len
            while pos + pattern_len <= len(seq) and seq[pos:pos+pattern_len] == pattern:
                repeat_count += 1
                pos += pattern_len
            if repeat_count >= 2:
                repeat_patterns.append({
                    "pattern": pattern,
                    "position": i,
                    "length": pattern_len,
                    "repeat_count": repeat_count,
                    "total_span": pattern_len * repeat_count,
                    "pattern_gc_content": round((pattern.count('G') + pattern.count('C')) / len(pattern) * 100, 1)
                })
    
    # Deduplicate repeat patterns
    seen_patterns = set()
    unique_repeats = []
    for rp in repeat_patterns:
        key = (rp["pattern"], rp["position"])
        if key not in seen_patterns:
            seen_patterns.add(key)
            unique_repeats.append(rp)
    
    # GC level classification
    if gc_content >= 60:
        gc_level = "high"
    elif gc_content >= 40:
        gc_level = "medium"
    else:
        gc_level = "low"
    
    # Calculate complexity metrics
    unique_dinuc = len([d for d, c in dinucleotides.items() if c > 0])
    unique_trinuc = len(trinucleotides)
    
    # Sequence complexity (Shannon entropy approximation)
    import math
    entropy = 0
    for nuc, count in counts.items():
        if count > 0:
            p = count / total
            entropy -= p * math.log2(p)
    max_entropy = 2.0  # log2(4) for 4 nucleotides
    complexity_ratio = entropy / max_entropy if max_entropy > 0 else 0
    
    # Find potential restriction enzyme sites
    restriction_sites = {
        "EcoRI": "GAATTC",
        "BamHI": "GGATCC", 
        "HindIII": "AAGCTT",
        "NotI": "GCGGCCGC",
        "XhoI": "CTCGAG",
        "SalI": "GTCGAC",
        "PstI": "CTGCAG",
        "SmaI": "CCCGGG",
        "KpnI": "GGTACC",
        "SacI": "GAGCTC"
    }
    found_sites = {}
    for enzyme, site in restriction_sites.items():
        positions = []
        start = 0
        while True:
            pos = seq.find(site, start)
            if pos == -1:
                break
            positions.append(pos)
            start = pos + 1
        if positions:
            found_sites[enzyme] = {
                "recognition_sequence": site,
                "positions": positions,
                "count": len(positions)
            }
    
    # Calculate codon positions analysis (for coding potential)
    codon_position_bias = {"position_1": {}, "position_2": {}, "position_3": {}}
    for i in range(0, len(seq) - 2, 3):
        codon = seq[i:i+3]
        for pos, nuc in enumerate(codon):
            pos_key = f"position_{pos+1}"
            codon_position_bias[pos_key][nuc] = codon_position_bias[pos_key].get(nuc, 0) + 1
    
    # Calculate AT/GC skew
    a_count = counts.get('A', 0)
    t_count = counts.get('T', 0)
    g_count = counts.get('G', 0)
    c_count = counts.get('C', 0)
    
    at_skew = round((a_count - t_count) / (a_count + t_count), 4) if (a_count + t_count) > 0 else 0
    gc_skew = round((g_count - c_count) / (g_count + c_count), 4) if (g_count + c_count) > 0 else 0
    
    # Molecular properties calculations
    mw_a = 331.2  # Molecular weight of dAMP
    mw_t = 322.2  # Molecular weight of dTMP
    mw_g = 347.2  # Molecular weight of dGMP
    mw_c = 307.2  # Molecular weight of dCMP
    exact_mw = (a_count * mw_a + t_count * mw_t + g_count * mw_g + c_count * mw_c) - (total - 1) * 18.015
    
    # Estimate melting temperature using different methods
    if total < 14:
        tm_basic = 2 * at_count + 4 * gc_count  # Wallace rule
    else:
        tm_basic = 64.9 + 41 * (gc_count - 16.4) / total  # Marmur-Doty formula
    
    # Nearest neighbor Tm estimation (simplified)
    nn_params = {
        'AA': -7.9, 'TT': -7.9, 'AT': -7.2, 'TA': -7.2,
        'CA': -8.5, 'TG': -8.5, 'GT': -8.4, 'AC': -8.4,
        'CT': -7.8, 'AG': -7.8, 'GA': -8.2, 'TC': -8.2,
        'CG': -10.6, 'GC': -9.8, 'GG': -8.0, 'CC': -8.0
    }
    dh_sum = sum(nn_params.get(seq[i:i+2], -8.0) for i in range(len(seq)-1))
    tm_nn = round(1000 * dh_sum / (len(seq) * 10.8 + 0.368 * len(seq) * math.log(0.00025)) - 273.15, 1)
    
    # Extract key values for top-level (Pattern-friendly)
    most_repeated = max(unique_repeats, key=lambda x: x["repeat_count"]) if unique_repeats else None
    complexity_class = "high" if complexity_ratio > 0.9 else "medium" if complexity_ratio > 0.7 else "low"
    
    # ============== TOP-LEVEL: Core fields for Pattern extraction ==============
    result = {
        "is_valid": True,
        "sequence": seq,
        "sequence_length": total,
        "nucleotide_counts": counts,
        "gc_content": round(gc_content, 2),
        "gc_level": gc_level,
        "complexity_classification": complexity_class,
        "repeat_pattern": most_repeated["pattern"] if most_repeated else "N/A",
        
        # ============== DETAILED_ANALYSIS: Verbose data for Normal mode tokens ==============
        "detailed_analysis": {
            "nucleotide_percentages": {
                "A": round(counts.get('A', 0) / total * 100, 2) if total > 0 else 0,
                "T": round(counts.get('T', 0) / total * 100, 2) if total > 0 else 0,
                "G": round(counts.get('G', 0) / total * 100, 2) if total > 0 else 0,
                "C": round(counts.get('C', 0) / total * 100, 2) if total > 0 else 0,
            },
            "at_content": round(100 - gc_content, 2),
            "nucleotide_ratios": {
                "purine_to_pyrimidine": round((a_count + g_count) / (t_count + c_count), 4) if (t_count + c_count) > 0 else 0,
                "A_to_T": round(a_count / t_count, 4) if t_count > 0 else float('inf') if a_count > 0 else 0,
                "G_to_C": round(g_count / c_count, 4) if c_count > 0 else float('inf') if g_count > 0 else 0,
                "chargaff_ratio_AT": round(a_count / t_count, 4) if t_count > 0 else 0,
                "chargaff_ratio_GC": round(g_count / c_count, 4) if c_count > 0 else 0
            },
            "strand_bias": {
                "at_skew": at_skew,
                "gc_skew": gc_skew,
                "interpretation": "Leading strand" if gc_skew > 0 else "Lagging strand" if gc_skew < 0 else "Balanced"
            },
            "dinucleotide_analysis": {
                "frequencies": dinucleotides,
                "percentages": dinucleotide_percentages,
                "total_dinucleotides": total_di,
                "unique_dinucleotides": unique_dinuc,
                "cpg_count": dinucleotides.get('CG', 0),
                "cpg_observed_expected": round(dinucleotides.get('CG', 0) / ((c_count * g_count) / total), 4) if (c_count * g_count) > 0 and total > 0 else 0
            },
            "trinucleotide_analysis": {
                "frequencies": dict(sorted(trinucleotides.items(), key=lambda x: -x[1])[:20]),
                "total_unique": unique_trinuc,
                "most_common": max(trinucleotides.items(), key=lambda x: x[1]) if trinucleotides else None,
                "least_common": min(trinucleotides.items(), key=lambda x: x[1]) if trinucleotides else None
            },
            "codon_position_bias": codon_position_bias,
            "repeat_analysis": {
                "total_patterns_found": len(unique_repeats),
                "repeat_patterns": unique_repeats[:15],
                "most_repeated": most_repeated,
                "longest_repeat_unit": max(unique_repeats, key=lambda x: x["length"]) if unique_repeats else None
            },
            "complexity_metrics": {
                "shannon_entropy": round(entropy, 4),
                "max_entropy": max_entropy,
                "complexity_ratio": round(complexity_ratio, 4),
                "complexity_classification": complexity_class
            },
            "restriction_enzyme_sites": found_sites,
            "molecular_properties": {
                "molecular_weight_estimate": round(exact_mw, 2),
                "molecular_weight_kda": round(exact_mw / 1000, 3),
                "extinction_coefficient_260nm": round(a_count * 15400 + t_count * 8700 + g_count * 11500 + c_count * 7400, 0),
                "absorbance_260nm_per_ug_ml": round(1 / (exact_mw / (a_count * 15400 + t_count * 8700 + g_count * 11500 + c_count * 7400 + 0.001)), 4)
            },
            "melting_temperature": {
                "tm_basic_celsius": round(tm_basic, 1),
                "tm_nearest_neighbor_celsius": tm_nn,
                "gc_dependent_tm": round(81.5 + 16.6 * math.log10(0.05) + 0.41 * gc_content - 600 / total, 1) if total > 0 else 0,
                "notes": "Tm varies with salt concentration and sequence context"
            },
            "sequence_features": {
                "starts_with": seq[:3] if len(seq) >= 3 else seq,
                "ends_with": seq[-3:] if len(seq) >= 3 else seq,
                "palindrome_check": seq == seq[::-1].translate(str.maketrans('ATGC', 'TACG')),
                "has_start_codon_atg": "ATG" in seq,
                "has_stop_codons": any(stop in seq for stop in ["TAA", "TAG", "TGA"])
            }
        }
    }
    
    return result


def transcribe_with_details(dna_sequence: str) -> Dict:
    """Transcribe DNA to mRNA with detailed analysis."""
    import math
    seq = dna_sequence.upper().strip()
    transcription_map = str.maketrans('ACGT', 'UGCA')
    mrna = seq.translate(transcription_map)
    
    # Analyze codons in all three reading frames
    reading_frames = {}
    for frame in range(3):
        frame_codons = [mrna[i:i+3] for i in range(frame, len(mrna) - 2, 3)]
        frame_aa = [CODON_MAP.get(c, 'Unknown') for c in frame_codons]
        reading_frames[f"frame_{frame+1}"] = {
            "codons": frame_codons,
            "amino_acids": frame_aa,
            "codon_count": len(frame_codons),
            "has_start": 'AUG' in frame_codons,
            "has_stop": any(c in frame_codons for c in ['UAA', 'UAG', 'UGA']),
            "start_positions": [i for i, c in enumerate(frame_codons) if c == 'AUG'],
            "stop_positions": [i for i, c in enumerate(frame_codons) if c in ['UAA', 'UAG', 'UGA']]
        }
    
    # Main frame (frame 1) analysis
    codons = [mrna[i:i+3] for i in range(0, len(mrna) - 2, 3)]
    codon_counts = dict(Counter(codons))
    
    # Find start codons (AUG) - all positions including non-frame
    all_start_positions = []
    for i in range(len(mrna) - 2):
        if mrna[i:i+3] == 'AUG':
            all_start_positions.append({
                "position": i,
                "in_frame": i % 3 == 0,
                "context": mrna[max(0, i-3):i+6]
            })
    
    # Find stop codons - all positions
    stop_codons = ['UAA', 'UAG', 'UGA']
    all_stop_positions = []
    for i in range(len(mrna) - 2):
        if mrna[i:i+3] in stop_codons:
            all_stop_positions.append({
                "position": i,
                "codon": mrna[i:i+3],
                "in_frame": i % 3 == 0,
                "context": mrna[max(0, i-3):i+6]
            })
    
    # Calculate codon usage bias with RSCU (Relative Synonymous Codon Usage)
    codon_usage = {}
    synonymous_groups = {}
    for codon, count in codon_counts.items():
        aa = CODON_MAP.get(codon, 'Unknown')
        if aa not in codon_usage:
            codon_usage[aa] = {}
            synonymous_groups[aa] = 0
        codon_usage[aa][codon] = count
        synonymous_groups[aa] += count
    
    # Calculate RSCU
    rscu_values = {}
    for aa, codons_dict in codon_usage.items():
        rscu_values[aa] = {}
        total_for_aa = synonymous_groups[aa]
        num_synonymous = len(codons_dict)
        for codon, count in codons_dict.items():
            expected = total_for_aa / num_synonymous if num_synonymous > 0 else 0
            rscu = count / expected if expected > 0 else 0
            rscu_values[aa][codon] = round(rscu, 3)
    
    # Identify ORFs (Open Reading Frames)
    orfs = []
    for frame in range(3):
        frame_seq = mrna[frame:]
        i = 0
        while i < len(frame_seq) - 2:
            if frame_seq[i:i+3] == 'AUG':
                start = frame + i
                j = i + 3
                while j < len(frame_seq) - 2:
                    codon = frame_seq[j:j+3]
                    if codon in ['UAA', 'UAG', 'UGA']:
                        end = frame + j + 3
                        orf_seq = mrna[start:end]
                        orf_codons = [orf_seq[k:k+3] for k in range(0, len(orf_seq)-2, 3)]
                        orf_aa = [CODON_MAP.get(c, '?') for c in orf_codons]
                        orfs.append({
                            "frame": frame + 1,
                            "start_position": start,
                            "end_position": end,
                            "length_nt": end - start,
                            "length_aa": len(orf_aa),
                            "sequence": orf_seq,
                            "amino_acids": '-'.join(orf_aa),
                            "stop_codon": codon
                        })
                        break
                    j += 3
                i = j + 3
            else:
                i += 3
    
    # Calculate codon adaptation index (simplified)
    total_codons = len(codons)
    unique_codons = len(codon_counts)
    
    # Nucleotide composition of mRNA
    mrna_composition = {
        'A': mrna.count('A'),
        'U': mrna.count('U'),
        'G': mrna.count('G'),
        'C': mrna.count('C')
    }
    
    # GC content of each codon position
    gc_by_position = {"position_1": 0, "position_2": 0, "position_3": 0}
    for codon in codons:
        for i, nuc in enumerate(codon):
            if nuc in 'GC':
                gc_by_position[f"position_{i+1}"] += 1
    for pos in gc_by_position:
        gc_by_position[pos] = round(gc_by_position[pos] / len(codons) * 100, 2) if codons else 0
    
    # Calculate effective number of codons (simplified Nc)
    nc_estimate = 0
    for aa, codons_dict in codon_usage.items():
        n = sum(codons_dict.values())
        k = len(codons_dict)
        if n > 0 and k > 1:
            homozygosity = sum((c/n)**2 for c in codons_dict.values())
            nc_estimate += 1 / homozygosity if homozygosity > 0 else k
        elif k == 1:
            nc_estimate += 1
    
    # ============== TOP-LEVEL: Core fields for Pattern extraction ==============
    result = {
        "dna_input": seq,
        "mrna_output": mrna,
        "length": len(mrna),
        "total_codons": total_codons,
        "has_start_codon": len(all_start_positions) > 0,
        "has_stop_codon": len(all_stop_positions) > 0,
        
        # ============== DETAILED_ANALYSIS: Verbose data for Normal mode tokens ==============
        "detailed_analysis": {
            "unique_codons_used": unique_codons,
            "codon_breakdown": codon_counts,
            "codon_percentages": {c: round(n/total_codons*100, 2) for c, n in codon_counts.items()} if total_codons > 0 else {},
            "start_codon_analysis": {
                "in_frame_positions": [p for p in all_start_positions if p["in_frame"]],
                "all_positions": all_start_positions,
                "total_count": len(all_start_positions)
            },
            "stop_codon_analysis": {
                "in_frame_positions": [p for p in all_stop_positions if p["in_frame"]],
                "all_positions": all_stop_positions,
                "total_count": len(all_stop_positions),
                "by_type": {
                    "UAA_ochre": sum(1 for p in all_stop_positions if p["codon"] == "UAA"),
                    "UAG_amber": sum(1 for p in all_stop_positions if p["codon"] == "UAG"),
                    "UGA_opal": sum(1 for p in all_stop_positions if p["codon"] == "UGA")
                }
            },
            "reading_frame_analysis": reading_frames,
            "open_reading_frames": {
                "total_found": len(orfs),
                "orfs": orfs,
                "longest_orf": max(orfs, key=lambda x: x["length_nt"]) if orfs else None
            },
            "codon_usage_by_amino_acid": codon_usage,
            "rscu_values": rscu_values,
            "gc_content_by_codon_position": gc_by_position,
            "effective_number_of_codons": round(nc_estimate, 2),
            "mrna_composition": mrna_composition,
            "mrna_gc_content": round((mrna_composition['G'] + mrna_composition['C']) / len(mrna) * 100, 2) if mrna else 0,
            "transcription_rule": "A→U, C→G, G→C, T→A",
            "transcription_details": {
                "template_strand": seq,
                "coding_strand": seq,
                "mrna_product": mrna,
                "direction": "5' to 3'"
            }
        }
    }
    
    return result


def translate_with_details(mrna_sequence: str) -> Dict:
    """Translate mRNA to amino acids with detailed analysis."""
    import math
    seq = mrna_sequence.upper().strip()
    codons = [seq[i:i+3] for i in range(0, len(seq) - 2, 3)]
    
    amino_acids = []
    amino_acid_details = []
    total_weight = 0
    hydrophobic_count = 0
    hydrophilic_count = 0
    charged_count = 0
    positive_count = 0
    negative_count = 0
    aromatic_count = 0
    aliphatic_count = 0
    tiny_count = 0
    small_count = 0
    polar_uncharged = 0
    
    # Aromatic amino acids
    aromatic_aa = ['Phenylalanine', 'Tyrosine', 'Tryptophan', 'Histidine']
    # Aliphatic amino acids
    aliphatic_aa = ['Alanine', 'Valine', 'Leucine', 'Isoleucine', 'Methionine']
    # Tiny amino acids
    tiny_aa = ['Alanine', 'Glycine', 'Serine']
    # Small amino acids
    small_aa = ['Alanine', 'Glycine', 'Serine', 'Threonine', 'Cysteine', 'Asparagine', 'Aspartate', 'Proline', 'Valine']
    
    pi_values = []
    
    for idx, codon in enumerate(codons):
        aa_name = CODON_MAP.get(codon, 'Unknown')
        amino_acids.append(aa_name)
        
        props = AMINO_ACID_PROPERTIES.get(aa_name, {})
        if props:
            mw = props.get('molecular_weight', 0)
            total_weight += mw
            pi_values.append(props.get('pI', 7.0))
            
            if props.get('type') == 'hydrophobic':
                hydrophobic_count += 1
            elif props.get('type') == 'hydrophilic':
                hydrophilic_count += 1
            
            polarity = props.get('polarity', '')
            if polarity == 'positive':
                charged_count += 1
                positive_count += 1
            elif polarity == 'negative':
                charged_count += 1
                negative_count += 1
            elif polarity == 'polar':
                polar_uncharged += 1
            
            if aa_name in aromatic_aa:
                aromatic_count += 1
            if aa_name in aliphatic_aa:
                aliphatic_count += 1
            if aa_name in tiny_aa:
                tiny_count += 1
            if aa_name in small_aa:
                small_count += 1
        
        amino_acid_details.append({
            "position": idx + 1,
            "codon": codon,
            "amino_acid": aa_name,
            "abbreviation": props.get('abbreviation', '?'),
            "single_letter": props.get('code', '?'),
            "type": props.get('type', 'unknown'),
            "polarity": props.get('polarity', 'unknown'),
            "molecular_weight": props.get('molecular_weight', 0),
            "pI": props.get('pI', 0),
            "is_aromatic": aa_name in aromatic_aa,
            "is_aliphatic": aa_name in aliphatic_aa
        })
    
    # Count amino acid frequencies
    aa_counts = dict(Counter(amino_acids))
    
    # Generate single-letter sequence
    single_letter_seq = ''.join([AMINO_ACID_PROPERTIES.get(aa, {}).get('code', 'X') for aa in amino_acids])
    
    total_aa = len(amino_acids)
    
    # Calculate amino acid percentages
    aa_percentages = {aa: round(count / total_aa * 100, 2) for aa, count in aa_counts.items()} if total_aa > 0 else {}
    
    # Group amino acids by property
    aa_by_property = {
        "hydrophobic": [aa for aa in amino_acids if AMINO_ACID_PROPERTIES.get(aa, {}).get('type') == 'hydrophobic'],
        "hydrophilic": [aa for aa in amino_acids if AMINO_ACID_PROPERTIES.get(aa, {}).get('type') == 'hydrophilic'],
        "positive_charged": [aa for aa in amino_acids if AMINO_ACID_PROPERTIES.get(aa, {}).get('polarity') == 'positive'],
        "negative_charged": [aa for aa in amino_acids if AMINO_ACID_PROPERTIES.get(aa, {}).get('polarity') == 'negative'],
        "polar_uncharged": [aa for aa in amino_acids if AMINO_ACID_PROPERTIES.get(aa, {}).get('polarity') == 'polar']
    }
    
    # Calculate GRAVY (Grand Average of Hydropathy)
    kyte_doolittle = {
        'Isoleucine': 4.5, 'Valine': 4.2, 'Leucine': 3.8, 'Phenylalanine': 2.8,
        'Cysteine': 2.5, 'Methionine': 1.9, 'Alanine': 1.8, 'Glycine': -0.4,
        'Threonine': -0.7, 'Serine': -0.8, 'Tryptophan': -0.9, 'Tyrosine': -1.3,
        'Proline': -1.6, 'Histidine': -3.2, 'Glutamate': -3.5, 'Glutamine': -3.5,
        'Aspartate': -3.5, 'Asparagine': -3.5, 'Lysine': -3.9, 'Arginine': -4.5
    }
    gravy = sum(kyte_doolittle.get(aa, 0) for aa in amino_acids) / total_aa if total_aa > 0 else 0
    
    # Calculate instability index (simplified)
    dipeptide_weights = {}  # Simplified - normally a 400-element table
    instability_sum = 0
    for i in range(len(amino_acids) - 1):
        # Simplified calculation
        instability_sum += 1
    instability_index = (10.0 / total_aa) * instability_sum if total_aa > 0 else 0
    
    # Calculate aliphatic index
    ala_pct = aa_counts.get('Alanine', 0) / total_aa * 100 if total_aa > 0 else 0
    val_pct = aa_counts.get('Valine', 0) / total_aa * 100 if total_aa > 0 else 0
    ile_pct = aa_counts.get('Isoleucine', 0) / total_aa * 100 if total_aa > 0 else 0
    leu_pct = aa_counts.get('Leucine', 0) / total_aa * 100 if total_aa > 0 else 0
    aliphatic_index = ala_pct + 2.9 * val_pct + 3.9 * (ile_pct + leu_pct)
    
    # Estimate isoelectric point (simplified)
    avg_pi = sum(pi_values) / len(pi_values) if pi_values else 7.0
    net_charge_ph7 = positive_count - negative_count
    
    # Calculate extinction coefficient at 280nm
    trp_count = aa_counts.get('Tryptophan', 0)
    tyr_count = aa_counts.get('Tyrosine', 0)
    cys_count = aa_counts.get('Cysteine', 0)
    extinction_280 = trp_count * 5500 + tyr_count * 1490 + (cys_count // 2) * 125
    
    # Secondary structure propensity (simplified)
    helix_formers = ['Alanine', 'Leucine', 'Methionine', 'Glutamate', 'Lysine']
    sheet_formers = ['Valine', 'Isoleucine', 'Tyrosine', 'Tryptophan', 'Threonine']
    helix_count = sum(1 for aa in amino_acids if aa in helix_formers)
    sheet_count = sum(1 for aa in amino_acids if aa in sheet_formers)
    
    # Find sequence motifs
    motifs = {
        "n_glycosylation_sites": [],  # N-X-S/T where X != P
        "phosphorylation_sites": [],
        "signal_peptide_likelihood": "low"
    }
    
    # Check for N-glycosylation sites (simplified)
    for i in range(len(amino_acids) - 2):
        if amino_acids[i] == 'Asparagine':
            if amino_acids[i+1] != 'Proline':
                if amino_acids[i+2] in ['Serine', 'Threonine']:
                    motifs["n_glycosylation_sites"].append({
                        "position": i + 1,
                        "motif": f"{amino_acids[i]}-{amino_acids[i+1]}-{amino_acids[i+2]}"
                    })
    
    # Calculate amino acid composition statistics
    composition_stats = {
        "most_common": max(aa_counts.items(), key=lambda x: x[1]) if aa_counts else None,
        "least_common": min(aa_counts.items(), key=lambda x: x[1]) if aa_counts else None,
        "unique_amino_acids": len(aa_counts),
        "diversity_index": len(aa_counts) / 20 if aa_counts else 0  # 20 standard amino acids
    }
    
    # ============== TOP-LEVEL: Core fields for Pattern extraction ==============
    result = {
        "mrna_input": seq,
        "amino_acid_chain": '-'.join(amino_acids),
        "single_letter_sequence": single_letter_seq,
        "total_amino_acids": total_aa,
        "contains_stop_codon": 'Stop' in amino_acids,
        
        # ============== DETAILED_ANALYSIS: Verbose data for Normal mode tokens ==============
        "detailed_analysis": {
            "amino_acid_counts": aa_counts,
            "amino_acid_percentages": aa_percentages,
            "amino_acid_details": amino_acid_details,
            "amino_acids_by_property": {k: len(v) for k, v in aa_by_property.items()},
            "composition_statistics": composition_stats,
            "protein_properties": {
                "estimated_molecular_weight_da": round(total_weight, 2),
                "estimated_molecular_weight_kda": round(total_weight / 1000, 3),
                "hydrophobic_residues": hydrophobic_count,
                "hydrophilic_residues": hydrophilic_count,
                "charged_residues": charged_count,
                "positive_charged": positive_count,
                "negative_charged": negative_count,
                "polar_uncharged": polar_uncharged,
                "aromatic_residues": aromatic_count,
                "aliphatic_residues": aliphatic_count,
                "tiny_residues": tiny_count,
                "small_residues": small_count,
                "hydrophobicity_ratio": round(hydrophobic_count / total_aa, 3) if total_aa > 0 else 0
            },
            "biophysical_properties": {
                "gravy_score": round(gravy, 3),
                "gravy_interpretation": "hydrophobic" if gravy > 0 else "hydrophilic",
                "aliphatic_index": round(aliphatic_index, 2),
                "instability_index": round(instability_index, 2),
                "is_stable": instability_index < 40,
                "estimated_pI": round(avg_pi, 2),
                "net_charge_at_ph7": net_charge_ph7,
                "extinction_coefficient_280nm": extinction_280,
                "absorbance_01_percent": round(extinction_280 / total_weight, 4) if total_weight > 0 else 0
            },
            "secondary_structure_propensity": {
                "helix_forming_residues": helix_count,
                "sheet_forming_residues": sheet_count,
                "helix_propensity": round(helix_count / total_aa * 100, 1) if total_aa > 0 else 0,
                "sheet_propensity": round(sheet_count / total_aa * 100, 1) if total_aa > 0 else 0,
                "predicted_structure": "alpha-helix rich" if helix_count > sheet_count else "beta-sheet rich" if sheet_count > helix_count else "mixed"
            },
            "sequence_motifs": motifs,
            "stop_position": amino_acids.index('Stop') if 'Stop' in amino_acids else -1,
            "translation_summary": {
                "input_length_nt": len(seq),
                "output_length_aa": total_aa,
                "coding_efficiency": round(total_aa * 3 / len(seq) * 100, 1) if len(seq) > 0 else 0
            }
        }
    }
    
    return result


def find_max_nucleotide_enhanced(nucleotide_counts: dict) -> Dict:
    """Find max nucleotide with detailed statistics."""
    if not nucleotide_counts:
        return {"error": "Empty nucleotide counts"}
    
    # Handle case where full result dict is passed instead of just counts
    if 'nucleotide_counts' in nucleotide_counts:
        nucleotide_counts = nucleotide_counts['nucleotide_counts']
    
    # Validate that we have proper nucleotide counts (should only have A, T, G, C keys with int values)
    valid_nucs = {'A', 'T', 'G', 'C'}
    filtered_counts = {}
    for key, value in nucleotide_counts.items():
        if key in valid_nucs and isinstance(value, (int, float)):
            filtered_counts[key] = int(value)
    
    if not filtered_counts:
        return {"error": "No valid nucleotide counts found. Expected {'A': int, 'T': int, 'G': int, 'C': int}"}
    
    nucleotide_counts = filtered_counts
    
    max_nuc = max(nucleotide_counts, key=nucleotide_counts.get)
    min_nuc = min(nucleotide_counts, key=nucleotide_counts.get)
    total = sum(nucleotide_counts.values())
    
    sorted_nucs = sorted(nucleotide_counts.items(), key=lambda x: -x[1])
    
    return {
        "max_nucleotide": {
            "nucleotide": max_nuc,
            "count": nucleotide_counts[max_nuc],
            "percentage": round(nucleotide_counts[max_nuc] / total * 100, 2) if total > 0 else 0
        },
        "min_nucleotide": {
            "nucleotide": min_nuc,
            "count": nucleotide_counts[min_nuc],
            "percentage": round(nucleotide_counts[min_nuc] / total * 100, 2) if total > 0 else 0
        },
        "ranking": [{"nucleotide": n, "count": c, "rank": i+1} for i, (n, c) in enumerate(sorted_nucs)],
        "total_nucleotides": total,
        "balance_ratio": round(min(nucleotide_counts.values()) / max(nucleotide_counts.values()), 3) if max(nucleotide_counts.values()) > 0 else 0,
        "is_balanced": all(abs(c/total - 0.25) < 0.1 for c in nucleotide_counts.values()) if total > 0 else False
    }


def reverse_transcribe_enhanced(mrna_sequence: str) -> Dict:
    """Reverse transcribe mRNA to DNA with analysis."""
    seq = mrna_sequence.upper().strip()
    reverse_transcription_map = str.maketrans('UCAG', 'AGTC')
    dna = seq.translate(reverse_transcription_map)

    return {
        "mrna_input": seq,
        "dna_output": dna,
        "length": len(dna),
        "reverse_transcription_rule": "U→A, C→G, A→T, G→C",
        "verification": {
            "input_length": len(seq),
            "output_length": len(dna),
            "lengths_match": len(seq) == len(dna)
        }
    }


# ============== Tool Handlers ==============

async def on_validate_and_analyze_dna(context: RunContextWrapper, params_str: str) -> Any:
    params = json.loads(params_str)
    dna_sequence = params.get("dna_sequence", "")
    result = validate_and_analyze_dna(dna_sequence)
    return result


async def on_transcribe_with_details(context: RunContextWrapper, params_str: str) -> Any:
    params = json.loads(params_str)
    dna_sequence = params.get("dna_sequence", "")
    result = transcribe_with_details(dna_sequence)
    return result


async def on_translate_with_details(context: RunContextWrapper, params_str: str) -> Any:
    params = json.loads(params_str)
    mrna_sequence = params.get("mrna_sequence", "")
    result = translate_with_details(mrna_sequence)
    return result


async def on_find_max_nucleotide_enhanced(context: RunContextWrapper, params_str: str) -> Any:
    params = json.loads(params_str)
    nucleotide_counts = params.get("nucleotide_counts", {})
    result = find_max_nucleotide_enhanced(nucleotide_counts)
    return result


async def on_reverse_transcribe_enhanced(context: RunContextWrapper, params_str: str) -> Any:
    params = json.loads(params_str)
    mrna_sequence = params.get("mrna_sequence", "")
    result = reverse_transcribe_enhanced(mrna_sequence)
    return result


# ============== Tool Definitions (Enhanced) ==============

tool_validate_dna = FunctionTool(
    name='local-dna_is_valid',
    description='''Validates DNA sequence and provides comprehensive analysis including nucleotide counts, GC content, dinucleotide frequencies, repeat patterns, and molecular properties.

**Input:** dna_sequence (str)

**Returns:** dict:
{
  "is_valid": bool,
  "length": int,
  "nucleotide_counts": {"A": int, "T": int, "G": int, "C": int},
  "gc_content": float,
  "molecular_weight": float,
  "repeat_patterns": [...]
}''',
    params_json_schema={
        "type": "object",
        "properties": {
            "dna_sequence": {
                "type": "string",
                "description": 'The DNA sequence to validate and analyze',
            },
        },
        "required": ["dna_sequence"]
    },
    on_invoke_tool=on_validate_and_analyze_dna
)

tool_count_nucleotides = FunctionTool(
    name='local-dna_count_nucleotides',
    description='''Validates DNA and returns detailed nucleotide analysis including counts, percentages, GC content, repeat patterns, and molecular weight estimates.

**Input:** dna_sequence (str)

**Returns:** dict:
{
  "counts": {"A": int, "T": int, "G": int, "C": int},
  "percentages": {"A": float, "T": float, "G": float, "C": float},
  "gc_content": float,
  "at_content": float,
  "molecular_weight": float
}''',
    params_json_schema={
        "type": "object",
        "properties": {
            "dna_sequence": {
                "type": "string",
                "description": 'The DNA sequence to analyze',
            },
        },
        "required": ["dna_sequence"]
    },
    on_invoke_tool=on_validate_and_analyze_dna
)

tool_transcribe_dna_to_mrna = FunctionTool(
    name='local-dna_transcribe_to_mrna',
    description='''Transcribes DNA to mRNA with detailed codon analysis, start/stop codon positions, and codon usage statistics.

**Input:** dna_sequence (str)

**Returns:** dict:
{
  "mrna_sequence": str,
  "length": int,
  "codons": [str],
  "codon_count": int,
  "start_codon_positions": [int],
  "stop_codon_positions": [int],
  "codon_usage": {...}
}''',
    params_json_schema={
        "type": "object",
        "properties": {
            "dna_sequence": {
                "type": "string",
                "description": 'The DNA sequence to transcribe',
            },
        },
        "required": ["dna_sequence"]
    },
    on_invoke_tool=on_transcribe_with_details
)

tool_translate_mrna_to_amino_acid = FunctionTool(
    name='local-dna_translate_to_amino',
    description='''Translates mRNA to amino acids with detailed per-codon breakdown, protein properties (molecular weight, hydrophobicity), and amino acid statistics.

**Input:** mrna_sequence (str)

**Returns:** dict:
{
  "amino_acid_sequence": str,
  "protein_length": int,
  "molecular_weight": float,
  "codon_breakdown": [{"codon": str, "amino_acid": str}],
  "amino_acid_stats": {...}
}''',
    params_json_schema={
        "type": "object",
        "properties": {
            "mrna_sequence": {
                "type": "string",
                "description": 'The mRNA sequence to translate',
            },
        },
        "required": ["mrna_sequence"]
    },
    on_invoke_tool=on_translate_with_details
)

tool_find_max_nucleotide = FunctionTool(
    name='local-dna_find_max_nucleotide',
    description='''Finds nucleotide with maximum count, plus ranking, balance ratio, and detailed statistics.

**Input:** nucleotide_counts (dict) - e.g., {"A": 100, "T": 90, "G": 80, "C": 70}

**Returns:** dict:
{
  "max_nucleotide": str,
  "max_count": int,
  "ranking": [{"nucleotide": str, "count": int}],
  "balance_ratio": float,
  "statistics": {...}
}''',
    params_json_schema={
        "type": "object",
        "properties": {
            "nucleotide_counts": {
                "type": "object",
                "description": 'Dictionary of nucleotide counts',
            },
        },
        "required": ["nucleotide_counts"]
    },
    on_invoke_tool=on_find_max_nucleotide_enhanced
)

tool_reverse_transcribe = FunctionTool(
    name='local-dna_reverse_transcribe',
    description='''Reverse transcribes mRNA to DNA with verification.

**Input:** mrna_sequence (str)

**Returns:** dict:
{
  "dna_sequence": str,
  "length": int,
  "verified": bool
}''',
    params_json_schema={
        "type": "object",
        "properties": {
            "mrna_sequence": {
                "type": "string",
                "description": 'The mRNA sequence to reverse transcribe',
            },
        },
        "required": ["mrna_sequence"]
    },
    on_invoke_tool=on_reverse_transcribe_enhanced
)

# Export all tools as a list
dna_tools = [
    tool_validate_dna,
    tool_count_nucleotides,
    tool_transcribe_dna_to_mrna,
    tool_translate_mrna_to_amino_acid,
    tool_find_max_nucleotide,
    tool_reverse_transcribe,
]
