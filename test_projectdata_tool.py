#!/usr/bin/env python3
"""
测试projectdata_tool工具是否可以调用成功
"""

import asyncio
import logging
import sys
import os

from langchain.agents import create_react_agent

from src.agents import create_agent
from src.config.agents import AGENT_LLM_MAP
from src.graph.nodes import _execute_agent_step
from src.llms.llm import get_llm_by_type
from src.prompts import apply_prompt_template

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from langchain_mcp_adapters.client import MultiServerMCPClient
from src.utils.loadmcp import load_config_from_file_async


# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def test_projectdata_tool():
    """测试projectdata_tool工具是否可以调用成功"""

    try:
        logger.info("🚀 开始测试projectdata_tool工具...")

        # 加载MCP配置
        config = await load_config_from_file_async()
        mcp_settings = config.get("mcp_settings", {})
        servers = mcp_settings.get("servers", {})

        # 为researcher代理配置MCP服务器
        researcher_servers = {}
        for server_name, server_config in servers.items():
            if (
                    server_config.get("enabled_tools")
                    and "researcher" in server_config.get("add_to_agents", [])
            ):
                researcher_servers[server_name] = {
                    k: v
                    for k, v in server_config.items()
                    if k in ("transport", "command", "args", "url", "env", "headers")
                }

        if not researcher_servers:
            logger.error("❌ 没有为researcher配置MCP服务器")
            return False

        logger.info(f"✅ 找到 {len(researcher_servers)} 个MCP服务器")

        # 创建MCP客户端并获取工具
        client = MultiServerMCPClient(researcher_servers)
        all_tools = await client.get_tools()

        logger.info(f"🔍 找到 {len(all_tools)} 个工具")


        # 构造State参数
        from src.prompts.planner_model import Plan, Step, StepType
        
        # 创建一个测试计划
        test_plan = Plan(
            locale="zh-CN",
            has_enough_context=False,
            thought="测试projectdata_tool工具的功能",
            title="测试projectdata_tool工具",
            steps=[
                Step(
                    need_search=True,
                    title="测试projectdata_tool工具调用",
                    description="使用projectdata_tool工具获取项目20250729001的完整数据",
                    step_type=StepType.RESEARCH
                )
            ]
        )
        
        # 构造State对象
        state = {
            "current_plan": test_plan,
            "locale": "zh-CN",
            "research_topic": "测试projectdata_tool工具",
            "observations": [],
            "resources": [],
            "plan_iterations": 0,
            "final_report": "",
            "auto_accepted_plan": False,
            "enable_background_investigation": True,
            "background_investigation_results": None
        }
        
        # 创建代理并执行步骤
        agent = create_agent("researcher", "researcher", all_tools, "researcher")
        logger.info("🤖 创建researcher代理成功")
        
        logger.info("🚀 开始执行代理步骤...")
        result = await _execute_agent_step(state, agent, "researcher")
        logger.info(f"✅ 代理步骤执行完成: {result}")

        # 检查是否有projectdata_tool
        projectdata_tool_found = any(tool.name == "projectdata_tool" for tool in all_tools)
        if not projectdata_tool_found:
            logger.error("❌ 未找到projectdata_tool工具")
            return False

        logger.info("✅ 找到projectdata_tool工具")

        # 查找projectdata_tool
        projectdata_tool = None
        for tool in all_tools:
            if tool.name == "projectdata_tool":
                projectdata_tool = tool
                break

        logger.info(f"📋 工具描述: {projectdata_tool.description}")

        # 测试工具调用
        logger.info("🧪 正在测试工具调用...")

        # 使用一个测试项目编号
        test_project_id = "20250729001"

        try:
            # 调用工具
            result = await projectdata_tool.ainvoke({"project_no": test_project_id})
            logger.info(f"✅ 工具调用成功！")
            logger.info(f"📊 结果: {result}")

            # 检查结果是否包含预期内容
            if "项目" in str(result) or "project" in str(result).lower():
                logger.info("🎉 工具返回了项目相关数据")
                return True
            else:
                logger.warning("⚠️ 工具返回的数据可能不完整")
                return True

        except Exception as call_error:
            logger.error(f"❌ 工具调用失败: {str(call_error)}")
            logger.error(f"🔍 错误类型: {type(call_error).__name__}")
            return False

    except Exception as e:
        logger.error(f"❌ 测试过程中发生错误: {str(e)}")
        logger.error(f"🔍 错误类型: {type(e).__name__}")
        import traceback
        logger.error(f"📋 完整错误信息: {traceback.format_exc()}")
        return False


async def main():
    """主测试函数"""
    logger.info("=" * 60)
    logger.info("🧪 开始测试projectdata_tool工具")
    logger.info("=" * 60)

    # 测试projectdata_tool
    success = await test_projectdata_tool()

    # 总结
    logger.info("\n" + "=" * 60)
    logger.info("📊 测试结果总结:")
    logger.info(f"projectdata_tool工具: {'✅ 成功' if success else '❌ 失败'}")
    logger.info("=" * 60)

    if success:
        logger.info("🎉 projectdata_tool工具可以正常使用！")
    else:
        logger.error("💥 projectdata_tool工具无法使用，请检查配置和网络连接")


if __name__ == "__main__":
    asyncio.run(main())
