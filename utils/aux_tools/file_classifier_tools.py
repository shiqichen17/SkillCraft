# file_classifier_tools.py
# File Classification Tools for local-file-organizer task
# Enhanced version with larger, more detailed outputs for Skill Mode efficiency

import json
import re
from typing import Any, List, Dict, Optional
from collections import Counter
from agents.tool import FunctionTool, RunContextWrapper


# File category mappings with detailed info
FILE_CATEGORIES = {
    "documents": {
        "extensions": [".txt", ".md", ".doc", ".docx", ".pdf", ".rtf"],
        "description": "Text documents and documentation",
        "typical_uses": ["Documentation", "Notes", "Reports", "Articles"]
    },
    "code": {
        "extensions": [".py", ".js", ".ts", ".jsx", ".tsx", ".sh", ".bash", ".java", ".cpp", ".c", ".go", ".rs", ".rb", ".php"],
        "description": "Source code and scripts",
        "typical_uses": ["Programming", "Automation", "Development"]
    },
    "data": {
        "extensions": [".json", ".csv", ".xml", ".sql", ".parquet", ".pickle"],
        "description": "Structured data files",
        "typical_uses": ["Data storage", "Data exchange", "Databases"]
    },
    "configs": {
        "extensions": [".yaml", ".yml", ".toml", ".ini", ".cfg", ".conf", ".env", ".properties"],
        "description": "Configuration and settings files",
        "typical_uses": ["Application settings", "Environment config", "Deployment"]
    },
    "media": {
        "extensions": [".jpg", ".jpeg", ".png", ".gif", ".svg", ".mp3", ".mp4", ".wav", ".webp", ".ico"],
        "description": "Images, audio, and video files",
        "typical_uses": ["Graphics", "Multimedia", "Assets"]
    }
}


# ============== Step 1: Identify File Type (Enhanced) ==============

def identify_file_type(filename: str, content: str = "") -> Dict:
    """Comprehensive file type identification with analysis."""
    # Extract extension
    parts = filename.rsplit('.', 1)
    if len(parts) > 1:
        ext = '.' + parts[1].lower()
        basename = parts[0]
    else:
        ext = ""
        basename = filename
    
    # Find category
    category = "other"
    category_info = {}
    for cat, info in FILE_CATEGORIES.items():
        if ext in info["extensions"]:
            category = cat
            category_info = info
            break
    
    # Special handling for config files with data extensions
    if category == "data" and ext in [".yaml", ".yml", ".json"]:
        config_keywords = ["config", "settings", "env", "deploy", "docker", "ci", "workflow"]
        if any(keyword in filename.lower() for keyword in config_keywords):
            category = "configs"
            category_info = FILE_CATEGORIES["configs"]
    
    # Detect file characteristics from content
    content_analysis = {}
    if content:
        lines = content.split('\n')
        words = content.split()
        content_analysis = {
            "line_count": len(lines),
            "word_count": len(words),
            "char_count": len(content),
            "is_empty": len(content.strip()) == 0,
            "has_shebang": lines[0].startswith('#!') if lines else False,
            "encoding_guess": "utf-8" if all(ord(c) < 128 for c in content[:1000]) else "possibly non-ascii"
        }
    
    # Naming pattern analysis
    naming_analysis = {
        "has_version": bool(re.search(r'v?\d+\.\d+', filename)),
        "has_date": bool(re.search(r'\d{4}[-_]?\d{2}[-_]?\d{2}', filename)),
        "is_hidden": filename.startswith('.'),
        "is_backup": any(filename.endswith(s) for s in ['.bak', '.backup', '.old', '~']),
        "is_temp": any(filename.endswith(s) for s in ['.tmp', '.temp']) or filename.startswith('tmp_'),
        "has_underscore": '_' in basename,
        "has_hyphen": '-' in basename,
        "is_camelcase": bool(re.search(r'[a-z][A-Z]', basename)),
        "is_uppercase": basename.isupper(),
        "is_lowercase": basename.islower()
    }
    
    return {
        "filename": filename,
        "basename": basename,
        "extension": ext,
        "extension_description": get_extension_description(ext),
        "category": category,
        "category_info": {
            "description": category_info.get("description", "Uncategorized file"),
            "typical_uses": category_info.get("typical_uses", [])
        },
        "naming_analysis": naming_analysis,
        "content_analysis": content_analysis,
        "suggested_actions": get_suggested_actions(category, naming_analysis)
    }


def get_extension_description(ext: str) -> str:
    """Get description for file extension."""
    descriptions = {
        ".py": "Python source code",
        ".js": "JavaScript source code",
        ".ts": "TypeScript source code",
        ".jsx": "React JSX component",
        ".tsx": "React TypeScript component",
        ".json": "JSON data file",
        ".yaml": "YAML configuration/data",
        ".yml": "YAML configuration/data",
        ".md": "Markdown document",
        ".txt": "Plain text file",
        ".csv": "Comma-separated values",
        ".xml": "XML document",
        ".html": "HTML document",
        ".css": "CSS stylesheet",
        ".sh": "Shell script",
        ".sql": "SQL script/query",
        ".toml": "TOML configuration",
        ".ini": "INI configuration",
        ".env": "Environment variables",
    }
    return descriptions.get(ext, f"{ext.upper()[1:]} file" if ext else "No extension")


def get_suggested_actions(category: str, naming_analysis: Dict) -> List[str]:
    """Get suggested actions based on file analysis."""
    actions = []
    
    if naming_analysis.get("is_backup"):
        actions.append("Consider moving to archive folder")
    if naming_analysis.get("is_temp"):
        actions.append("Review if temporary file should be deleted")
    if naming_analysis.get("is_hidden"):
        actions.append("Hidden file - may contain sensitive settings")
    
    category_actions = {
        "code": ["Consider adding to version control", "Review for code documentation"],
        "configs": ["Verify sensitive data is not exposed", "Consider using environment variables"],
        "data": ["Validate data integrity", "Consider backup strategy"],
        "documents": ["Check if needs indexing", "Verify accessibility"],
        "media": ["Consider compression if large", "Add alt text if image"]
    }
    
    actions.extend(category_actions.get(category, []))
    return actions


async def on_identify_file_type(context: RunContextWrapper, params_str: str) -> Any:
    import os
    params = json.loads(params_str)
    
    # Support both filepath (reads file) and filename/content
    filepath = params.get("filepath", "")
    filename = params.get("filename", "")
    content = params.get("content", "")
    
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
        filename = "unknown"
    
    result = identify_file_type(filename, content)
    return result


tool_identify_file_type = FunctionTool(
    name='local-file_identify_type',
    description='''Comprehensive file type identification with naming analysis, content analysis, and suggested actions.

**Input (Option 1 - Direct filepath):** filepath (str) - Path to file (e.g., "inbox/meeting_notes.txt")
**Input (Option 2 - Content):** filename (str), content (str, optional) - Filename and content

**Returns:** dict with these EXACT keys:
{
  "filename": str,
  "basename": str,
  "extension": str,  // e.g., ".py", ".json"
  "category": str,   // "documents", "code", "data", "configs", "media", "other"
  "category_info": {"description": str, "typical_uses": [str]},
  "naming_analysis": {"has_version": bool, "is_temp": bool, ...},
  "content_analysis": {"line_count": int, "word_count": int, ...},
  "suggested_actions": [str]
}

**Key fields to use:**
- category: Use for determining which metadata extractor to call
- extension: Use for code/data metadata extraction
- filename: Use for report generation''',
    params_json_schema={
        "type": "object",
        "properties": {
            "filepath": {"type": "string", "description": "Path to file (e.g., 'inbox/meeting_notes.txt')"},
            "filename": {"type": "string", "description": "The filename (optional if using filepath)"},
            "content": {"type": "string", "description": "Optional file content (alternative to filepath)"},
        },
        "required": []
    },
    on_invoke_tool=on_identify_file_type
)


# ============== Step 2: Extract Document Metadata (Enhanced) ==============

def extract_document_metadata(content: str, filename: str = "") -> Dict:
    """Comprehensive document metadata extraction."""
    lines = content.split('\n')
    words = content.split()
    
    # Basic stats
    non_empty_lines = [l for l in lines if l.strip()]
    paragraphs = content.split('\n\n')
    paragraphs = [p for p in paragraphs if p.strip()]
    
    # Find title (first non-empty line or markdown heading)
    title = ""
    for line in lines:
        stripped = line.strip()
        if stripped:
            if stripped.startswith('# '):
                title = stripped[2:]
            else:
                title = stripped[:100]
            break
    
    # Markdown-specific analysis
    md_analysis = {}
    if filename.endswith('.md'):
        md_analysis = {
            "headings": len([l for l in lines if l.strip().startswith('#')]),
            "code_blocks": content.count('```') // 2,
            "links": len(re.findall(r'\[([^\]]+)\]\([^)]+\)', content)),
            "images": len(re.findall(r'!\[([^\]]*)\]\([^)]+\)', content)),
            "bold_text": len(re.findall(r'\*\*[^*]+\*\*', content)),
            "italic_text": len(re.findall(r'(?<!\*)\*[^*]+\*(?!\*)', content)),
            "lists": len([l for l in lines if re.match(r'^\s*[-*+]\s', l) or re.match(r'^\s*\d+\.\s', l)])
        }
    
    # Text analysis
    avg_word_length = sum(len(w) for w in words) / len(words) if words else 0
    sentence_endings = len(re.findall(r'[.!?]', content))
    
    # Complexity metrics
    unique_words = len(set(w.lower() for w in words))
    vocabulary_richness = unique_words / len(words) if words else 0
    
    return {
        "filename": filename,
        "title": title,
        "basic_stats": {
            "line_count": len(lines),
            "non_empty_lines": len(non_empty_lines),
            "word_count": len(words),
            "char_count": len(content),
            "paragraph_count": len(paragraphs)
        },
        "text_analysis": {
            "avg_word_length": round(avg_word_length, 2),
            "sentence_count": sentence_endings,
            "avg_words_per_sentence": round(len(words) / sentence_endings, 1) if sentence_endings else 0,
            "unique_words": unique_words,
            "vocabulary_richness": round(vocabulary_richness, 3)
        },
        "content_preview": {
            "first_line": lines[0] if lines else "",
            "last_line": lines[-1] if lines else "",
            "sample_paragraph": paragraphs[0][:200] if paragraphs else ""
        },
        "markdown_analysis": md_analysis,
        "reading_time_minutes": round(len(words) / 200, 1)  # ~200 WPM average
    }


async def on_extract_document_metadata(context: RunContextWrapper, params_str: str) -> Any:
    import os
    params = json.loads(params_str)
    filepath = params.get("filepath", "")
    content = params.get("content", "")
    filename = params.get("filename", "")
    
    # If filepath provided, read the file internally
    if filepath and not content:
        try:
            workspace = getattr(context, 'workspace_path', '') or ''
            full_path = os.path.join(workspace, filepath) if workspace else filepath
            
            if os.path.exists(full_path):
                with open(full_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                if not filename:
                    filename = os.path.basename(filepath)
            else:
                return {"error": f"File not found: {filepath}"}
        except Exception as e:
            return {"error": f"Failed to read file: {str(e)}"}
    
    if not filename:
        filename = "unknown.txt"
    
    result = extract_document_metadata(content, filename)
    return result


tool_extract_document_metadata = FunctionTool(
    name='local-file_extract_doc_meta',
    description='''Comprehensive document analysis including text statistics, markdown parsing, and reading time estimation.

**Input (Option 1 - Recommended):** filepath (str) - Path to file, content will be read internally
**Input (Option 2):** content (str), filename (str, optional) - Direct content

**Returns:** dict with these EXACT keys:
{
  "filename": str,
  "title": str,
  "basic_stats": {
    "line_count": int,
    "word_count": int,
    "char_count": int,
    "paragraph_count": int
  },
  "text_analysis": {"avg_word_length": float, "sentence_count": int, ...},
  "markdown_analysis": {"headings": int, "code_blocks": int, "links": int, ...},  // Only for .md files
  "reading_time_minutes": float
}

**Key fields:** basic_stats.word_count, basic_stats.line_count, reading_time_minutes''',
    params_json_schema={
        "type": "object",
        "properties": {
            "filepath": {"type": "string", "description": "Path to file (e.g., 'inbox/notes.txt') - RECOMMENDED"},
            "content": {"type": "string", "description": "File content (alternative to filepath)"},
            "filename": {"type": "string", "description": "Optional filename for format detection"},
        },
        "required": []
    },
    on_invoke_tool=on_extract_document_metadata
)


# ============== Step 3: Extract Code Metadata (Enhanced) ==============

def extract_code_metadata(content: str, extension: str) -> Dict:
    """Comprehensive code file analysis."""
    lines = content.split('\n')
    non_empty = [l for l in lines if l.strip()]
    comment_lines = []
    code_lines = []
    
    # Language-specific analysis
    language = {
        ".py": "Python", ".js": "JavaScript", ".ts": "TypeScript",
        ".jsx": "React JSX", ".tsx": "React TSX", ".sh": "Shell",
        ".java": "Java", ".cpp": "C++", ".c": "C", ".go": "Go", ".rs": "Rust"
    }.get(extension, "Unknown")
    
    # Count different line types
    functions = []
    classes = []
    imports = []
    
    if extension == ".py":
        comment_lines = [l for l in lines if l.strip().startswith('#')]
        for match in re.finditer(r'^(?:async\s+)?def\s+(\w+)\s*\(([^)]*)\)', content, re.MULTILINE):
            functions.append({"name": match.group(1), "params": match.group(2).split(',') if match.group(2) else []})
        for match in re.finditer(r'^class\s+(\w+)', content, re.MULTILINE):
            classes.append({"name": match.group(1)})
        for match in re.finditer(r'^(?:import\s+(\S+)|from\s+(\S+)\s+import)', content, re.MULTILINE):
            imports.append(match.group(1) or match.group(2))
    
    elif extension in [".js", ".ts", ".jsx", ".tsx"]:
        comment_lines = [l for l in lines if l.strip().startswith('//')]
        for match in re.finditer(r'(?:function\s+(\w+)|(?:const|let|var)\s+(\w+)\s*=\s*(?:async\s*)?\([^)]*\)\s*=>)', content):
            name = match.group(1) or match.group(2)
            if name:
                functions.append({"name": name, "params": []})
        for match in re.finditer(r'class\s+(\w+)', content):
            classes.append({"name": match.group(1)})
        for match in re.finditer(r'import\s+.*\s+from\s+[\'"]([^\'"]+)[\'"]', content):
            imports.append(match.group(1))
    
    elif extension in [".sh", ".bash"]:
        comment_lines = [l for l in lines if l.strip().startswith('#') and not l.strip().startswith('#!')]
        for match in re.finditer(r'^(\w+)\s*\(\)\s*\{', content, re.MULTILINE):
            functions.append({"name": match.group(1), "params": []})
    
    code_lines = [l for l in lines if l.strip() and l not in comment_lines]
    
    # Calculate complexity metrics
    if_count = len(re.findall(r'\bif\b', content))
    loop_count = len(re.findall(r'\b(for|while)\b', content))
    try_count = len(re.findall(r'\btry\b', content))
    
    # Estimate cyclomatic complexity
    complexity = 1 + if_count + loop_count
    complexity_rating = "low" if complexity < 10 else ("medium" if complexity < 20 else "high")
    
    return {
        "language": language,
        "extension": extension,
        "line_statistics": {
            "total_lines": len(lines),
            "code_lines": len(code_lines),
            "comment_lines": len(comment_lines),
            "empty_lines": len(lines) - len(non_empty),
            "comment_ratio": round(len(comment_lines) / len(lines), 3) if lines else 0
        },
        "structure": {
            "functions": functions,
            "function_count": len(functions),
            "classes": classes,
            "class_count": len(classes),
            "imports": imports,
            "import_count": len(imports)
        },
        "complexity_analysis": {
            "if_statements": if_count,
            "loops": loop_count,
            "try_blocks": try_count,
            "estimated_complexity": complexity,
            "complexity_rating": complexity_rating
        },
        "code_patterns": {
            "has_main": ('if __name__' in content if extension == ".py" else False),
            "has_tests": bool(re.search(r'test_|_test|\.test\.|spec\.', content.lower())),
            "has_docstrings": bool(re.search(r'""".*?"""', content, re.DOTALL)) if extension == ".py" else False,
            "has_type_hints": bool(re.search(r':\s*(?:str|int|float|bool|List|Dict|Optional)', content)) if extension == ".py" else False
        },
        "quality_indicators": {
            "has_error_handling": try_count > 0,
            "is_documented": len(comment_lines) > len(functions),
            "follows_conventions": not bool(re.search(r'[a-z][A-Z]', '\n'.join(f["name"] for f in functions))) if extension == ".py" else True
        }
    }


async def on_extract_code_metadata(context: RunContextWrapper, params_str: str) -> Any:
    import os
    params = json.loads(params_str)
    filepath = params.get("filepath", "")
    content = params.get("content", "")
    extension = params.get("extension", "")
    
    # If filepath provided, read the file internally
    if filepath and not content:
        try:
            workspace = getattr(context, 'workspace_path', '') or ''
            full_path = os.path.join(workspace, filepath) if workspace else filepath
            
            if os.path.exists(full_path):
                with open(full_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                if not extension:
                    _, extension = os.path.splitext(filepath)
            else:
                return {"error": f"File not found: {filepath}"}
        except Exception as e:
            return {"error": f"Failed to read file: {str(e)}"}
    
    if not extension:
        extension = ".py"
    
    result = extract_code_metadata(content, extension)
    return result


tool_extract_code_metadata = FunctionTool(
    name='local-file_extract_code_meta',
    description='''Comprehensive code analysis: structure, complexity metrics, quality indicators, and code patterns.

**Input (Option 1 - Recommended):** filepath (str) - Path to file, content and extension inferred automatically
**Input (Option 2):** content (str), extension (str) - Direct content with extension

**Returns:** dict with these EXACT keys:
{
  "language": str,  // "Python", "JavaScript", etc.
  "extension": str,
  "line_statistics": {
    "total_lines": int,
    "code_lines": int,
    "comment_lines": int,
    "empty_lines": int,
    "comment_ratio": float
  },
  "structure": {
    "functions": [{"name": str, "params": [str]}],
    "function_count": int,
    "classes": [{"name": str}],
    "class_count": int,
    "imports": [str],
    "import_count": int
  },
  "complexity_analysis": {"estimated_complexity": int, "complexity_rating": str},
  "quality_indicators": {"has_error_handling": bool, "is_documented": bool}
}

**Key fields:** language, line_statistics.total_lines, structure.function_count''',
    params_json_schema={
        "type": "object",
        "properties": {
            "filepath": {"type": "string", "description": "Path to file (e.g., 'src/script.py') - RECOMMENDED"},
            "content": {"type": "string", "description": "File content (alternative to filepath)"},
            "extension": {"type": "string", "description": "File extension (e.g., .py, .js) - auto-detected if filepath provided"},
        },
        "required": []
    },
    on_invoke_tool=on_extract_code_metadata
)


# ============== Step 4: Extract Data Metadata (Enhanced) ==============

def extract_data_metadata(content: str, extension: str) -> Dict:
    """Comprehensive data file analysis."""
    lines = content.split('\n')
    
    result = {
        "extension": extension,
        "line_count": len(lines),
        "char_count": len(content)
    }
    
    if extension == ".json":
        try:
            data = json.loads(content)
            
            def analyze_structure(obj, depth=0, max_depth=3):
                """Recursively analyze JSON structure."""
                if depth > max_depth:
                    return {"type": "...", "truncated": True}
                
                if isinstance(obj, dict):
                    return {
                        "type": "object",
                        "keys": list(obj.keys())[:20],
                        "key_count": len(obj),
                        "sample_values": {k: analyze_structure(v, depth+1) for k, v in list(obj.items())[:5]}
                    }
                elif isinstance(obj, list):
                    return {
                        "type": "array",
                        "length": len(obj),
                        "item_type": type(obj[0]).__name__ if obj else "empty",
                        "sample_items": [analyze_structure(item, depth+1) for item in obj[:3]]
                    }
                else:
                    return {"type": type(obj).__name__, "sample": str(obj)[:50]}
            
            if isinstance(data, list):
                result.update({
                    "data_type": "array",
                    "record_count": len(data),
                    "fields": list(data[0].keys()) if data and isinstance(data[0], dict) else [],
                    "field_count": len(data[0].keys()) if data and isinstance(data[0], dict) else 0,
                    "structure": analyze_structure(data),
                    "sample_record": data[0] if data else None
                })
            elif isinstance(data, dict):
                result.update({
                    "data_type": "object",
                    "record_count": 1,
                    "fields": list(data.keys())[:50],
                    "field_count": len(data.keys()),
                    "structure": analyze_structure(data),
                    "nested_objects": sum(1 for v in data.values() if isinstance(v, dict)),
                    "nested_arrays": sum(1 for v in data.values() if isinstance(v, list))
                })
        except json.JSONDecodeError as e:
            result["parse_error"] = str(e)
    
    elif extension == ".csv":
        non_empty_lines = [l for l in lines if l.strip()]
        if non_empty_lines:
            header = non_empty_lines[0].split(',')
            result.update({
                "data_type": "tabular",
                "record_count": len(non_empty_lines) - 1,
                "fields": [h.strip() for h in header],
                "field_count": len(header),
                "sample_rows": [l.split(',') for l in non_empty_lines[1:4]],
                "has_header": True,
                "delimiter": ","
            })
    
    elif extension in [".yaml", ".yml"]:
        non_empty = [l for l in lines if l.strip() and not l.strip().startswith('#')]
        top_level_keys = [l.split(':')[0] for l in non_empty if ':' in l and not l.startswith(' ')]
        result.update({
            "data_type": "yaml",
            "top_level_keys": top_level_keys[:20],
            "key_count": len([l for l in lines if ':' in l]),
            "comment_lines": len([l for l in lines if l.strip().startswith('#')]),
            "nesting_depth": max(len(l) - len(l.lstrip()) for l in non_empty) // 2 if non_empty else 0
        })
    
    return result


async def on_extract_data_metadata(context: RunContextWrapper, params_str: str) -> Any:
    import os
    params = json.loads(params_str)
    filepath = params.get("filepath", "")
    content = params.get("content", "")
    extension = params.get("extension", "")
    
    # If filepath provided, read the file internally
    if filepath and not content:
        try:
            workspace = getattr(context, 'workspace_path', '') or ''
            full_path = os.path.join(workspace, filepath) if workspace else filepath
            
            if os.path.exists(full_path):
                with open(full_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                if not extension:
                    _, extension = os.path.splitext(filepath)
            else:
                return {"error": f"File not found: {filepath}"}
        except Exception as e:
            return {"error": f"Failed to read file: {str(e)}"}
    
    if not extension:
        extension = ".json"
    
    result = extract_data_metadata(content, extension)
    return result


tool_extract_data_metadata = FunctionTool(
    name='local-file_extract_data_meta',
    description='''Comprehensive data file analysis: structure analysis, schema detection, sample records.

**Input (Option 1 - Recommended):** filepath (str) - Path to file, content and extension inferred automatically
**Input (Option 2):** content (str), extension (str) - Direct content with extension

**Returns:** dict with these EXACT keys:
{
  "extension": str,
  "line_count": int,
  "char_count": int,
  "data_type": str,  // "array", "object", "tabular", "yaml"
  "record_count": int,
  "fields": [str],   // field/column names
  "field_count": int,
  "structure": {...},  // Detailed structure analysis
  "sample_record": {...} or null  // For JSON arrays
}

**Key fields:** data_type, record_count, fields, field_count''',
    params_json_schema={
        "type": "object",
        "properties": {
            "filepath": {"type": "string", "description": "Path to file (e.g., 'data/users.json') - RECOMMENDED"},
            "content": {"type": "string", "description": "File content (alternative to filepath)"},
            "extension": {"type": "string", "description": "File extension (e.g., .json, .csv) - auto-detected if filepath provided"},
        },
        "required": []
    },
    on_invoke_tool=on_extract_data_metadata
)


# ============== Step 5: Extract Config Metadata (Enhanced) ==============

def extract_config_metadata(content: str, filename: str = "") -> Dict:
    """Comprehensive configuration file analysis."""
    lines = content.split('\n')
    
    # Detect config type
    config_type = "unknown"
    if filename.endswith(('.yaml', '.yml')):
        config_type = "yaml"
    elif filename.endswith('.toml'):
        config_type = "toml"
    elif filename.endswith('.ini'):
        config_type = "ini"
    elif filename.endswith('.env'):
        config_type = "env"
    elif filename.endswith('.json'):
        config_type = "json"
    
    # Parse sections and keys
    sections = {}
    current_section = "global"
    sections[current_section] = []
    
    sensitive_patterns = ['password', 'secret', 'key', 'token', 'api_key', 'apikey', 'credential']
    sensitive_keys = []
    
    for line in lines:
        line = line.strip()
        if not line or line.startswith('#') or line.startswith(';'):
            continue
        
        # Section headers
        if (line.startswith('[') and line.endswith(']')):
            current_section = line[1:-1]
            sections[current_section] = []
        elif line.endswith(':') and '=' not in line:
            current_section = line[:-1]
            sections[current_section] = []
        # Key-value pairs
        elif '=' in line or ': ' in line:
            if '=' in line:
                key = line.split('=')[0].strip()
            else:
                key = line.split(': ')[0].strip()
            sections[current_section].append(key)
            
            # Check for sensitive keys
            if any(p in key.lower() for p in sensitive_patterns):
                sensitive_keys.append(key)
    
    # Environment detection
    env_indicators = {
        "development": ['dev', 'development', 'debug', 'localhost'],
        "production": ['prod', 'production', 'live'],
        "testing": ['test', 'testing', 'staging']
    }
    
    detected_env = "unknown"
    content_lower = content.lower()
    for env, indicators in env_indicators.items():
        if any(ind in content_lower for ind in indicators):
            detected_env = env
            break
    
    # Count by section
    section_summary = {sec: len(keys) for sec, keys in sections.items()}
    
    return {
        "filename": filename,
        "config_type": config_type,
        "line_count": len(lines),
        "section_analysis": {
            "section_count": len(sections),
            "sections": list(sections.keys()),
            "keys_per_section": section_summary,
            "total_keys": sum(len(k) for k in sections.values())
        },
        "keys_by_section": sections,
        "security_analysis": {
            "sensitive_keys_found": len(sensitive_keys),
            "sensitive_keys": sensitive_keys,
            "has_exposed_secrets": any('=' in line and any(p in line.lower() for p in sensitive_patterns) 
                                       for line in lines if not line.strip().startswith('#'))
        },
        "environment_detection": {
            "detected_environment": detected_env,
            "has_env_vars": '${' in content or '$(' in content,
            "has_placeholders": '{{' in content or '<' in content
        },
        "quality_checks": {
            "has_comments": any(l.strip().startswith('#') or l.strip().startswith(';') for l in lines),
            "is_well_organized": len(sections) > 1,
            "uses_sections": any(l.strip().startswith('[') for l in lines)
        }
    }


async def on_extract_config_metadata(context: RunContextWrapper, params_str: str) -> Any:
    import os
    params = json.loads(params_str)
    filepath = params.get("filepath", "")
    content = params.get("content", "")
    filename = params.get("filename", "")
    
    # If filepath provided, read the file internally
    if filepath and not content:
        try:
            workspace = getattr(context, 'workspace_path', '') or ''
            full_path = os.path.join(workspace, filepath) if workspace else filepath
            
            if os.path.exists(full_path):
                with open(full_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                if not filename:
                    filename = os.path.basename(filepath)
            else:
                return {"error": f"File not found: {filepath}"}
        except Exception as e:
            return {"error": f"Failed to read file: {str(e)}"}
    
    if not filename:
        filename = "config.ini"
    
    result = extract_config_metadata(content, filename)
    return result


tool_extract_config_metadata = FunctionTool(
    name='local-file_extract_config_meta',
    description='''Comprehensive config analysis: section structure, security audit, environment detection.

**Input (Option 1 - Recommended):** filepath (str) - Path to file, content will be read internally
**Input (Option 2):** content (str), filename (str) - Direct content with filename

**Returns:** dict with these EXACT keys:
{
  "filename": str,
  "config_type": str,  // "yaml", "toml", "ini", "env", "json"
  "line_count": int,
  "section_analysis": {
    "section_count": int,
    "sections": [str],
    "keys_per_section": {str: int},
    "total_keys": int
  },
  "keys_by_section": {str: [str]},
  "security_analysis": {
    "sensitive_keys_found": int,
    "sensitive_keys": [str],
    "has_exposed_secrets": bool
  },
  "environment_detection": {"detected_environment": str},
  "quality_checks": {"has_comments": bool, "is_well_organized": bool}
}

**Key fields:** config_type, section_analysis.total_keys, security_analysis.sensitive_keys_found''',
    params_json_schema={
        "type": "object",
        "properties": {
            "filepath": {"type": "string", "description": "Path to file (e.g., 'configs/app.yaml') - RECOMMENDED"},
            "content": {"type": "string", "description": "File content (alternative to filepath)"},
            "filename": {"type": "string", "description": "Filename for format detection - auto-detected if filepath provided"},
        },
        "required": []
    },
    on_invoke_tool=on_extract_config_metadata
)


# ============== Step 6: Generate File Report (Enhanced) ==============

def generate_file_report(
    filename: str,
    original_path: str,
    file_type: Dict,
    metadata: Dict,
    size_bytes: int = 0
) -> Dict:
    """Generate comprehensive file processing report."""
    category = file_type.get("category", "other")
    
    # Determine new path
    new_path = f"organized/{category}/{filename}"
    
    # Calculate priority
    priority = "normal"
    if file_type.get("naming_analysis", {}).get("is_temp"):
        priority = "low"
    elif category in ["code", "configs"]:
        priority = "high"
    
    # Get size description
    size_kb = size_bytes / 1024
    size_mb = size_kb / 1024
    size_desc = f"{size_bytes} bytes"
    if size_mb >= 1:
        size_desc = f"{size_mb:.2f} MB"
    elif size_kb >= 1:
        size_desc = f"{size_kb:.2f} KB"
    
    return {
        "file_info": {
            "original_name": filename,
            "original_path": original_path,
            "new_path": new_path,
            "category": category,
            "file_type": file_type.get("extension", "").lstrip('.'),
            "extension_description": file_type.get("extension_description", "")
        },
        "size_info": {
            "bytes": size_bytes,
            "formatted": size_desc
        },
        "classification_details": {
            "category_info": file_type.get("category_info", {}),
            "naming_analysis": file_type.get("naming_analysis", {}),
            "suggested_actions": file_type.get("suggested_actions", [])
        },
        "content_metadata": metadata,
        "processing_info": {
            "priority": priority,
            "action": "move",
            "destination": new_path,
            "requires_review": file_type.get("naming_analysis", {}).get("is_backup", False)
        }
    }


async def on_generate_file_report(context: RunContextWrapper, params_str: str) -> Any:
    params = json.loads(params_str)
    filename = params.get("filename", "unknown")
    original_path = params.get("original_path", "inbox/unknown")
    file_type = params.get("file_type", {})
    metadata = params.get("metadata", {})
    size_bytes = params.get("size_bytes", 0)
    result = generate_file_report(filename, original_path, file_type, metadata, size_bytes)
    return result


tool_generate_file_report = FunctionTool(
    name='local-file_generate_report',
    description='''Generate comprehensive file report with classification details, size info, and processing recommendations.

**Input:** 
- filename (str)
- original_path (str)
- file_type (dict) - Result from file_identify_type
- metadata (dict) - Result from extract_*_meta tool (can be empty {} if extraction failed)
- size_bytes (int) - File size in bytes (use 0 if unknown)

**Returns:** dict with these EXACT keys:
{
  "file_info": {
    "original_name": str,
    "original_path": str,
    "new_path": str,  // e.g., "organized/code/script.py"
    "category": str,
    "file_type": str,  // extension without dot
    "extension_description": str
  },
  "size_info": {
    "bytes": int,
    "formatted": str  // e.g., "1.5 KB"
  },
  "classification_details": {
    "category_info": {...},
    "naming_analysis": {...},
    "suggested_actions": [str]
  },
  "content_metadata": {...},  // The metadata dict you passed in
  "processing_info": {
    "priority": str,  // "low", "normal", "high"
    "action": str,
    "destination": str,
    "requires_review": bool
  }
}

**Key fields:** file_info.category, file_info.new_path, size_info.bytes''',
    params_json_schema={
        "type": "object",
        "properties": {
            "filename": {"type": "string", "description": "The filename"},
            "original_path": {"type": "string", "description": "Original file path"},
            "file_type": {"type": "object", "description": "Result from file_identify_type"},
            "metadata": {"type": "object", "description": "Result from extract metadata tool"},
            "size_bytes": {"type": "integer", "description": "File size in bytes"},
        },
        "required": ["filename", "original_path", "file_type", "metadata"]
    },
    on_invoke_tool=on_generate_file_report
)


# ============== Step 7: Generate Organization Summary (Enhanced) ==============

def generate_organization_summary(file_reports: List[Dict]) -> Dict:
    """Generate comprehensive organization summary."""
    categories = Counter()
    extensions = Counter()
    total_size = 0
    files_by_category = {}
    priority_counts = Counter()
    
    for report in file_reports:
        file_info = report.get("file_info", {})
        cat = file_info.get("category", "other")
        ext = file_info.get("file_type", "")
        size = report.get("size_info", {}).get("bytes", 0)
        priority = report.get("processing_info", {}).get("priority", "normal")
        
        categories[cat] += 1
        extensions[ext] += 1
        total_size += size
        priority_counts[priority] += 1
        
        if cat not in files_by_category:
            files_by_category[cat] = []
        files_by_category[cat].append(file_info.get("original_name", ""))
    
    # Calculate size distribution
    size_distribution = {cat: 0 for cat in categories}
    for report in file_reports:
        cat = report.get("file_info", {}).get("category", "other")
        size_distribution[cat] += report.get("size_info", {}).get("bytes", 0)
    
    # Format sizes
    def format_size(bytes_val):
        if bytes_val >= 1024 * 1024:
            return f"{bytes_val / (1024*1024):.2f} MB"
        elif bytes_val >= 1024:
            return f"{bytes_val / 1024:.2f} KB"
        return f"{bytes_val} bytes"
    
    return {
        "summary": {
            "total_files": len(file_reports),
            "total_size": format_size(total_size),
            "total_size_bytes": total_size,
            "categories_used": len(categories)
        },
        "category_breakdown": {
            "counts": dict(categories),
            "percentages": {k: round(v / len(file_reports) * 100, 1) for k, v in categories.items()},
            "sizes": {k: format_size(v) for k, v in size_distribution.items()}
        },
        "extension_distribution": dict(extensions.most_common(10)),
        "priority_breakdown": dict(priority_counts),
        "files_by_category": files_by_category,
        "organization_result": {
            "directories_created": list(categories.keys()),
            "files_moved": len(file_reports),
            "action_required": sum(1 for r in file_reports 
                                   if r.get("processing_info", {}).get("requires_review", False))
        },
        "recommendations": generate_summary_recommendations(file_reports, categories)
    }


def generate_summary_recommendations(file_reports: List[Dict], categories: Counter) -> List[str]:
    """Generate recommendations based on analysis."""
    recs = []
    
    if categories.get("other", 0) > 3:
        recs.append("Several files couldn't be categorized - consider adding custom rules")
    
    total = sum(categories.values())
    if categories.get("configs", 0) / total > 0.3:
        recs.append("High proportion of config files - consider consolidating configurations")
    
    if categories.get("code", 0) / total > 0.5:
        recs.append("Code-heavy project - ensure proper documentation exists")
    
    temp_files = sum(1 for r in file_reports 
                     if r.get("classification_details", {}).get("naming_analysis", {}).get("is_temp", False))
    if temp_files > 0:
        recs.append(f"Found {temp_files} temporary files - consider cleanup")
    
    backup_files = sum(1 for r in file_reports
                       if r.get("classification_details", {}).get("naming_analysis", {}).get("is_backup", False))
    if backup_files > 0:
        recs.append(f"Found {backup_files} backup files - archive or remove if not needed")
    
    return recs if recs else ["Organization complete - no issues detected"]


async def on_generate_organization_summary(context: RunContextWrapper, params_str: str) -> Any:
    params = json.loads(params_str)
    file_reports = params.get("file_reports", [])
    result = generate_organization_summary(file_reports)
    return result


tool_generate_organization_summary = FunctionTool(
    name='local-file_generate_summary',
    description='''Generate comprehensive organization summary with category breakdown, size distribution, and recommendations.

**Input:** file_reports (list[dict]) - Array of file reports from generate_report

**Returns:** dict with these EXACT keys:
{
  "summary": {
    "total_files": int,
    "total_size": str,  // formatted, e.g., "1.5 MB"
    "total_size_bytes": int,
    "categories_used": int
  },
  "category_breakdown": {
    "counts": {"documents": int, "code": int, ...},
    "percentages": {"documents": float, ...},
    "sizes": {"documents": str, ...}
  },
  "extension_distribution": {"py": int, "json": int, ...},
  "priority_breakdown": {"low": int, "normal": int, "high": int},
  "files_by_category": {"documents": [str], "code": [str], ...},
  "organization_result": {
    "directories_created": [str],
    "files_moved": int,
    "action_required": int
  },
  "recommendations": [str]
}

**Key fields:** summary.total_files, category_breakdown.counts, recommendations''',
    params_json_schema={
        "type": "object",
        "properties": {
            "file_reports": {"type": "array", "description": "Array of file reports"},
        },
        "required": ["file_reports"]
    },
    on_invoke_tool=on_generate_organization_summary
)


# ============== Export all tools ==============

file_classifier_tools = [
    tool_identify_file_type,          # Step 1: Identify type
    tool_extract_document_metadata,   # Step 2a: Doc metadata
    tool_extract_code_metadata,       # Step 2b: Code metadata
    tool_extract_data_metadata,       # Step 2c: Data metadata
    tool_extract_config_metadata,     # Step 2d: Config metadata
    tool_generate_file_report,        # Step 3: Generate report
    tool_generate_organization_summary, # Step 4: Summary
]
