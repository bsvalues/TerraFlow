"""
MCP Integrators Module

This package contains modules to integrate agents with the MCP system.
"""

import logging
import importlib
import os

# Configure logging
logger = logging.getLogger(__name__)

def initialize_integrators(mcp_instance):
    """Initialize all available agent integrators"""
    # Get all Python files in the integrators directory
    current_dir = os.path.dirname(os.path.abspath(__file__))
    integrator_files = [f[:-3] for f in os.listdir(current_dir) 
                      if f.endswith('_integrator.py')]
    
    success_count = 0
    
    for integrator_file in integrator_files:
        try:
            # Import the integrator module
            module_name = f"mcp.integrators.{integrator_file}"
            module = importlib.import_module(module_name)
            
            # Call the initialize_agent function
            if hasattr(module, 'initialize_agent'):
                if module.initialize_agent(mcp_instance):
                    success_count += 1
            else:
                logger.warning(f"Integrator {integrator_file} does not have initialize_agent function")
        except Exception as e:
            logger.error(f"Error initializing integrator {integrator_file}: {str(e)}")
    
    logger.info(f"Initialized {success_count} agent integrators")
    return success_count > 0