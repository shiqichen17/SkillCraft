# csv_tools.py
# CSV/Excel Processing Tools for batch-excel-merger task
# Enhanced version with larger, more detailed outputs for Skill Mode efficiency

import json
import csv
import io
from typing import Any, List, Dict, Optional
from collections import Counter
from agents.tool import FunctionTool, RunContextWrapper


# ============== Step 1: Parse CSV/Excel Data (Enhanced) ==============

def parse_spreadsheet_data(content: str, filename: str) -> Dict:
    """Parse CSV/Excel-like data with comprehensive analysis."""
    lines = content.strip().split('\n')
    
    # Detect format
    is_csv = ',' in lines[0] if lines else False
    is_tsv = '\t' in lines[0] if lines else False
    delimiter = ',' if is_csv else '\t' if is_tsv else ','
    
    records = []
    headers = []
    column_stats = {}
    
    try:
        reader = csv.DictReader(io.StringIO(content), delimiter=delimiter)
        headers = reader.fieldnames or []
        
        for row in reader:
            records.append(dict(row))
        
        # Calculate column statistics
        for header in headers:
            values = [r.get(header, '') for r in records]
            non_empty = [v for v in values if v and v.strip()]
            
            # Try to detect numeric columns
            numeric_values = []
            for v in non_empty:
                try:
                    numeric_values.append(float(str(v).replace(',', '').replace('$', '').replace('%', '')))
                except (ValueError, TypeError):
                    pass
            
            col_stat = {
                "name": header,
                "total_values": len(values),
                "non_empty": len(non_empty),
                "empty": len(values) - len(non_empty),
                "fill_rate": round(len(non_empty) / len(values) * 100, 1) if values else 0,
                "unique_values": len(set(non_empty)),
                "is_numeric": len(numeric_values) > len(non_empty) * 0.8,
                "sample_values": list(set(non_empty))[:5]
            }
            
            if numeric_values:
                col_stat["numeric_stats"] = {
                    "min": min(numeric_values),
                    "max": max(numeric_values),
                    "avg": round(sum(numeric_values) / len(numeric_values), 2),
                    "sum": round(sum(numeric_values), 2)
                }
            
            column_stats[header] = col_stat
    
    except Exception as e:
        return {
            "filename": filename,
            "error": str(e),
            "valid": False,
            "records": [],
            "headers": []
        }
    
    # Extract department from filename
    dept_name = filename.replace('dept_', '').replace('.xlsx', '').replace('.csv', '').replace('.txt', '')
    dept_name = dept_name.replace('_', ' ').title()
    
    return {
        "filename": filename,
        "department": dept_name,
        "valid": True,
        "format": {
            "type": "csv" if is_csv else "tsv" if is_tsv else "unknown",
            "delimiter": delimiter,
            "total_lines": len(lines),
            "data_rows": len(records)
        },
        "headers": headers,
        "column_count": len(headers),
        "record_count": len(records),
        "column_statistics": column_stats,
        "records": records,
        "sample_records": records[:5] if len(records) > 5 else records
    }


async def on_parse_spreadsheet_data(context: RunContextWrapper, params_str: str) -> Any:
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
        filename = "unknown.csv"
    
    result = parse_spreadsheet_data(content, filename)
    return result


tool_parse_spreadsheet_data = FunctionTool(
    name='local-csv_parse',
    description='''Parse CSV/Excel-like data with comprehensive column statistics, numeric analysis, and format detection.

**Input (Option 1 - Direct filepath):** filepath (str) - Path to CSV file (e.g., "reports/dept_sales.csv")
**Input (Option 2 - Content):** content (str), filename (str) - CSV content and filename

**Returns:** dict:
{
  "filename": str,
  "headers": [str],
  "records": [dict],
  "row_count": int,
  "column_stats": {...},
  "data_types": {...}
}''',
    params_json_schema={
        "type": "object",
        "properties": {
            "filepath": {"type": "string", "description": "Path to CSV file (e.g., 'reports/dept_sales.csv')"},
            "content": {"type": "string", "description": "The CSV/text content (alternative to filepath)"},
            "filename": {"type": "string", "description": "The filename (optional if using filepath)"},
        },
        "required": []
    },
    on_invoke_tool=on_parse_spreadsheet_data
)


# ============== Step 2: Extract Department Metrics (Enhanced) ==============

def extract_department_metrics(records: List[Dict], department: str, column_stats: Dict = None) -> Dict:
    """Extract comprehensive metrics from department records."""
    if not records:
        return {
            "department": department,
            "error": "No records provided",
            "metrics": {}
        }
    
    # Initialize metrics
    employee_count = 0
    total_budget = 0
    total_revenue = 0
    total_expenses = 0
    project_count = 0
    kpi_scores = []
    salary_values = []
    performance_values = []
    
    # Analyze each record
    record_analysis = []
    
    for idx, record in enumerate(records):
        record_metrics = {"row": idx + 1}
        
        for key, value in record.items():
            key_lower = key.lower()
            value_str = str(value).replace(',', '').replace('$', '').replace('%', '').strip()
            
            # Employee detection
            if any(k in key_lower for k in ['name', 'employee', 'emp_name', 'employee_name', 'staff']):
                employee_count += 1
                record_metrics["employee_name"] = value
            
            # Budget/financial metrics
            if 'budget' in key_lower or 'allocation' in key_lower:
                try:
                    amount = float(value_str)
                    total_budget += amount
                    record_metrics["budget"] = amount
                except (ValueError, TypeError):
                    pass
            
            if 'revenue' in key_lower or 'income' in key_lower or 'sales' in key_lower:
                try:
                    amount = float(value_str)
                    total_revenue += amount
                    record_metrics["revenue"] = amount
                except (ValueError, TypeError):
                    pass
            
            if 'expense' in key_lower or 'cost' in key_lower:
                try:
                    amount = float(value_str)
                    total_expenses += amount
                    record_metrics["expense"] = amount
                except (ValueError, TypeError):
                    pass
            
            if 'salary' in key_lower or 'wage' in key_lower or 'compensation' in key_lower:
                try:
                    amount = float(value_str)
                    salary_values.append(amount)
                    record_metrics["salary"] = amount
                except (ValueError, TypeError):
                    pass
            
            # Project counting
            if 'project' in key_lower:
                project_count += 1
                record_metrics["project"] = value
            
            # KPI/Performance metrics
            if 'kpi' in key_lower or 'score' in key_lower or 'rating' in key_lower:
                try:
                    score = float(value_str)
                    if 0 <= score <= 100:
                        kpi_scores.append(score)
                        record_metrics["kpi_score"] = score
                except (ValueError, TypeError):
                    pass
            
            if 'performance' in key_lower:
                try:
                    perf = float(value_str)
                    performance_values.append(perf)
                    record_metrics["performance"] = perf
                except (ValueError, TypeError):
                    pass
        
        if len(record_metrics) > 1:
            record_analysis.append(record_metrics)
    
    # Use record count if no employees detected
    if employee_count == 0:
        employee_count = len(records)
    
    # Calculate derived metrics
    avg_kpi = sum(kpi_scores) / len(kpi_scores) if kpi_scores else None
    avg_salary = sum(salary_values) / len(salary_values) if salary_values else None
    avg_performance = sum(performance_values) / len(performance_values) if performance_values else None
    
    # Calculate budget utilization if we have both
    budget_utilization = None
    if total_budget > 0 and total_expenses > 0:
        budget_utilization = round(total_expenses / total_budget * 100, 1)
    
    # Calculate salary distribution percentiles
    salary_percentiles = {}
    if salary_values:
        sorted_salaries = sorted(salary_values)
        n = len(sorted_salaries)
        salary_percentiles = {
            "p10": sorted_salaries[int(n * 0.1)] if n > 0 else None,
            "p25": sorted_salaries[int(n * 0.25)] if n > 0 else None,
            "p50_median": sorted_salaries[int(n * 0.5)] if n > 0 else None,
            "p75": sorted_salaries[int(n * 0.75)] if n > 0 else None,
            "p90": sorted_salaries[int(n * 0.9)] if n > 0 else None,
            "std_dev": round((sum((x - avg_salary) ** 2 for x in salary_values) / len(salary_values)) ** 0.5, 2) if avg_salary else None
        }
    
    # Calculate KPI distribution
    kpi_distribution = {}
    if kpi_scores:
        kpi_distribution = {
            "excellent_90_100": len([k for k in kpi_scores if k >= 90]),
            "good_80_89": len([k for k in kpi_scores if 80 <= k < 90]),
            "satisfactory_70_79": len([k for k in kpi_scores if 70 <= k < 80]),
            "needs_improvement_60_69": len([k for k in kpi_scores if 60 <= k < 70]),
            "poor_below_60": len([k for k in kpi_scores if k < 60]),
            "distribution_analysis": {
                "high_performers_percentage": round(len([k for k in kpi_scores if k >= 80]) / len(kpi_scores) * 100, 1) if kpi_scores else 0,
                "low_performers_percentage": round(len([k for k in kpi_scores if k < 70]) / len(kpi_scores) * 100, 1) if kpi_scores else 0
            }
        }
    
    # Analyze cost efficiency
    cost_efficiency = {}
    if total_revenue > 0 and total_expenses > 0:
        cost_efficiency = {
            "cost_to_revenue_ratio": round(total_expenses / total_revenue * 100, 2),
            "profit_margin": round((total_revenue - total_expenses) / total_revenue * 100, 2),
            "revenue_per_employee": round(total_revenue / employee_count, 2) if employee_count > 0 else None,
            "cost_per_employee": round(total_expenses / employee_count, 2) if employee_count > 0 else None,
            "efficiency_rating": "excellent" if (total_revenue - total_expenses) / total_revenue > 0.2 else "good" if (total_revenue - total_expenses) / total_revenue > 0.1 else "needs_improvement"
        }
    
    # Detailed headcount analysis
    headcount_analysis = {
        "employee_count": employee_count,
        "records_processed": len(records),
        "data_completeness": round(len(record_analysis) / len(records) * 100, 1) if records else 0,
        "records_with_salary_data": len(salary_values),
        "records_with_kpi_data": len(kpi_scores),
        "records_with_project_data": project_count
    }
    
    return {
        "department": department,
        "headcount": headcount_analysis,
        "financial": {
            "total_budget": round(total_budget, 2),
            "total_revenue": round(total_revenue, 2),
            "total_expenses": round(total_expenses, 2),
            "net_result": round(total_revenue - total_expenses, 2) if total_revenue > 0 else None,
            "budget_utilization_percent": budget_utilization,
            "budget_status": "under_budget" if budget_utilization and budget_utilization < 90 else "on_track" if budget_utilization and budget_utilization < 100 else "over_budget" if budget_utilization else "unknown"
        },
        "salary_analysis": {
            "total_payroll": round(sum(salary_values), 2) if salary_values else 0,
            "avg_salary": round(avg_salary, 2) if avg_salary else None,
            "min_salary": round(min(salary_values), 2) if salary_values else None,
            "max_salary": round(max(salary_values), 2) if salary_values else None,
            "salary_range": round(max(salary_values) - min(salary_values), 2) if salary_values else None,
            "salary_count": len(salary_values),
            "percentiles": salary_percentiles,
            "payroll_to_budget_ratio": round(sum(salary_values) / total_budget * 100, 2) if total_budget > 0 and salary_values else None
        },
        "performance": {
            "avg_kpi_score": round(avg_kpi, 1) if avg_kpi else None,
            "min_kpi": round(min(kpi_scores), 1) if kpi_scores else None,
            "max_kpi": round(max(kpi_scores), 1) if kpi_scores else None,
            "kpi_data_points": len(kpi_scores),
            "avg_performance": round(avg_performance, 1) if avg_performance else None,
            "kpi_distribution": kpi_distribution,
            "performance_trend": "improving" if avg_kpi and avg_kpi > 75 else "stable" if avg_kpi and avg_kpi > 65 else "declining" if avg_kpi else "unknown"
        },
        "projects": {
            "project_count": project_count,
            "projects_per_employee": round(project_count / employee_count, 2) if employee_count > 0 else 0,
            "workload_assessment": "high" if project_count / employee_count > 3 else "moderate" if project_count / employee_count > 1.5 else "low" if employee_count > 0 else "unknown"
        },
        "cost_efficiency": cost_efficiency,
        "record_analysis": record_analysis,  # Full analysis, not limited
        "raw_metrics": {
            "all_salary_values": salary_values,
            "all_kpi_scores": kpi_scores,
            "all_performance_values": performance_values
        }
    }


async def on_extract_department_metrics(context: RunContextWrapper, params_str: str) -> Any:
    params = json.loads(params_str)
    records = params.get("records", [])
    department = params.get("department", "Unknown")
    column_stats = params.get("column_stats", {})
    result = extract_department_metrics(records, department, column_stats)
    return result


tool_extract_department_metrics = FunctionTool(
    name='local-csv_extract_metrics',
    description='''Extract comprehensive metrics: headcount, financials, salary analysis, performance, and projects from department records.

**Input:** records (list[dict]), department (str), column_stats (dict, optional)

**Returns:** dict:
{
  "department": str,
  "headcount": int,
  "salary_stats": {"avg": float, "min": float, "max": float},
  "performance_stats": {...},
  "projects": [...]
}''',
    params_json_schema={
        "type": "object",
        "properties": {
            "records": {"type": "array", "description": "The parsed records from csv_parse"},
            "department": {"type": "string", "description": "Department name"},
            "column_stats": {"type": "object", "description": "Column statistics from csv_parse (optional)"},
        },
        "required": ["records", "department"]
    },
    on_invoke_tool=on_extract_department_metrics
)


# ============== Step 3: Validate Data Quality (Enhanced) ==============

def validate_data_quality(records: List[Dict], headers: List[str], column_stats: Dict = None) -> Dict:
    """Comprehensive data quality validation."""
    if not records:
        return {
            "data_quality": "empty",
            "quality_score": 0,
            "issues": [{"type": "critical", "message": "No records found"}],
            "warnings": [],
            "completeness": 0.0
        }
    
    issues = []
    warnings = []
    quality_checks = []
    
    # Check 1: Completeness
    missing_count = 0
    total_fields = 0
    missing_by_column = {}
    
    for record in records:
        for key, value in record.items():
            total_fields += 1
            if value is None or str(value).strip() == "" or str(value).upper() in ["N/A", "NULL", "NONE", "-"]:
                missing_count += 1
                missing_by_column[key] = missing_by_column.get(key, 0) + 1
    
    completeness = 1.0 - (missing_count / total_fields) if total_fields > 0 else 0.0
    quality_checks.append({
        "check": "completeness",
        "passed": completeness >= 0.9,
        "score": round(completeness * 100, 1),
        "details": f"{missing_count} missing values out of {total_fields} total fields"
    })
    
    if completeness < 0.9:
        warnings.append({
            "type": "completeness",
            "message": f"Data completeness is {completeness*100:.1f}%",
            "missing_by_column": missing_by_column
        })
    
    if completeness < 0.5:
        issues.append({
            "type": "critical_completeness",
            "message": "Significant data missing (>50%)",
            "severity": "high"
        })
    
    # Check 2: Duplicate detection
    seen_rows = set()
    duplicate_count = 0
    for record in records:
        row_key = tuple(sorted(record.items()))
        if row_key in seen_rows:
            duplicate_count += 1
        seen_rows.add(row_key)
    
    quality_checks.append({
        "check": "duplicates",
        "passed": duplicate_count == 0,
        "score": round((1 - duplicate_count / len(records)) * 100, 1) if records else 100,
        "details": f"{duplicate_count} duplicate rows detected"
    })
    
    if duplicate_count > 0:
        warnings.append({
            "type": "duplicates",
            "message": f"{duplicate_count} duplicate rows found",
            "severity": "medium"
        })
    
    # Check 3: Data consistency (check for mixed types in columns)
    type_issues = []
    if column_stats:
        for col_name, stats in column_stats.items():
            if stats.get("is_numeric") and stats.get("non_empty", 0) != len([v for v in stats.get("sample_values", []) if v]):
                type_issues.append(col_name)
    
    quality_checks.append({
        "check": "type_consistency",
        "passed": len(type_issues) == 0,
        "score": round((1 - len(type_issues) / len(headers)) * 100, 1) if headers else 100,
        "details": f"{len(type_issues)} columns with potential type inconsistency"
    })
    
    if type_issues:
        warnings.append({
            "type": "type_inconsistency",
            "message": f"Columns with mixed types: {type_issues[:5]}",
            "severity": "low"
        })
    
    # Check 4: Column naming conventions
    naming_issues = []
    for header in headers:
        if header.startswith(' ') or header.endswith(' '):
            naming_issues.append(f"'{header}' has leading/trailing spaces")
        if any(c in header for c in ['!', '@', '#', '$', '%', '^', '&', '*']):
            naming_issues.append(f"'{header}' contains special characters")
    
    quality_checks.append({
        "check": "naming_conventions",
        "passed": len(naming_issues) == 0,
        "score": 100 if not naming_issues else 80,
        "details": f"{len(naming_issues)} naming issues found"
    })
    
    # Calculate overall quality score
    avg_score = sum(c["score"] for c in quality_checks) / len(quality_checks)
    
    if avg_score >= 90:
        quality_status = "excellent"
    elif avg_score >= 75:
        quality_status = "good"
    elif avg_score >= 50:
        quality_status = "fair"
    else:
        quality_status = "poor"
    
    return {
        "data_quality": quality_status,
        "quality_score": round(avg_score, 1),
        "completeness": round(completeness, 3),
        "quality_checks": quality_checks,
        "issues": issues,
        "warnings": warnings,
        "statistics": {
            "total_records": len(records),
            "total_fields": total_fields,
            "missing_values": missing_count,
            "duplicate_rows": duplicate_count,
            "columns_with_issues": len(type_issues) + len(naming_issues)
        },
        "missing_by_column": dict(sorted(missing_by_column.items(), key=lambda x: -x[1])[:5])
    }


async def on_validate_data_quality(context: RunContextWrapper, params_str: str) -> Any:
    params = json.loads(params_str)
    records = params.get("records", [])
    headers = params.get("headers", [])
    column_stats = params.get("column_stats", {})
    result = validate_data_quality(records, headers, column_stats)
    return result


tool_validate_data_quality = FunctionTool(
    name='local-csv_validate_quality',
    description='''Comprehensive data quality validation: completeness, duplicates, type consistency, and naming conventions with detailed scoring.

**Input:** records (list[dict]), headers (list[str]), column_stats (dict, optional)

**Returns:** dict:
{
  "quality_score": float,
  "completeness": float,
  "duplicates_found": int,
  "issues": [...],
  "recommendations": [...]
}''',
    params_json_schema={
        "type": "object",
        "properties": {
            "records": {"type": "array", "description": "The parsed records from csv_parse"},
            "headers": {"type": "array", "description": "Column headers from csv_parse"},
            "column_stats": {"type": "object", "description": "Column statistics from csv_parse (optional)"},
        },
        "required": ["records", "headers"]
    },
    on_invoke_tool=on_validate_data_quality
)


# ============== Step 4: Generate Department Report (Enhanced) ==============

def generate_department_report(
    parse_result: Dict,
    metrics: Dict,
    quality: Dict
) -> Dict:
    """Generate a comprehensive department report."""
    department = metrics.get("department", parse_result.get("department", "Unknown"))
    
    # Calculate overall department score - handle None values explicitly
    quality_score = quality.get("quality_score", 0) or 0
    kpi_score = metrics.get("performance", {}).get("avg_kpi_score")
    
    # Ensure numeric comparison works with None values
    if kpi_score is not None and quality_score:
        overall_score = (quality_score * 0.3 + float(kpi_score) * 0.7)
    elif quality_score:
        overall_score = quality_score
    else:
        overall_score = 50
    
    # Determine department health status
    if overall_score >= 80:
        status = "excellent"
    elif overall_score >= 60:
        status = "good"
    elif overall_score >= 40:
        status = "needs_improvement"
    else:
        status = "critical"
    
    # Generate recommendations - handle None values safely
    recommendations = []
    completeness = quality.get("completeness", 0)
    if completeness is not None and completeness < 0.9:
        recommendations.append("Improve data completeness - many fields have missing values")
    
    avg_kpi_for_rec = metrics.get("performance", {}).get("avg_kpi_score")
    if avg_kpi_for_rec is not None and avg_kpi_for_rec < 70:
        recommendations.append("Address performance issues - KPI scores below target")
    
    budget_util = metrics.get("financial", {}).get("budget_utilization_percent")
    if budget_util is not None and budget_util > 100:
        recommendations.append("Review budget allocation - currently over-budget")
    
    return {
        "department": department,
        "filename": parse_result.get("filename", "unknown"),
        "status": status,
        "overall_score": round(overall_score, 1),
        "summary": {
            "employee_count": metrics.get("headcount", {}).get("employee_count", 0),
            "total_budget": metrics.get("financial", {}).get("total_budget", 0),
            "total_revenue": metrics.get("financial", {}).get("total_revenue", 0),
            "avg_kpi_score": metrics.get("performance", {}).get("avg_kpi_score"),
            "data_quality": quality.get("data_quality", "unknown"),
            "quality_score": quality.get("quality_score", 0)
        },
        "financials": metrics.get("financial", {}),
        "salary_analysis": metrics.get("salary_analysis", {}),
        "performance": metrics.get("performance", {}),
        "projects": metrics.get("projects", {}),
        "data_quality_details": {
            "quality_checks": quality.get("quality_checks", []),
            "issues": quality.get("issues", []),
            "warnings": quality.get("warnings", [])
        },
        "recommendations": recommendations,
        "record_count": parse_result.get("record_count", 0),
        "column_count": parse_result.get("column_count", 0)
    }


async def on_generate_department_report(context: RunContextWrapper, params_str: str) -> Any:
    params = json.loads(params_str)
    parse_result = params.get("parse_result", {})
    metrics = params.get("metrics", {})
    quality = params.get("quality", {})
    result = generate_department_report(parse_result, metrics, quality)
    return result


tool_generate_department_report = FunctionTool(
    name='local-csv_generate_report',
    description='''Generate comprehensive department report with scoring, status, recommendations, and all metrics combined.

**Input:** parse_result (dict), metrics (dict), quality (dict) - Results from previous tools

**Returns:** dict:
{
  "department": str,
  "overall_score": float,
  "status": str,
  "summary": {...},
  "recommendations": [...]
}''',
    params_json_schema={
        "type": "object",
        "properties": {
            "parse_result": {"type": "object", "description": "Result from csv_parse"},
            "metrics": {"type": "object", "description": "Result from csv_extract_metrics"},
            "quality": {"type": "object", "description": "Result from csv_validate_quality"},
        },
        "required": ["parse_result", "metrics", "quality"]
    },
    on_invoke_tool=on_generate_department_report
)


# ============== Helper Functions for Enhanced Analysis ==============

def calculate_efficiency_index(report: Dict) -> float:
    """Calculate efficiency index based on multiple factors."""
    kpi = report.get("summary", {}).get("avg_kpi_score") or 50
    quality = report.get("summary", {}).get("quality_score", 50) or 50
    overall = report.get("overall_score", 50) or 50
    
    # Weighted efficiency index
    efficiency = (kpi * 0.4 + quality * 0.3 + overall * 0.3)
    return round(efficiency, 2)

def calculate_concentration_index(values: List[float]) -> Dict:
    """Calculate concentration/distribution index (like Gini coefficient approximation)."""
    if not values or all(v == 0 for v in values):
        return {"index": 0, "interpretation": "no_data"}
    
    values = [v or 0 for v in values]
    total = sum(values)
    if total == 0:
        return {"index": 0, "interpretation": "no_data"}
    
    # Calculate Herfindahl-Hirschman Index (HHI)
    shares = [(v / total) ** 2 for v in values]
    hhi = sum(shares)
    
    # Normalize HHI to 0-1 scale
    normalized_hhi = (hhi - 1/len(values)) / (1 - 1/len(values)) if len(values) > 1 else 1
    
    if normalized_hhi < 0.15:
        interpretation = "highly_distributed"
    elif normalized_hhi < 0.25:
        interpretation = "moderately_distributed"
    elif normalized_hhi < 0.5:
        interpretation = "moderately_concentrated"
    else:
        interpretation = "highly_concentrated"
    
    return {
        "hhi_index": round(hhi, 4),
        "normalized_index": round(normalized_hhi, 4),
        "interpretation": interpretation,
        "top_share_percentage": round(max(values) / total * 100, 2) if total > 0 else 0
    }


# ============== Step 5: Merge Department Reports (Enhanced) ==============

def merge_department_reports(reports: List[Dict]) -> Dict:
    """Merge all department reports into a comprehensive company summary."""
    if not reports:
        return {"error": "No reports to merge", "departments": []}
    
    # Aggregate totals
    total_employees = sum(r.get("summary", {}).get("employee_count", 0) for r in reports)
    total_budget = sum(r.get("summary", {}).get("total_budget", 0) for r in reports)
    total_revenue = sum(r.get("summary", {}).get("total_revenue", 0) for r in reports)
    
    # Calculate averages
    kpi_values = [r.get("summary", {}).get("avg_kpi_score") for r in reports if r.get("summary", {}).get("avg_kpi_score")]
    quality_scores = [r.get("summary", {}).get("quality_score", 0) for r in reports]
    overall_scores = [r.get("overall_score", 0) for r in reports]
    
    avg_kpi = sum(kpi_values) / len(kpi_values) if kpi_values else None
    avg_quality = sum(quality_scores) / len(quality_scores) if quality_scores else 0
    avg_overall = sum(overall_scores) / len(overall_scores) if overall_scores else 0
    
    # Department rankings - ensure None values don't cause comparison issues
    dept_rankings = sorted(reports, key=lambda x: x.get("overall_score", 0) or 0, reverse=True)
    
    # Find extremes - use 0 as default for None values to avoid comparison errors
    largest_dept = max(reports, key=lambda x: (x.get("summary", {}).get("employee_count", 0) or 0))
    highest_budget = max(reports, key=lambda x: (x.get("summary", {}).get("total_budget", 0) or 0))
    best_kpi = max(reports, key=lambda x: (x.get("summary", {}).get("avg_kpi_score") or 0))
    best_quality = max(reports, key=lambda x: (x.get("summary", {}).get("quality_score", 0) or 0))
    
    # Status distribution
    status_counts = Counter(r.get("status", "unknown") for r in reports)
    
    # Identify issues
    departments_with_issues = [r.get("department") for r in reports if r.get("status") in ["needs_improvement", "critical"]]
    
    # Generate company-wide recommendations
    company_recommendations = []
    if status_counts.get("critical", 0) > 0:
        company_recommendations.append(f"Immediate attention needed for {status_counts['critical']} critical department(s)")
    if avg_quality < 80:
        company_recommendations.append("Improve overall data quality across departments")
    if avg_kpi and avg_kpi < 70:
        company_recommendations.append("Review company-wide performance metrics and targets")
    
    # Cross-department comparisons
    cross_dept_analysis = []
    for r in reports:
        dept_analysis = {
            "department": r.get("department"),
            "vs_company_avg": {
                "kpi_vs_avg": round((r.get("summary", {}).get("avg_kpi_score") or 0) - (avg_kpi or 0), 1) if avg_kpi else None,
                "quality_vs_avg": round((r.get("summary", {}).get("quality_score", 0) or 0) - avg_quality, 1),
                "score_vs_avg": round((r.get("overall_score", 0) or 0) - avg_overall, 1)
            },
            "budget_share": round((r.get("summary", {}).get("total_budget", 0) or 0) / total_budget * 100, 2) if total_budget > 0 else 0,
            "employee_share": round((r.get("summary", {}).get("employee_count", 0) or 0) / total_employees * 100, 2) if total_employees > 0 else 0,
            "efficiency_index": calculate_efficiency_index(r)
        }
        cross_dept_analysis.append(dept_analysis)
    
    # Calculate variance and distribution metrics
    if overall_scores:
        score_variance = sum((s - avg_overall) ** 2 for s in overall_scores) / len(overall_scores)
        score_std_dev = score_variance ** 0.5
    else:
        score_variance = 0
        score_std_dev = 0
    
    statistical_summary = {
        "score_statistics": {
            "mean": round(avg_overall, 2),
            "variance": round(score_variance, 2),
            "std_deviation": round(score_std_dev, 2),
            "min_score": min(overall_scores) if overall_scores else 0,
            "max_score": max(overall_scores) if overall_scores else 0,
            "score_range": max(overall_scores) - min(overall_scores) if overall_scores else 0
        },
        "budget_statistics": {
            "total": round(total_budget, 2),
            "avg_per_department": round(total_budget / len(reports), 2) if reports else 0,
            "budget_concentration": calculate_concentration_index([r.get("summary", {}).get("total_budget", 0) for r in reports])
        },
        "employee_statistics": {
            "total": total_employees,
            "avg_per_department": round(total_employees / len(reports), 2) if reports else 0,
            "employee_concentration": calculate_concentration_index([r.get("summary", {}).get("employee_count", 0) for r in reports])
        }
    }
    
    # Generate detailed department profiles
    department_profiles = []
    for r in reports:
        profile = {
            "name": r.get("department"),
            "status": r.get("status"),
            "overall_score": r.get("overall_score", 0),
            "ranking": dept_rankings.index(r) + 1 if r in dept_rankings else None,
            "summary": r.get("summary", {}),
            "financials": r.get("financials", {}),
            "salary_analysis": r.get("salary_analysis", {}),
            "performance_details": r.get("performance", {}),
            "recommendations": r.get("recommendations", []),
            "data_quality": {
                "quality_score": r.get("summary", {}).get("quality_score", 0),
                "data_quality_status": r.get("summary", {}).get("data_quality", "unknown")
            }
        }
        department_profiles.append(profile)
    
    return {
        "company_summary": {
            "total_departments": len(reports),
            "total_employees": total_employees,
            "total_budget": round(total_budget, 2),
            "total_revenue": round(total_revenue, 2),
            "net_position": round(total_revenue - total_budget, 2) if total_revenue > 0 else None,
            "avg_kpi_score": round(avg_kpi, 1) if avg_kpi else None,
            "avg_quality_score": round(avg_quality, 1),
            "avg_overall_score": round(avg_overall, 1),
            "company_health": "healthy" if avg_overall >= 70 else "moderate" if avg_overall >= 50 else "needs_attention"
        },
        "statistical_summary": statistical_summary,
        "department_rankings": [
            {
                "rank": idx + 1,
                "department": r.get("department"),
                "overall_score": r.get("overall_score", 0),
                "status": r.get("status"),
                "kpi_score": r.get("summary", {}).get("avg_kpi_score"),
                "employee_count": r.get("summary", {}).get("employee_count", 0),
                "budget": r.get("summary", {}).get("total_budget", 0)
            }
            for idx, r in enumerate(dept_rankings)
        ],
        "cross_department_analysis": cross_dept_analysis,
        "highlights": {
            "largest_department": {
                "name": largest_dept.get("department"),
                "employee_count": largest_dept.get("summary", {}).get("employee_count", 0),
                "percentage_of_total": round((largest_dept.get("summary", {}).get("employee_count", 0) or 0) / total_employees * 100, 1) if total_employees > 0 else 0
            },
            "highest_budget_department": {
                "name": highest_budget.get("department"),
                "budget": highest_budget.get("summary", {}).get("total_budget", 0),
                "percentage_of_total": round((highest_budget.get("summary", {}).get("total_budget", 0) or 0) / total_budget * 100, 1) if total_budget > 0 else 0
            },
            "best_performing": {
                "name": best_kpi.get("department"),
                "kpi_score": best_kpi.get("summary", {}).get("avg_kpi_score"),
                "above_average_by": round((best_kpi.get("summary", {}).get("avg_kpi_score") or 0) - (avg_kpi or 0), 1) if avg_kpi else None
            },
            "best_data_quality": {
                "name": best_quality.get("department"),
                "quality_score": best_quality.get("summary", {}).get("quality_score", 0)
            },
            "worst_performing": {
                "name": dept_rankings[-1].get("department") if dept_rankings else None,
                "overall_score": dept_rankings[-1].get("overall_score", 0) if dept_rankings else 0
            }
        },
        "health_overview": {
            "status_distribution": dict(status_counts),
            "departments_needing_attention": departments_with_issues,
            "healthy_departments": len(reports) - len(departments_with_issues),
            "health_percentage": round((len(reports) - len(departments_with_issues)) / len(reports) * 100, 1) if reports else 0
        },
        "recommendations": company_recommendations,
        "department_profiles": department_profiles,
        "departments": [
            {
                "name": r.get("department"),
                "status": r.get("status"),
                "overall_score": r.get("overall_score", 0),
                "employees": r.get("summary", {}).get("employee_count", 0),
                "budget": r.get("summary", {}).get("total_budget", 0),
                "revenue": r.get("summary", {}).get("total_revenue", 0),
                "kpi": r.get("summary", {}).get("avg_kpi_score"),
                "quality": r.get("summary", {}).get("quality_score", 0),
                "all_metrics": r.get("summary", {})
            }
            for r in reports
        ]
    }


async def on_merge_department_reports(context: RunContextWrapper, params_str: str) -> Any:
    params = json.loads(params_str)
    reports = params.get("reports", [])
    result = merge_department_reports(reports)
    return result


tool_merge_department_reports = FunctionTool(
    name='local-csv_merge_reports',
    description='''Merge all department reports into comprehensive company summary with rankings, highlights, health overview, and recommendations.

**Input:** reports (list[dict]) - Array of department reports from csv_generate_report

**Returns:** dict:
{
  "company_summary": {...},
  "department_rankings": [...],
  "overall_health": float,
  "highlights": [...],
  "recommendations": [...]
}''',
    params_json_schema={
        "type": "object",
        "properties": {
            "reports": {"type": "array", "description": "Array of department reports from csv_generate_report"},
        },
        "required": ["reports"]
    },
    on_invoke_tool=on_merge_department_reports
)


# ============== Export all tools ==============

csv_tools = [
    tool_parse_spreadsheet_data,     # Step 1: Parse data
    tool_extract_department_metrics, # Step 2: Extract metrics
    tool_validate_data_quality,      # Step 3: Validate quality
    tool_generate_department_report, # Step 4: Generate report
    tool_merge_department_reports,   # Step 5: Merge reports
]
