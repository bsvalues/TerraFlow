"""
Sales Verification Agent Integrator

This module integrates the Sales Verification Agent with the MCP system.
"""

import logging
import sys
from mcp.agents.base_agent import BaseAgent
from mcp.agents.sales_verification_agent import SalesVerificationAgent

# Configure logging
logger = logging.getLogger(__name__)

def initialize_agent(mcp_instance):
    """Initialize and register the Sales Verification Agent with MCP"""
    try:
        # Create the Sales Verification Agent
        agent = SalesVerificationAgent()
        
        # Register the agent with MCP
        mcp_instance.register_agent('sales_verification', agent)
        
        logger.info("Sales Verification Agent registered successfully")
        return True
    except ImportError as e:
        logger.error(f"Import error initializing Sales Verification Agent: {str(e)}")
        logger.error(f"Python path: {sys.path}")
        return False
    except Exception as e:
        logger.error(f"Error initializing Sales Verification Agent: {str(e)}")
        return False