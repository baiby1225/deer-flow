# Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
# SPDX-License-Identifier: MIT

import logging

from src.config.configuration import get_recursion_limit
from src.utils.loadmcp import load_config_from_file

# Configure logging
logging.basicConfig(
    level=logging.INFO,  # Default level is INFO
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)


def enable_debug_logging():
    """Enable debug level logging for more detailed execution information."""
    logging.getLogger("src").setLevel(logging.DEBUG)


logger = logging.getLogger(__name__)


# Create the graph - import here to avoid circular import
def get_graph():
    from src.graph import build_graph
    return build_graph()

# Create graph instance for langgraph dev
graph = get_graph()


async def run_agent_workflow_async(
        user_input: str,
        debug: bool = False,
        max_plan_iterations: int = 1,
        max_step_num: int = 3,
        enable_background_investigation: bool = True,
):
    """Run the agent workflow asynchronously with the given user input.

    Args:
        user_input: The user's query or request
        debug: If True, enables debug level logging
        max_plan_iterations: Maximum number of plan iterations
        max_step_num: Maximum number of steps in a plan
        enable_background_investigation: If True, performs web search before planning to enhance context

    Returns:
        The final state after the workflow completes
    """
    if not user_input:
        raise ValueError("Input could not be empty")

    if debug:
        enable_debug_logging()

    logger.info(f"Starting async workflow with user input: {user_input}")
    
    # Load MCP configuration from file
    file_config = load_config_from_file()
    
    initial_state = {
        # Runtime Variables
        "messages": [{"role": "user", "content": user_input}],
        "auto_accepted_plan": True,
        "enable_background_investigation": enable_background_investigation,
    }
    
    # Build config with file configuration as base, overridden by function parameters
    config = {
        "configurable": {
            "thread_id": "default",
            "max_plan_iterations": file_config.get("max_plan_iterations", max_plan_iterations),
            "max_step_num": file_config.get("max_step_num", max_step_num),
            "max_search_results": file_config.get("max_search_results", 3),
            "report_style": file_config.get("report_style", "academic"),
            "enable_deep_thinking": file_config.get("enable_deep_thinking", False),
            "mcp_settings": file_config.get("mcp_settings",{}),
        },
        "recursion_limit": get_recursion_limit(default=100),
    }
    last_message_cnt = 0
    async for s in graph.astream(
            input=initial_state, config=config, stream_mode="values"
    ):
        try:
            if isinstance(s, dict) and "messages" in s:
                if len(s["messages"]) <= last_message_cnt:
                    continue
                last_message_cnt = len(s["messages"])
                message = s["messages"][-1]
                if isinstance(message, tuple):
                    print(message)
                else:
                    message.pretty_print()
            else:
                # For any other output format
                print(f"Output: {s}")
        except Exception as e:
            logger.error(f"Error processing stream output: {e}")
            print(f"Error processing output: {str(e)}")

    logger.info("Async workflow completed successfully")


if __name__ == "__main__":
    print(graph.get_graph(xray=True).draw_mermaid())
