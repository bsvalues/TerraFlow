#!/usr/bin/env python
"""
Agent Management CLI

This script provides a command-line interface for managing AI agents,
including enabling/disabling agents and configuring timeout settings.
"""

import argparse
import sys
import logging
import time
from ai_agents.agent_config import get_agent_config_manager
from ai_agents.agent_manager import agent_manager

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def parse_args():
    """Parse command-line arguments"""
    parser = argparse.ArgumentParser(description='AI Agent Management CLI')
    
    # Create subparsers for different commands
    subparsers = parser.add_subparsers(dest='command', help='Command to execute')
    
    # List command
    list_parser = subparsers.add_parser('list', help='List all registered agents')
    
    # Enable command
    enable_parser = subparsers.add_parser('enable', help='Enable an agent type')
    enable_parser.add_argument('agent_type', help='Type of agent to enable')
    
    # Disable command
    disable_parser = subparsers.add_parser('disable', help='Disable an agent type')
    disable_parser.add_argument('agent_type', help='Type of agent to disable')
    
    # Config command
    config_parser = subparsers.add_parser('config', help='Configure agent settings')
    config_parser.add_argument('--timeout', type=int, help='Inactivity timeout in seconds')
    config_parser.add_argument('--warning-interval', type=int, help='Warning interval in seconds')
    config_parser.add_argument('--warnings', choices=['enable', 'disable'], help='Enable or disable timeout warnings')
    config_parser.add_argument('--auto-restart', choices=['enable', 'disable'], help='Enable or disable auto-restart')
    
    # Status command
    status_parser = subparsers.add_parser('status', help='Show agent status')
    
    return parser.parse_args()

def main():
    """Main function for the CLI"""
    args = parse_args()
    config = get_agent_config_manager()
    
    if args.command == 'list':
        # List all registered agent types
        if hasattr(agent_manager, 'agent_types'):
            print("Registered Agent Types:")
            for agent_type in agent_manager.agent_types.keys():
                enabled = config.is_agent_enabled(agent_type)
                status = "Enabled" if enabled else "Disabled"
                print(f"  - {agent_type}: {status}")
        else:
            print("No agent types are registered.")
            
    elif args.command == 'enable':
        # Enable an agent type
        if config.enable_agent(args.agent_type):
            print(f"Enabled agent type: {args.agent_type}")
        else:
            print(f"Failed to enable agent type: {args.agent_type}")
            
    elif args.command == 'disable':
        # Disable an agent type
        if config.disable_agent(args.agent_type):
            print(f"Disabled agent type: {args.agent_type}")
        else:
            print(f"Failed to disable agent type: {args.agent_type}")
            
    elif args.command == 'config':
        # Configure agent settings
        changed = False
        
        if args.timeout is not None:
            config.config['timeout_seconds'] = args.timeout
            changed = True
            print(f"Set inactivity timeout to {args.timeout} seconds")
            
        if args.warning_interval is not None:
            config.config['warning_interval'] = args.warning_interval
            changed = True
            print(f"Set warning interval to {args.warning_interval} seconds")
            
        if args.warnings == 'enable':
            config.config['disable_timeout_warnings'] = False
            changed = True
            print("Enabled timeout warnings")
        elif args.warnings == 'disable':
            config.config['disable_timeout_warnings'] = True
            changed = True
            print("Disabled timeout warnings")
            
        if args.auto_restart == 'enable':
            config.config['auto_restart_on_timeout'] = True
            changed = True
            print("Enabled automatic agent restart")
        elif args.auto_restart == 'disable':
            config.config['auto_restart_on_timeout'] = False
            changed = True
            print("Disabled automatic agent restart")
            
        if changed:
            config.save_config()
            print("Configuration saved.")
            
    elif args.command == 'status':
        # Show status of active agents
        if hasattr(agent_manager, 'agents'):
            print("Active Agents:")
            for agent_id, agent in agent_manager.agents.items():
                last_active = time.time() - agent.last_activity
                print(f"  - {agent_id} ({agent.__class__.__name__}): Last active {last_active:.1f} seconds ago, Status: {agent.status}")
        else:
            print("No active agents.")
    else:
        print("No command specified. Use --help for usage information.")
        
if __name__ == "__main__":
    main()