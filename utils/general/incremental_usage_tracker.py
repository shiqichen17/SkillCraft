"""
Incremental Usage Tracker - Robust token tracking that persists even on abnormal termination.

This module provides a file-based incremental tracking system that:
1. Saves usage data after each update
2. Can recover data if the main tracking mechanism fails
3. Provides atomic writes to prevent corruption
"""

import json
import os
import fcntl
import errno
import time
from pathlib import Path
from typing import Dict, Any, Optional, Tuple
from datetime import datetime
from dataclasses import dataclass, field, asdict


@dataclass
class UsageSnapshot:
    """A snapshot of usage data at a point in time."""
    input_tokens: int = 0
    output_tokens: int = 0
    total_tokens: int = 0
    requests: int = 0
    last_input_tokens: int = 0
    tool_calls: int = 0
    turns: int = 0
    openrouter_cost: float = 0.0
    cost_source: str = "unknown"
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'UsageSnapshot':
        # Filter out unknown fields
        known_fields = {f.name for f in cls.__dataclass_fields__.values()}
        filtered_data = {k: v for k, v in data.items() if k in known_fields}
        return cls(**filtered_data)


class IncrementalUsageTracker:
    """
    File-based incremental usage tracker that persists token/cost data after each update.
    
    Features:
    - Atomic writes using file locking
    - Automatic recovery from last saved state
    - Multiple backup sources (incremental file, session history, model tracking)
    """
    
    def __init__(self, tracking_dir: Path, session_id: str):
        """
        Initialize the tracker.
        
        Args:
            tracking_dir: Directory to store tracking files (usually conversation_history dir)
            session_id: Unique session identifier
        """
        self.tracking_dir = Path(tracking_dir)
        self.session_id = session_id
        self.tracking_file = self.tracking_dir / f"{session_id}_usage_tracking.json"
        
        # In-memory state
        self._current: UsageSnapshot = UsageSnapshot()
        self._history: list[UsageSnapshot] = []
        self._initialized = False
        
        # Ensure directory exists
        self.tracking_dir.mkdir(parents=True, exist_ok=True)
        
        # Load existing data if available
        self._load_existing()
    
    def _load_existing(self) -> None:
        """Load existing tracking data from file."""
        if self.tracking_file.exists():
            try:
                with open(self.tracking_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self._current = UsageSnapshot.from_dict(data.get('current', {}))
                    self._history = [
                        UsageSnapshot.from_dict(h) for h in data.get('history', [])
                    ]
                    self._initialized = True
            except (json.JSONDecodeError, Exception) as e:
                print(f"[USAGE TRACKER] Warning: Failed to load existing tracking data: {e}")
    
    def _save(self) -> None:
        """Save current state to file atomically."""
        data = {
            'session_id': self.session_id,
            'current': self._current.to_dict(),
            'history': [h.to_dict() for h in self._history[-50:]],  # Keep last 50 snapshots
            'last_updated': datetime.now().isoformat()
        }
        
        # Atomic write with file locking
        temp_file = self.tracking_file.with_suffix('.tmp')
        try:
            with open(temp_file, 'w', encoding='utf-8') as f:
                # Try to acquire lock (non-blocking)
                try:
                    fcntl.flock(f.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
                except IOError:
                    # If can't get lock immediately, wait briefly and retry
                    time.sleep(0.01)
                    fcntl.flock(f.fileno(), fcntl.LOCK_EX)
                
                try:
                    json.dump(data, f, ensure_ascii=False, indent=2)
                    f.flush()
                    os.fsync(f.fileno())
                finally:
                    fcntl.flock(f.fileno(), fcntl.LOCK_UN)
            
            # Atomic rename
            os.replace(temp_file, self.tracking_file)
        except Exception as e:
            print(f"[USAGE TRACKER] Warning: Failed to save tracking data: {e}")
            # Clean up temp file if it exists
            if temp_file.exists():
                try:
                    os.remove(temp_file)
                except:
                    pass
    
    def update(self,
               input_tokens: int = None,
               output_tokens: int = None,
               requests: int = None,
               last_input_tokens: int = None,
               tool_calls: int = None,
               turns: int = None,
               openrouter_cost: float = None,
               cost_source: str = None) -> None:
        """
        Update usage stats and persist immediately.
        
        Only updates fields that are provided (not None) and are greater than current values
        (for monotonically increasing metrics like tokens).
        """
        updated = False
        
        if input_tokens is not None and input_tokens > self._current.input_tokens:
            self._current.input_tokens = input_tokens
            updated = True
        
        if output_tokens is not None and output_tokens > self._current.output_tokens:
            self._current.output_tokens = output_tokens
            updated = True
        
        if requests is not None and requests > self._current.requests:
            self._current.requests = requests
            updated = True
        
        if last_input_tokens is not None:
            self._current.last_input_tokens = last_input_tokens
            updated = True
        
        if tool_calls is not None and tool_calls > self._current.tool_calls:
            self._current.tool_calls = tool_calls
            updated = True
        
        if turns is not None and turns > self._current.turns:
            self._current.turns = turns
            updated = True
        
        if openrouter_cost is not None and openrouter_cost > self._current.openrouter_cost:
            self._current.openrouter_cost = openrouter_cost
            updated = True
        
        if cost_source is not None:
            self._current.cost_source = cost_source
            updated = True
        
        # Update total_tokens
        self._current.total_tokens = self._current.input_tokens + self._current.output_tokens
        self._current.timestamp = datetime.now().isoformat()
        
        if updated:
            # Save snapshot to history
            self._history.append(UsageSnapshot(
                input_tokens=self._current.input_tokens,
                output_tokens=self._current.output_tokens,
                total_tokens=self._current.total_tokens,
                requests=self._current.requests,
                last_input_tokens=self._current.last_input_tokens,
                tool_calls=self._current.tool_calls,
                turns=self._current.turns,
                openrouter_cost=self._current.openrouter_cost,
                cost_source=self._current.cost_source
            ))
            
            # Persist immediately
            self._save()
    
    def get_current(self) -> UsageSnapshot:
        """Get the current usage snapshot."""
        return self._current
    
    def get_summary(self) -> Dict[str, Any]:
        """Get a summary dict suitable for integration with existing code."""
        return {
            'input_tokens': self._current.input_tokens,
            'output_tokens': self._current.output_tokens,
            'total_tokens': self._current.total_tokens,
            'requests': self._current.requests,
            'last_input_tokens': self._current.last_input_tokens,
            'tool_calls': self._current.tool_calls,
            'turns': self._current.turns,
            'openrouter_cost': self._current.openrouter_cost,
            'cost_source': self._current.cost_source,
            'tracking_source': 'incremental_tracker'
        }
    
    def has_data(self) -> bool:
        """Check if we have any meaningful tracked data."""
        return (self._current.input_tokens > 0 or 
                self._current.output_tokens > 0 or 
                self._current.requests > 0 or
                self._current.tool_calls > 0)


def reconstruct_usage_from_session_history(
    session_history_file: Path,
    model_name: str = None
) -> Optional[Dict[str, Any]]:
    """
    Reconstruct basic usage stats from session history file.
    
    This is a fallback when the main tracking and incremental tracking both failed.
    Note: This cannot provide accurate token counts, only structural metrics.
    
    Args:
        session_history_file: Path to the session_history.jsonl file
        model_name: Optional model name for cost estimation
        
    Returns:
        Dict with reconstructed stats or None if failed
    """
    if not session_history_file.exists():
        return None
    
    try:
        entries = []
        with open(session_history_file, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line:
                    try:
                        entries.append(json.loads(line))
                    except json.JSONDecodeError:
                        continue
        
        if not entries:
            return None
        
        # Count basic metrics
        turns = set()
        tool_calls = 0
        llm_requests = 0
        
        for entry in entries:
            turn = entry.get('turn', 0)
            turns.add(turn)
            
            item_type = entry.get('item_type', '')
            if item_type == 'tool_call_item':
                tool_calls += 1
            elif item_type == 'message_output_item':
                llm_requests += 1
        
        return {
            'input_tokens': 0,  # Cannot reconstruct
            'output_tokens': 0,  # Cannot reconstruct  
            'total_tokens': 0,
            'requests': llm_requests,
            'tool_calls': tool_calls,
            'turns': len(turns),
            'tracking_source': 'session_history_reconstruction',
            'note': 'Token counts unavailable - reconstructed from session history structure only'
        }
        
    except Exception as e:
        print(f"[USAGE TRACKER] Error reconstructing from session history: {e}")
        return None


def get_usage_from_model_tracking(model) -> Optional[Dict[str, Any]]:
    """
    Extract usage data from the model's internal tracking.
    
    Args:
        model: The agent model (OpenAIChatCompletionsModelWithRetry or similar)
        
    Returns:
        Dict with model-tracked data or None
    """
    if model is None:
        return None
    
    result = {}
    
    # Try to get precise cost from OpenRouter tracking
    if hasattr(model, 'get_precise_cost'):
        try:
            cost, source = model.get_precise_cost()
            if cost > 0:
                result['openrouter_cost'] = cost
                result['cost_source'] = source
        except Exception:
            pass
    
    # Try to get total_openrouter_cost directly
    if hasattr(model, 'total_openrouter_cost'):
        cost = getattr(model, 'total_openrouter_cost', 0)
        if cost > 0:
            result['openrouter_cost'] = cost
            result['cost_source'] = getattr(model, 'cost_source', 'openrouter_api')
    
    return result if result else None
