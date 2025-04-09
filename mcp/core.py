"""
Master Control Program (MCP) Core Module

This module provides the central coordination for the MCP architecture,
which manages and orchestrates the various specialized agents in the system.
The MCP is designed as a central intelligence that delegates tasks to appropriate agents.
"""

import logging
import threading
import time
from typing import Dict, List, Callable, Any, Optional
import importlib
import os
import sys
import json

# Setup logging
logging.basicConfig(level=logging.INFO, 
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('mcp')

class MCP:
    """Master Control Program coordinator class"""
    
    def __init__(self):
        """Initialize the MCP"""
        self.agents = {}  # Dictionary to store registered agents
        self.tasks = {}   # Dictionary to store active tasks
        self.task_queue = []  # Queue of pending tasks
        self.task_results = {}  # Storage for task results
        self.running = False
        self.worker_thread = None
        self.task_id_counter = 0
        logger.info("MCP initialized")
    
    def register_agent(self, agent_id: str, agent_instance) -> bool:
        """Register an agent with the MCP"""
        if agent_id in self.agents:
            logger.warning(f"Agent {agent_id} already registered")
            return False
        
        self.agents[agent_id] = agent_instance
        logger.info(f"Agent {agent_id} registered")
        return True
    
    def deregister_agent(self, agent_id: str) -> bool:
        """Remove an agent from the MCP registry"""
        if agent_id not in self.agents:
            logger.warning(f"Agent {agent_id} not registered")
            return False
        
        del self.agents[agent_id]
        logger.info(f"Agent {agent_id} deregistered")
        return True
    
    def submit_task(self, agent_id: str, task_data: Dict[str, Any], 
                   callback: Optional[Callable] = None) -> Optional[str]:
        """Submit a task to an agent"""
        if agent_id not in self.agents:
            logger.error(f"Cannot submit task to unknown agent {agent_id}")
            return None
        
        self.task_id_counter += 1
        task_id = f"task_{self.task_id_counter}"
        
        task = {
            'id': task_id,
            'agent_id': agent_id,
            'data': task_data,
            'status': 'pending',
            'callback': callback,
            'submitted_at': time.time()
        }
        
        self.tasks[task_id] = task
        self.task_queue.append(task_id)
        logger.info(f"Task {task_id} submitted to agent {agent_id}")
        
        # Start worker thread if not already running
        if not self.running:
            self.start()
        
        return task_id
    
    def get_task_status(self, task_id: str) -> Optional[Dict[str, Any]]:
        """Get the status of a specific task"""
        if task_id not in self.tasks:
            logger.warning(f"Task {task_id} not found")
            return None
        
        return {
            'id': task_id,
            'status': self.tasks[task_id]['status'],
            'agent_id': self.tasks[task_id]['agent_id'],
            'submitted_at': self.tasks[task_id]['submitted_at']
        }
    
    def get_task_result(self, task_id: str) -> Any:
        """Get the result of a completed task"""
        if task_id not in self.task_results:
            logger.warning(f"No results for task {task_id}")
            return None
        
        return self.task_results[task_id]
    
    def start(self) -> bool:
        """Start the MCP worker thread"""
        if self.running:
            logger.warning("MCP already running")
            return False
        
        self.running = True
        self.worker_thread = threading.Thread(target=self._worker_loop)
        self.worker_thread.daemon = True
        self.worker_thread.start()
        logger.info("MCP worker thread started")
        return True
    
    def stop(self) -> bool:
        """Stop the MCP worker thread"""
        if not self.running:
            logger.warning("MCP not running")
            return False
        
        self.running = False
        if self.worker_thread:
            self.worker_thread.join(timeout=5.0)
        logger.info("MCP worker thread stopped")
        return True
    
    def _worker_loop(self):
        """Main worker loop for processing tasks"""
        logger.info("Worker loop started")
        while self.running:
            if not self.task_queue:
                time.sleep(0.1)  # Sleep briefly if no tasks
                continue
            
            # Get next task
            task_id = self.task_queue.pop(0)
            task = self.tasks[task_id]
            
            # Update status
            task['status'] = 'processing'
            
            try:
                # Process task
                agent = self.agents[task['agent_id']]
                result = agent.process_task(task['data'])
                
                # Store result
                self.task_results[task_id] = result
                task['status'] = 'completed'
                
                # Call callback if provided
                if task['callback']:
                    try:
                        task['callback'](task_id, result)
                    except Exception as e:
                        logger.error(f"Error in task callback: {str(e)}")
                
            except Exception as e:
                task['status'] = 'failed'
                task['error'] = str(e)
                logger.error(f"Error processing task {task_id}: {str(e)}")
        
        logger.info("Worker loop terminated")
    
    def get_agent_info(self, agent_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """Get information about registered agents"""
        if agent_id:
            if agent_id not in self.agents:
                return None
            agent = self.agents[agent_id]
            return {
                'id': agent_id,
                'type': agent.__class__.__name__,
                'capabilities': getattr(agent, 'capabilities', []),
                'status': getattr(agent, 'status', 'unknown')
            }
        else:
            # Return info for all agents
            return {
                agent_id: {
                    'type': agent.__class__.__name__,
                    'capabilities': getattr(agent, 'capabilities', []),
                    'status': getattr(agent, 'status', 'unknown')
                }
                for agent_id, agent in self.agents.items()
            }
    
    def discover_agents(self, agent_dir: str = 'agents') -> List[str]:
        """Automatically discover and register available agents"""
        agent_modules = []
        
        # Get absolute path to the agent directory
        agent_path = os.path.abspath(os.path.join(os.path.dirname(__file__), agent_dir))
        
        # Add to Python path if needed
        if agent_path not in sys.path:
            sys.path.append(agent_path)
        
        # Look for Python files in the agent directory
        for file in os.listdir(agent_path):
            if file.endswith('.py') and not file.startswith('__'):
                module_name = file[:-3]  # Remove .py extension
                try:
                    # Import the module
                    import_path = f"mcp.agents.{module_name}"
                    module = importlib.import_module(import_path)
                    agent_modules.append(module_name)
                    
                    # Look for Agent classes in the module
                    for attr_name in dir(module):
                        attr = getattr(module, attr_name)
                        if (isinstance(attr, type) and 
                            attr_name.endswith('Agent') and 
                            hasattr(attr, 'process_task')):
                            
                            # Skip if it's the BaseAgent class
                            if attr_name == 'BaseAgent':
                                continue
                                
                            # Skip if already registered from direct import
                            agent_id = f"{module_name}.{attr_name}"
                            if agent_id in self.agents:
                                logger.info(f"Agent {agent_id} already registered")
                                continue
                                
                            # Create instance and register
                            agent_instance = attr()
                            self.register_agent(agent_id, agent_instance)
                
                except Exception as e:
                    logger.error(f"Error loading agent module {module_name}: {str(e)}")
        
        return agent_modules
    
    def agent_status_report(self) -> str:
        """Generate a human-readable status report of all agents"""
        if not self.agents:
            return "No agents registered."
        
        report = "MCP Agent Status Report\n"
        report += "=====================\n\n"
        
        for agent_id, agent in self.agents.items():
            report += f"Agent: {agent_id}\n"
            report += f"Type: {agent.__class__.__name__}\n"
            report += f"Status: {getattr(agent, 'status', 'unknown')}\n"
            if hasattr(agent, 'capabilities'):
                report += "Capabilities:\n"
                for capability in agent.capabilities:
                    report += f"  - {capability}\n"
            if hasattr(agent, 'last_activity'):
                report += f"Last Activity: {agent.last_activity}\n"
            report += "\n"
        
        return report

# Create a global instance
mcp_instance = MCP()