# code_parser_tools.py
# Code Parsing Tools for batch-code-documentation task
# Enhanced version with larger, more detailed outputs for Skill Mode efficiency

import json
import ast
import re
from typing import Any, List, Dict, Optional
from agents.tool import FunctionTool, RunContextWrapper


# ============== Step 1: Parse Python Module (Enhanced) ==============

def parse_python_module(source_code: str, filename: str) -> Dict:
    """Parse a Python module and extract comprehensive structure."""
    try:
        tree = ast.parse(source_code)
    except SyntaxError as e:
        return {
            "filename": filename,
            "error": f"Syntax error at line {e.lineno}: {str(e)}",
            "valid": False,
            "partial_analysis": {
                "total_lines": len(source_code.splitlines()),
                "raw_size_bytes": len(source_code)
            }
        }
    
    # Extract module docstring
    module_docstring = ast.get_docstring(tree) or ""
    
    # Extract imports with details
    imports = []
    import_from = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imports.append({
                    "module": alias.name,
                    "alias": alias.asname,
                    "line": node.lineno
                })
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                for alias in node.names:
                    import_from.append({
                        "module": node.module,
                        "name": alias.name,
                        "alias": alias.asname,
                        "line": node.lineno,
                        "level": node.level
                    })
    
    # Extract global variables and constants
    globals_list = []
    for node in ast.iter_child_nodes(tree):
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name):
                    value_repr = ""
                    try:
                        if hasattr(ast, 'unparse'):
                            value_repr = ast.unparse(node.value)[:100]
                    except:
                        pass
                    globals_list.append({
                        "name": target.id,
                        "line": node.lineno,
                        "is_constant": target.id.isupper(),
                        "value_preview": value_repr
                    })
    
    # Count different node types
    node_counts = {}
    for node in ast.walk(tree):
        node_type = type(node).__name__
        node_counts[node_type] = node_counts.get(node_type, 0) + 1
    
    lines = source_code.splitlines()
    total_lines = len(lines)
    blank_lines = sum(1 for line in lines if not line.strip())
    comment_lines = sum(1 for line in lines if line.strip().startswith('#'))
    code_lines = total_lines - blank_lines - comment_lines
    
    return {
        "filename": filename,
        "module_name": filename.replace('.py', ''),
        "valid": True,
        "total_lines": total_lines,
        "code_lines": code_lines,
        "blank_lines": blank_lines,
        "comment_lines": comment_lines,
        "size_bytes": len(source_code),
        "module_docstring": module_docstring,
        "imports": imports,
        "imports_from": import_from,
        "import_count": len(imports) + len(import_from),
        "global_variables": globals_list,
        "ast_node_counts": node_counts,
        "has_main_block": "__name__" in source_code and "__main__" in source_code,
        "uses_type_hints": "typing" in str(imports) or "->" in source_code or ": " in source_code
    }


async def on_parse_python_module(context: RunContextWrapper, params_str: str) -> Any:
    import os
    params = json.loads(params_str)
    
    # Support both filepath (reads file) and source_code (uses directly)
    filepath = params.get("filepath", "")
    source_code = params.get("source_code", "")
    filename = params.get("filename", "")
    
    # If filepath provided, read the file
    if filepath and not source_code:
        try:
            workspace = getattr(context, 'workspace_path', '') or ''
            full_path = os.path.join(workspace, filepath) if workspace else filepath
            
            if os.path.exists(full_path):
                with open(full_path, 'r', encoding='utf-8') as f:
                    source_code = f.read()
                filename = os.path.basename(filepath)
            else:
                return {"error": f"File not found: {filepath}"}
        except Exception as e:
            return {"error": f"Failed to read file: {str(e)}"}
    
    if not filename:
        filename = "unknown.py"
    
    result = parse_python_module(source_code, filename)
    return result


tool_parse_python_module = FunctionTool(
    name='local-code_parse_module',
    description='''Parse Python module with comprehensive analysis: imports, globals, line counts, AST statistics, and structure validation.

**Input (Option 1 - Direct filepath):** filepath (str) - Path to Python file (e.g., "src/module_01.py")
**Input (Option 2 - Source code):** source_code (str), filename (str) - Source code and filename

**Returns:** dict:
{
  "filename": str,
  "valid": bool,
  "total_lines": int,
  "code_lines": int,
  "imports": [{"module": str, "alias": str, "line": int}],
  "imports_from": [...],
  "global_variables": [...],
  "module_docstring": str
}''',
    params_json_schema={
        "type": "object",
        "properties": {
            "filepath": {"type": "string", "description": "Path to Python file (e.g., 'src/module_01.py')"},
            "source_code": {"type": "string", "description": "The Python source code (alternative to filepath)"},
            "filename": {"type": "string", "description": "The filename (optional if using filepath)"},
        },
        "required": []
    },
    on_invoke_tool=on_parse_python_module
)


# ============== Step 2: Extract Classes (Enhanced) ==============

def extract_classes(source_code: str) -> List[Dict]:
    """Extract all classes with detailed method and attribute analysis."""
    try:
        tree = ast.parse(source_code)
    except SyntaxError:
        return []
    
    classes = []
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef):
            # Extract base classes
            bases = []
            for base in node.bases:
                try:
                    if hasattr(ast, 'unparse'):
                        bases.append(ast.unparse(base))
                    elif isinstance(base, ast.Name):
                        bases.append(base.id)
                except:
                    pass
            
            # Extract decorators
            decorators = []
            for dec in node.decorator_list:
                try:
                    if hasattr(ast, 'unparse'):
                        decorators.append(ast.unparse(dec))
                    elif isinstance(dec, ast.Name):
                        decorators.append(dec.id)
                except:
                    pass
            
            # Extract methods with details
            methods = []
            instance_attributes = []
            class_attributes = []
            
            for item in node.body:
                if isinstance(item, ast.FunctionDef) or isinstance(item, ast.AsyncFunctionDef):
                    # Extract method parameters
                    params = []
                    for arg in item.args.args:
                        param_type = ""
                        if arg.annotation and hasattr(ast, 'unparse'):
                            try:
                                param_type = ast.unparse(arg.annotation)
                            except:
                                pass
                        params.append({
                            "name": arg.arg,
                            "type": param_type
                        })
                    
                    # Extract return type
                    return_type = ""
                    if item.returns and hasattr(ast, 'unparse'):
                        try:
                            return_type = ast.unparse(item.returns)
                        except:
                            pass
                    
                    # Method decorators
                    method_decorators = []
                    for dec in item.decorator_list:
                        try:
                            if hasattr(ast, 'unparse'):
                                method_decorators.append(ast.unparse(dec))
                            elif isinstance(dec, ast.Name):
                                method_decorators.append(dec.id)
                        except:
                            pass
                    
                    # Determine method type
                    method_type = "instance"
                    if "staticmethod" in method_decorators:
                        method_type = "static"
                    elif "classmethod" in method_decorators:
                        method_type = "class"
                    elif "property" in method_decorators:
                        method_type = "property"
                    
                    methods.append({
                        "name": item.name,
                        "line_number": item.lineno,
                        "end_line": item.end_lineno if hasattr(item, 'end_lineno') else None,
                        "is_async": isinstance(item, ast.AsyncFunctionDef),
                        "method_type": method_type,
                        "decorators": method_decorators,
                        "parameters": params,
                        "parameter_count": len(params),
                        "return_type": return_type,
                        "docstring": ast.get_docstring(item) or "",
                        "is_private": item.name.startswith('_') and not item.name.startswith('__'),
                        "is_dunder": item.name.startswith('__') and item.name.endswith('__')
                    })
                    
                    # Extract instance attributes from __init__
                    if item.name == '__init__':
                        for stmt in ast.walk(item):
                            if isinstance(stmt, ast.Assign):
                                for target in stmt.targets:
                                    if isinstance(target, ast.Attribute) and isinstance(target.value, ast.Name):
                                        if target.value.id == 'self':
                                            instance_attributes.append(target.attr)
                
                elif isinstance(item, ast.Assign):
                    for target in item.targets:
                        if isinstance(target, ast.Name):
                            class_attributes.append(target.id)
            
            class_info = {
                "name": node.name,
                "line_number": node.lineno,
                "end_line": node.end_lineno if hasattr(node, 'end_lineno') else None,
                "bases": bases,
                "decorators": decorators,
                "docstring": ast.get_docstring(node) or "",
                "methods": methods,
                "method_count": len(methods),
                "instance_attributes": list(set(instance_attributes)),
                "class_attributes": class_attributes,
                "has_init": any(m["name"] == "__init__" for m in methods),
                "has_str_repr": any(m["name"] in ["__str__", "__repr__"] for m in methods),
                "is_dataclass": "@dataclass" in str(decorators),
                "public_methods": [m for m in methods if not m["is_private"] and not m["is_dunder"]],
                "private_methods": [m for m in methods if m["is_private"]]
            }
            classes.append(class_info)
    
    return classes


async def on_extract_classes(context: RunContextWrapper, params_str: str) -> Any:
    params = json.loads(params_str)
    source_code = params.get("source_code", "")
    classes_list = extract_classes(source_code)
    # Return dict format as documented
    return {
        "classes": classes_list,
        "class_count": len(classes_list)
    }


tool_extract_classes = FunctionTool(
    name='local-code_extract_classes',
    description='''Extract all classes with detailed analysis: methods with signatures, attributes, decorators, inheritance, and documentation.

**Input:** source_code (str)

**Returns:** dict:
{
  "classes": [{"name": str, "line": int, "bases": [str], "decorators": [str], "docstring": str, "methods": [...], "attributes": [...]}],
  "class_count": int
}''',
    params_json_schema={
        "type": "object",
        "properties": {
            "source_code": {"type": "string", "description": "The Python source code to analyze"},
        },
        "required": ["source_code"]
    },
    on_invoke_tool=on_extract_classes
)


# ============== Step 3: Extract Functions (Enhanced) ==============

def extract_functions(source_code: str) -> List[Dict]:
    """Extract all top-level functions with comprehensive details."""
    try:
        tree = ast.parse(source_code)
    except SyntaxError:
        return []
    
    functions = []
    for node in ast.iter_child_nodes(tree):
        if isinstance(node, ast.FunctionDef) or isinstance(node, ast.AsyncFunctionDef):
            # Extract parameters with defaults
            params = []
            defaults = node.args.defaults
            args = node.args.args
            
            # Calculate offset for defaults (defaults align to end of args)
            default_offset = len(args) - len(defaults)
            
            for i, arg in enumerate(args):
                param_type = ""
                if arg.annotation and hasattr(ast, 'unparse'):
                    try:
                        param_type = ast.unparse(arg.annotation)
                    except:
                        pass
                
                default_value = None
                default_idx = i - default_offset
                if default_idx >= 0 and default_idx < len(defaults):
                    try:
                        if hasattr(ast, 'unparse'):
                            default_value = ast.unparse(defaults[default_idx])
                    except:
                        pass
                
                params.append({
                    "name": arg.arg,
                    "type": param_type,
                    "has_default": default_value is not None,
                    "default": default_value
                })
            
            # *args and **kwargs
            if node.args.vararg:
                params.append({
                    "name": f"*{node.args.vararg.arg}",
                    "type": "",
                    "has_default": False,
                    "is_vararg": True
                })
            if node.args.kwarg:
                params.append({
                    "name": f"**{node.args.kwarg.arg}",
                    "type": "",
                    "has_default": False,
                    "is_kwarg": True
                })
            
            # Extract return type
            return_type = ""
            if node.returns and hasattr(ast, 'unparse'):
                try:
                    return_type = ast.unparse(node.returns)
                except:
                    pass
            
            # Extract decorators
            decorators = []
            for dec in node.decorator_list:
                try:
                    if hasattr(ast, 'unparse'):
                        decorators.append(ast.unparse(dec))
                    elif isinstance(dec, ast.Name):
                        decorators.append(dec.id)
                except:
                    pass
            
            # Extract function calls made within
            calls_made = []
            for subnode in ast.walk(node):
                if isinstance(subnode, ast.Call):
                    if isinstance(subnode.func, ast.Name):
                        calls_made.append(subnode.func.id)
                    elif isinstance(subnode.func, ast.Attribute):
                        calls_made.append(subnode.func.attr)
            
            # Calculate complexity indicators
            line_count = (node.end_lineno - node.lineno + 1) if hasattr(node, 'end_lineno') else 0
            has_loops = any(isinstance(n, (ast.For, ast.While)) for n in ast.walk(node))
            has_conditionals = any(isinstance(n, ast.If) for n in ast.walk(node))
            has_try_except = any(isinstance(n, ast.Try) for n in ast.walk(node))
            
            func_info = {
                "name": node.name,
                "line_number": node.lineno,
                "end_line": node.end_lineno if hasattr(node, 'end_lineno') else None,
                "line_count": line_count,
                "parameters": params,
                "parameter_count": len([p for p in params if not p.get("is_vararg") and not p.get("is_kwarg")]),
                "return_type": return_type,
                "decorators": decorators,
                "docstring": ast.get_docstring(node) or "",
                "is_async": isinstance(node, ast.AsyncFunctionDef),
                "is_private": node.name.startswith('_'),
                "is_generator": any(isinstance(n, (ast.Yield, ast.YieldFrom)) for n in ast.walk(node)),
                "calls_made": list(set(calls_made))[:10],
                "complexity_indicators": {
                    "has_loops": has_loops,
                    "has_conditionals": has_conditionals,
                    "has_try_except": has_try_except,
                    "lines": line_count
                }
            }
            functions.append(func_info)
    
    return functions


async def on_extract_functions(context: RunContextWrapper, params_str: str) -> Any:
    params = json.loads(params_str)
    source_code = params.get("source_code", "")
    functions_list = extract_functions(source_code)
    # Return dict format as documented
    return {
        "functions": functions_list,
        "function_count": len(functions_list)
    }


tool_extract_functions = FunctionTool(
    name='local-code_extract_functions',
    description='''Extract all top-level functions with detailed signatures, default values, decorators, calls made, and complexity indicators.

**Input:** source_code (str)

**Returns:** dict:
{
  "functions": [{"name": str, "line": int, "args": [...], "returns": str, "decorators": [str], "docstring": str, "is_async": bool}],
  "function_count": int
}''',
    params_json_schema={
        "type": "object",
        "properties": {
            "source_code": {"type": "string", "description": "The Python source code to analyze"},
        },
        "required": ["source_code"]
    },
    on_invoke_tool=on_extract_functions
)


# ============== Step 4: Calculate Metrics (Enhanced) ==============

def calculate_code_metrics(module_info: Dict, classes: List[Dict], functions: List[Dict]) -> Dict:
    """Calculate comprehensive code documentation and quality metrics."""
    total_lines = module_info.get("total_lines", 0)
    code_lines = module_info.get("code_lines", 0)
    class_count = len(classes)
    function_count = len(functions)
    
    # Count documented items
    module_documented = 1 if module_info.get("module_docstring") else 0
    classes_documented = sum(1 for cls in classes if cls.get("docstring"))
    functions_documented = sum(1 for func in functions if func.get("docstring"))
    methods_documented = sum(
        sum(1 for m in cls.get("methods", []) if m.get("docstring"))
        for cls in classes
    )
    total_methods = sum(cls.get("method_count", 0) for cls in classes)
    
    total_items = 1 + class_count + function_count + total_methods
    items_documented = module_documented + classes_documented + functions_documented + methods_documented
    
    documented_ratio = items_documented / total_items if total_items > 0 else 0.0
    
    # Calculate complexity score
    if total_lines < 100 and (class_count + function_count) < 5:
        complexity_score = "low"
        complexity_points = 20
    elif total_lines > 500 or (class_count + function_count) > 20:
        complexity_score = "high"
        complexity_points = 80
    elif total_lines > 300 or (class_count + function_count) > 15:
        complexity_score = "medium-high"
        complexity_points = 60
    elif total_lines > 150 or (class_count + function_count) > 8:
        complexity_score = "medium"
        complexity_points = 40
    else:
        complexity_score = "low-medium"
        complexity_points = 30
    
    # Type hint usage
    functions_with_hints = sum(1 for f in functions if f.get("return_type") or any(p.get("type") for p in f.get("parameters", [])))
    type_hint_coverage = functions_with_hints / function_count if function_count > 0 else 0
    
    # Calculate lines per function/class
    avg_lines_per_function = sum(f.get("line_count", 0) for f in functions) / function_count if function_count > 0 else 0
    
    return {
        "class_count": class_count,
        "function_count": function_count,
        "method_count": total_methods,
        "total_lines": total_lines,
        "code_lines": code_lines,
        "documentation_metrics": {
            "documented_ratio": round(documented_ratio, 2),
            "module_documented": module_documented == 1,
            "classes_documented": classes_documented,
            "functions_documented": functions_documented,
            "methods_documented": methods_documented,
            "items_documented": items_documented,
            "total_items": total_items
        },
        "complexity": {
            "score": complexity_score,
            "points": complexity_points,
            "average_function_lines": round(avg_lines_per_function, 1)
        },
        "type_hints": {
            "functions_with_hints": functions_with_hints,
            "coverage": round(type_hint_coverage, 2)
        },
        "quality_score": min(100, int(
            documented_ratio * 40 +  # Documentation: 40%
            type_hint_coverage * 30 +  # Type hints: 30%
            (1 - complexity_points/100) * 30  # Simplicity: 30%
        )),
        "import_count": module_info.get("import_count", 0)
    }


async def on_calculate_code_metrics(context: RunContextWrapper, params_str: str) -> Any:
    params = json.loads(params_str)
    module_info = params.get("module_info", {})
    classes_input = params.get("classes", [])
    functions_input = params.get("functions", [])
    
    # Handle both list and dict inputs for backward compatibility
    # If input is dict with "classes" key, extract the list
    if isinstance(classes_input, dict):
        classes = classes_input.get("classes", [])
    else:
        classes = classes_input
    
    # If input is dict with "functions" key, extract the list
    if isinstance(functions_input, dict):
        functions = functions_input.get("functions", [])
    else:
        functions = functions_input
    result = calculate_code_metrics(module_info, classes, functions)
    return result


tool_calculate_code_metrics = FunctionTool(
    name='local-code_calculate_metrics',
    description='''Calculate comprehensive code metrics: documentation coverage, complexity score, type hint coverage, and quality score.

**Input:** module_info (dict), classes (dict or list), functions (dict or list) - Results from previous tools
- classes: Can be the dict from code_extract_classes ({"classes": [...], "class_count": int}) or just the list
- functions: Can be the dict from code_extract_functions ({"functions": [...], "function_count": int}) or just the list

**Returns:** dict:
{
  "class_count": int,
  "function_count": int,
  "method_count": int,
  "total_lines": int,
  "documentation_metrics": {"documented_ratio": float, ...},
  "complexity": {"score": str, "points": int},
  "type_hints": {"coverage": float},
  "quality_score": int
}''',
    params_json_schema={
        "type": "object",
        "properties": {
            "module_info": {"type": "object", "description": "Module info from code_parse_module"},
            "classes": {"description": "Classes from code_extract_classes (dict or list)"},
            "functions": {"description": "Functions from code_extract_functions (dict or list)"},
        },
        "required": ["module_info", "classes", "functions"]
    },
    on_invoke_tool=on_calculate_code_metrics
)


# ============== Step 5: Generate Documentation (Enhanced) ==============

def generate_module_documentation(module_info: Dict, classes: List[Dict], functions: List[Dict], metrics: Dict) -> str:
    """Generate comprehensive markdown documentation for a Python module."""
    filename = module_info.get("filename", "unknown.py")
    module_name = module_info.get("module_name", "unknown")
    
    doc_lines = []
    doc_lines.append(f"# Module: {module_name}")
    doc_lines.append("")
    
    # Module docstring
    if module_info.get("module_docstring"):
        doc_lines.append(f"> {module_info['module_docstring']}")
        doc_lines.append("")
    
    # Quality badge
    quality_score = metrics.get("quality_score", 0)
    if quality_score >= 80:
        badge = "🟢 Excellent"
    elif quality_score >= 60:
        badge = "🟡 Good"
    elif quality_score >= 40:
        badge = "🟠 Fair"
    else:
        badge = "🔴 Needs Improvement"
    
    doc_lines.append(f"**Quality Score: {quality_score}/100** {badge}")
    doc_lines.append("")
    
    # Overview section
    doc_lines.append("## Overview")
    doc_lines.append("")
    doc_lines.append("| Metric | Value |")
    doc_lines.append("|--------|-------|")
    doc_lines.append(f"| **File** | `{filename}` |")
    doc_lines.append(f"| **Total Lines** | {metrics.get('total_lines', 0)} |")
    doc_lines.append(f"| **Code Lines** | {metrics.get('code_lines', 0)} |")
    doc_lines.append(f"| **Classes** | {metrics.get('class_count', 0)} |")
    doc_lines.append(f"| **Functions** | {metrics.get('function_count', 0)} |")
    doc_lines.append(f"| **Methods** | {metrics.get('method_count', 0)} |")
    doc_lines.append(f"| **Complexity** | {metrics.get('complexity', {}).get('score', 'unknown')} |")
    doc_lines.append(f"| **Doc Coverage** | {int(metrics.get('documentation_metrics', {}).get('documented_ratio', 0) * 100)}% |")
    doc_lines.append(f"| **Type Hints** | {int(metrics.get('type_hints', {}).get('coverage', 0) * 100)}% |")
    doc_lines.append("")
    
    # Dependencies section
    if module_info.get("imports") or module_info.get("imports_from"):
        doc_lines.append("## Dependencies")
        doc_lines.append("")
        for imp in module_info.get("imports", []):
            alias_str = f" as {imp['alias']}" if imp.get('alias') else ""
            doc_lines.append(f"- `import {imp['module']}{alias_str}`")
        for imp in module_info.get("imports_from", []):
            alias_str = f" as {imp['alias']}" if imp.get('alias') else ""
            doc_lines.append(f"- `from {imp['module']} import {imp['name']}{alias_str}`")
        doc_lines.append("")
    
    # Classes section
    if classes:
        doc_lines.append("## Classes")
        doc_lines.append("")
        for cls in classes:
            bases_str = f"({', '.join(cls['bases'])})" if cls.get('bases') else ""
            doc_lines.append(f"### `class {cls['name']}{bases_str}`")
            doc_lines.append("")
            if cls.get("docstring"):
                doc_lines.append(f"> {cls['docstring']}")
                doc_lines.append("")
            doc_lines.append(f"*Defined at line {cls['line_number']}*")
            doc_lines.append("")
            
            # Class attributes
            if cls.get("instance_attributes"):
                doc_lines.append(f"**Instance Attributes:** `{'`, `'.join(cls['instance_attributes'])}`")
                doc_lines.append("")
            
            # Methods table
            if cls.get("methods"):
                doc_lines.append("**Methods:**")
                doc_lines.append("")
                doc_lines.append("| Method | Type | Parameters | Returns |")
                doc_lines.append("|--------|------|------------|---------|")
                for method in cls["methods"]:
                    params = ", ".join([p['name'] for p in method.get('parameters', [])])
                    ret = method.get('return_type', 'None') or 'None'
                    mtype = method.get('method_type', 'instance')
                    doc_lines.append(f"| `{method['name']}` | {mtype} | {params} | {ret} |")
                doc_lines.append("")
    
    # Functions section
    if functions:
        doc_lines.append("## Functions")
        doc_lines.append("")
        for func in functions:
            async_prefix = "async " if func.get("is_async") else ""
            doc_lines.append(f"### `{async_prefix}def {func['name']}(...)`")
            doc_lines.append("")
            if func.get("docstring"):
                doc_lines.append(f"> {func['docstring']}")
                doc_lines.append("")
            
            # Signature
            params_str = ", ".join(
                f"{p['name']}: {p['type']}" if p.get('type') else p['name']
                for p in func.get("parameters", [])
            )
            return_type = func.get("return_type", "")
            return_annotation = f" -> {return_type}" if return_type else ""
            doc_lines.append(f"```python")
            doc_lines.append(f"def {func['name']}({params_str}){return_annotation}")
            doc_lines.append(f"```")
            doc_lines.append("")
            
            # Parameters table
            if func.get("parameters"):
                doc_lines.append("| Parameter | Type | Default |")
                doc_lines.append("|-----------|------|---------|")
                for param in func["parameters"]:
                    ptype = param.get('type') or '-'
                    default = param.get('default', '-') or '-'
                    doc_lines.append(f"| `{param['name']}` | {ptype} | {default} |")
                doc_lines.append("")
    
    return "\n".join(doc_lines)


async def on_generate_module_documentation(context: RunContextWrapper, params_str: str) -> Any:
    params = json.loads(params_str)
    module_info = params.get("module_info", {})
    classes_input = params.get("classes", [])
    functions_input = params.get("functions", [])
    metrics = params.get("metrics", {})
    
    # Handle both list and dict inputs for backward compatibility
    if isinstance(classes_input, dict):
        classes = classes_input.get("classes", [])
    else:
        classes = classes_input
    
    if isinstance(functions_input, dict):
        functions = functions_input.get("functions", [])
    else:
        functions = functions_input
    
    markdown_content = generate_module_documentation(module_info, classes, functions, metrics)
    return markdown_content  # Return raw markdown string as documented


tool_generate_module_documentation = FunctionTool(
    name='local-code_generate_docs',
    description='''Generate comprehensive markdown documentation with quality scores, dependency list, class/function details, and formatted tables.

**Input:** module_info (dict), classes (dict or list), functions (dict or list), metrics (dict) - Results from previous tools
- classes: Can be the dict from code_extract_classes or just the list
- functions: Can be the dict from code_extract_functions or just the list

**Returns:** str - Raw markdown content (use directly for writing to file)''',
    params_json_schema={
        "type": "object",
        "properties": {
            "module_info": {"type": "object", "description": "Module info from code_parse_module"},
            "classes": {"type": "array", "description": "Classes from code_extract_classes"},
            "functions": {"type": "array", "description": "Functions from code_extract_functions"},
            "metrics": {"type": "object", "description": "Metrics from code_calculate_metrics"},
        },
        "required": ["module_info", "classes", "functions", "metrics"]
    },
    on_invoke_tool=on_generate_module_documentation
)


# ============== Export all tools ==============

code_parser_tools = [
    tool_parse_python_module,    # Step 1: Parse module
    tool_extract_classes,         # Step 2: Extract classes
    tool_extract_functions,       # Step 3: Extract functions
    tool_calculate_code_metrics,  # Step 4: Calculate metrics
    tool_generate_module_documentation,  # Step 5: Generate docs
]
