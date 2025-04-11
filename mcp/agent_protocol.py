"""
Agent-to-Agent Protocol Implementation for Benton County GeoAssessmentPro

This module implements the Agent-to-Agent communication protocol that allows
specialized agents to collaborate effectively on complex assessment workflows.
The protocol enables structured communication, knowledge sharing, and coordinated
task execution among autonomous agents within the MCP architecture.

Key features:
- Message passing with semantic protocol enforcement
- Contextual knowledge exchange between specialized agents
- Structured conversation protocols for complex workflows
- History tracking for audit and improvement

Reference: This implementation aligns with emerging standards for agent-to-agent
communication while being customized for the specific needs of property assessment
workflows in Benton County.
"""

import logging
import time
import uuid
import json
import threading
from typing import Dict, List, Any, Optional, Union, Callable
from datetime import datetime
from enum import Enum

# Setup logging
logger = logging.getLogger('agent_protocol')

class MessageType(Enum):
    """Types of messages in the Agent-to-Agent protocol"""
    QUERY = "query"           # Request for information
    INFORM = "inform"         # Provide information
    REQUEST = "request"       # Request an action
    PROPOSE = "propose"       # Propose a solution or approach
    ACCEPT = "accept"         # Accept a proposal
    REJECT = "reject"         # Reject a proposal
    INFORM_REF = "inform_ref" # Reference to external information
    CONFIRM = "confirm"       # Confirm understanding or receipt
    DISCONFIRM = "disconfirm" # Disconfirm understanding
    FAILURE = "failure"       # Report failure
    NOT_UNDERSTOOD = "not_understood" # Message not understood


class ConversationState(Enum):
    """States of a conversation between agents"""
    INITIATED = "initiated"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    TIMED_OUT = "timed_out"


class AgentMessage:
    """
    Structured message for Agent-to-Agent communication
    
    This class represents a message exchanged between agents, following
    a structured protocol that enables semantic validation and workflow support.
    """
    
    def __init__(
        self,
        message_type: Union[MessageType, str],
        content: Any,
        sender_id: str,
        receiver_id: str,
        conversation_id: Optional[str] = None,
        reply_to: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ):
        """
        Initialize a new agent message
        
        Args:
            message_type: Type of message (from MessageType enum or string)
            content: The content of the message
            sender_id: ID of the sending agent
            receiver_id: ID of the receiving agent
            conversation_id: ID of the conversation this message belongs to
            reply_to: ID of the message this is a reply to
            metadata: Additional contextual information
        """
        self.id = str(uuid.uuid4())
        
        # Convert string message type to enum if needed
        if isinstance(message_type, str):
            try:
                self.message_type = MessageType(message_type)
            except ValueError:
                raise ValueError(f"Invalid message type: {message_type}")
        else:
            self.message_type = message_type
            
        self.content = content
        self.sender_id = sender_id
        self.receiver_id = receiver_id
        self.conversation_id = conversation_id or str(uuid.uuid4())
        self.reply_to = reply_to
        self.timestamp = datetime.utcnow().isoformat()
        self.metadata = metadata or {}
        
    def to_dict(self) -> Dict[str, Any]:
        """Convert message to dictionary representation"""
        return {
            "id": self.id,
            "message_type": self.message_type.value,
            "content": self.content,
            "sender_id": self.sender_id,
            "receiver_id": self.receiver_id,
            "conversation_id": self.conversation_id,
            "reply_to": self.reply_to,
            "timestamp": self.timestamp,
            "metadata": self.metadata
        }
        
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'AgentMessage':
        """Create message from dictionary representation"""
        # Create a basic instance
        message = cls(
            message_type=data["message_type"],
            content=data["content"],
            sender_id=data["sender_id"],
            receiver_id=data["receiver_id"],
            conversation_id=data.get("conversation_id"),
            reply_to=data.get("reply_to"),
            metadata=data.get("metadata", {})
        )
        
        # Set the id and timestamp from the data
        message.id = data["id"]
        message.timestamp = data["timestamp"]
        
        return message
        
    def validate(self) -> bool:
        """
        Validate message structure and content based on message type
        
        Returns:
            True if message is valid, raises ValueError otherwise
        """
        # Basic validation - all messages need these fields
        if not self.sender_id or not self.receiver_id:
            raise ValueError("Message must have sender and receiver IDs")
            
        if not self.content:
            raise ValueError("Message must have content")
            
        # Message type specific validation
        if self.message_type == MessageType.QUERY:
            if not isinstance(self.content, dict) or "query" not in self.content:
                raise ValueError("QUERY message must have 'query' field in content")
                
        elif self.message_type == MessageType.INFORM:
            if not isinstance(self.content, dict) or "information" not in self.content:
                raise ValueError("INFORM message must have 'information' field in content")
                
        elif self.message_type == MessageType.REQUEST:
            if not isinstance(self.content, dict) or "action" not in self.content:
                raise ValueError("REQUEST message must have 'action' field in content")
                
        # More validations can be added for other message types
                
        return True


class Conversation:
    """
    Represents a conversation between agents
    
    A conversation is a sequence of related messages exchanged between agents
    as part of a specific workflow or task. This class manages the state and
    history of the conversation.
    """
    
    def __init__(
        self,
        id: Optional[str] = None,
        initiator_id: Optional[str] = None,
        responder_id: Optional[str] = None,
        topic: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ):
        """
        Initialize a new conversation
        
        Args:
            id: Unique identifier for the conversation
            initiator_id: ID of the agent initiating the conversation
            responder_id: ID of the agent responding to the conversation
            topic: Topic or purpose of the conversation
            metadata: Additional contextual information
        """
        self.id = id or str(uuid.uuid4())
        self.initiator_id = initiator_id
        self.responder_id = responder_id
        self.topic = topic or "general"
        self.state = ConversationState.INITIATED
        self.messages: List[AgentMessage] = []
        self.created_at = datetime.utcnow().isoformat()
        self.updated_at = self.created_at
        self.completed_at = None
        self.metadata = metadata or {}
        
    def add_message(self, message: AgentMessage) -> None:
        """
        Add a message to the conversation
        
        Args:
            message: The message to add
        """
        # Ensure message belongs to this conversation
        if message.conversation_id != self.id:
            raise ValueError(f"Message belongs to conversation {message.conversation_id}, not {self.id}")
            
        # Set conversation state to in progress when messages are added
        if self.state == ConversationState.INITIATED:
            self.state = ConversationState.IN_PROGRESS
            
        # Add message and update timestamp
        self.messages.append(message)
        self.updated_at = datetime.utcnow().isoformat()
        
    def complete(self, success: bool = True) -> None:
        """
        Mark the conversation as completed
        
        Args:
            success: Whether the conversation completed successfully
        """
        self.state = ConversationState.COMPLETED if success else ConversationState.FAILED
        self.completed_at = datetime.utcnow().isoformat()
        self.updated_at = self.completed_at
        
    def to_dict(self) -> Dict[str, Any]:
        """Convert conversation to dictionary representation"""
        return {
            "id": self.id,
            "initiator_id": self.initiator_id,
            "responder_id": self.responder_id,
            "topic": self.topic,
            "state": self.state.value,
            "messages": [m.to_dict() for m in self.messages],
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "completed_at": self.completed_at,
            "metadata": self.metadata
        }
        
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Conversation':
        """Create conversation from dictionary representation"""
        conversation = cls(
            id=data["id"],
            initiator_id=data.get("initiator_id"),
            responder_id=data.get("responder_id"),
            topic=data.get("topic", "general"),
            metadata=data.get("metadata", {})
        )
        
        # Set timestamps
        conversation.created_at = data["created_at"]
        conversation.updated_at = data["updated_at"]
        conversation.completed_at = data.get("completed_at")
        
        # Set state
        try:
            conversation.state = ConversationState(data["state"])
        except ValueError:
            conversation.state = ConversationState.IN_PROGRESS
            
        # Add messages
        for msg_data in data.get("messages", []):
            conversation.messages.append(AgentMessage.from_dict(msg_data))
            
        return conversation


class AgentCommunicationProtocol:
    """
    Implementation of Agent-to-Agent communication protocol
    
    This class provides the core protocol implementation for structured
    communication between specialized agents in the MCP architecture.
    It manages message passing, conversation tracking, and protocol enforcement.
    """
    
    def __init__(self, mcp_instance):
        """
        Initialize the communication protocol
        
        Args:
            mcp_instance: Reference to the MCP instance for agent lookup
        """
        self.mcp = mcp_instance
        self.conversations: Dict[str, Conversation] = {}
        self.message_handlers: Dict[str, Dict[MessageType, Callable]] = {}
        self.logger = logging.getLogger('agent_protocol')
        self.logger.info("Agent Communication Protocol initialized")
        
    def register_message_handler(
        self, 
        agent_id: str, 
        message_type: MessageType, 
        handler: Callable[[AgentMessage], Optional[AgentMessage]]
    ) -> None:
        """
        Register a message handler for a specific agent and message type
        
        Args:
            agent_id: ID of the agent registering the handler
            message_type: Type of message to handle
            handler: Function to call when a message of this type is received
        """
        if agent_id not in self.message_handlers:
            self.message_handlers[agent_id] = {}
            
        self.message_handlers[agent_id][message_type] = handler
        self.logger.info(f"Registered handler for {message_type.value} messages to {agent_id}")
        
    def create_conversation(
        self,
        initiator_id: str,
        responder_id: str,
        topic: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Create a new conversation between agents
        
        Args:
            initiator_id: ID of the agent initiating the conversation
            responder_id: ID of the agent responding to the conversation
            topic: Topic or purpose of the conversation
            metadata: Additional contextual information
            
        Returns:
            ID of the created conversation
        """
        conversation = Conversation(
            initiator_id=initiator_id,
            responder_id=responder_id,
            topic=topic,
            metadata=metadata
        )
        
        self.conversations[conversation.id] = conversation
        self.logger.info(f"Created conversation {conversation.id} between {initiator_id} and {responder_id} on topic: {topic}")
        
        return conversation.id
        
    def send_message(
        self,
        message_type: Union[MessageType, str],
        content: Any,
        sender_id: str,
        receiver_id: str,
        conversation_id: Optional[str] = None,
        reply_to: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        wait_for_response: bool = False,
        timeout: float = 30.0
    ) -> Union[str, AgentMessage]:
        """
        Send a message from one agent to another
        
        Args:
            message_type: Type of message to send
            content: Content of the message
            sender_id: ID of the sending agent
            receiver_id: ID of the receiving agent
            conversation_id: ID of the conversation this message belongs to
            reply_to: ID of the message this is a reply to
            metadata: Additional contextual information
            wait_for_response: Whether to wait for a response
            timeout: Timeout in seconds when waiting for response
            
        Returns:
            Message ID if wait_for_response is False, otherwise the response message
        """
        # Verify agents exist
        if sender_id not in self.mcp.agents:
            raise ValueError(f"Sending agent {sender_id} not registered with MCP")
            
        if receiver_id not in self.mcp.agents:
            raise ValueError(f"Receiving agent {receiver_id} not registered with MCP")
            
        # Create or get conversation
        if conversation_id and conversation_id in self.conversations:
            conversation = self.conversations[conversation_id]
        elif conversation_id:
            # Reference to non-existent conversation
            raise ValueError(f"Conversation {conversation_id} not found")
        else:
            # Create new conversation
            conversation_id = self.create_conversation(
                initiator_id=sender_id,
                responder_id=receiver_id,
                topic=metadata.get("topic", "general") if metadata else "general",
                metadata=metadata
            )
            conversation = self.conversations[conversation_id]
            
        # Create and validate message
        message = AgentMessage(
            message_type=message_type,
            content=content,
            sender_id=sender_id,
            receiver_id=receiver_id,
            conversation_id=conversation_id,
            reply_to=reply_to,
            metadata=metadata
        )
        
        try:
            message.validate()
        except ValueError as e:
            self.logger.error(f"Invalid message: {str(e)}")
            raise
            
        # Add message to conversation
        conversation.add_message(message)
        
        # Deliver message
        self._deliver_message(message)
        
        if wait_for_response:
            # Wait for response with timeout
            start_time = time.time()
            while time.time() - start_time < timeout:
                # Check for responses
                for msg in conversation.messages:
                    if msg.reply_to == message.id:
                        return msg
                        
                # Wait a bit before checking again
                time.sleep(0.1)
                
            # Timeout reached
            raise TimeoutError(f"No response received within {timeout} seconds")
            
        return message.id
        
    def _deliver_message(self, message: AgentMessage) -> None:
        """
        Deliver a message to its intended recipient
        
        Args:
            message: The message to deliver
        """
        # Get receiving agent
        receiver_id = message.receiver_id
        
        # Check if there's a registered handler
        if (receiver_id in self.message_handlers and 
            message.message_type in self.message_handlers[receiver_id]):
            
            # Call the handler
            handler = self.message_handlers[receiver_id][message.message_type]
            try:
                # Execute handler in a separate thread to avoid blocking
                threading.Thread(
                    target=self._execute_handler,
                    args=(handler, message)
                ).start()
                
                self.logger.info(f"Delivered {message.message_type.value} message from {message.sender_id} to {receiver_id}")
            except Exception as e:
                self.logger.error(f"Error in message handler: {str(e)}")
        else:
            # No specific handler, use default handling through MCP task system
            self._default_message_handling(message)
            
    def _execute_handler(self, handler: Callable, message: AgentMessage) -> None:
        """
        Execute a message handler safely
        
        Args:
            handler: The handler function to call
            message: The message to handle
        """
        try:
            # Call handler
            response = handler(message)
            
            # If handler returned a response message, deliver it
            if isinstance(response, AgentMessage):
                # Make sure conversation ID and reply_to are set
                if not response.conversation_id:
                    response.conversation_id = message.conversation_id
                if not response.reply_to:
                    response.reply_to = message.id
                    
                # Add to conversation and deliver
                if message.conversation_id in self.conversations:
                    self.conversations[message.conversation_id].add_message(response)
                self._deliver_message(response)
                
        except Exception as e:
            self.logger.error(f"Error in message handler: {str(e)}")
            
            # Send failure message back to sender
            try:
                failure_msg = AgentMessage(
                    message_type=MessageType.FAILURE,
                    content={"error": str(e)},
                    sender_id=message.receiver_id,
                    receiver_id=message.sender_id,
                    conversation_id=message.conversation_id,
                    reply_to=message.id
                )
                
                if message.conversation_id in self.conversations:
                    self.conversations[message.conversation_id].add_message(failure_msg)
                self._deliver_message(failure_msg)
            except Exception as e2:
                self.logger.error(f"Error sending failure message: {str(e2)}")
                
    def _default_message_handling(self, message: AgentMessage) -> None:
        """
        Default handling for messages without specific handlers
        
        Args:
            message: The message to handle
        """
        # Convert message to task for MCP system
        task_data = {
            "task_type": f"handle_{message.message_type.value}_message",
            "message": message.to_dict(),
            "context": {
                "conversation_id": message.conversation_id
            }
        }
        
        # Submit task to receiving agent
        try:
            self.mcp.submit_task(message.receiver_id, task_data)
            self.logger.info(f"Submitted message as task to {message.receiver_id}")
        except Exception as e:
            self.logger.error(f"Error submitting message as task: {str(e)}")
            
    def get_conversation(self, conversation_id: str) -> Optional[Conversation]:
        """
        Retrieve a conversation by ID
        
        Args:
            conversation_id: ID of the conversation to retrieve
            
        Returns:
            The conversation if found, None otherwise
        """
        return self.conversations.get(conversation_id)
        
    def get_agent_conversations(self, agent_id: str) -> List[Conversation]:
        """
        Get all conversations involving a specific agent
        
        Args:
            agent_id: ID of the agent
            
        Returns:
            List of conversations involving the agent
        """
        return [
            conv for conv in self.conversations.values()
            if conv.initiator_id == agent_id or conv.responder_id == agent_id
        ]