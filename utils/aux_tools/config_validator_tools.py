# config_validator_tools.py
# Configuration Validation Tools for batch-config-validator task
# Enhanced version with larger, more detailed outputs for Skill Mode efficiency

import json
import yaml
import re
from datetime import date, datetime
from typing import Any, List, Dict, Optional
from collections import Counter
from agents.tool import FunctionTool, RunContextWrapper


def _convert_dates_to_strings(obj):
    """Recursively convert date/datetime objects to ISO format strings.
    
    This handles YAML's automatic date parsing which can produce datetime.date
    objects that aren't JSON serializable.
    """
    if isinstance(obj, (date, datetime)):
        return obj.isoformat()
    elif isinstance(obj, dict):
        return {k: _convert_dates_to_strings(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [_convert_dates_to_strings(item) for item in obj]
    return obj


# Required fields by config type
REQUIRED_FIELDS = {
    "app_config": ["name", "version", "environment"],
    "database": ["host", "port", "name", "user"],
    "cache": ["type", "host", "port"],
    "logging": ["level", "handlers"],
    "security": ["auth_enabled", "rate_limit"],
    "api_gateway": ["routes", "port"],
    "messaging": ["broker", "port"],
    "storage": ["type", "path"],
    "monitoring": ["enabled", "interval"],
    "services": ["services"],
    "networking": ["interface", "port"],
    "deployment": ["environment", "replicas"]
}

# Security sensitive patterns with severity
SECURITY_PATTERNS = {
    "plaintext_password": {
        "pattern": r'password\s*[=:]\s*["\'][^"\']{3,}["\']',
        "severity": "high",
        "recommendation": "Use environment variables or secrets manager"
    },
    "api_key_exposed": {
        "pattern": r'api[_-]?key\s*[=:]\s*["\'][^"\']{10,}["\']',
        "severity": "critical",
        "recommendation": "Move API keys to secure vault"
    },
    "secret_exposed": {
        "pattern": r'secret\s*[=:]\s*["\'][^"\']{8,}["\']',
        "severity": "critical",
        "recommendation": "Use encrypted secrets storage"
    },
    "hardcoded_ip": {
        "pattern": r'\b(?:192\.168|10\.|172\.(?:1[6-9]|2\d|3[01]))\.\d{1,3}\.\d{1,3}\b',
        "severity": "low",
        "recommendation": "Consider using hostname or DNS"
    }
}

# CWE references for security patterns
CWE_REFERENCES = {
    "plaintext_password": {
        "cwe_id": "CWE-256",
        "name": "Plaintext Storage of Password",
        "description": "Storing passwords in plaintext can lead to credential theft"
    },
    "api_key_exposed": {
        "cwe_id": "CWE-798",
        "name": "Use of Hard-coded Credentials",
        "description": "Hard-coded API keys can be extracted and misused"
    },
    "secret_exposed": {
        "cwe_id": "CWE-798",
        "name": "Use of Hard-coded Credentials",
        "description": "Exposed secrets enable unauthorized access"
    },
    "hardcoded_ip": {
        "cwe_id": "CWE-1188",
        "name": "Insecure Default Initialization",
        "description": "Hardcoded IPs reduce portability and may expose internal network"
    }
}

# Remediation steps for security issues
REMEDIATION_STEPS = {
    "plaintext_password": [
        "1. Remove plaintext password from configuration",
        "2. Use environment variables: ${DB_PASSWORD}",
        "3. Or use a secrets manager (AWS Secrets Manager, HashiCorp Vault)",
        "4. Implement encryption at rest for sensitive configs"
    ],
    "api_key_exposed": [
        "1. Remove API key from configuration file",
        "2. Use environment variables: ${API_KEY}",
        "3. Store in secure vault with rotation policy",
        "4. Implement API key scoping and least privilege"
    ],
    "secret_exposed": [
        "1. Remove secret from configuration",
        "2. Use encrypted secrets storage",
        "3. Implement secret rotation",
        "4. Add secret scanning to CI/CD pipeline"
    ],
    "hardcoded_ip": [
        "1. Replace IP with hostname or DNS name",
        "2. Use service discovery for dynamic environments",
        "3. Consider using configuration management",
        "4. Document network dependencies"
    ]
}

def get_cwe_reference(pattern_name: str) -> Dict:
    """Get CWE reference for a security pattern."""
    return CWE_REFERENCES.get(pattern_name, {
        "cwe_id": "CWE-Unknown",
        "name": "Unknown Security Issue",
        "description": "Security issue requires further analysis"
    })

def get_remediation_steps(pattern_name: str) -> List[str]:
    """Get remediation steps for a security pattern."""
    return REMEDIATION_STEPS.get(pattern_name, [
        "1. Review the security finding",
        "2. Consult security best practices",
        "3. Implement appropriate mitigation"
    ])

def assess_owasp_compliance(findings: List[Dict], best_practices: List[Dict]) -> Dict:
    """Assess OWASP compliance based on findings."""
    owasp_checks = {
        "A01_broken_access_control": {
            "status": "pass" if not any(f["type"] == "api_key_exposed" for f in findings) else "fail",
            "description": "Access control mechanisms"
        },
        "A02_cryptographic_failures": {
            "status": "pass" if not any(f["type"] == "plaintext_password" for f in findings) else "fail",
            "description": "Proper encryption and hashing"
        },
        "A03_injection": {
            "status": "pass",  # Config files typically don't have injection issues
            "description": "Input validation and sanitization"
        },
        "A05_security_misconfiguration": {
            "status": "pass" if sum(1 for p in best_practices if p["status"] == "bad") == 0 else "fail",
            "description": "Secure default configurations"
        },
        "A07_authentication_failures": {
            "status": "pass" if any(p["practice"] == "Authentication enabled" and p["status"] == "good" for p in best_practices) else "warning",
            "description": "Proper authentication mechanisms"
        }
    }
    passed = sum(1 for c in owasp_checks.values() if c["status"] == "pass")
    return {
        "checks": owasp_checks,
        "passed": passed,
        "total": len(owasp_checks),
        "compliance_percentage": round(passed / len(owasp_checks) * 100, 1)
    }

def check_encryption_settings(parsed_content: Dict) -> Dict:
    """Check encryption-related settings in config."""
    encryption_indicators = ["ssl", "tls", "https", "encrypt", "cipher"]
    found_settings = {}
    
    def search_config(obj, path=""):
        if isinstance(obj, dict):
            for k, v in obj.items():
                full_path = f"{path}.{k}" if path else k
                if any(ind in k.lower() for ind in encryption_indicators):
                    found_settings[full_path] = {
                        "value": v,
                        "enabled": v is True or str(v).lower() in ["true", "enabled", "yes", "1"]
                    }
                if isinstance(v, dict):
                    search_config(v, full_path)
    
    if parsed_content:
        search_config(parsed_content)
    
    enabled_count = sum(1 for s in found_settings.values() if s["enabled"])
    return {
        "encryption_settings_found": len(found_settings),
        "encryption_enabled_count": enabled_count,
        "settings": found_settings,
        "recommendation": "Enable all encryption settings" if enabled_count < len(found_settings) else "Encryption properly configured"
    }

def check_auth_settings(parsed_content: Dict) -> Dict:
    """Check authentication settings in config."""
    auth_indicators = ["auth", "authentication", "login", "session", "token", "jwt", "oauth"]
    found_settings = {}
    
    def search_config(obj, path=""):
        if isinstance(obj, dict):
            for k, v in obj.items():
                full_path = f"{path}.{k}" if path else k
                if any(ind in k.lower() for ind in auth_indicators):
                    found_settings[full_path] = {
                        "value": v if not isinstance(v, dict) else "complex_config",
                        "type": type(v).__name__
                    }
                if isinstance(v, dict):
                    search_config(v, full_path)
    
    if parsed_content:
        search_config(parsed_content)
    
    return {
        "auth_settings_found": len(found_settings),
        "settings": found_settings,
        "has_authentication": len(found_settings) > 0
    }

def check_network_settings(parsed_content: Dict) -> Dict:
    """Check network security settings in config."""
    network_indicators = ["port", "host", "bind", "listen", "cors", "proxy", "firewall"]
    exposed_ports = []
    network_configs = []
    
    def search_config(obj, path=""):
        if isinstance(obj, dict):
            for k, v in obj.items():
                full_path = f"{path}.{k}" if path else k
                if "port" in k.lower():
                    try:
                        port_val = int(v)
                        exposed_ports.append({"path": full_path, "port": port_val})
                    except (ValueError, TypeError):
                        pass
                if any(ind in k.lower() for ind in network_indicators):
                    network_configs.append({
                        "path": full_path,
                        "key": k,
                        "value": str(v)[:50]
                    })
                if isinstance(v, dict):
                    search_config(v, full_path)
    
    if parsed_content:
        search_config(parsed_content)
    
    return {
        "exposed_ports": exposed_ports,
        "port_count": len(exposed_ports),
        "network_configs": network_configs,
        "network_config_count": len(network_configs),
        "security_recommendation": "Review exposed ports and network bindings"
    }

# Value validation rules
VALUE_RULES = {
    "port": {"min": 1, "max": 65535, "description": "TCP/UDP port number"},
    "timeout": {"min": 100, "max": 300000, "description": "Timeout in milliseconds"},
    "ttl": {"min": 1, "max": 86400, "description": "Time to live in seconds"},
    "pool_size": {"min": 1, "max": 1000, "description": "Connection pool size"},
    "replicas": {"min": 1, "max": 100, "description": "Number of replicas"},
    "workers": {"min": 1, "max": 256, "description": "Number of workers"},
    "threads": {"min": 1, "max": 512, "description": "Number of threads"},
    "retry": {"min": 0, "max": 10, "description": "Retry count"},
    "interval": {"min": 100, "max": 86400000, "description": "Interval in milliseconds"}
}


# ============== Step 1: Parse Config File (Enhanced) ==============

def parse_config_file(content: str, filename: str) -> Dict:
    """Parse a configuration file with comprehensive analysis."""
    file_ext = filename.split('.')[-1].lower()
    lines = content.strip().split('\n')
    
    result = {
        "filename": filename,
        "format": file_ext,
        "valid_syntax": False,
        "parsed_content": None,
        "error": None,
        "statistics": {
            "total_lines": len(lines),
            "non_empty_lines": sum(1 for line in lines if line.strip()),
            "comment_lines": 0,
            "size_bytes": len(content)
        }
    }
    
    # Count comments by format
    if file_ext in ['yaml', 'yml']:
        result["statistics"]["comment_lines"] = sum(1 for line in lines if line.strip().startswith('#'))
    elif file_ext == 'json':
        result["statistics"]["comment_lines"] = 0  # JSON doesn't support comments
    elif file_ext == 'toml':
        result["statistics"]["comment_lines"] = sum(1 for line in lines if line.strip().startswith('#'))
    elif file_ext == 'ini':
        result["statistics"]["comment_lines"] = sum(1 for line in lines if line.strip().startswith(('#', ';')))
    
    try:
        if file_ext == 'json':
            parsed = json.loads(content)
            result["valid_syntax"] = True
            result["parsed_content"] = parsed
        elif file_ext in ['yaml', 'yml']:
            parsed = yaml.safe_load(content)
            # Convert any date objects to strings to ensure JSON serialization works
            parsed = _convert_dates_to_strings(parsed)
            result["valid_syntax"] = True
            result["parsed_content"] = parsed
        elif file_ext == 'toml':
            parsed = {}
            current_section = None
            for line in lines:
                line = line.strip()
                if not line or line.startswith('#'):
                    continue
                if line.startswith('[') and line.endswith(']'):
                    current_section = line[1:-1]
                    parsed[current_section] = {}
                elif '=' in line:
                    key, value = line.split('=', 1)
                    key = key.strip()
                    value = value.strip().strip('"').strip("'")
                    # Try to parse as number or boolean
                    if value.lower() == 'true':
                        value = True
                    elif value.lower() == 'false':
                        value = False
                    else:
                        try:
                            value = int(value)
                        except ValueError:
                            try:
                                value = float(value)
                            except ValueError:
                                pass
                    if current_section:
                        parsed[current_section][key] = value
                    else:
                        parsed[key] = value
            result["valid_syntax"] = True
            result["parsed_content"] = parsed
        elif file_ext == 'ini':
            parsed = {}
            current_section = "default"
            for line in lines:
                line = line.strip()
                if not line or line.startswith('#') or line.startswith(';'):
                    continue
                if line.startswith('[') and line.endswith(']'):
                    current_section = line[1:-1]
                    parsed[current_section] = {}
                elif '=' in line:
                    key, value = line.split('=', 1)
                    parsed.setdefault(current_section, {})[key.strip()] = value.strip()
            result["valid_syntax"] = True
            result["parsed_content"] = parsed
        else:
            result["error"] = f"Unsupported format: {file_ext}"
    except Exception as e:
        result["error"] = str(e)
    
    # Add structure analysis if parsed successfully
    if result["valid_syntax"] and result["parsed_content"]:
        content_analysis = analyze_structure(result["parsed_content"])
        result["structure"] = content_analysis
    
    return result


def analyze_structure(obj, prefix="") -> Dict:
    """Analyze the structure of parsed configuration."""
    keys = []
    sections = []
    values = []
    
    if isinstance(obj, dict):
        for k, v in obj.items():
            full_key = f"{prefix}.{k}" if prefix else k
            if isinstance(v, dict):
                sections.append(k)
                sub_analysis = analyze_structure(v, full_key)
                keys.extend(sub_analysis["all_keys"])
            else:
                keys.append(full_key)
                values.append({"key": full_key, "value": str(v)[:50], "type": type(v).__name__})
    
    return {
        "all_keys": keys,
        "top_level_sections": sections,
        "total_keys": len(keys),
        "total_sections": len(sections),
        "sample_values": values[:10]
    }


async def on_parse_config_file(context: RunContextWrapper, params_str: str) -> Any:
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
        filename = "unknown.yaml"
    
    result = parse_config_file(content, filename)
    return result


tool_parse_config_file = FunctionTool(
    name='local-config_parse',
    description='''Parse a configuration file (YAML, JSON, TOML, INI) with detailed structure analysis. Returns parsed content, statistics, and structure breakdown.

**Input (Option 1 - Direct filepath):** filepath (str) - Path to config file (e.g., "configs/app_config.yaml")
**Input (Option 2 - Content):** content (str), filename (str) - Config content and filename

**Returns:** dict:
{
  "filename": str,
  "format": str,
  "parsed_content": dict,
  "statistics": {"key_count": int, "depth": int, ...},
  "structure": {...}
}''',
    params_json_schema={
        "type": "object",
        "properties": {
            "filepath": {"type": "string", "description": "Path to config file (e.g., 'configs/app_config.yaml')"},
            "content": {"type": "string", "description": "The configuration file content (alternative to filepath)"},
            "filename": {"type": "string", "description": "The filename (optional if using filepath)"},
        },
        "required": []
    },
    on_invoke_tool=on_parse_config_file
)


# ============== Step 2: Validate Schema (Enhanced) ==============

def validate_schema(parsed_content: Dict, filename: str) -> Dict:
    """Validate configuration schema with detailed field analysis."""
    # Determine config type from filename
    config_type = None
    for key in REQUIRED_FIELDS.keys():
        if key in filename.lower():
            config_type = key
            break
    
    if config_type is None:
        base_name = filename.replace('.yaml', '').replace('.json', '').replace('.toml', '').replace('.ini', '')
        for key in REQUIRED_FIELDS.keys():
            if key in base_name.lower():
                config_type = key
                break
    
    if config_type is None:
        config_type = "generic"
    
    required = REQUIRED_FIELDS.get(config_type, [])
    
    # Get all keys recursively
    all_keys = []
    def extract_keys(obj, prefix=""):
        if isinstance(obj, dict):
            for k, v in obj.items():
                full_key = f"{prefix}.{k}" if prefix else k
                all_keys.append({"key": full_key, "depth": prefix.count('.') + 1 if prefix else 0})
                if isinstance(v, dict):
                    extract_keys(v, full_key)
    
    if parsed_content:
        extract_keys(parsed_content)
    
    # Flatten for simple checking
    flat_keys = set()
    if isinstance(parsed_content, dict):
        flat_keys = set(parsed_content.keys())
        for k, v in parsed_content.items():
            if isinstance(v, dict):
                flat_keys.update(v.keys())
    
    present = []
    missing = []
    field_details = []
    
    for field in required:
        found = field in flat_keys or any(field in k["key"] for k in all_keys)
        if found:
            present.append(field)
            field_details.append({"field": field, "status": "present", "required": True})
        else:
            missing.append(field)
            field_details.append({"field": field, "status": "missing", "required": True})
    
    # Analyze key patterns
    key_depth_dist = Counter(k["depth"] for k in all_keys)
    
    return {
        "config_type": config_type,
        "schema_valid": len(missing) == 0,
        "required_fields_present": present,
        "required_fields_missing": missing,
        "field_details": field_details,
        "total_fields": len(all_keys),
        "all_keys": all_keys,
        "key_depth_distribution": dict(key_depth_dist),
        "max_depth": max(k["depth"] for k in all_keys) if all_keys else 0,
        "compliance_score": len(present) / len(required) * 100 if required else 100
    }


async def on_validate_schema(context: RunContextWrapper, params_str: str) -> Any:
    params = json.loads(params_str)
    parsed_content = params.get("parsed_content", {})
    filename = params.get("filename", "unknown")
    result = validate_schema(parsed_content, filename)
    return result


tool_validate_schema = FunctionTool(
    name='local-config_validate_schema',
    description='''Validate configuration schema with detailed field analysis, key depth distribution, and compliance scoring.

**Input:** parsed_content (dict), filename (str)

**Returns:** dict:
{
  "schema_valid": bool,
  "compliance_score": float,
  "field_analysis": {...},
  "issues": [...],
  "depth_distribution": {...}
}''',
    params_json_schema={
        "type": "object",
        "properties": {
            "parsed_content": {"type": "object", "description": "The parsed config from config_parse"},
            "filename": {"type": "string", "description": "The config filename"},
        },
        "required": ["parsed_content", "filename"]
    },
    on_invoke_tool=on_validate_schema
)


# ============== Step 3: Validate Values (Enhanced) ==============

def validate_values(parsed_content: Dict) -> Dict:
    """Validate configuration values with detailed analysis."""
    issues = []
    warnings = []
    validated_values = []
    
    def check_value(key, value, path=""):
        full_path = f"{path}.{key}" if path else key
        result = {"key": full_path, "value": value, "checks": []}
        
        for rule_name, rule in VALUE_RULES.items():
            if rule_name in key.lower():
                try:
                    numeric_val = int(value) if isinstance(value, str) else value
                    if isinstance(numeric_val, (int, float)):
                        if numeric_val < rule["min"]:
                            issues.append({
                                "path": full_path,
                                "issue": f"{rule['description']} below minimum",
                                "value": numeric_val,
                                "min": rule["min"],
                                "severity": "error"
                            })
                            result["checks"].append({"rule": rule_name, "passed": False})
                        elif numeric_val > rule["max"]:
                            warnings.append({
                                "path": full_path,
                                "warning": f"{rule['description']} above maximum",
                                "value": numeric_val,
                                "max": rule["max"],
                                "severity": "warning"
                            })
                            result["checks"].append({"rule": rule_name, "passed": False})
                        else:
                            result["checks"].append({"rule": rule_name, "passed": True})
                except (ValueError, TypeError):
                    pass
        
        if result["checks"]:
            validated_values.append(result)
    
    def traverse(obj, path=""):
        if isinstance(obj, dict):
            for k, v in obj.items():
                new_path = f"{path}.{k}" if path else k
                if isinstance(v, dict):
                    traverse(v, new_path)
                else:
                    check_value(k, v, path)
    
    if parsed_content:
        traverse(parsed_content)
    
    # Calculate validation statistics
    total_checks = sum(len(v["checks"]) for v in validated_values)
    passed_checks = sum(sum(1 for c in v["checks"] if c["passed"]) for v in validated_values)
    
    return {
        "values_valid": len(issues) == 0,
        "value_issues": issues,
        "value_warnings": warnings,
        "validated_values": validated_values,
        "validation_stats": {
            "total_values_checked": len(validated_values),
            "total_rules_applied": total_checks,
            "rules_passed": passed_checks,
            "rules_failed": total_checks - passed_checks,
            "pass_rate": round(passed_checks / total_checks * 100, 2) if total_checks > 0 else 100
        }
    }


async def on_validate_values(context: RunContextWrapper, params_str: str) -> Any:
    params = json.loads(params_str)
    parsed_content = params.get("parsed_content", {})
    result = validate_values(parsed_content)
    return result


tool_validate_values = FunctionTool(
    name='local-config_validate_values',
    description='''Validate configuration values against rules (ports, timeouts, pool sizes, etc.) with detailed validation statistics.

**Input:** parsed_content (dict)

**Returns:** dict:
{
  "values_valid": bool,
  "validation_score": float,
  "validated_fields": [...],
  "issues": [...],
  "statistics": {...}
}''',
    params_json_schema={
        "type": "object",
        "properties": {
            "parsed_content": {"type": "object", "description": "The parsed config from config_parse"},
        },
        "required": ["parsed_content"]
    },
    on_invoke_tool=on_validate_values
)


# ============== Step 4: Security Check (Enhanced) ==============

def check_security(content: str, parsed_content: Dict) -> Dict:
    """Comprehensive security analysis of configuration with detailed pattern matching."""
    findings = []
    recommendations = []
    security_score = 100
    pattern_matches_detail = []
    line_analysis = []
    
    # Analyze each line for security issues
    lines = content.split('\n')
    for line_num, line in enumerate(lines, 1):
        line_issues = []
        for pattern_name, pattern_info in SECURITY_PATTERNS.items():
            if re.search(pattern_info["pattern"], line, re.IGNORECASE):
                line_issues.append({
                    "pattern": pattern_name,
                    "severity": pattern_info["severity"],
                    "recommendation": pattern_info["recommendation"]
                })
        if line_issues:
            line_analysis.append({
                "line_number": line_num,
                "content_preview": line[:80] + "..." if len(line) > 80 else line,
                "issues": line_issues
            })
    
    # Check for sensitive patterns in raw content
    for pattern_name, pattern_info in SECURITY_PATTERNS.items():
        matches = re.findall(pattern_info["pattern"], content, re.IGNORECASE)
        if matches:
            finding = {
                "type": pattern_name,
                "severity": pattern_info["severity"],
                "instances": len(matches),
                "recommendation": pattern_info["recommendation"],
                "matched_patterns": matches[:5],  # Show first 5 matches
                "cwe_reference": get_cwe_reference(pattern_name),
                "remediation_steps": get_remediation_steps(pattern_name)
            }
            findings.append(finding)
            
            pattern_matches_detail.append({
                "pattern_name": pattern_name,
                "regex": pattern_info["pattern"],
                "match_count": len(matches),
                "severity_weight": {"critical": 25, "high": 15, "medium": 10, "low": 5}.get(pattern_info["severity"], 5)
            })
            
            if pattern_info["severity"] == "critical":
                security_score -= 25
            elif pattern_info["severity"] == "high":
                security_score -= 15
            elif pattern_info["severity"] == "medium":
                security_score -= 10
            else:
                security_score -= 5
            
            recommendations.append(pattern_info["recommendation"])
    
    # Check for security best practices in parsed content
    best_practices = []
    
    def check_settings(obj, path=""):
        nonlocal security_score
        if not isinstance(obj, dict):
            return
        
        # Check HTTPS/SSL
        for key in ['https', 'ssl', 'tls']:
            if key in obj:
                if obj[key] is True:
                    best_practices.append({"practice": f"{key.upper()} enabled", "status": "good"})
                else:
                    best_practices.append({"practice": f"{key.upper()} disabled", "status": "bad"})
                    security_score -= 10
        
        # Check authentication
        for key in ['auth_enabled', 'authentication', 'auth']:
            if key in obj:
                if obj[key] is True:
                    best_practices.append({"practice": "Authentication enabled", "status": "good"})
                else:
                    best_practices.append({"practice": "Authentication disabled", "status": "bad"})
                    security_score -= 15
        
        # Check debug mode
        if obj.get('environment', '').lower() == 'production':
            if obj.get('debug') is True:
                findings.append({
                    "type": "debug_in_production",
                    "severity": "high",
                    "recommendation": "Disable debug mode in production"
                })
                security_score -= 20
                best_practices.append({"practice": "Debug mode in production", "status": "bad"})
            else:
                best_practices.append({"practice": "Debug mode disabled in production", "status": "good"})
        
        # Check rate limiting
        if 'rate_limit' in obj or 'ratelimit' in str(obj).lower():
            if obj.get('rate_limit') or obj.get('rate_limit_enabled'):
                best_practices.append({"practice": "Rate limiting enabled", "status": "good"})
            else:
                best_practices.append({"practice": "Rate limiting not configured", "status": "warning"})
                security_score -= 5
        
        for k, v in obj.items():
            if isinstance(v, dict):
                check_settings(v, f"{path}.{k}" if path else k)
    
    if parsed_content:
        check_settings(parsed_content)
    
    # Determine overall status
    if security_score >= 80:
        status = "passed"
        risk_level = "low"
    elif security_score >= 60:
        status = "warning"
        risk_level = "medium"
    elif security_score >= 40:
        status = "warning"
        risk_level = "high"
    else:
        status = "failed"
        risk_level = "critical"
    
    # Generate comprehensive security audit trail
    audit_trail = {
        "patterns_checked": list(SECURITY_PATTERNS.keys()),
        "total_patterns": len(SECURITY_PATTERNS),
        "patterns_triggered": len([f for f in findings]),
        "content_length": len(content),
        "lines_analyzed": len(lines),
        "lines_with_issues": len(line_analysis)
    }
    
    # Calculate risk distribution
    risk_distribution = {
        "critical": sum(1 for f in findings if f["severity"] == "critical"),
        "high": sum(1 for f in findings if f["severity"] == "high"),
        "medium": sum(1 for f in findings if f["severity"] == "medium"),
        "low": sum(1 for f in findings if f["severity"] == "low")
    }
    
    # Generate detailed compliance report
    compliance_report = {
        "owasp_alignment": assess_owasp_compliance(findings, best_practices),
        "encryption_status": check_encryption_settings(parsed_content),
        "authentication_status": check_auth_settings(parsed_content),
        "network_security": check_network_settings(parsed_content)
    }
    
    return {
        "security_check": status,
        "security_score": max(0, security_score),
        "risk_level": risk_level,
        "findings": findings,
        "best_practices_audit": best_practices,
        "recommendations": list(set(recommendations)),
        "summary": {
            "critical_issues": risk_distribution["critical"],
            "high_issues": risk_distribution["high"],
            "medium_issues": risk_distribution["medium"],
            "low_issues": risk_distribution["low"],
            "total_issues": sum(risk_distribution.values()),
            "good_practices": sum(1 for p in best_practices if p["status"] == "good"),
            "bad_practices": sum(1 for p in best_practices if p["status"] == "bad"),
            "warning_practices": sum(1 for p in best_practices if p["status"] == "warning")
        },
        "detailed_analysis": {
            "line_by_line_issues": line_analysis,
            "pattern_match_details": pattern_matches_detail,
            "risk_distribution": risk_distribution
        },
        "audit_trail": audit_trail,
        "compliance_report": compliance_report,
        "security_metrics": {
            "vulnerability_density": round(len(findings) / max(1, len(lines)) * 100, 3),
            "secure_config_percentage": round(max(0, security_score), 1),
            "practices_compliance_rate": round(
                sum(1 for p in best_practices if p["status"] == "good") / 
                max(1, len(best_practices)) * 100, 1
            ) if best_practices else 100
        }
    }


async def on_check_security(context: RunContextWrapper, params_str: str) -> Any:
    import os
    params = json.loads(params_str)
    filepath = params.get("filepath", "")
    content = params.get("content", "")
    parsed_content = params.get("parsed_content", {})
    
    # If filepath provided, read the file internally
    if filepath and not content:
        try:
            workspace = getattr(context, 'workspace_path', '') or ''
            full_path = os.path.join(workspace, filepath) if workspace else filepath
            
            if os.path.exists(full_path):
                with open(full_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                # Also parse the content if parsed_content not provided
                if not parsed_content:
                    filename = os.path.basename(filepath)
                    parse_result = parse_config_file(content, filename)
                    if parse_result.get("valid_syntax"):
                        parsed_content = parse_result.get("parsed_content", {})
            else:
                return {"error": f"File not found: {filepath}"}
        except Exception as e:
            return {"error": f"Failed to read file: {str(e)}"}
    
    result = check_security(content, parsed_content)
    return result


tool_check_security = FunctionTool(
    name='local-config_check_security',
    description='''Comprehensive security audit with pattern detection, best practices check, risk assessment, and actionable recommendations.

**Input (Option 1 - Recommended):** filepath (str) - Path to config file, reads and parses internally
**Input (Option 2):** content (str), parsed_content (dict) - Raw content and parsed config

**Returns:** dict:
{
  "security_score": float,
  "risk_level": str,
  "findings": [...],
  "best_practices": {...},
  "recommendations": [...]
}''',
    params_json_schema={
        "type": "object",
        "properties": {
            "filepath": {"type": "string", "description": "Path to config file (e.g., 'configs/app.yaml') - RECOMMENDED"},
            "content": {"type": "string", "description": "Raw config file content (alternative to filepath)"},
            "parsed_content": {"type": "object", "description": "The parsed config from config_parse (optional if using filepath)"},
        },
        "required": []
    },
    on_invoke_tool=on_check_security
)


# ============== Step 5: Generate Validation Report (Enhanced) ==============

def generate_validation_report(
    parse_result: Dict, 
    schema_result: Dict, 
    values_result: Dict, 
    security_result: Dict
) -> Dict:
    """Generate comprehensive validation report with all details."""
    filename = parse_result.get("filename", "unknown")
    
    # Calculate overall score
    scores = {
        "syntax": 100 if parse_result.get("valid_syntax") else 0,
        "schema": schema_result.get("compliance_score", 0),
        "values": values_result.get("validation_stats", {}).get("pass_rate", 100),
        "security": security_result.get("security_score", 0)
    }
    overall_score = sum(scores.values()) / len(scores)
    
    # Determine overall status
    if overall_score >= 80:
        overall_status = "passed"
    elif overall_score >= 60:
        overall_status = "warning"
    else:
        overall_status = "failed"
    
    # Collect all issues
    all_issues = []
    if not parse_result.get("valid_syntax"):
        all_issues.append({
            "category": "syntax",
            "severity": "critical",
            "message": f"Syntax error: {parse_result.get('error', 'unknown')}"
        })
    
    for field in schema_result.get("required_fields_missing", []):
        all_issues.append({
            "category": "schema",
            "severity": "error",
            "message": f"Missing required field: {field}"
        })
    
    for issue in values_result.get("value_issues", []):
        all_issues.append({
            "category": "values",
            "severity": issue.get("severity", "error"),
            "message": issue.get("issue", "Value validation failed")
        })
    
    for finding in security_result.get("findings", []):
        all_issues.append({
            "category": "security",
            "severity": finding.get("severity", "warning"),
            "message": finding.get("type", "Security issue")
        })
    
    return {
        "filename": filename,
        "format": parse_result.get("format", "unknown"),
        "overall_status": overall_status,
        "overall_score": round(overall_score, 2),
        "scores": scores,
        "validation_summary": {
            "syntax_valid": parse_result.get("valid_syntax", False),
            "schema_valid": schema_result.get("schema_valid", False),
            "values_valid": values_result.get("values_valid", False),
            "security_check": security_result.get("security_check", "unknown"),
            "risk_level": security_result.get("risk_level", "unknown")
        },
        "statistics": parse_result.get("statistics", {}),
        "structure": parse_result.get("structure", {}),
        "all_issues": all_issues,
        "issue_counts": {
            "critical": sum(1 for i in all_issues if i["severity"] == "critical"),
            "error": sum(1 for i in all_issues if i["severity"] == "error"),
            "warning": sum(1 for i in all_issues if i["severity"] == "warning"),
            "low": sum(1 for i in all_issues if i["severity"] == "low")
        },
        "recommendations": security_result.get("recommendations", []),
        "best_practices": security_result.get("best_practices_audit", [])
    }


async def on_generate_validation_report(context: RunContextWrapper, params_str: str) -> Any:
    params = json.loads(params_str)
    parse_result = params.get("parse_result", {})
    schema_result = params.get("schema_result", {})
    values_result = params.get("values_result", {})
    security_result = params.get("security_result", {})
    result = generate_validation_report(parse_result, schema_result, values_result, security_result)
    return result


tool_generate_validation_report = FunctionTool(
    name='local-config_generate_report',
    description='''Generate comprehensive validation report with overall scoring, issue categorization, and recommendations.

**Input:** parse_result (dict), schema_result (dict), values_result (dict), security_result (dict) - Results from previous tools

**Returns:** dict:
{
  "filename": str,
  "overall_score": float,
  "status": str,
  "summary": {...},
  "all_issues": [...],
  "recommendations": [...]
}''',
    params_json_schema={
        "type": "object",
        "properties": {
            "parse_result": {"type": "object", "description": "Result from config_parse"},
            "schema_result": {"type": "object", "description": "Result from config_validate_schema"},
            "values_result": {"type": "object", "description": "Result from config_validate_values"},
            "security_result": {"type": "object", "description": "Result from config_check_security"},
        },
        "required": ["parse_result", "schema_result", "values_result", "security_result"]
    },
    on_invoke_tool=on_generate_validation_report
)


# ============== Export all tools ==============

config_validator_tools = [
    tool_parse_config_file,          # Step 1: Parse config
    tool_validate_schema,            # Step 2: Check required fields
    tool_validate_values,            # Step 3: Validate value ranges
    tool_check_security,             # Step 4: Security check
    tool_generate_validation_report, # Step 5: Generate report
]
