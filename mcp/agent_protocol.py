"""
Agent-to-Agent (A2A) Communication Protocol

This module implements a standardized messaging protocol for agent-to-agent 
communication within the MCP system. It provides classes and utilities for
creating, validating, and processing messages between agents.

The protocol follows a JSON-based format with standardized fields to ensure
consistency and reliability in agent communication.
"""

import json
import uuid
import logging
import datetime
from enum import Enum
from typing import Dict, Any, Optional, List, Union

logger = logging.getLogger(__name__)

class MessageType(Enum):
    """Enumeration of standard message types"""
    COMMAND = "command"           # Direct instruction to perform an action
    EVENT = "event"               # Notification of something that has happened
    QUERY = "query"               # Request for information
    RESPONSE = "response"         # Reply to a query or command
    ERROR = "error"               # Error notification
    STATUS_UPDATE = "status_update"  # Agent status update
    POLICY_UPDATE = "policy_update"  # Update to agent policy/rules
    TASK_REQUEST = "task_request"    # Request for task execution
    DATA_EXCHANGE = "data_exchange"  # Exchange of data
    HELP_REQUEST = "help_request"    # Request for assistance

class MessagePriority(Enum):
    """Enumeration of message priorities"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

class Message:
    """
    Standard message class for agent-to-agent communication
    """
    
    def __init__(self, 
                 source_agent_id: str,
                 target_agent_id: str,
                 message_type: Union[MessageType, str],
                 payload: Dict[str, Any],
                 correlation_id: Optional[str] = None,
                 message_id: Optional[str] = None,
                 priority: Union[MessagePriority, str] = MessagePriority.MEDIUM,
                 ttl: Optional[int] = None,
                 metadata: Optional[Dict[str, Any]] = None):
        """
        Initialize a new message
        
        Args:
            source_agent_id: ID of the agent sending the message
            target_agent_id: ID of the intended recipient (or 'broadcast')
            message_type: Type of message (from MessageType enum or string)
            payload: Message payload (event-specific data)
            correlation_id: Optional ID to correlate related messages (default: None)
            message_id: Optional unique ID for this message (default: auto-generated UUID)
            priority: Message priority (from MessagePriority enum or string)
            ttl: Time-to-live in seconds (default: None)
            metadata: Optional additional metadata
        """
        self.message_id = message_id or str(uuid.uuid4())
        self.correlation_id = correlation_id
        self.source_agent_id = source_agent_id
        self.target_agent_id = target_agent_id
        
        # Handle message_type as either enum or string
        if isinstance(message_type, MessageType):
            self.message_type = message_type.value
        else:
            # Validate the string against allowed values
            try:
                self.message_type = MessageType(message_type).value
            except ValueError:
                # If not a valid enum value, use the string directly but log a warning
                self.message_type = message_type
                logger.warning(f"Using non-standard message type: {message_type}")
        
        self.timestamp = datetime.datetime.utcnow().isoformat() + "Z"
        self.payload = payload or {}
        
        # Handle priority as either enum or string
        if isinstance(priority, MessagePriority):
            self.priority = priority.value
        else:
            try:
                self.priority = MessagePriority(priority).value
            except ValueError:
                self.priority = MessagePriority.MEDIUM.value
                logger.warning(f"Invalid priority '{priority}', using default MEDIUM")
        
        # Initialize metadata dictionary
        self.metadata = metadata or {}
        
        # Add TTL to metadata if provided
        if ttl is not None:
            self.metadata["ttl"] = ttl
            
    def to_dict(self) -> Dict[str, Any]:
        """Convert message to dictionary representation"""
        result = {
            "messageId": self.message_id,
            "sourceAgentId": self.source_agent_id,
            "targetAgentId": self.target_agent_id,
            "messageType": self.message_type,
            "timestamp": self.timestamp,
            "payload": self.payload,
            "metadata": {
                "priority": self.priority,
                **self.metadata
            }
        }
        
        # Add correlation ID if present
        if self.correlation_id:
            result["correlationId"] = self.correlation_id
            
        return result
    
    def to_json(self) -> str:
        """Convert message to JSON string"""
        return json.dumps(self.to_dict())
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Message':
        """Create a Message object from a dictionary"""
        # Extract metadata fields
        metadata = data.get("metadata", {})
        priority = metadata.get("priority", MessagePriority.MEDIUM.value)
        ttl = metadata.get("ttl")
        
        # Remove specific fields from metadata to avoid duplication
        if "priority" in metadata:
            metadata_copy = metadata.copy()
            del metadata_copy["priority"]
            if "ttl" in metadata_copy:
                del metadata_copy["ttl"]
        else:
            metadata_copy = metadata
        
        # Create and return the Message object
        return cls(
            source_agent_id=data.get("sourceAgentId"),
            target_agent_id=data.get("targetAgentId"),
            message_type=data.get("messageType"),
            payload=data.get("payload", {}),
            correlation_id=data.get("correlationId"),
            message_id=data.get("messageId"),
            priority=priority,
            ttl=ttl,
            metadata=metadata_copy
        )
    
    @classmethod
    def from_json(cls, json_str: str) -> 'Message':
        """Create a Message object from a JSON string"""
        try:
            data = json.loads(json_str)
            return cls.from_dict(data)
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse message JSON: {e}")
            raise ValueError(f"Invalid message JSON: {e}")
        
    def is_expired(self) -> bool:
        """Check if the message has expired based on TTL"""
        ttl = self.metadata.get("ttl")
        if ttl is None:
            return False
        
        creation_time = datetime.datetime.fromisoformat(self.timestamp.rstrip("Z"))
        current_time = datetime.datetime.utcnow()
        age_seconds = (current_time - creation_time).total_seconds()
        
        return age_seconds > ttl
    
    def is_valid(self) -> bool:
        """Validate required fields and format"""
        # Check required fields
        if not self.source_agent_id or not self.target_agent_id:
            return False
        
        # Ensure payload is a dict
        if not isinstance(self.payload, dict):
            return False
            
        # Check if message has expired
        if self.is_expired():
            return False
            
        return True
    
    def __str__(self) -> str:
        """String representation of the message"""
        return (f"Message(id={self.message_id}, type={self.message_type}, "
                f"from={self.source_agent_id}, to={self.target_agent_id})")

class AgentCommunicationProtocol:
    """
    Handles communication protocol between agents.
    
    This class provides methods for sending, receiving, and processing
    messages between agents according to the standardized format.
    """
    
    def __init__(self, mcp_instance):
        """Initialize the protocol handler with reference to MCP"""
        self.mcp = mcp_instance
        self.handlers = {}
        self.logger = logging.getLogger(__name__)
        
    def register_handler(self, message_type: Union[MessageType, str], handler_func):
        """Register a handler function for a specific message type"""
        if isinstance(message_type, MessageType):
            self.handlers[message_type.value] = handler_func
        else:
            self.handlers[message_type] = handler_func
            
    def process_message(self, message: Message) -> Optional[Message]:
        """
        Process an incoming message and route it to the appropriate handler
        
        Returns a response message if applicable, or None
        """
        if not message.is_valid():
            self.logger.warning(f"Received invalid message: {message}")
            return self._create_error_response(
                message, 
                "INVALID_MESSAGE", 
                "Message validation failed"
            )
        
        # Find the appropriate handler based on message type
        handler = self.handlers.get(message.message_type)
        if handler:
            try:
                return handler(message)
            except Exception as e:
                self.logger.error(f"Error processing message {message.message_id}: {str(e)}")
                return self._create_error_response(
                    message, 
                    "PROCESSING_ERROR", 
                    f"Error processing message: {str(e)}"
                )
        else:
            self.logger.warning(f"No handler for message type: {message.message_type}")
            return self._create_error_response(
                message, 
                "UNSUPPORTED_TYPE", 
                f"No handler for message type: {message.message_type}"
            )
    
    def send_message(self, message: Message) -> bool:
        """Send a message to its target agent"""
        if not message.is_valid():
            self.logger.warning(f"Attempted to send invalid message: {message}")
            return False
        
        target = message.target_agent_id
        if target == "broadcast":
            # Handle broadcast messages
            self.logger.info(f"Broadcasting message: {message}")
            # Implementation depends on MCP's broadcast capability
            # For now, just log it
            return True
        else:
            # Send to specific agent
            self.logger.debug(f"Sending message to {target}: {message}")
            # Actual implementation depends on how agents receive messages
            # For now, just log it
            return True
    
    def _create_error_response(self, original_message: Message, 
                              error_code: str, error_message: str) -> Message:
        """Create an error response message"""
        return Message(
            source_agent_id="protocol_handler",
            target_agent_id=original_message.source_agent_id,
            message_type=MessageType.ERROR,
            correlation_id=original_message.message_id,
            payload={
                "errorCode": error_code,
                "errorMessage": error_message,
                "originalMessageId": original_message.message_id
            }
        )

# Helper functions for common message creation
def create_command(source: str, target: str, command_name: str, 
                  parameters: Dict[str, Any], correlation_id: Optional[str] = None,
                  priority: MessagePriority = MessagePriority.MEDIUM) -> Message:
    """Create a command message"""
    return Message(
        source_agent_id=source,
        target_agent_id=target,
        message_type=MessageType.COMMAND,
        correlation_id=correlation_id,
        priority=priority,
        payload={
            "commandName": command_name,
            "parameters": parameters
        }
    )

def create_event(source: str, target: str, event_name: str, 
                event_data: Dict[str, Any], correlation_id: Optional[str] = None) -> Message:
    """Create an event message"""
    return Message(
        source_agent_id=source,
        target_agent_id=target,
        message_type=MessageType.EVENT,
        correlation_id=correlation_id,
        payload={
            "eventName": event_name,
            "eventData": event_data
        }
    )

def create_response(source: str, target: str, original_message_id: str,
                   status: str, result: Any) -> Message:
    """Create a response message"""
    return Message(
        source_agent_id=source,
        target_agent_id=target,
        message_type=MessageType.RESPONSE,
        correlation_id=original_message_id,
        payload={
            "status": status,
            "result": result
        }
    )

def create_help_request(source: str, target: str, issue_description: str,
                       context_data: Dict[str, Any]) -> Message:
    """Create a help request message"""
    return Message(
        source_agent_id=source,
        target_agent_id=target,
        message_type=MessageType.HELP_REQUEST,
        priority=MessagePriority.HIGH,
        payload={
            "issueDescription": issue_description,
            "contextData": context_data
        }
    )