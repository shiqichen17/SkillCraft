from dataclasses import dataclass, field
from typing import Optional, Union, Literal, Dict
import os
from utils.api_model.model_provider import API_MAPPINGS

@dataclass
class Model:
    """Model configuration"""
    short_name: str
    provider: str
    real_name: Optional[str] = None
    
    def __post_init__(self):
        """By default, use short_name as real_name if not provided"""
        if self.real_name is None:
            # For local VLLM provider, use the model name as-is without mapping
            if self.provider == "local_vllm":
                self.real_name = self.short_name
            elif self.provider == "unified":
                # For unified provider, check if TOOLATHLON_OPENAI_BASE_URL points to OpenRouter
                # If so, try to get the OpenRouter model name from API_MAPPINGS
                base_url = os.getenv('TOOLATHLON_OPENAI_BASE_URL', '')
                if 'openrouter.ai' in base_url and self.short_name in API_MAPPINGS:
                    mapping = API_MAPPINGS[self.short_name]
                    if 'api_model' in mapping:
                        api_models = mapping['api_model']
                        if 'openrouter' in api_models:
                            self.real_name = api_models['openrouter']
                        else:
                            self.real_name = self.short_name
                    else:
                        self.real_name = self.short_name
                else:
                    self.real_name = self.short_name
            else:
                # For other providers, get model name from API_MAPPINGS
                if self.short_name not in API_MAPPINGS:
                    raise KeyError(
                        f"Model '{self.short_name}' not found in API_MAPPINGS. "
                        f"Available models: {list(API_MAPPINGS.keys())}"
                    )
                mapping = API_MAPPINGS[self.short_name]
                if 'api_model' not in mapping:
                    raise KeyError(
                        f"Model '{self.short_name}' does not have 'api_model' key in API_MAPPINGS."
                    )
                api_models = mapping['api_model']
                if self.provider not in api_models:
                    raise KeyError(
                        f"Provider '{self.provider}' not found for model '{self.short_name}'. "
                        f"Available providers: {list(api_models.keys())}"
                    )
                self.real_name = api_models[self.provider]
        if "claude" in self.real_name and "3.7" in self.real_name:
            print("\033[91m" + "Warning: we suggest you to use **claude-4.5-sonnet** instead of **claude-3.7-sonnet**, as they have the same price and obviously the former is better." + "\033[0m")

@dataclass
class Generation:
    """Generation parameter configuration"""
    temperature: Optional[float] = None  # None = use model default
    top_p: float = 1.0
    max_tokens: int = 8192
    extra_body: Optional[Dict] = None
    
    def __post_init__(self):
        """Validate the reasonableness of generation parameters"""
        if self.temperature is not None and not 0 <= self.temperature <= 2:
            raise ValueError(f"temperature should be between 0 and 2, but got {self.temperature}")
        
        if not 0 < self.top_p <= 1:
            raise ValueError(f"top_p should be between 0 and 1, but got {self.top_p}")
        
        if self.max_tokens < 1:
            raise ValueError(f"max_tokens should be greater than 0, but got {self.max_tokens}")