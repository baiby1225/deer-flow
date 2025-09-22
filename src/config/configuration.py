# Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
# SPDX-License-Identifier: MIT

import logging
import os
from dataclasses import dataclass, field, fields
from typing import Any, Optional

from langchain_core.runnables import RunnableConfig

from src.config.report_style import ReportStyle
from src.rag.retriever import Resource
from src.config.loader import get_str_env, get_int_env, get_bool_env

logger = logging.getLogger(__name__)


def get_recursion_limit(default: int = 25) -> int:
    """Get the recursion limit from environment variable or use default.

    Args:
        default: Default recursion limit if environment variable is not set or invalid

    Returns:
        int: The recursion limit to use
    """
    env_value_str = get_str_env("AGENT_RECURSION_LIMIT", str(default))
    parsed_limit = get_int_env("AGENT_RECURSION_LIMIT", default)

    if parsed_limit > 0:
        logger.info(f"Recursion limit set to: {parsed_limit}")
        return parsed_limit
    else:
        logger.warning(
            f"AGENT_RECURSION_LIMIT value '{env_value_str}' (parsed as {parsed_limit}) is not positive. "
            f"Using default value {default}."
        )
        return default


@dataclass(kw_only=True)
class Configuration:
    """The configurable fields."""

    resources: list[Resource] = field(
        default_factory=list
    )  # Resources to be used for the research
    max_plan_iterations: int = 1  # Maximum number of plan iterations
    max_step_num: int = 3  # Maximum number of steps in a plan
    max_search_results: int = 3  # Maximum number of search results
    mcp_settings: dict = None  # MCP settings, including dynamic loaded tools
    report_style: str = ReportStyle.ACADEMIC.value  # Report style
    enable_deep_thinking: bool = False  # Whether to enable deep thinking
    company_knowledge_bases: list[str] = field(
        default_factory=lambda: ["风管知识库", "运管知识库"]
    )  # 我司指定的知识库名称列表

    @classmethod
    def from_runnable_config(
        cls, config: Optional[RunnableConfig] = None
    ) -> "Configuration":
        """Create a Configuration instance from a RunnableConfig."""

        configurable = (
            config["configurable"] if config and "configurable" in config else {}
        )

        # 尝试从YAML配置文件加载配置
        yaml_config = {}
        try:
            from .loader import load_yaml_config
            yaml_config = load_yaml_config("conf.yaml")
        except Exception as e:
            logger.warning(f"Failed to load YAML config: {e}")

        values: dict[str, Any] = {}
        for f in fields(cls):
            if f.init:
                # 优先级：环境变量 > configurable > YAML配置 > 默认值
                env_value = os.environ.get(f.name.upper())
                configurable_value = configurable.get(f.name)
                yaml_value = yaml_config.get(f.name.upper())
                
                if env_value is not None:
                    # 处理环境变量中的列表（用逗号分隔）
                    if f.name == "company_knowledge_bases" and isinstance(env_value, str):
                        values[f.name] = [item.strip() for item in env_value.split(",") if item.strip()]
                    else:
                        values[f.name] = env_value
                elif configurable_value is not None:
                    values[f.name] = configurable_value
                elif yaml_value is not None:
                    values[f.name] = yaml_value

        return cls(**{k: v for k, v in values.items() if v is not None})
