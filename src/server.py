"""COMSOL MCP Server - Main entry point."""

import logging
from mcp.server.fastmcp import FastMCP

from .tools.session import register_session_tools
from .tools.model import register_model_tools
from .tools.parameters import register_parameter_tools
from .tools.geometry import register_geometry_tools
from .tools.physics import register_physics_tools
from .tools.mesh import register_mesh_tools
from .tools.study import register_study_tools
from .tools.results import register_results_tools
from .tools.audit import register_audit_tools, register_boundary_info_tool
from .tools.modify import register_modify_tools, register_interpolate_tool, register_material_function_tools
from .resources.model_resources import register_model_resources
from .knowledge.embedded import register_knowledge_tools

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

mcp = FastMCP("COMSOL MCP")


def register_all_tools() -> None:
    """Register all MCP tools."""
    register_session_tools(mcp)
    register_model_tools(mcp)
    register_parameter_tools(mcp)
    register_geometry_tools(mcp)
    register_physics_tools(mcp)
    register_mesh_tools(mcp)
    register_study_tools(mcp)
    register_results_tools(mcp)
    register_audit_tools(mcp)
    register_modify_tools(mcp)
    register_interpolate_tool(mcp)
    register_material_function_tools(mcp)
    register_boundary_info_tool(mcp)
    register_knowledge_tools(mcp)
    logger.info("Registered all tools")


def register_all_resources() -> None:
    """Register all MCP resources."""
    register_model_resources(mcp)
    logger.info("Registered all resources")


def main() -> None:
    """Run the MCP server."""
    logger.info("Starting COMSOL MCP Server...")
    
    register_all_tools()
    register_all_resources()
    
    # Pre-start COMSOL session on the main thread to avoid JVM hang in AnyIO worker threads
    logger.info("Pre-starting COMSOL session on main thread...")
    try:
        from .tools.session import session_manager
        # Use default cores and version
        res = session_manager.start()
        if res.get("success"):
            logger.info(f"COMSOL session pre-started successfully: {res}")
        else:
            logger.error(f"Failed to pre-start COMSOL session: {res.get('error')}")
    except Exception as e:
        logger.error(f"Failed to pre-start COMSOL session: {e}")
        
    mcp.run()


if __name__ == "__main__":
    main()
