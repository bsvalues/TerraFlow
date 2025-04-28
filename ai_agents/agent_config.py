"""
Agent Configuration Manager

This module provides configuration management for AI agents, including
automatic timeout management and agent activation settings.
"""

import os
import json
import logging
from typing import Dict, Any, Optional, List

logger = logging.getLogger(__name__)

# Default configuration
DEFAULT_AGENT_CONFIG = {
    "timeout_seconds": 600,  # Default inactive timeout (10 minutes)
    "enabled_agents": ["*"],  # Wildcard means all agents are enabled
    "disable_timeout_warnings": False,  # By default, show timeout warnings
    "warning_interval": 300,  # How often to log warnings (5 minutes)
    "auto_restart_on_timeout": False,  # Auto restart inactive agents
}

class AgentConfigManager:
    """Manage agent configuration and behavior"""
    
    def __init__(self, config_file: Optional[str] = None):
        """Initialize the agent configuration manager"""
        self.config = DEFAULT_AGENT_CONFIG.copy()
        self.config_file = config_file or os.environ.get("AGENT_CONFIG_FILE", "agent_config.json")
        self._load_config()
        
    def _load_config(self):
        """Load configuration from a JSON file if available"""
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, "r") as f:
                    file_config = json.load(f)
                    self.config.update(file_config)
                logger.info(f"Loaded agent configuration from {self.config_file}")
            except Exception as e:
                logger.error(f"Error loading agent config file {self.config_file}: {str(e)}")
                
    def save_config(self):
        """Save current configuration to the config file"""
        try:
            with open(self.config_file, "w") as f:
                json.dump(self.config, f, indent=2)
            logger.info(f"Saved agent configuration to {self.config_file}")
            return True
        except Exception as e:
            logger.error(f"Error saving agent config file {self.config_file}: {str(e)}")
            return False
            
    def is_agent_enabled(self, agent_type: str) -> bool:
        """Check if a specific agent type is enabled"""
        enabled_agents = self.config.get("enabled_agents", [])
        return "*" in enabled_agents or agent_type in enabled_agents
        
    def is_timeout_warning_enabled(self) -> bool:
        """Check if timeout warnings are enabled"""
        return not self.config.get("disable_timeout_warnings", False)
        
    def get_timeout_seconds(self) -> int:
        """Get the agent inactivity timeout in seconds"""
        return self.config.get("timeout_seconds", 600)
        
    def get_warning_interval(self) -> int:
        """Get the interval for timeout warnings in seconds"""
        return self.config.get("warning_interval", 300)
        
    def should_auto_restart(self) -> bool:
        """Check if inactive agents should be automatically restarted"""
        return self.config.get("auto_restart_on_timeout", False)
        
    def enable_agent(self, agent_type: str) -> bool:
        """Enable a specific agent type"""
        enabled_agents = self.config.get("enabled_agents", [])
        if agent_type not in enabled_agents and "*" not in enabled_agents:
            enabled_agents.append(agent_type)
            self.config["enabled_agents"] = enabled_agents
            return self.save_config()
        return True
        
    def disable_agent(self, agent_type: str) -> bool:
        """Disable a specific agent type"""
        enabled_agents = self.config.get("enabled_agents", [])
        if "*" in enabled_agents:
            # If wildcard is present, replace with list of all types except this one
            # This would require getting a list of all agent types from elsewhere
            pass
        elif agent_type in enabled_agents:
            enabled_agents.remove(agent_type)
            self.config["enabled_agents"] = enabled_agents
            return self.save_config()
        return True

# Singleton instance
_agent_config_manager = None

def get_agent_config_manager() -> AgentConfigManager:
    """Get the singleton instance of the agent configuration manager"""
    global _agent_config_manager
    if _agent_config_manager is None:
        _agent_config_manager = AgentConfigManager()
    return _agent_config_manager