# tool_name_resolver.py
# Unified tool name resolution and auto-correction logic
"""
This module provides robust tool name resolution to handle common LLM mistakes:

1. Using underscore instead of hyphen for prefix separator:
   - local_claim_done → local-claim_done
   - filesystem_read_file → filesystem-read_file

2. Forgetting the prefix entirely:
   - claim_done → local-claim_done
   - read_file → (depends on available tools)

3. Mixed formats:
   - local_gitlab_get_project_info → local-gitlab_get_project_info

Resolution Strategy (in order):
1. Try exact match
2. Try replacing first underscore with hyphen (prefix correction)
3. Try adding 'local-' prefix
4. Try adding 'local-' prefix + replacing first underscore with hyphen
"""

from typing import Optional, Set, List, Callable
import logging

logger = logging.getLogger(__name__)


def normalize_tool_name(
    tool_name: str,
    available_tools: Set[str],
    default_prefix: str = "local"
) -> tuple[str, bool]:
    """
    Normalize a tool name to match available tools.
    
    Args:
        tool_name: The tool name to normalize (may be malformed)
        available_tools: Set of valid tool names to match against
        default_prefix: Default prefix to try if tool not found (default: "local")
        
    Returns:
        Tuple of (normalized_name, was_corrected)
        - normalized_name: The corrected tool name (or original if no correction found)
        - was_corrected: True if the name was modified
        
    Examples:
        >>> available = {"local-claim_done", "filesystem-read_file", "local-gitlab_get_info"}
        >>> normalize_tool_name("local-claim_done", available)
        ("local-claim_done", False)  # Exact match
        >>> normalize_tool_name("local_claim_done", available)
        ("local-claim_done", True)   # Underscore → hyphen
        >>> normalize_tool_name("claim_done", available)
        ("local-claim_done", True)   # Added prefix
        >>> normalize_tool_name("filesystem_read_file", available)
        ("filesystem-read_file", True)  # Underscore → hyphen
    """
    original_name = tool_name
    
    # Strategy 1: Exact match
    if tool_name in available_tools:
        return tool_name, False
    
    # Strategy 2: Replace first underscore with hyphen (prefix correction)
    # This handles: local_claim_done → local-claim_done
    #               filesystem_read_file → filesystem-read_file
    if '_' in tool_name:
        first_underscore_idx = tool_name.index('_')
        corrected = tool_name[:first_underscore_idx] + '-' + tool_name[first_underscore_idx + 1:]
        if corrected in available_tools:
            logger.info(f"Tool name auto-corrected (underscore→hyphen): '{original_name}' → '{corrected}'")
            return corrected, True
    
    # Strategy 3: Add default prefix
    # This handles: claim_done → local-claim_done
    prefixed = f"{default_prefix}-{tool_name}"
    if prefixed in available_tools:
        logger.info(f"Tool name auto-corrected (added prefix): '{original_name}' → '{prefixed}'")
        return prefixed, True
    
    # Strategy 4: Add default prefix + replace first underscore with hyphen
    # This handles edge cases where both issues exist
    if '_' in tool_name:
        first_underscore_idx = tool_name.index('_')
        name_with_hyphen = tool_name[:first_underscore_idx] + '-' + tool_name[first_underscore_idx + 1:]
        prefixed_corrected = f"{default_prefix}-{name_with_hyphen}"
        if prefixed_corrected in available_tools:
            logger.info(f"Tool name auto-corrected (prefix + underscore→hyphen): '{original_name}' → '{prefixed_corrected}'")
            return prefixed_corrected, True
    
    # Strategy 5: Try replacing ALL underscores with hyphens (full normalization)
    # This handles: local_list_skills → local-list-skills
    all_hyphens = tool_name.replace('_', '-')
    if all_hyphens in available_tools:
        logger.info(f"Tool name auto-corrected (all underscores→hyphens): '{original_name}' → '{all_hyphens}'")
        return all_hyphens, True
    
    # Strategy 6: Add prefix + replace ALL underscores with hyphens
    prefixed_all_hyphens = f"{default_prefix}-{all_hyphens}"
    if prefixed_all_hyphens in available_tools:
        logger.info(f"Tool name auto-corrected (prefix + all underscores→hyphens): '{original_name}' → '{prefixed_all_hyphens}'")
        return prefixed_all_hyphens, True
    
    # No match found, return original
    logger.warning(f"Tool name '{original_name}' could not be resolved. Available tools: {sorted(available_tools)[:10]}...")
    return tool_name, False


def normalize_tool_name_for_skill(
    tool_name: str,
    local_tools: Set[str],
    mcp_servers: List[str] = None
) -> str:
    """
    Normalize tool name specifically for skill execution context.
    
    This is a simplified version that focuses on the most common cases
    in skill scripts where tools are called via call_tool().
    
    Args:
        tool_name: The tool name from skill script
        local_tools: Set of available local tool names (e.g., {"local-gitlab_get_info", ...})
        mcp_servers: List of connected MCP server names (for server-prefixed tools)
        
    Returns:
        Normalized tool name
    """
    # Quick fix for the most common mistake: local_ → local-
    if tool_name.startswith('local_'):
        corrected = 'local-' + tool_name[6:]
        if not local_tools or corrected in local_tools:
            logger.debug(f"Skill tool name corrected: '{tool_name}' → '{corrected}'")
            return corrected
    
    # If we have a list of local tools, do full resolution
    if local_tools:
        normalized, _ = normalize_tool_name(tool_name, local_tools, default_prefix="local")
        return normalized
    
    return tool_name


# Convenience function for checking if a name looks like it has a valid prefix
def has_valid_prefix(tool_name: str, known_prefixes: Set[str] = None) -> bool:
    """
    Check if tool name has a recognizable prefix.
    
    Args:
        tool_name: The tool name to check
        known_prefixes: Set of known prefixes (default: {"local", "filesystem"})
        
    Returns:
        True if the tool name starts with a known prefix followed by '-'
    """
    if known_prefixes is None:
        known_prefixes = {"local", "filesystem", "pdf-tools"}
    
    for prefix in known_prefixes:
        if tool_name.startswith(f"{prefix}-"):
            return True
    return False
