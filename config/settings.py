"""
Configuration management for the Gary Wealth Data API
"""
import os
import yaml
import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)

class Config:
    """Configuration class for loading environment settings"""
    
    def __init__(self):
        self.config_data = self._load_config()
        
    def _load_config(self) -> Dict[str, Any]:
        """Load configuration from env.yaml or environment variables"""
        config = {}
        
        # Try to load from env.yaml first
        try:
            with open('env.yaml', 'r') as file:
                config = yaml.safe_load(file) or {}
                logger.info("Loaded configuration from env.yaml")
        except FileNotFoundError:
            logger.info("env.yaml not found, using environment variables")
        
        # Fallback to environment variables
        config.setdefault('SUPABASE_URL', os.getenv('SUPABASE_URL'))
        config.setdefault('SUPABASE_KEY', os.getenv('SUPABASE_KEY'))
        config.setdefault('ENV', os.getenv('ENV', 'development'))
        config.setdefault('DEBUG', os.getenv('DEBUG', 'false').lower() == 'true')
        config.setdefault('PORT', int(os.getenv('PORT', 8080)))
        
        return config
    
    def get(self, key: str, default: Any = None) -> Any:
        """Get configuration value by key"""
        return self.config_data.get(key, default)
    
    def validate_required_config(self) -> None:
        """Validate that required configuration is present"""
        required_keys = ['SUPABASE_URL', 'SUPABASE_KEY']
        missing_keys = [key for key in required_keys if not self.get(key)]
        
        if missing_keys:
            raise ValueError(f"Missing required configuration: {missing_keys}")
    
    @property
    def supabase_url(self) -> str:
        return self.get('SUPABASE_URL')
    
    @property
    def supabase_key(self) -> str:
        return self.get('SUPABASE_KEY')
    
    @property
    def environment(self) -> str:
        return self.get('ENV', 'development')
    
    @property
    def debug(self) -> bool:
        return self.get('DEBUG', False)
    
    @property
    def port(self) -> int:
        return self.get('PORT', 8080)

# Global config instance
config = Config()
