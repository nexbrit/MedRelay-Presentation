"""Configuration loader utility"""

import yaml
import os
from typing import Dict, Any
import logging
from pathlib import Path

logger = logging.getLogger(__name__)


class ConfigLoader:
    """Load and manage application configuration"""

    def __init__(self, config_path: str = None):
        """
        Initialize config loader

        Args:
            config_path: Path to config file (defaults to config/config.yaml)
        """
        if config_path is None:
            # Default to config/config.yaml relative to project root
            project_root = Path(__file__).parent.parent
            config_path = project_root / 'config' / 'config.yaml'

        self.config_path = Path(config_path)
        self.config = self.load_config()

    def load_config(self) -> Dict[str, Any]:
        """
        Load configuration from YAML file

        Returns:
            Configuration dictionary
        """
        try:
            if not self.config_path.exists():
                logger.warning(f"Config file not found at {self.config_path}, using defaults")
                return self.get_default_config()

            with open(self.config_path, 'r') as f:
                config = yaml.safe_load(f)

            logger.info(f"Configuration loaded from {self.config_path}")
            return config

        except Exception as e:
            logger.error(f"Error loading config: {e}")
            return self.get_default_config()

    def get_default_config(self) -> Dict[str, Any]:
        """
        Get default configuration

        Returns:
            Default configuration dictionary
        """
        return {
            'upstox': {
                'sandbox_mode': True
            },
            'trading': {
                'instruments': ['NIFTY', 'BANKNIFTY'],
                'signals': {
                    'rsi': {'period': 14, 'overbought': 70, 'oversold': 30},
                    'macd': {'fast_period': 12, 'slow_period': 26, 'signal_period': 9},
                    'ema': {'short_period': 9, 'medium_period': 21, 'long_period': 50},
                    'bollinger': {'period': 20, 'std_dev': 2.0}
                },
                'risk': {
                    'max_position_size': 100000,
                    'stop_loss_percentage': 2.0,
                    'take_profit_percentage': 4.0,
                    'max_positions': 5
                }
            },
            'screener': {
                'min_volume': 100000,
                'volume_surge_factor': 2.0,
                'min_price': 10,
                'max_price': 50000
            },
            'logging': {
                'level': 'INFO',
                'console': True
            }
        }

    def get(self, key: str, default: Any = None) -> Any:
        """
        Get configuration value by key path

        Args:
            key: Dot-separated key path (e.g., 'trading.signals.rsi.period')
            default: Default value if key not found

        Returns:
            Configuration value
        """
        keys = key.split('.')
        value = self.config

        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return default

        return value

    def update(self, key: str, value: Any):
        """
        Update configuration value

        Args:
            key: Dot-separated key path
            value: New value
        """
        keys = key.split('.')
        config = self.config

        for k in keys[:-1]:
            if k not in config:
                config[k] = {}
            config = config[k]

        config[keys[-1]] = value
        logger.debug(f"Config updated: {key} = {value}")

    def save(self, output_path: str = None):
        """
        Save configuration to file

        Args:
            output_path: Output file path (defaults to original config path)
        """
        save_path = Path(output_path) if output_path else self.config_path

        try:
            save_path.parent.mkdir(parents=True, exist_ok=True)

            with open(save_path, 'w') as f:
                yaml.dump(self.config, f, default_flow_style=False, indent=2)

            logger.info(f"Configuration saved to {save_path}")

        except Exception as e:
            logger.error(f"Error saving config: {e}")
