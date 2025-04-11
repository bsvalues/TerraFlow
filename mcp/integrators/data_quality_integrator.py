"""
Data Quality Agent Integrator

This module integrates the Data Quality Agent with the MCP system.
"""

import logging
import sys
from mcp.core import BaseAgent
from mcp.agents.data_quality_agent import DataQualityAgent

# Configure logging
logger = logging.getLogger(__name__)

def initialize_agent(mcp_instance):
    """Initialize and register the Data Quality Agent with MCP"""
    try:
        # Create the Data Quality Agent
        agent = DataQualityAgent()
        
        # Register the agent with MCP
        mcp_instance.register_agent('data_quality', agent)
        
        logger.info("Data Quality Agent registered successfully")
        return True
    except ImportError as e:
        logger.error(f"Import error initializing Data Quality Agent: {str(e)}")
        logger.error(f"Python path: {sys.path}")
        return False
    except Exception as e:
        logger.error(f"Error initializing Data Quality Agent: {str(e)}")
        return False