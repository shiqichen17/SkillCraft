"""
Free Dictionary API Tools

Provides tools to look up word definitions, pronunciations, and examples.
Designed for skill mode scenarios with structured vocabulary data.

API Documentation: https://dictionaryapi.dev/
No authentication required.
"""

import json
from typing import Any
from agents.tool import FunctionTool, RunContextWrapper
import requests

# Base URL for Free Dictionary API
DICTIONARY_BASE_URL = "https://api.dictionaryapi.dev/api/v2/entries"


def _make_request(endpoint: str) -> list:
    """Make a request to Dictionary API with error handling."""
    url = f"{DICTIONARY_BASE_URL}{endpoint}"
    headers = {"User-Agent": "DikaNong-PatternReuse/1.0"}
    
    try:
        response = requests.get(url, headers=headers, timeout=15)
        if response.status_code == 404:
            return [{"error": "Word not found", "success": False}]
        response.raise_for_status()
        return response.json()
    except requests.exceptions.Timeout:
        return [{"error": "Request timeout", "success": False}]
    except requests.exceptions.RequestException as e:
        return [{"error": str(e), "success": False}]
    except json.JSONDecodeError:
        return [{"error": "Invalid JSON response", "success": False}]


def _parse_params(params_str: str) -> dict:
    """Parse parameters from string."""
    if not params_str:
        return {}
    if isinstance(params_str, dict):
        return params_str
    try:
        return json.loads(params_str)
    except json.JSONDecodeError:
        return {}


# ============== Tool Implementation Functions ==============

def _lookup_word(word: str, language: str = "en") -> dict:
    """Look up a word in the dictionary with VERBOSE extended data for skill mode."""
    import random
    random.seed(hash(word) % 10000)
    
    data = _make_request(f"/{language}/{word}")
    
    if isinstance(data, list) and len(data) > 0:
        if "error" in data[0]:
            return data[0]
        
        entry = data[0]
        
        # Extract phonetics - VERBOSE: all variants
        phonetics = entry.get("phonetics", [])
        pronunciation = None
        audio_url = None
        all_phonetics = []
        for p in phonetics:
            if p.get("text"):
                if not pronunciation:
                    pronunciation = p.get("text")
                all_phonetics.append({
                    "text": p.get("text"),
                    "audio": p.get("audio"),
                    "source_license": p.get("sourceUrl", "Unknown")
                })
            if p.get("audio") and not audio_url:
                audio_url = p.get("audio")
        
        # Extract meanings - VERBOSE: ALL definitions
        meanings = []
        all_definitions = []
        synonyms = set()
        antonyms = set()
        
        for meaning in entry.get("meanings", []):
            part_of_speech = meaning.get("partOfSpeech")
            definitions = []
            
            # VERBOSE: Get ALL definitions, not just 3
            for defn in meaning.get("definitions", []):
                def_obj = {
                    "definition": defn.get("definition"),
                    "example": defn.get("example"),
                    "synonyms": defn.get("synonyms", []),
                    "antonyms": defn.get("antonyms", [])
                }
                definitions.append(def_obj)
                all_definitions.append(defn.get("definition"))
                
                # Collect synonyms and antonyms
                for syn in defn.get("synonyms", []):
                    synonyms.add(syn)
                for ant in defn.get("antonyms", []):
                    antonyms.add(ant)
            
            # Also get part-level synonyms/antonyms
            for syn in meaning.get("synonyms", []):
                synonyms.add(syn)
            for ant in meaning.get("antonyms", []):
                antonyms.add(ant)
            
            meanings.append({
                "part_of_speech": part_of_speech,
                "definition_count": len(definitions),
                "definitions": definitions,
                "part_synonyms": meaning.get("synonyms", []),
                "part_antonyms": meaning.get("antonyms", [])
            })
        
        # VERBOSE: Generate synthetic related words analysis
        related_words_analysis = []
        base_synonyms = list(synonyms)
        
        # ULTRA VERBOSE: Generate 80 related word entries for skill mode
        related_patterns = ["similar", "related", "derived", "compound", "opposite"]
        for i in range(80):
            if i < len(base_synonyms):
                rel_word = base_synonyms[i]
                relationship = "synonym"
            else:
                # Generate synthetic related words
                suffixes = ["ness", "ly", "ment", "tion", "able", "ful", "less", "ize", "er", "ist"]
                prefixes = ["un", "re", "pre", "dis", "mis", "over", "under", "out", "non", "anti"]
                
                if i % 3 == 0 and len(word) > 3:
                    rel_word = word + random.choice(suffixes)
                    relationship = "derived"
                elif i % 3 == 1:
                    rel_word = random.choice(prefixes) + word
                    relationship = "compound"
                else:
                    rel_word = f"{word}-related-{i}"
                    relationship = "related"
            
            related_words_analysis.append({
                "word": rel_word,
                "relationship": relationship,
                "similarity_score": round(random.uniform(0.5, 0.95), 3),
                "frequency_rank": random.randint(1000, 50000),
                "common_contexts": random.sample(["formal", "informal", "academic", "literary", "technical", "colloquial", "archaic", "modern"], 3),
                "part_of_speech": random.choice(["noun", "verb", "adjective", "adverb"]),
                # ULTRA VERBOSE: Extended word relationship data
                "corpus_frequency": random.randint(100, 1000000),
                "first_recorded_use": random.randint(1200, 2000),
                "syllable_count": random.randint(1, 5),
                "phonetic_similarity": round(random.uniform(0.3, 0.95), 3),
                "semantic_field": random.choice(["emotion", "action", "state", "quality", "object", "person", "place", "time"]),
                "register": random.choice(["formal", "neutral", "informal", "slang", "technical", "literary"]),
                "connotation": random.choice(["positive", "negative", "neutral"]),
                "collocates": random.sample(["make", "take", "do", "have", "get", "good", "bad", "very", "more", "much"], 4),
                "example_sentence": f"The word '{rel_word}' is commonly used in {random.choice(['academic', 'everyday', 'professional', 'literary'])} contexts.",
                "difficulty_level": random.choice(["basic", "intermediate", "advanced", "specialized"]),
                "learning_priority": random.randint(1, 10)
            })
        
        # VERBOSE: Generate usage patterns
        usage_contexts = ["formal writing", "academic papers", "casual conversation", "business communication", 
                        "literature", "technical documents", "news articles", "social media", "legal documents", "scientific papers"]
        
        usage_patterns = []
        for context in usage_contexts:
            usage_patterns.append({
                "context": context,
                "frequency": random.choice(["very common", "common", "moderate", "uncommon", "rare"]),
                "formality_level": random.choice(["very formal", "formal", "neutral", "informal", "very informal"]),
                "typical_collocations": [f"{random.choice(['make', 'take', 'do', 'have', 'get'])} {word}", 
                                        f"{word} {random.choice(['of', 'for', 'with', 'to', 'in'])}"],
                "example_sentence": f"In {context.lower()}, '{word}' is often used to express {random.choice(['intensity', 'quality', 'action', 'state', 'emotion'])}."
            })
        
        # VERBOSE: Historical usage data
        historical_usage = []
        for decade in range(1800, 2030, 20):
            historical_usage.append({
                "period": f"{decade}s",
                "relative_frequency": round(random.uniform(0.1, 1.0), 3),
                "dominant_meaning": random.choice([d for d in all_definitions]) if all_definitions else "primary meaning",
                "notable_shift": random.choice([None, "meaning expanded", "meaning narrowed", "new usage emerged", "archaic usage declined"])
            })
        
        # VERBOSE: Linguistic analysis
        syllable_count = len([c for c in pronunciation or "" if c in "aeiouəɪʊɔæɛ"]) or max(1, len(word) // 3)
        
        linguistic_analysis = {
            "word_length": len(word),
            "syllable_count": syllable_count,
            "morphological_structure": {
                "prefix": word[:2] if len(word) > 4 else None,
                "root": word[2:-2] if len(word) > 4 else word,
                "suffix": word[-2:] if len(word) > 4 else None
            },
            "phonetic_features": {
                "starts_with_vowel": word[0].lower() in "aeiou",
                "ends_with_vowel": word[-1].lower() in "aeiou",
                "contains_digraph": any(dg in word.lower() for dg in ["th", "ch", "sh", "ph", "wh", "ng"]),
                "consonant_clusters": sum(1 for i in range(len(word)-1) if word[i].lower() not in "aeiou" and word[i+1].lower() not in "aeiou")
            },
            "etymology_analysis": {
                "likely_origin": random.choice(["Latin", "Greek", "Old English", "French", "German", "Norse", "Arabic"]),
                "language_family": random.choice(["Indo-European", "Germanic", "Romance", "Semitic"]),
                "borrowing_period": random.choice(["Ancient", "Medieval", "Early Modern", "Modern"])
            },
            "register_analysis": {
                "formality": random.choice(["very formal", "formal", "neutral", "informal"]),
                "domain": random.choice(["general", "academic", "technical", "colloquial", "literary"]),
                "connotation": random.choice(["positive", "neutral", "negative", "context-dependent"])
            }
        }
        
        return {
            "success": True,
            "word": entry.get("word"),
            "phonetic": pronunciation,
            "audio_url": audio_url,
            "origin": entry.get("origin"),
            "meanings": meanings,
            "definition_count": len(all_definitions),
            "primary_definition": all_definitions[0] if all_definitions else None,
            "synonyms": list(synonyms),
            "antonyms": list(antonyms),
            # VERBOSE: Extended data for pattern to extract summary from
            "all_phonetics": all_phonetics,
            "related_words_analysis": {
                "total_analyzed": len(related_words_analysis),
                "words": related_words_analysis
            },
            "usage_patterns": usage_patterns,
            "historical_usage": historical_usage,
            "linguistic_analysis": linguistic_analysis
        }
    
    return {"error": f"Word '{word}' not found", "success": False}


def _get_synonyms(word: str) -> dict:
    """Get synonyms for a word."""
    result = _lookup_word(word)
    
    if not result.get("success"):
        return result
    
    return {
        "success": True,
        "word": result.get("word"),
        "synonyms": result.get("synonyms", []),
        "count": len(result.get("synonyms", []))
    }


def _get_definitions(word: str) -> dict:
    """Get just the definitions for a word."""
    result = _lookup_word(word)
    
    if not result.get("success"):
        return result
    
    definitions = []
    for meaning in result.get("meanings", []):
        for defn in meaning.get("definitions", []):
            definitions.append({
                "part_of_speech": meaning.get("part_of_speech"),
                "definition": defn.get("definition"),
                "example": defn.get("example")
            })
    
    return {
        "success": True,
        "word": result.get("word"),
        "definitions": definitions,
        "count": len(definitions)
    }


def _get_word_details(word: str) -> dict:
    """Get comprehensive word details with VERBOSE analysis for skill mode."""
    import random
    random.seed(hash(word) % 10000)
    
    result = _lookup_word(word)
    
    if not result.get("success"):
        return result
    
    # Determine word complexity
    syllable_count = len([c for c in result.get("phonetic", "") if c in "aeiouəɪʊɔæɛ"])
    if syllable_count == 0:
        syllable_count = max(1, len(word) // 3)
    
    complexity = "simple" if syllable_count <= 2 else "moderate" if syllable_count <= 4 else "complex"
    
    # VERBOSE: Generate comprehensive word family analysis
    word_family = []
    suffixes = ["ness", "ly", "ment", "tion", "able", "ful", "less", "ize", "er", "ist", "ity", "ous", "ive", "al"]
    prefixes = ["un", "re", "pre", "dis", "mis", "over", "under", "out", "non", "anti", "semi", "multi", "super", "sub"]
    
    for i in range(25):
        if i < len(suffixes):
            derived_word = word + suffixes[i]
            derivation_type = "suffix"
        elif i < len(suffixes) + len(prefixes):
            derived_word = prefixes[i - len(suffixes)] + word
            derivation_type = "prefix"
        else:
            derived_word = f"{word}{random.choice(suffixes)}"
            derivation_type = "compound"
        
        word_family.append({
            "word": derived_word,
            "derivation_type": derivation_type,
            "part_of_speech": random.choice(["noun", "verb", "adjective", "adverb"]),
            "definition_preview": f"Related to {word}: {random.choice(['quality of', 'act of', 'state of', 'relating to', 'without', 'with'])} {word}",
            "frequency": random.choice(["common", "moderate", "uncommon", "rare"]),
            "formality": random.choice(["formal", "neutral", "informal"])
        })
    
    # VERBOSE: Cross-language cognates
    languages = ["Spanish", "French", "German", "Italian", "Portuguese", "Dutch", "Swedish", "Danish", "Norwegian", "Latin", "Greek"]
    cognates = []
    for lang in languages:
        cognates.append({
            "language": lang,
            "cognate": f"{word}_{lang[:2].lower()}",
            "similarity": round(random.uniform(0.3, 0.9), 2),
            "meaning_preserved": random.choice([True, True, True, False]),
            "false_friend_warning": random.choice([None, None, None, "partial meaning shift", "different connotation"])
        })
    
    # VERBOSE: Collocations analysis
    collocations = []
    verb_collocations = ["make", "take", "do", "have", "get", "give", "put", "bring", "keep", "hold"]
    prep_collocations = ["of", "for", "with", "to", "in", "on", "at", "by", "from", "about"]
    
    for v in verb_collocations:
        collocations.append({
            "pattern": f"{v} + {word}",
            "type": "verb_noun",
            "frequency": random.randint(100, 10000),
            "example": f"You should {v} {word} carefully.",
            "register": random.choice(["formal", "neutral", "informal"])
        })
    
    for p in prep_collocations:
        collocations.append({
            "pattern": f"{word} + {p}",
            "type": "noun_prep",
            "frequency": random.randint(100, 10000),
            "example": f"The {word} {p} something is important.",
            "register": random.choice(["formal", "neutral", "informal"])
        })
    
    return {
        "success": True,
        "word": result.get("word"),
        "phonetic": result.get("phonetic"),
        "audio_url": result.get("audio_url"),
        "origin": result.get("origin"),
        "meanings": result.get("meanings"),
        "synonyms": result.get("synonyms"),
        "antonyms": result.get("antonyms"),
        "complexity": complexity,
        "estimated_syllables": syllable_count,
        "part_of_speech_count": len(result.get("meanings", [])),
        # VERBOSE: Extended analysis for pattern to extract summary from
        "word_family": {
            "total_derivatives": len(word_family),
            "derivatives": word_family
        },
        "cross_language_cognates": {
            "languages_analyzed": len(cognates),
            "cognates": cognates
        },
        "collocations_analysis": {
            "total_collocations": len(collocations),
            "collocations": collocations
        },
        "usage_patterns": result.get("usage_patterns", []),
        "historical_usage": result.get("historical_usage", []),
        "linguistic_analysis": result.get("linguistic_analysis", {})
    }


def _get_word_phonetics(word: str) -> dict:
    """Get phonetic information and pronunciation for a word."""
    result = _lookup_word(word)
    
    if not result.get("success"):
        return result
    
    # Extract all phonetics
    phonetics = result.get("phonetics", [])
    audio_urls = [p.get("audio") for p in phonetics if p.get("audio")]
    ipa_texts = [p.get("text") for p in phonetics if p.get("text")]
    
    # Analyze pronunciation difficulty
    phonetic_text = result.get("phonetic", "")
    has_schwa = "ə" in phonetic_text
    has_stress = "ˈ" in phonetic_text or "ˌ" in phonetic_text
    
    difficulty = "easy"
    if has_schwa or len(phonetic_text) > 8:
        difficulty = "moderate"
    if len(ipa_texts) > 2 or (has_schwa and has_stress):
        difficulty = "challenging"
    
    return {
        "success": True,
        "word": result.get("word"),
        "primary_phonetic": result.get("phonetic"),
        "all_phonetics": ipa_texts[:5],
        "audio_urls": audio_urls[:3],
        "has_audio": len(audio_urls) > 0,
        "pronunciation_analysis": {
            "difficulty": difficulty,
            "has_schwa": has_schwa,
            "has_stress_marks": has_stress,
            "syllable_estimate": max(1, len([c for c in phonetic_text if c in "aeiouəɪʊɔæɛ"]))
        },
        "regional_variants": len(ipa_texts)
    }


# ============== Tool Handlers ==============

async def on_lookup_word(context: RunContextWrapper, params_str: str) -> Any:
    """Handler for word lookup."""
    params = _parse_params(params_str)
    word = params.get("word")
    language = params.get("language", "en")
    
    if not word:
        return {"error": "word is required", "success": False}
    
    result = _lookup_word(word, language)
    return result


async def on_get_synonyms(context: RunContextWrapper, params_str: str) -> Any:
    """Handler for getting synonyms."""
    params = _parse_params(params_str)
    word = params.get("word")
    
    if not word:
        return {"error": "word is required", "success": False}
    
    result = _get_synonyms(word)
    return result


async def on_get_definitions(context: RunContextWrapper, params_str: str) -> Any:
    """Handler for getting definitions."""
    params = _parse_params(params_str)
    word = params.get("word")
    
    if not word:
        return {"error": "word is required", "success": False}
    
    result = _get_definitions(word)
    return result


async def on_get_word_details(context: RunContextWrapper, params_str: str) -> Any:
    """Handler for comprehensive word details."""
    params = _parse_params(params_str)
    word = params.get("word")
    
    if not word:
        return {"error": "word is required", "success": False}
    
    result = _get_word_details(word)
    return result


async def on_get_word_phonetics(context: RunContextWrapper, params_str: str) -> Any:
    """Handler for word phonetics."""
    params = _parse_params(params_str)
    word = params.get("word")
    
    if not word:
        return {"error": "word is required", "success": False}
    
    result = _get_word_phonetics(word)
    return result


# ============== Tool Definitions ==============

tool_dictionary_lookup = FunctionTool(
    name='local-dictionary_lookup',
    description='''Look up a word in the dictionary to get definitions, pronunciation, and more.

Returns dict:
{
    "success": bool,              # Whether lookup succeeded
    "word": str,                  # The word looked up
    "phonetic": str | None,       # Phonetic transcription (e.g., "/həˈloʊ/")
    "audio_url": str | None,      # URL to pronunciation audio
    "origin": str | None,         # Etymology/origin of the word
    "meanings": [                 # List of meanings by part of speech
        {
            "part_of_speech": str,  # e.g., "noun", "verb", "adjective"
            "definitions": [
                {
                    "definition": str,   # The definition text
                    "example": str | None  # Example sentence
                }
            ]
        }
    ],
    "definition_count": int,      # Total number of definitions
    "primary_definition": str,    # First/main definition
    "synonyms": [str],           # List of synonyms (up to 10)
    "antonyms": [str]            # List of antonyms (up to 10)
}

On error: {"error": str, "success": False}''',
    params_json_schema={
        "type": "object",
        "properties": {
            "word": {
                "type": "string",
                "description": "The word to look up"
            },
            "language": {
                "type": "string",
                "description": "Language code (default: 'en')"
            }
        },
        "required": ["word"]
    },
    on_invoke_tool=on_lookup_word
)

tool_dictionary_synonyms = FunctionTool(
    name='local-dictionary_synonyms',
    description='''Get synonyms for a word.

Returns dict:
{
    "success": bool,           # Whether lookup succeeded
    "word": str,               # The word queried
    "synonyms": [str],         # List of synonyms (up to 10)
    "count": int               # Number of synonyms found
}

On error: {"error": str, "success": False}''',
    params_json_schema={
        "type": "object",
        "properties": {
            "word": {
                "type": "string",
                "description": "The word to find synonyms for"
            }
        },
        "required": ["word"]
    },
    on_invoke_tool=on_get_synonyms
)

tool_dictionary_definitions = FunctionTool(
    name='local-dictionary_definitions',
    description='''Get all definitions for a word organized by part of speech.

Returns dict:
{
    "success": bool,           # Whether lookup succeeded
    "word": str,               # The word queried
    "definitions": [           # List of all definitions
        {
            "part_of_speech": str,   # e.g., "noun", "verb"
            "definition": str,       # The definition text
            "example": str | None    # Example sentence
        }
    ],
    "count": int               # Total number of definitions
}

On error: {"error": str, "success": False}''',
    params_json_schema={
        "type": "object",
        "properties": {
            "word": {
                "type": "string",
                "description": "The word to get definitions for"
            }
        },
        "required": ["word"]
    },
    on_invoke_tool=on_get_definitions
)

tool_dictionary_details = FunctionTool(
    name='local-dictionary_word_details',
    description='''Get comprehensive word details including etymology, complexity, and all meanings.

Returns dict:
{
    "success": bool,              # Whether lookup succeeded
    "word": str,                  # The word analyzed
    "phonetic": str | None,       # Phonetic transcription
    "audio_url": str | None,      # URL to pronunciation audio
    "origin": str | None,         # Etymology/origin
    "meanings": [                 # List of meanings
        {
            "part_of_speech": str,
            "definitions": [{"definition": str, "example": str | None}]
        }
    ],
    "synonyms": [str],           # List of synonyms
    "antonyms": [str],           # List of antonyms
    "complexity": str,           # Word complexity: "simple", "moderate", or "complex"
    "estimated_syllables": int,  # Estimated syllable count
    "part_of_speech_count": int  # Number of different parts of speech
}

On error: {"error": str, "success": False}''',
    params_json_schema={
        "type": "object",
        "properties": {
            "word": {
                "type": "string",
                "description": "The word to analyze"
            }
        },
        "required": ["word"]
    },
    on_invoke_tool=on_get_word_details
)


tool_dictionary_phonetics = FunctionTool(
    name='local-dictionary_phonetics',
    description='''Get phonetic information and pronunciation details for a word.

**Returns:** dict:
{
  "success": bool,
  "word": str,                        # The word queried
  "primary_phonetic": str | null,     # Main IPA pronunciation
  "all_phonetics": [str],             # Up to 5 IPA variants
  "audio_urls": [str],                # Up to 3 audio pronunciation URLs
  "has_audio": bool,                  # Whether audio is available
  "pronunciation_analysis": {
    "difficulty": str,                # "easy", "moderate", or "challenging"
    "has_schwa": bool,                # Contains schwa sound (ə)
    "has_stress_marks": bool,         # Contains stress markers
    "syllable_estimate": int          # Estimated syllable count
  },
  "regional_variants": int            # Number of pronunciation variants
}''',
    params_json_schema={
        "type": "object",
        "properties": {
            "word": {
                "type": "string",
                "description": "The word to get phonetics for"
            }
        },
        "required": ["word"]
    },
    on_invoke_tool=on_get_word_phonetics
)


# Export all tools as a list
dictionary_tools = [
    tool_dictionary_lookup,
    tool_dictionary_synonyms,
    tool_dictionary_definitions,
    tool_dictionary_details,
    tool_dictionary_phonetics,
]

