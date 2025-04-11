"""
Master Control Program (MCP) Core Module

This module provides the central coordination for the MCP architecture,
which manages and orchestrates the various specialized agents in the system.
The MCP is designed as a central intelligence that delegates tasks to appropriate agents.

The enhanced version now supports the Agent-to-Agent communication protocol,
enabling specialized agents to collaborate effectively on complex assessment workflows.
It also provides a centralized experience buffer for agent learning and improvement.
"""

import logging
import threading
import time
from typing import Dict, List, Callable, Any, Optional, Union
import importlib
import os
import sys
import json
import uuid

# Agent-to-Agent protocol support
from mcp.agent_protocol import AgentCommunicationProtocol, MessageType, Message
from mcp.message_broker import MessageBroker
from mcp.experience_buffer import ExperienceBuffer, Experience
from mcp.master_prompt import MasterPromptManager, MasterPrompt

# Setup logging
logging.basicConfig(level=logging.INFO, 
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('mcp')

class MCP:
    """
    Master Control Program coordinator class
    
    This class serves as the central coordination system for the agent-based architecture,
    managing agent registration, task delegation, workflow orchestration, and inter-agent
    communication through the Agent-to-Agent protocol.
    """
    
    def __init__(self):
        """Initialize the MCP"""
        self.agents = {}  # Dictionary to store registered agents
        self.tasks = {}   # Dictionary to store active tasks
        self.task_queue = []  # Queue of pending tasks
        self.task_results = {}  # Storage for task results
        self.running = False
        self.worker_thread = None
        self.task_id_counter = 0
        self.conversations = {}  # Storage for agent conversations
        
        # Initialize message broker
        self.message_broker = MessageBroker()
        
        # Initialize experience buffer
        self.experience_buffer = ExperienceBuffer(max_size=10000, cleanup_interval=3600)
        
        # Agent-to-Agent communication protocol
        self.protocol = AgentCommunicationProtocol(self)
        
        # Master Prompt Manager
        self.master_prompt_manager = MasterPromptManager(self)
        
        # Assessment domain customization
        self.assessment_context = {
            "state": "Washington",
            "county": "Benton",
            "current_assessment_year": time.strftime("%Y"),
            "property_types": ["residential", "commercial", "agricultural", "industrial"]
        }
        
        # Initialize the default system master prompt
        self.default_master_prompt = self.master_prompt_manager.get_default_system_prompt()
        
        logger.info("MCP initialized with Agent-to-Agent protocol, experience buffer, and master prompt system support")
    
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
        """Start the MCP worker thread and its components"""
        if self.running:
            logger.warning("MCP already running")
            return False
        
        # Start message broker
        self.message_broker.start()
        logger.info("Message broker started")
        
        # Start experience buffer
        self.experience_buffer.start()
        logger.info("Experience buffer started")
        
        # Start MCP worker thread
        self.running = True
        self.worker_thread = threading.Thread(target=self._worker_loop)
        self.worker_thread.daemon = True
        self.worker_thread.start()
        logger.info("MCP worker thread started")
        return True
    
    def stop(self) -> bool:
        """Stop the MCP worker thread and its components"""
        if not self.running:
            logger.warning("MCP not running")
            return False
        
        # Stop MCP worker thread
        self.running = False
        if self.worker_thread:
            self.worker_thread.join(timeout=5.0)
        logger.info("MCP worker thread stopped")
        
        # Stop experience buffer
        self.experience_buffer.stop()
        logger.info("Experience buffer stopped")
        
        # Stop message broker
        self.message_broker.stop()
        logger.info("Message broker stopped")
        
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
    
    def get_agent(self, agent_id: str):
        """Get an agent by its ID"""
        if agent_id in self.agents:
            return self.agents[agent_id]
        return None
        
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

    def inject_protocol_handler(self) -> None:
        """
        Inject the protocol into all registered agents
        
        This method provides each agent with a reference to the protocol,
        enabling them to use the Agent-to-Agent communication functionality.
        """
        for agent_id, agent in self.agents.items():
            # Add protocol to agent if it has the proper interface
            if hasattr(agent, 'send_query') and hasattr(agent, 'send_inform') and hasattr(agent, 'send_request'):
                # Inject the protocol into the agent's methods
                agent.send_query.__defaults__ = agent.send_query.__defaults__[:-1] + (self.protocol,)
                agent.send_inform.__defaults__ = agent.send_inform.__defaults__[:-1] + (self.protocol,)
                agent.send_request.__defaults__ = agent.send_request.__defaults__[:-1] + (self.protocol,)
                
                logger.info(f"Injected protocol handler into agent {agent_id}")
                
                # Register default message handlers if they exist
                if hasattr(agent, '_handle_query'):
                    self.protocol.register_message_handler(
                        agent_id,
                        MessageType.QUERY,
                        agent._handle_query
                    )
                
                if hasattr(agent, '_handle_inform'):
                    self.protocol.register_message_handler(
                        agent_id,
                        MessageType.INFORM,
                        agent._handle_inform
                    )
                
                if hasattr(agent, '_handle_request'):
                    self.protocol.register_message_handler(
                        agent_id,
                        MessageType.REQUEST,
                        agent._handle_request
                    )
    
    def register_message_handler(
        self, 
        agent_id: str, 
        message_type: Union[str, MessageType], 
        handler: Callable
    ) -> bool:
        """
        Register a message handler for an agent
        
        Args:
            agent_id: ID of the agent
            message_type: Type of message to handle
            handler: Function to call when a message of this type is received
            
        Returns:
            True if handler registered successfully, False otherwise
        """
        if agent_id not in self.agents:
            logger.error(f"Cannot register handler for unknown agent {agent_id}")
            return False
        
        # Convert string message types to enum if needed
        if isinstance(message_type, str):
            try:
                message_type = MessageType(message_type)
            except ValueError:
                logger.error(f"Invalid message type: {message_type}")
                return False
        
        self.protocol.register_message_handler(agent_id, message_type, handler)
        logger.info(f"Registered {message_type.value if isinstance(message_type, MessageType) else message_type} handler for agent {agent_id}")
        return True
    
    def send_agent_message(
        self,
        sender_id: str,
        receiver_id: str,
        message_type: Union[str, MessageType],
        content: Dict[str, Any],
        wait_for_response: bool = False,
        timeout: float = 30.0
    ) -> Optional[Any]:
        """
        Send a message from one agent to another
        
        Args:
            sender_id: ID of the sending agent
            receiver_id: ID of the receiving agent
            message_type: Type of message to send
            content: Content of the message (should be a dictionary)
            wait_for_response: Whether to wait for a response
            timeout: Timeout in seconds when waiting for response
            
        Returns:
            Response message if wait_for_response is True, otherwise None
        """
        if sender_id not in self.agents:
            logger.error(f"Unknown sending agent {sender_id}")
            return None
        
        if receiver_id not in self.agents and receiver_id != "broadcast":
            logger.error(f"Unknown receiving agent {receiver_id}")
            return None
        
        try:
            # Create the message
            message = Message(
                source_agent_id=sender_id,
                target_agent_id=receiver_id,
                message_type=message_type,
                payload=content
            )
            
            # Send through the protocol handler
            result = self.protocol.send_message(
                message=message,
                wait_for_response=wait_for_response,
                timeout=timeout
            )
            
            return result
        except Exception as e:
            logger.error(f"Error sending message from {sender_id} to {receiver_id}: {str(e)}")
            return None
    
    def create_conversation(
        self,
        initiator_id: str,
        responder_id: str,
        topic: str
    ) -> Optional[str]:
        """
        Create a conversation between two agents
        
        Args:
            initiator_id: ID of the initiating agent
            responder_id: ID of the responding agent
            topic: Topic of the conversation
            
        Returns:
            Conversation ID if successful, None otherwise
        """
        if initiator_id not in self.agents:
            logger.error(f"Unknown initiating agent {initiator_id}")
            return None
        
        if responder_id not in self.agents:
            logger.error(f"Unknown responding agent {responder_id}")
            return None
        
        try:
            conversation_id = self.protocol.create_conversation(
                initiator_id=initiator_id,
                responder_id=responder_id,
                topic=topic
            )
            
            logger.info(f"Created conversation {conversation_id} between {initiator_id} and {responder_id}")
            return conversation_id
        except Exception as e:
            logger.error(f"Error creating conversation: {str(e)}")
            return None
    
    def get_conversation(self, conversation_id: str) -> Optional[Dict[str, Any]]:
        """
        Get a conversation by ID
        
        Args:
            conversation_id: ID of the conversation
            
        Returns:
            Conversation data if found, None otherwise
        """
        try:
            conversation = self.protocol.get_conversation(conversation_id)
            if conversation:
                return conversation.to_dict()
            return None
        except Exception as e:
            logger.error(f"Error getting conversation {conversation_id}: {str(e)}")
            return None
    
    def distribute_master_prompt(self, prompt_id: Optional[str] = None) -> bool:
        """
        Distribute a master prompt to all registered agents
        
        This is a centralized function to broadcast a specific master prompt 
        to all agents, ensuring system-wide consistency in agent behavior
        and coordination.
        
        Args:
            prompt_id: ID of the prompt to distribute (default: the system default prompt)
            
        Returns:
            True if distribution was successful, False otherwise
        """
        try:
            # Use default prompt if none specified
            if prompt_id is None:
                prompt = self.default_master_prompt
            else:
                prompt = self.master_prompt_manager.get_prompt(prompt_id)
            
            # Register all agents for this prompt
            for agent_id in self.agents.keys():
                self.master_prompt_manager.register_agent(agent_id, prompt.prompt_id)
            
            logger.info(f"Distributed master prompt {prompt.prompt_id} to {len(self.agents)} agents")
            return True
        except Exception as e:
            logger.error(f"Error distributing master prompt: {str(e)}")
            return False
    
    def register_workflow_agent(self, agent_type: str) -> str:
        """
        Register a specialized assessment agent with the MCP
        
        Args:
            agent_type: Type of agent to register
            
        Returns:
            ID of the registered agent
        """
        try:
            # Import the agent class
            module_path = f"mcp.agents.{agent_type}_agent"
            class_name = f"{agent_type.title().replace('_', '')}Agent"
            
            module = importlib.import_module(module_path)
            agent_class = getattr(module, class_name)
            
            # Create and register the agent
            agent = agent_class()
            agent_id = agent_type
            
            self.register_agent(agent_id, agent)
            
            # Inject protocol handler
            self.inject_protocol_handler()
            
            return agent_id
        except Exception as e:
            logger.error(f"Error registering workflow agent {agent_type}: {str(e)}")
            return ""


# Create a global instance
mcp_instance = MCP()