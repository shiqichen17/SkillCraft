# log_parser_tools.py
# Log Parsing Tools for batch-log-analyzer task
# Enhanced version with larger, more detailed outputs for Skill Mode efficiency

import json
import re
from typing import Any, List, Dict, Optional
from collections import Counter
from datetime import datetime
from agents.tool import FunctionTool, RunContextWrapper


# Log format pattern
LOG_PATTERN = re.compile(
    r'\[(\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2})\]\s+\[(\w+)\]\s+(.*)'
)

# Response time pattern
RESPONSE_TIME_PATTERN = re.compile(r'processed in (\d+)ms')
STATUS_PATTERN = re.compile(r'status:\s*(\d+)')

# Error type patterns with descriptions
ERROR_TYPE_PATTERNS = {
    "DatabaseError": {
        "pattern": r'database|db|query|connection|timeout|sql',
        "severity": "high",
        "description": "Database connectivity or query issues",
        "suggested_action": "Check database server status and connection pool"
    },
    "AuthError": {
        "pattern": r'auth|authentication|login|password|user|credential|unauthorized',
        "severity": "high",
        "description": "Authentication or authorization failures",
        "suggested_action": "Review authentication logs and user access"
    },
    "NetworkError": {
        "pattern": r'network|socket|connection refused|timeout|dns|http',
        "severity": "medium",
        "description": "Network connectivity issues",
        "suggested_action": "Check network connectivity and firewall rules"
    },
    "MemoryError": {
        "pattern": r'memory|heap|oom|out of memory|gc',
        "severity": "critical",
        "description": "Memory allocation or garbage collection issues",
        "suggested_action": "Review memory usage and consider scaling"
    },
    "DiskError": {
        "pattern": r'disk|storage|space|write|read|io|file',
        "severity": "high",
        "description": "Disk I/O or storage issues",
        "suggested_action": "Check disk space and I/O performance"
    },
    "ConfigError": {
        "pattern": r'config|configuration|setting|parameter|invalid',
        "severity": "medium",
        "description": "Configuration or parameter issues",
        "suggested_action": "Review application configuration"
    },
}

WARNING_CATEGORIES = {
    "memory": {"pattern": r'memory|heap|ram', "threshold": "warning"},
    "cpu": {"pattern": r'cpu|processor|load', "threshold": "warning"},
    "disk": {"pattern": r'disk|space|storage', "threshold": "warning"},
    "network": {"pattern": r'network|connection|latency', "threshold": "warning"},
    "performance": {"pattern": r'slow|latency|timeout|delay', "threshold": "warning"},
    "resource": {"pattern": r'resource|limit|quota|pool', "threshold": "warning"},
}


# ============== Step 1: Parse Log File (Enhanced) ==============

def parse_log_file(content: str, filename: str) -> Dict:
    """Parse a log file and extract ALL entries with detailed analysis."""
    lines = content.strip().split('\n')
    entries = []
    parse_errors = []
    
    for line_num, line in enumerate(lines, 1):
        match = LOG_PATTERN.match(line.strip())
        if match:
            timestamp, level, message = match.groups()
            
            # Extract additional info from message
            response_time = None
            status_code = None
            
            time_match = RESPONSE_TIME_PATTERN.search(message)
            if time_match:
                response_time = int(time_match.group(1))
            
            status_match = STATUS_PATTERN.search(message)
            if status_match:
                status_code = int(status_match.group(1))
            
            entries.append({
                "line_number": line_num,
                "timestamp": timestamp,
                "level": level.upper(),
                "message": message,
                "response_time_ms": response_time,
                "status_code": status_code
            })
        elif line.strip():
            parse_errors.append({"line": line_num, "content": line[:100]})
    
    # Calculate time span
    timestamps = [e["timestamp"] for e in entries if e["timestamp"]]
    time_span = {"start": timestamps[0], "end": timestamps[-1]} if timestamps else {}
    
    # Level distribution
    level_counts = Counter(e["level"] for e in entries)
    
    return {
        "filename": filename,
        "server_id": filename.replace('.log', ''),
        "total_lines": len(lines),
        "parsed_entries": len(entries),
        "parse_errors": len(parse_errors),
        "time_span": time_span,
        "level_distribution": dict(level_counts),
        "entries": entries,  # Full entries list
        "first_10_entries": entries[:10],
        "last_10_entries": entries[-10:] if len(entries) > 10 else entries,
        "sample_parse_errors": parse_errors[:5]
    }


async def on_parse_log_file(context: RunContextWrapper, params_str: str) -> Any:
    params = json.loads(params_str)
    
    # Support both filepath (reads file) and content (uses directly)
    filepath = params.get("filepath", "")
    content = params.get("content", "")
    filename = params.get("filename", "")
    
    # If filepath provided, read the file
    if filepath and not content:
        import os
        try:
            # Get workspace path from context if available
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
        filename = "unknown.log"
    
    result = parse_log_file(content, filename)
    return result


tool_parse_log_file = FunctionTool(
    name='local-log_parse',
    description='''Parse a server log file to extract ALL structured entries with timestamps, levels, messages, response times, and status codes. Returns complete entry list for analysis.

**Input (Option 1 - Direct filepath):** filepath (str) - Path to the log file (e.g., "logs/server_01.log")
**Input (Option 2 - Content):** content (str), filename (str) - Log content and filename

**Returns:** dict:
{
  "filename": str,
  "total_lines": int,
  "entries": [{"timestamp": str, "level": str, "message": str, "response_time_ms": float, "status_code": int}],
  "parse_stats": {...}
}''',
    params_json_schema={
        "type": "object",
        "properties": {
            "filepath": {"type": "string", "description": "Path to the log file (e.g., 'logs/server_01.log')"},
            "content": {"type": "string", "description": "The log file content (alternative to filepath)"},
            "filename": {"type": "string", "description": "The filename (optional if using filepath)"},
        },
        "required": []
    },
    on_invoke_tool=on_parse_log_file
)


# ============== Step 2: Analyze Errors (Enhanced) ==============

def analyze_errors(entries: List[Dict]) -> Dict:
    """Analyze error entries with detailed categorization and context."""
    errors = [e for e in entries if e.get("level") == "ERROR"]
    
    # Categorize errors by type with full context
    categorized_errors = []
    type_counts = Counter()
    severity_counts = {"critical": 0, "high": 0, "medium": 0, "low": 0}
    
    for error in errors:
        message = error.get("message", "").lower()
        error_type = "UnknownError"
        error_info = {"severity": "low", "description": "Unknown error type", "suggested_action": "Review logs manually"}
        
        for etype, info in ERROR_TYPE_PATTERNS.items():
            if re.search(info["pattern"], message, re.IGNORECASE):
                error_type = etype
                error_info = info
                break
        
        type_counts[error_type] += 1
        severity_counts[error_info["severity"]] += 1
        
        categorized_errors.append({
            "timestamp": error.get("timestamp"),
            "line_number": error.get("line_number"),
            "message": error.get("message"),
            "error_type": error_type,
            "severity": error_info["severity"],
            "description": error_info["description"],
            "suggested_action": error_info["suggested_action"]
        })
    
    # Find error patterns (repeated messages)
    message_patterns = Counter(e["message"][:50] for e in errors)
    repeated_patterns = [{"pattern": p, "count": c} for p, c in message_patterns.most_common(5) if c > 1]
    
    # Time distribution of errors
    error_by_hour = Counter()
    for error in errors:
        ts = error.get("timestamp", "")
        if ts:
            try:
                hour = ts.split()[1].split(":")[0]
                error_by_hour[hour] += 1
            except:
                pass
    
    return {
        "error_count": len(errors),
        "error_types": list(type_counts.keys()),
        "type_distribution": dict(type_counts),
        "severity_distribution": severity_counts,
        "most_common_type": type_counts.most_common(1)[0][0] if type_counts else None,
        "most_critical_count": severity_counts["critical"] + severity_counts["high"],
        "categorized_errors": categorized_errors,
        "repeated_patterns": repeated_patterns,
        "error_by_hour": dict(error_by_hour),
        "first_error": categorized_errors[0] if categorized_errors else None,
        "last_error": categorized_errors[-1] if categorized_errors else None,
        "recommendations": [
            info["suggested_action"] for etype, info in ERROR_TYPE_PATTERNS.items()
            if type_counts.get(etype, 0) > 0
        ]
    }


async def on_analyze_errors(context: RunContextWrapper, params_str: str) -> Any:
    params = json.loads(params_str)
    entries = params.get("entries", [])
    result = analyze_errors(entries)
    return result


tool_analyze_errors = FunctionTool(
    name='local-log_analyze_errors',
    description='''Analyze ALL error entries with detailed categorization, severity levels, patterns, time distribution, and actionable recommendations.

**Input:** entries (list[dict]) - The parsed log entries from log_parse

**Returns:** dict:
{
  "error_count": int,
  "error_rate": float,
  "categories": {...},
  "severity_distribution": {...},
  "patterns": [...],
  "recommendations": [...]
}''',
    params_json_schema={
        "type": "object",
        "properties": {
            "entries": {"type": "array", "description": "The parsed log entries from log_parse"},
        },
        "required": ["entries"]
    },
    on_invoke_tool=on_analyze_errors
)


# ============== Step 3: Analyze Warnings (Enhanced) ==============

def analyze_warnings(entries: List[Dict]) -> Dict:
    """Analyze warning entries with detailed categorization."""
    warnings = [e for e in entries if e.get("level") == "WARNING"]
    
    # Categorize warnings
    categories = {cat: {"count": 0, "messages": []} for cat in WARNING_CATEGORIES}
    categories["other"] = {"count": 0, "messages": []}
    
    categorized_warnings = []
    
    for warning in warnings:
        message = warning.get("message", "").lower()
        category = "other"
        
        for cat, info in WARNING_CATEGORIES.items():
            if re.search(info["pattern"], message, re.IGNORECASE):
                category = cat
                break
        
        categories[category]["count"] += 1
        if len(categories[category]["messages"]) < 3:
            categories[category]["messages"].append(warning.get("message", ""))
        
        categorized_warnings.append({
            "timestamp": warning.get("timestamp"),
            "line_number": warning.get("line_number"),
            "message": warning.get("message"),
            "category": category
        })
    
    # Find warning trends
    warning_by_minute = Counter()
    for warning in warnings:
        ts = warning.get("timestamp", "")
        if ts:
            try:
                minute = ts[:16]  # YYYY-MM-DD HH:MM
                warning_by_minute[minute] += 1
            except:
                pass
    
    # Find peak warning periods
    peak_minutes = warning_by_minute.most_common(5)
    
    return {
        "warning_count": len(warnings),
        "categories": {cat: data["count"] for cat, data in categories.items()},
        "category_details": categories,
        "categorized_warnings": categorized_warnings,
        "peak_warning_periods": [{"time": t, "count": c} for t, c in peak_minutes],
        "warning_messages_sample": [w.get("message", "") for w in warnings[:10]],
        "resource_warnings": categories["memory"]["count"] + categories["cpu"]["count"] + categories["disk"]["count"],
        "performance_warnings": categories["performance"]["count"]
    }


async def on_analyze_warnings(context: RunContextWrapper, params_str: str) -> Any:
    params = json.loads(params_str)
    entries = params.get("entries", [])
    result = analyze_warnings(entries)
    return result


tool_analyze_warnings = FunctionTool(
    name='local-log_analyze_warnings',
    description='''Analyze ALL warning entries with categorization (memory, cpu, disk, network, performance), peak periods, and detailed breakdown.

**Input:** entries (list[dict]) - The parsed log entries from log_parse

**Returns:** dict:
{
  "warning_count": int,
  "categories": {"memory": int, "cpu": int, "disk": int, ...},
  "peak_periods": [...],
  "breakdown": {...}
}''',
    params_json_schema={
        "type": "object",
        "properties": {
            "entries": {"type": "array", "description": "The parsed log entries from log_parse"},
        },
        "required": ["entries"]
    },
    on_invoke_tool=on_analyze_warnings
)


# ============== Step 4: Analyze Requests (Enhanced) ==============

def analyze_requests(entries: List[Dict]) -> Dict:
    """Analyze request statistics with detailed metrics."""
    info_entries = [e for e in entries if e.get("level") == "INFO"]
    
    requests = []
    response_times = []
    status_codes = Counter()
    
    for entry in info_entries:
        message = entry.get("message", "")
        response_time = entry.get("response_time_ms")
        status_code = entry.get("status_code")
        
        if response_time is not None or "request" in message.lower() or "processed" in message.lower():
            request_info = {
                "timestamp": entry.get("timestamp"),
                "message": message,
                "response_time_ms": response_time,
                "status_code": status_code
            }
            requests.append(request_info)
            
            if response_time:
                response_times.append(response_time)
            if status_code:
                status_codes[status_code] += 1
    
    # Calculate response time statistics
    if response_times:
        sorted_times = sorted(response_times)
        avg_time = sum(response_times) / len(response_times)
        p50 = sorted_times[len(sorted_times) // 2]
        p95_idx = int(len(sorted_times) * 0.95)
        p99_idx = int(len(sorted_times) * 0.99)
        p95 = sorted_times[min(p95_idx, len(sorted_times) - 1)]
        p99 = sorted_times[min(p99_idx, len(sorted_times) - 1)]
        
        # Categorize by speed
        fast = sum(1 for t in response_times if t < 100)
        normal = sum(1 for t in response_times if 100 <= t < 300)
        slow = sum(1 for t in response_times if 300 <= t < 1000)
        very_slow = sum(1 for t in response_times if t >= 1000)
    else:
        avg_time = p50 = p95 = p99 = 0
        fast = normal = slow = very_slow = 0
    
    # Calculate success rate
    success_count = sum(1 for s in status_codes.elements() if 200 <= s < 300)
    client_error = sum(1 for s in status_codes.elements() if 400 <= s < 500)
    server_error = sum(1 for s in status_codes.elements() if 500 <= s < 600)
    total_with_status = sum(status_codes.values())
    
    success_rate = (success_count / total_with_status * 100) if total_with_status > 0 else 100.0
    
    return {
        "total_requests": len(requests),
        "requests_with_timing": len(response_times),
        "requests_with_status": total_with_status,
        "status_code_distribution": dict(status_codes),
        "success_count": success_count,
        "client_errors": client_error,
        "server_errors": server_error,
        "success_rate": round(success_rate, 2),
        "response_time_stats": {
            "average_ms": round(avg_time, 1),
            "median_ms": p50,
            "p95_ms": p95,
            "p99_ms": p99,
            "min_ms": min(response_times) if response_times else 0,
            "max_ms": max(response_times) if response_times else 0
        },
        "response_time_distribution": {
            "fast_under_100ms": fast,
            "normal_100_300ms": normal,
            "slow_300_1000ms": slow,
            "very_slow_over_1000ms": very_slow
        },
        "sample_requests": requests[:15],
        "slowest_requests": sorted(requests, key=lambda x: x.get("response_time_ms") or 0, reverse=True)[:5]
    }


async def on_analyze_requests(context: RunContextWrapper, params_str: str) -> Any:
    params = json.loads(params_str)
    entries = params.get("entries", [])
    result = analyze_requests(entries)
    return result


tool_analyze_requests = FunctionTool(
    name='local-log_analyze_requests',
    description='''Analyze request statistics with detailed metrics: response times (avg, p50, p95, p99), status codes, success rates, and slowest requests.

**Input:** entries (list[dict]) - The parsed log entries from log_parse

**Returns:** dict:
{
  "request_count": int,
  "response_times": {"avg": float, "p50": float, "p95": float, "p99": float},
  "status_codes": {...},
  "success_rate": float,
  "slowest_requests": [...]
}''',
    params_json_schema={
        "type": "object",
        "properties": {
            "entries": {"type": "array", "description": "The parsed log entries from log_parse"},
        },
        "required": ["entries"]
    },
    on_invoke_tool=on_analyze_requests
)


# ============== Step 5: Calculate Health Score (Enhanced) ==============

def calculate_health_score(error_analysis: Dict, warning_analysis: Dict, request_analysis: Dict, total_lines: int) -> Dict:
    """Calculate comprehensive server health score with detailed breakdown."""
    score = 100
    issues = []
    recommendations = []
    
    # Error rate impact (40 points max)
    error_count = error_analysis.get("error_count", 0)
    if total_lines > 0:
        error_rate = (error_count / total_lines) * 100
        if error_rate > 10:
            score -= 40
            issues.append(f"Critical error rate: {error_rate:.1f}%")
        elif error_rate > 5:
            score -= 30
            issues.append(f"High error rate: {error_rate:.1f}%")
        elif error_rate > 2:
            score -= 20
            issues.append(f"Elevated error rate: {error_rate:.1f}%")
        elif error_rate > 0:
            score -= 10
    else:
        error_rate = 0
    
    # Critical errors penalty
    critical_count = error_analysis.get("most_critical_count", 0)
    if critical_count > 5:
        score -= 10
        issues.append(f"Multiple critical errors: {critical_count}")
    
    # Warning rate impact (25 points max)
    warning_count = warning_analysis.get("warning_count", 0)
    if total_lines > 0:
        warning_rate = (warning_count / total_lines) * 100
        if warning_rate > 15:
            score -= 25
            issues.append(f"High warning rate: {warning_rate:.1f}%")
        elif warning_rate > 10:
            score -= 15
        elif warning_rate > 5:
            score -= 10
        elif warning_rate > 0:
            score -= 5
    else:
        warning_rate = 0
    
    # Resource warnings penalty
    resource_warnings = warning_analysis.get("resource_warnings", 0)
    if resource_warnings > 10:
        score -= 5
        issues.append(f"Resource pressure detected: {resource_warnings} warnings")
    
    # Success rate impact (25 points max)
    success_rate = request_analysis.get("success_rate", 100)
    if success_rate < 90:
        score -= 25
        issues.append(f"Low success rate: {success_rate}%")
    elif success_rate < 95:
        score -= 15
        issues.append(f"Below target success rate: {success_rate}%")
    elif success_rate < 99:
        score -= 5
    
    # Response time impact (10 points max)
    response_stats = request_analysis.get("response_time_stats", {})
    avg_response = response_stats.get("average_ms", 0)
    p95_response = response_stats.get("p95_ms", 0)
    
    if avg_response > 500:
        score -= 10
        issues.append(f"Slow average response: {avg_response}ms")
    elif avg_response > 300:
        score -= 7
    elif avg_response > 200:
        score -= 3
    
    if p95_response > 1000:
        score -= 5
        issues.append(f"High p95 latency: {p95_response}ms")
    
    score = max(0, min(100, score))
    
    # Determine health status
    if score >= 90:
        status = "excellent"
        color = "green"
    elif score >= 75:
        status = "good"
        color = "green"
    elif score >= 50:
        status = "moderate"
        color = "yellow"
    elif score >= 25:
        status = "poor"
        color = "orange"
    else:
        status = "critical"
        color = "red"
    
    # Generate recommendations
    recommendations.extend(error_analysis.get("recommendations", []))
    if avg_response > 300:
        recommendations.append("Investigate slow endpoints and optimize queries")
    if resource_warnings > 5:
        recommendations.append("Review resource allocation and scaling needs")
    
    return {
        "health_score": score,
        "health_status": status,
        "status_color": color,
        "issues_found": issues,
        "recommendations": recommendations[:5],
        "score_breakdown": {
            "error_impact": {
                "count": error_count,
                "rate_percent": round(error_rate, 2),
                "critical_count": critical_count
            },
            "warning_impact": {
                "count": warning_count,
                "rate_percent": round(warning_rate, 2),
                "resource_warnings": resource_warnings
            },
            "request_metrics": {
                "success_rate": success_rate,
                "avg_response_ms": avg_response,
                "p95_response_ms": p95_response
            }
        },
        "summary": {
            "total_log_lines": total_lines,
            "error_count": error_count,
            "warning_count": warning_count,
            "request_count": request_analysis.get("total_requests", 0)
        }
    }


async def on_calculate_health_score(context: RunContextWrapper, params_str: str) -> Any:
    params = json.loads(params_str)
    error_analysis = params.get("error_analysis", {})
    warning_analysis = params.get("warning_analysis", {})
    request_analysis = params.get("request_analysis", {})
    total_lines = params.get("total_lines", 0)
    result = calculate_health_score(error_analysis, warning_analysis, request_analysis, total_lines)
    return result


tool_calculate_health_score = FunctionTool(
    name='local-log_calculate_health',
    description='''Calculate comprehensive server health score with detailed breakdown, issues list, and actionable recommendations.

**Input:** error_analysis (dict), warning_analysis (dict), request_analysis (dict), total_lines (int) - Results from previous tools

**Returns:** dict:
{
  "health_score": float,
  "status": str,
  "breakdown": {"error_score": float, "warning_score": float, "performance_score": float},
  "issues": [...],
  "recommendations": [...]
}''',
    params_json_schema={
        "type": "object",
        "properties": {
            "error_analysis": {"type": "object", "description": "Result from log_analyze_errors"},
            "warning_analysis": {"type": "object", "description": "Result from log_analyze_warnings"},
            "request_analysis": {"type": "object", "description": "Result from log_analyze_requests"},
            "total_lines": {"type": "integer", "description": "Total lines in the log file"},
        },
        "required": ["error_analysis", "warning_analysis", "request_analysis", "total_lines"]
    },
    on_invoke_tool=on_calculate_health_score
)


# ============== Export all tools ==============

log_parser_tools = [
    tool_parse_log_file,       # Step 1: Parse log
    tool_analyze_errors,        # Step 2: Analyze errors
    tool_analyze_warnings,      # Step 3: Analyze warnings
    tool_analyze_requests,      # Step 4: Analyze requests
    tool_calculate_health_score, # Step 5: Calculate health
]
