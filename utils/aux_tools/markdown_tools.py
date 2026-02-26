# markdown_tools.py
# Markdown Processing Tools for local-markdown-toc task
# Enhanced version with larger, more detailed outputs for Skill Mode efficiency

import json
import re
from typing import Any, List, Dict, Optional
from collections import Counter
from agents.tool import FunctionTool, RunContextWrapper


# ============== Step 1: Parse Markdown Content (Enhanced) ==============

def parse_markdown_content(content: str, filename: str) -> Dict:
    """Comprehensive markdown parsing with structure analysis."""
    lines = content.split('\n')
    headings = []
    code_blocks = []
    links = []
    images = []
    lists = []
    blockquotes = []
    
    # Pattern for headings
    heading_pattern = re.compile(r'^(#{1,6})\s+(.+?)\s*$')
    # Pattern for links [text](url)
    link_pattern = re.compile(r'\[([^\]]+)\]\(([^)]+)\)')
    # Pattern for images ![alt](url)
    image_pattern = re.compile(r'!\[([^\]]*)\]\(([^)]+)\)')
    
    in_code_block = False
    code_block_start = 0
    code_block_lang = ""
    current_code = []
    
    for line_num, line in enumerate(lines, 1):
        # Track code blocks
        if line.strip().startswith('```'):
            if not in_code_block:
                in_code_block = True
                code_block_start = line_num
                code_block_lang = line.strip()[3:].strip()
                current_code = []
            else:
                in_code_block = False
                code_blocks.append({
                    "start_line": code_block_start,
                    "end_line": line_num,
                    "language": code_block_lang or "unknown",
                    "lines": len(current_code),
                    "preview": "\n".join(current_code[:3]) if current_code else ""
                })
            continue
        
        if in_code_block:
            current_code.append(line)
            continue
        
        # Parse headings
        match = heading_pattern.match(line)
        if match:
            level = len(match.group(1))
            text = match.group(2).strip()
            
            # Generate anchor (GitHub-style)
            anchor = text.lower()
            anchor = re.sub(r'[^\w\s-]', '', anchor)
            anchor = re.sub(r'\s+', '-', anchor)
            anchor = re.sub(r'-+', '-', anchor)
            
            headings.append({
                "level": level,
                "text": text,
                "anchor": anchor,
                "line": line_num,
                "parent_heading": None  # Will be filled in structure analysis
            })
        
        # Parse links
        for match in link_pattern.finditer(line):
            links.append({
                "text": match.group(1),
                "url": match.group(2),
                "line": line_num,
                "is_external": match.group(2).startswith(('http://', 'https://', '//'))
            })
        
        # Parse images
        for match in image_pattern.finditer(line):
            images.append({
                "alt": match.group(1),
                "url": match.group(2),
                "line": line_num
            })
        
        # Track lists
        if line.strip().startswith(('-', '*', '+')) or re.match(r'^\d+\.', line.strip()):
            if not lists or lists[-1]["end_line"] < line_num - 1:
                lists.append({"start_line": line_num, "end_line": line_num, "items": 1})
            else:
                lists[-1]["end_line"] = line_num
                lists[-1]["items"] += 1
        
        # Track blockquotes
        if line.strip().startswith('>'):
            if not blockquotes or blockquotes[-1]["end_line"] < line_num - 1:
                blockquotes.append({"start_line": line_num, "end_line": line_num, "lines": 1})
            else:
                blockquotes[-1]["end_line"] = line_num
                blockquotes[-1]["lines"] += 1
    
    # Build heading hierarchy
    for i, heading in enumerate(headings):
        for j in range(i - 1, -1, -1):
            if headings[j]["level"] < heading["level"]:
                heading["parent_heading"] = headings[j]["text"]
                break
    
    # Get document title (first h1)
    title = ""
    for h in headings:
        if h["level"] == 1:
            title = h["text"]
            break
    
    # Calculate statistics
    word_count = len(content.split())
    char_count = len(content)
    
    # Heading level distribution
    level_dist = Counter(h["level"] for h in headings)
    
    # Link type distribution
    internal_links = sum(1 for l in links if not l["is_external"])
    external_links = sum(1 for l in links if l["is_external"])
    
    return {
        "filename": filename,
        "title": title,
        "statistics": {
            "total_lines": len(lines),
            "word_count": word_count,
            "char_count": char_count,
            "total_headings": len(headings),
            "max_depth": max([h["level"] for h in headings]) if headings else 0,
            "code_blocks": len(code_blocks),
            "total_code_lines": sum(cb["lines"] for cb in code_blocks),
            "links": len(links),
            "images": len(images),
            "lists": len(lists),
            "blockquotes": len(blockquotes)
        },
        "heading_distribution": {f"h{k}": v for k, v in sorted(level_dist.items())},
        "link_summary": {
            "total": len(links),
            "internal": internal_links,
            "external": external_links,
            "sample_links": links[:5]
        },
        "headings": headings,
        "code_blocks": code_blocks,
        "images": images,
        "structure_preview": {
            "first_heading": headings[0] if headings else None,
            "last_heading": headings[-1] if headings else None,
            "top_level_sections": [h for h in headings if h["level"] <= 2][:10]
        }
    }


async def on_parse_markdown_content(context: RunContextWrapper, params_str: str) -> Any:
    import os
    params = json.loads(params_str)
    
    # Support both filepath (reads file) and content (uses directly)
    filepath = params.get("filepath", "")
    content = params.get("content", "")
    filename = params.get("filename", "")
    
    # If filepath provided, read the file
    if filepath and not content:
        try:
            workspace = getattr(context, 'workspace_path', '') or ''
            full_path = os.path.join(workspace, filepath) if workspace else filepath
            
            if os.path.exists(full_path):
                with open(full_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                filename = os.path.basename(filepath)
            else:
                return {"error": f"File not found: {filepath}"}
        except Exception as e:
            return {"error": f"Failed to read file: {str(e)}"}
    
    if not filename:
        filename = "unknown.md"
    
    result = parse_markdown_content(content, filename)
    return result


tool_parse_markdown_content = FunctionTool(
    name='local-md_parse_headings',
    description='''Comprehensive markdown parsing: headings, code blocks, links, images, lists, blockquotes with statistics and structure analysis.

**Input (Option 1 - Direct filepath):** filepath (str) - Path to markdown file (e.g., "markdown_files/doc_01.md")
**Input (Option 2 - Content):** content (str), filename (str) - Markdown content and filename

**Returns:** dict:
{
  "filename": str,
  "total_lines": int,
  "headings": [{"level": int, "text": str, "anchor": str, "line": int}],
  "code_blocks": [...],
  "links": [...],
  "statistics": {...}
}''',
    params_json_schema={
        "type": "object",
        "properties": {
            "filepath": {"type": "string", "description": "Path to markdown file (e.g., 'markdown_files/doc_01.md')"},
            "content": {"type": "string", "description": "The markdown content (alternative to filepath)"},
            "filename": {"type": "string", "description": "The filename (optional if using filepath)"},
        },
        "required": []
    },
    on_invoke_tool=on_parse_markdown_content
)


# ============== Step 2: Handle Duplicate Anchors (Enhanced) ==============

def deduplicate_anchors(headings: List[Dict]) -> Dict:
    """Handle duplicate anchors with detailed tracking."""
    anchor_counts = {}
    anchor_occurrences = {}
    result = []
    duplicates_info = []
    
    for heading in headings:
        anchor = heading.get("anchor", "")
        
        if anchor in anchor_counts:
            anchor_counts[anchor] += 1
            new_anchor = f"{anchor}-{anchor_counts[anchor]}"
            duplicates_info.append({
                "original_anchor": anchor,
                "new_anchor": new_anchor,
                "heading_text": heading.get("text", ""),
                "line": heading.get("line", 0),
                "occurrence": anchor_counts[anchor] + 1
            })
        else:
            anchor_counts[anchor] = 0
            new_anchor = anchor
        
        # Track all occurrences
        if anchor not in anchor_occurrences:
            anchor_occurrences[anchor] = []
        anchor_occurrences[anchor].append(heading.get("text", ""))
        
        result.append({
            **heading,
            "anchor": new_anchor,
            "original_anchor": heading.get("anchor", ""),
            "is_duplicate": anchor_counts[anchor] > 0
        })
    
    # Find anchors that had duplicates
    duplicate_anchors = {k: v for k, v in anchor_occurrences.items() if len(v) > 1}
    
    return {
        "deduplicated_headings": result,  # Match the documented key name
        "duplicates_fixed": len(duplicates_info),
        "duplicate_details": duplicates_info,
        "duplicate_anchors": duplicate_anchors,
        "unique_anchors": len(anchor_counts),
        "total_headings": len(headings)
    }


async def on_deduplicate_anchors(context: RunContextWrapper, params_str: str) -> Any:
    params = json.loads(params_str)
    headings = params.get("headings", [])
    result = deduplicate_anchors(headings)
    return result


tool_deduplicate_anchors = FunctionTool(
    name='local-md_deduplicate_anchors',
    description='''Handle duplicate anchors with detailed tracking of all occurrences and duplicates fixed.

**Input:** headings (list[dict]) - The headings array from md_parse_headings

**Returns:** dict:
{
  "deduplicated_headings": [{"level": int, "text": str, "anchor": str, "original_anchor": str}],
  "duplicates_found": int,
  "duplicate_details": {...}
}''',
    params_json_schema={
        "type": "object",
        "properties": {
            "headings": {"type": "array", "description": "The headings array from md_parse_headings"},
        },
        "required": ["headings"]
    },
    on_invoke_tool=on_deduplicate_anchors
)


# ============== Step 3: Generate TOC (Enhanced) ==============

def generate_toc(headings: List[Dict], skip_title: bool = True, min_level: int = 2) -> Dict:
    """Generate TOC with detailed structure information."""
    toc_lines = ["## Table of Contents", ""]
    toc_entries = []
    
    for heading in headings:
        level = heading.get("level", 2)
        
        if skip_title and level == 1:
            continue
        
        if level < min_level:
            continue
        
        indent = "  " * (level - min_level)
        text = heading.get("text", "")
        anchor = heading.get("anchor", "")
        
        toc_line = f"{indent}- [{text}](#{anchor})"
        toc_lines.append(toc_line)
        
        toc_entries.append({
            "level": level,
            "text": text,
            "anchor": anchor,
            "indent_level": level - min_level,
            "toc_line": toc_line
        })
    
    toc_lines.append("")
    toc_content = "\n".join(toc_lines)
    
    # Calculate TOC statistics
    level_counts = Counter(e["level"] for e in toc_entries)
    
    return {
        "toc_content": toc_content,
        "toc_lines": len(toc_lines) - 1,
        "entries_included": len(toc_entries),
        "toc_entries": toc_entries,
        "level_distribution": {f"h{k}": v for k, v in sorted(level_counts.items())},
        "max_indent": max(e["indent_level"] for e in toc_entries) if toc_entries else 0,
        "toc_size_chars": len(toc_content),
        "configuration": {
            "skip_title": skip_title,
            "min_level": min_level
        }
    }


async def on_generate_toc(context: RunContextWrapper, params_str: str) -> Any:
    params = json.loads(params_str)
    headings = params.get("headings", [])
    skip_title = params.get("skip_title", True)
    min_level = params.get("min_level", 2)
    result = generate_toc(headings, skip_title, min_level)
    return result


tool_generate_toc = FunctionTool(
    name='local-md_generate_toc',
    description='''Generate formatted TOC with detailed entry information, level distribution, and configuration tracking.

**Input:** headings (list[dict]), skip_title (bool, optional), min_level (int, optional)

**Returns:** dict:
{
  "toc_content": str,
  "entries_included": int,
  "toc_lines": int,
  "level_distribution": {"h2": int, "h3": int, ...},
  "configuration": {"skip_title": bool, "min_level": int}
}''',
    params_json_schema={
        "type": "object",
        "properties": {
            "headings": {"type": "array", "description": "The deduplicated headings array"},
            "skip_title": {"type": "boolean", "description": "Whether to skip h1 title in TOC (default: true)"},
            "min_level": {"type": "integer", "description": "Minimum heading level to include (default: 2)"},
        },
        "required": ["headings"]
    },
    on_invoke_tool=on_generate_toc
)


# ============== Step 4: Insert TOC into Document (Enhanced) ==============

def insert_toc_into_document(content: str, toc_content: str) -> Dict:
    """Insert TOC with detailed change tracking."""
    lines = content.split('\n')
    original_line_count = len(lines)
    original_char_count = len(content)
    
    # Find insertion point
    h1_line_idx = -1
    h1_text = ""
    for i, line in enumerate(lines):
        if line.strip().startswith('# ') and not line.strip().startswith('## '):
            h1_line_idx = i
            h1_text = line.strip()[2:].strip()
            break
    
    if h1_line_idx == -1:
        insert_idx = 0
        insertion_after = "(beginning of document)"
    else:
        insert_idx = h1_line_idx + 1
        while insert_idx < len(lines) and lines[insert_idx].strip() == '':
            insert_idx += 1
        insertion_after = f"heading: {h1_text}"
    
    # Build new content
    new_lines = lines[:insert_idx] + ['', toc_content, ''] + lines[insert_idx:]
    new_content = '\n'.join(new_lines)
    
    # Clean up multiple consecutive blank lines
    new_content = re.sub(r'\n{4,}', '\n\n\n', new_content)
    
    new_line_count = len(new_content.split('\n'))
    new_char_count = len(new_content)
    
    return {
        "modified_content": new_content,  # Match documentation
        "insertion_details": {
            "inserted_at_line": insert_idx + 1,
            "insertion_after": insertion_after,
            "toc_lines_added": len(toc_content.split('\n'))
        },
        "size_changes": {
            "original_lines": original_line_count,
            "new_lines": new_line_count,
            "lines_added": new_line_count - original_line_count,
            "original_chars": original_char_count,
            "new_chars": new_char_count,
            "chars_added": new_char_count - original_char_count
        },
        "validation": {
            "toc_inserted": toc_content in new_content,
            "original_preserved": all(line in new_content for line in lines[:10])
        }
    }


async def on_insert_toc_into_document(context: RunContextWrapper, params_str: str) -> Any:
    params = json.loads(params_str)
    content = params.get("content", "")
    toc_content = params.get("toc_content", "")
    result = insert_toc_into_document(content, toc_content)
    return result


tool_insert_toc_into_document = FunctionTool(
    name='local-md_insert_toc',
    description='''Insert TOC with detailed change tracking, size changes, and validation.

**Input:** content (str), toc_content (str)

**Returns:** dict:
{
  "success": bool,
  "modified_content": str,
  "changes": {"lines_added": int, "position": str, "original_size": int, "new_size": int}
}''',
    params_json_schema={
        "type": "object",
        "properties": {
            "content": {"type": "string", "description": "The original markdown content"},
            "toc_content": {"type": "string", "description": "The generated TOC from md_generate_toc"},
        },
        "required": ["content", "toc_content"]
    },
    on_invoke_tool=on_insert_toc_into_document
)


# ============== Step 5: Generate Document Report (Enhanced) ==============

def generate_document_report(
    parse_result: Dict,
    dedup_result: Dict,
    toc_result: Dict,
    insert_result: Dict
) -> Dict:
    """Generate comprehensive document processing report."""
    filename = parse_result.get("filename", "unknown")
    
    # Calculate quality score
    quality_score = 100
    issues = []
    recommendations = []
    
    stats = parse_result.get("statistics", {})
    
    # Check heading structure
    if stats.get("total_headings", 0) == 0:
        quality_score -= 30
        issues.append("No headings found in document")
        recommendations.append("Add headings to structure the document")
    elif stats.get("max_depth", 0) > 4:
        quality_score -= 10
        issues.append("Heading hierarchy is too deep (>4 levels)")
        recommendations.append("Consider flattening the heading structure")
    
    # Check for duplicate anchors
    if dedup_result.get("duplicates_fixed", 0) > 0:
        quality_score -= 5 * dedup_result["duplicates_fixed"]
        issues.append(f"{dedup_result['duplicates_fixed']} duplicate heading anchors found")
        recommendations.append("Use unique heading names to avoid anchor conflicts")
    
    # Check document length
    if stats.get("word_count", 0) > 5000 and stats.get("total_headings", 0) < 5:
        quality_score -= 15
        issues.append("Long document with few headings")
        recommendations.append("Add more section headings for better navigation")
    
    quality_score = max(0, quality_score)
    
    # Determine status
    if quality_score >= 80:
        status = "excellent"
    elif quality_score >= 60:
        status = "good"
    elif quality_score >= 40:
        status = "needs_improvement"
    else:
        status = "poor"
    
    return {
        "filename": filename,
        "title": parse_result.get("title", ""),
        "status": status,
        "quality_score": quality_score,
        "document_statistics": parse_result.get("statistics", {}),
        "heading_analysis": {
            "total_headings": parse_result.get("statistics", {}).get("total_headings", 0),
            "max_depth": parse_result.get("statistics", {}).get("max_depth", 0),
            "distribution": parse_result.get("heading_distribution", {}),
            "duplicates_fixed": dedup_result.get("duplicates_fixed", 0),
            "unique_anchors": dedup_result.get("unique_anchors", 0)
        },
        "toc_generation": {
            "entries_included": toc_result.get("entries_included", 0),
            "toc_lines": toc_result.get("toc_lines", 0),
            "level_distribution": toc_result.get("level_distribution", {})
        },
        "content_analysis": {
            "code_blocks": parse_result.get("statistics", {}).get("code_blocks", 0),
            "total_code_lines": parse_result.get("statistics", {}).get("total_code_lines", 0),
            "links": parse_result.get("link_summary", {}),
            "images": parse_result.get("statistics", {}).get("images", 0)
        },
        "size_changes": insert_result.get("size_changes", {}),
        "issues": issues,
        "recommendations": recommendations,
        "headings": parse_result.get("headings", [])
    }


async def on_generate_document_report(context: RunContextWrapper, params_str: str) -> Any:
    params = json.loads(params_str)
    parse_result = params.get("parse_result", {})
    dedup_result = params.get("dedup_result", {})
    toc_result = params.get("toc_result", {})
    insert_result = params.get("insert_result", {})
    result = generate_document_report(parse_result, dedup_result, toc_result, insert_result)
    return result


tool_generate_document_report = FunctionTool(
    name='local-md_generate_report',
    description='''Generate comprehensive report with quality scoring, issues detection, and recommendations.

**Input:** parse_result (dict), dedup_result (dict), toc_result (dict), insert_result (dict) - Results from previous tools

**Returns:** dict (directly, NOT nested under "report"):
{
  "filename": str,
  "status": str,
  "quality_score": int,
  "heading_analysis": {...},
  "issues": [...],
  "recommendations": [...]
}''',
    params_json_schema={
        "type": "object",
        "properties": {
            "parse_result": {"type": "object", "description": "Result from md_parse_headings"},
            "dedup_result": {"type": "object", "description": "Result from md_deduplicate_anchors"},
            "toc_result": {"type": "object", "description": "Result from md_generate_toc"},
            "insert_result": {"type": "object", "description": "Result from md_insert_toc"},
        },
        "required": ["parse_result", "dedup_result", "toc_result", "insert_result"]
    },
    on_invoke_tool=on_generate_document_report
)


# ============== Export all tools ==============

markdown_tools = [
    tool_parse_markdown_content,    # Step 1: Parse content
    tool_deduplicate_anchors,       # Step 2: Handle duplicates
    tool_generate_toc,              # Step 3: Generate TOC
    tool_insert_toc_into_document,  # Step 4: Insert TOC
    tool_generate_document_report,  # Step 5: Generate report
]
