import logging
from pathlib import Path

import yaml

logger = logging.getLogger(__name__)


def load_config_from_file(config_path: str = "mcp.yaml") -> dict:
    """Load configuration from YAML file.

    Args:
        config_path: Path to the configuration file

    Returns:
        dict: Configuration dictionary
    """
    try:
        config_file = Path(config_path)
        if not config_file.exists():
            logger.warning(f"MCP configuration file {config_path} not found, using defaults")
            return {}

        with open(config_file, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
            logger.info(f"MCP configuration loaded from {config_path}")
            return config or {}
    except Exception as e:
        logger.error(f"Error loading configuration from {config_path}: {e}")
        return {}