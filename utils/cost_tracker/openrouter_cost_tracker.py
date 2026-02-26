"""
OpenRouter Cost Tracker

Tracks actual API costs by querying OpenRouter's credit balance before and after task execution.
This provides accurate cost data including cache discounts and actual billing.

Usage:
    from utils.cost_tracker import OpenRouterCostTracker
    
    # As context manager
    with OpenRouterCostTracker(api_key) as tracker:
        # Run task...
        pass
    print(f"Actual cost: ${tracker.actual_cost_usd:.6f}")
    
    # Or manual tracking
    tracker = OpenRouterCostTracker(api_key)
    tracker.start()
    # Run task...
    tracker.stop()
    print(f"Actual cost: ${tracker.actual_cost_usd:.6f}")
"""

import requests
import time
import os
from typing import Optional, Dict, Any
from dataclasses import dataclass, field


@dataclass
class CreditSnapshot:
    """Snapshot of OpenRouter credit balance at a point in time."""
    timestamp: float
    total_credits: float = 0.0
    total_usage: float = 0.0
    available_credits: float = 0.0
    rate_limit_requests: Optional[int] = None
    rate_limit_interval: Optional[str] = None
    is_free_tier: bool = False
    error: Optional[str] = None
    
    @property
    def is_valid(self) -> bool:
        return self.error is None


def get_openrouter_credits(api_key: str, timeout: float = 10.0) -> CreditSnapshot:
    """
    Query OpenRouter API for current credit balance.
    
    Args:
        api_key: OpenRouter API key
        timeout: Request timeout in seconds
        
    Returns:
        CreditSnapshot with current balance information
    """
    snapshot = CreditSnapshot(timestamp=time.time())
    
    if not api_key or api_key == "fake-key":
        snapshot.error = "No valid API key provided"
        return snapshot
    
    try:
        response = requests.get(
            "https://openrouter.ai/api/v1/credits",
            headers={"Authorization": f"Bearer {api_key}"},
            timeout=timeout
        )
        
        if response.status_code == 200:
            data = response.json().get("data", {})
            snapshot.total_credits = float(data.get("total_credits", 0))
            snapshot.total_usage = float(data.get("total_usage", 0))
            snapshot.available_credits = snapshot.total_credits - snapshot.total_usage
            snapshot.rate_limit_requests = data.get("rate_limit", {}).get("requests")
            snapshot.rate_limit_interval = data.get("rate_limit", {}).get("interval")
            snapshot.is_free_tier = data.get("is_free_tier", False)
        elif response.status_code == 401:
            snapshot.error = "Invalid API key (401 Unauthorized)"
        elif response.status_code == 429:
            snapshot.error = "Rate limited (429 Too Many Requests)"
        else:
            snapshot.error = f"API error: {response.status_code} - {response.text[:200]}"
            
    except requests.Timeout:
        snapshot.error = "Request timeout"
    except requests.RequestException as e:
        snapshot.error = f"Request failed: {str(e)}"
    except Exception as e:
        snapshot.error = f"Unexpected error: {str(e)}"
    
    return snapshot


class OpenRouterCostTracker:
    """
    Tracks actual OpenRouter API costs by comparing credit balances before and after operations.
    
    This provides accurate cost tracking that includes:
    - Actual token pricing (not estimates)
    - Cache discounts
    - Any pricing changes
    
    Attributes:
        actual_cost_usd: The actual USD cost (difference in credits used)
        start_snapshot: Credit snapshot at start
        end_snapshot: Credit snapshot at end
        is_valid: Whether both snapshots were successful
    """
    
    def __init__(self, api_key: Optional[str] = None, auto_detect_key: bool = True):
        """
        Initialize the cost tracker.
        
        Args:
            api_key: OpenRouter API key. If None and auto_detect_key is True,
                    will try to get from global_configs or environment.
            auto_detect_key: Whether to auto-detect API key from config/env
        """
        self.api_key = api_key
        
        if self.api_key is None and auto_detect_key:
            self.api_key = self._detect_api_key()
        
        self.start_snapshot: Optional[CreditSnapshot] = None
        self.end_snapshot: Optional[CreditSnapshot] = None
        self._started = False
    
    def _detect_api_key(self) -> Optional[str]:
        """Try to detect API key from various sources."""
        # Try global_configs first
        try:
            from configs.global_configs import global_configs
            if hasattr(global_configs, 'openrouter_key') and global_configs.openrouter_key and global_configs.openrouter_key != "xxx":
                return global_configs.openrouter_key
        except (ImportError, ModuleNotFoundError):
            pass
        
        # Try environment variables
        for env_var in ['OPENROUTER_API_KEY', 'TOOLATHLON_OPENAI_API_KEY']:
            key = os.environ.get(env_var)
            if key and key != "fake-key":
                return key
        
        # Try reading from config file directly (fallback)
        try:
            import re
            config_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 
                                       'configs', 'global_configs.py')
            if os.path.exists(config_path):
                with open(config_path, 'r') as f:
                    content = f.read()
                    # Look for openrouter_key = "sk-..."
                    match = re.search(r'openrouter_key\s*=\s*["\']([^"\']+)["\']', content)
                    if match:
                        key = match.group(1)
                        if key and key != "xxx":
                            return key
        except Exception:
            pass
        
        return None
    
    def start(self) -> 'OpenRouterCostTracker':
        """Start tracking costs by taking initial credit snapshot."""
        self.start_snapshot = get_openrouter_credits(self.api_key)
        self._started = True
        return self
    
    def stop(self) -> 'OpenRouterCostTracker':
        """Stop tracking costs by taking final credit snapshot."""
        if not self._started:
            raise RuntimeError("Cannot stop tracking before starting. Call start() first.")
        self.end_snapshot = get_openrouter_credits(self.api_key)
        return self
    
    @property
    def is_valid(self) -> bool:
        """Check if both snapshots are valid."""
        return (
            self.start_snapshot is not None and 
            self.end_snapshot is not None and
            self.start_snapshot.is_valid and 
            self.end_snapshot.is_valid
        )
    
    @property
    def actual_cost_usd(self) -> float:
        """
        Get the actual cost in USD.
        
        Returns the difference in total_usage between start and end snapshots.
        Returns 0.0 if tracking is invalid.
        """
        if not self.is_valid:
            return 0.0
        return self.end_snapshot.total_usage - self.start_snapshot.total_usage
    
    @property
    def credits_before(self) -> float:
        """Available credits before the operation."""
        if self.start_snapshot and self.start_snapshot.is_valid:
            return self.start_snapshot.available_credits
        return 0.0
    
    @property
    def credits_after(self) -> float:
        """Available credits after the operation."""
        if self.end_snapshot and self.end_snapshot.is_valid:
            return self.end_snapshot.available_credits
        return 0.0
    
    def get_tracking_result(self) -> Dict[str, Any]:
        """
        Get a dictionary with all tracking results.
        
        Returns:
            Dict containing actual_cost_usd, is_valid, error messages, etc.
        """
        result = {
            "actual_cost_usd": self.actual_cost_usd,
            "is_valid": self.is_valid,
            "credits_before": self.credits_before,
            "credits_after": self.credits_after,
            "tracking_method": "openrouter_credits_api",
        }
        
        # Add error information if any
        errors = []
        if self.start_snapshot and self.start_snapshot.error:
            errors.append(f"Start snapshot error: {self.start_snapshot.error}")
        if self.end_snapshot and self.end_snapshot.error:
            errors.append(f"End snapshot error: {self.end_snapshot.error}")
        
        if errors:
            result["errors"] = errors
            result["tracking_method"] = "failed"
        
        return result
    
    def __enter__(self) -> 'OpenRouterCostTracker':
        """Context manager entry - start tracking."""
        return self.start()
    
    def __exit__(self, exc_type, exc_val, exc_tb) -> bool:
        """Context manager exit - stop tracking."""
        self.stop()
        return False  # Don't suppress exceptions


# Convenience function for one-off queries
def get_current_balance(api_key: Optional[str] = None) -> Dict[str, Any]:
    """
    Get current OpenRouter credit balance.
    
    Args:
        api_key: API key, or None to auto-detect
        
    Returns:
        Dict with balance information
    """
    if api_key is None:
        tracker = OpenRouterCostTracker(auto_detect_key=True)
        api_key = tracker.api_key
    
    snapshot = get_openrouter_credits(api_key)
    
    return {
        "available_credits": snapshot.available_credits,
        "total_credits": snapshot.total_credits,
        "total_usage": snapshot.total_usage,
        "is_free_tier": snapshot.is_free_tier,
        "is_valid": snapshot.is_valid,
        "error": snapshot.error
    }


if __name__ == "__main__":
    # Test the cost tracker
    print("Testing OpenRouter Cost Tracker...")
    
    balance = get_current_balance()
    print(f"\nCurrent balance: ${balance['available_credits']:.4f}")
    print(f"Total credits: ${balance['total_credits']:.4f}")
    print(f"Total usage: ${balance['total_usage']:.4f}")
    
    if balance['error']:
        print(f"Error: {balance['error']}")
    else:
        print("✓ Cost tracker is working correctly")
