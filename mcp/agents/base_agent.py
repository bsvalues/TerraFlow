"""
Base Agent Module

This module provides the BaseAgent class that all specialized agents
in the MCP architecture should inherit from. It defines the common
interface and functionality that all agents must implement.
"""

import logging
import time
from typing import Dict, List, Any, Optional
import uuid
import threading

# Setup logging
logging.basicConfig(level=logging.INFO, 
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

class BaseAgent:
    """Base class for all MCP agents"""
    
    def __init__(self, agent_id: Optional[str] = None):
        """Initialize the base agent"""
        self.agent_id = agent_id or f"{self.__class__.__name__}_{uuid.uuid4().hex[:8]}"
        self.status = "initialized"
        self.capabilities = []
        self.last_activity = time.time()
        self.logger = logging.getLogger(f"agent.{self.agent_id}")
        self.active_tasks = {}
        self.logger.info(f"Agent {self.agent_id} initialized")
    
    def process_task(self, task_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process a task assigned to this agent
        
        This method must be implemented by all derived agent classes.
        """
        raise NotImplementedError("Agents must implement process_task method")
    
    def get_status(self) -> str:
        """Get the current status of the agent"""
        return self.status
    
    def set_status(self, status: str) -> None:
        """Set the agent status"""
        self.status = status
        self.last_activity = time.time()
        self.logger.info(f"Agent status changed to: {status}")
    
    def get_capabilities(self) -> List[str]:
        """Get the list of agent capabilities"""
        return self.capabilities
    
    def update_capabilities(self, capabilities: List[str]) -> None:
        """Update the agent capabilities list"""
        self.capabilities = capabilities
        self.logger.info(f"Agent capabilities updated: {capabilities}")
    
    def add_capability(self, capability: str) -> None:
        """Add a new capability to the agent"""
        if capability not in self.capabilities:
            self.capabilities.append(capability)
            self.logger.info(f"Added capability: {capability}")
    
    def can_process(self, task_type: str) -> bool:
        """Check if the agent can process a specific task type"""
        return task_type in self.capabilities
    
    def shutdown(self) -> None:
        """Shutdown the agent gracefully"""
        self.set_status("shutdown")
        self.logger.info(f"Agent {self.agent_id} shutdown")
    
    def start_background_task(self, task_func, task_data: Dict[str, Any]) -> str:
        """Start a task in the background and return a task ID"""
        task_id = f"bg_{uuid.uuid4().hex[:12]}"
        
        def wrapper():
            try:
                self.active_tasks[task_id] = {"status": "running", "started": time.time()}
                result = task_func(task_data)
                self.active_tasks[task_id] = {
                    "status": "completed",
                    "started": self.active_tasks[task_id]["started"],
                    "completed": time.time(),
                    "result": result
                }
            except Exception as e:
                self.logger.error(f"Background task {task_id} failed: {str(e)}")
                self.active_tasks[task_id] = {
                    "status": "failed",
                    "started": self.active_tasks[task_id]["started"],
                    "completed": time.time(),
                    "error": str(e)
                }
        
        thread = threading.Thread(target=wrapper)
        thread.daemon = True
        thread.start()
        
        return task_id
    
    def get_background_task_status(self, task_id: str) -> Dict[str, Any]:
        """Get the status of a background task"""
        if task_id not in self.active_tasks:
            return {"status": "unknown", "error": "Task ID not found"}
        return self.active_tasks[task_id]

# Agent registry to keep track of all agent implementations
_agent_registry = {}