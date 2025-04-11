"""
MCP Message Broker

This module implements a simple message broker for handling agent-to-agent communication.
It acts as a centralized message bus that routes messages between agents based on the
standardized message format defined in agent_protocol.py.
"""

import logging
import threading
import queue
import time
from typing import Dict, List, Callable, Any, Optional, Set
from collections import defaultdict
import uuid

from mcp.agent_protocol import Message, MessageType, MessagePriority

logger = logging.getLogger(__name__)

class MessageBroker:
    """
    Message broker for agent-to-agent communication.
    
    This broker implements a simple publish-subscribe model for message routing.
    Agents can subscribe to topics or direct messages, and the broker routes
    messages accordingly.
    """
    
    def __init__(self):
        """Initialize the message broker"""
        self.topics = defaultdict(set)  # Mapping of topic to set of subscribers
        self.subscribers = {}  # Mapping of agent_id to subscriber info
        self.queues = {}  # Mapping of agent_id to message queue
        self.running = False
        self.worker_thread = None
        self.lock = threading.RLock()
        
    def start(self):
        """Start the message broker"""
        with self.lock:
            if self.running:
                logger.warning("Message broker already running")
                return
                
            self.running = True
            self.worker_thread = threading.Thread(target=self._worker, daemon=True)
            self.worker_thread.start()
            logger.info("Message broker started")
    
    def stop(self):
        """Stop the message broker"""
        with self.lock:
            if not self.running:
                logger.warning("Message broker not running")
                return
                
            self.running = False
            if self.worker_thread:
                self.worker_thread.join(timeout=5.0)
                self.worker_thread = None
            logger.info("Message broker stopped")
    
    def subscribe(self, agent_id: str, callback: Optional[Callable[[Message], None]] = None) -> queue.Queue:
        """
        Subscribe an agent to receive messages
        
        Args:
            agent_id: The ID of the agent subscribing
            callback: Optional callback function to be called when a message is received.
                     If None, messages will be placed in a queue that the agent can poll.
                     
        Returns:
            A queue for the agent to poll for messages (if callback is None)
        """
        with self.lock:
            # Create a message queue for this agent
            msg_queue = queue.Queue()
            self.queues[agent_id] = msg_queue
            
            # Store subscriber info
            self.subscribers[agent_id] = {
                'callback': callback,
                'queue': msg_queue,
                'topics': set()
            }
            
            # Auto-subscribe to direct messages
            self.topics[agent_id].add(agent_id)
            
            logger.info(f"Agent {agent_id} subscribed to message broker")
            return msg_queue
    
    def unsubscribe(self, agent_id: str):
        """Unsubscribe an agent from the broker"""
        with self.lock:
            if agent_id not in self.subscribers:
                logger.warning(f"Agent {agent_id} not subscribed")
                return
                
            # Remove from topics
            for topic, subscribers in self.topics.items():
                if agent_id in subscribers:
                    subscribers.remove(agent_id)
            
            # Remove subscriber info
            del self.subscribers[agent_id]
            
            # Remove queue
            if agent_id in self.queues:
                del self.queues[agent_id]
                
            logger.info(f"Agent {agent_id} unsubscribed from message broker")
    
    def subscribe_to_topic(self, agent_id: str, topic: str):
        """Subscribe an agent to a specific topic"""
        with self.lock:
            if agent_id not in self.subscribers:
                logger.warning(f"Agent {agent_id} not subscribed to broker")
                return
                
            self.topics[topic].add(agent_id)
            self.subscribers[agent_id]['topics'].add(topic)
            logger.info(f"Agent {agent_id} subscribed to topic {topic}")
    
    def unsubscribe_from_topic(self, agent_id: str, topic: str):
        """Unsubscribe an agent from a specific topic"""
        with self.lock:
            if agent_id not in self.subscribers:
                logger.warning(f"Agent {agent_id} not subscribed to broker")
                return
                
            if topic in self.topics and agent_id in self.topics[topic]:
                self.topics[topic].remove(agent_id)
                
            if topic in self.subscribers[agent_id]['topics']:
                self.subscribers[agent_id]['topics'].remove(topic)
                
            logger.info(f"Agent {agent_id} unsubscribed from topic {topic}")
    
    def publish(self, message: Message) -> bool:
        """
        Publish a message to the broker
        
        Args:
            message: The message to publish
            
        Returns:
            True if the message was successfully published, False otherwise
        """
        if not message.is_valid():
            logger.warning(f"Attempted to publish invalid message: {message}")
            return False
            
        with self.lock:
            # Get target subscribers
            target = message.target_agent_id
            subscribers = set()
            
            if target == "broadcast":
                # Message for all subscribers
                for agent_id in self.subscribers:
                    subscribers.add(agent_id)
            elif target in self.topics:
                # Message for subscribers of a specific topic
                subscribers = self.topics[target].copy()
            else:
                # Direct message to a specific agent
                if target in self.subscribers:
                    subscribers.add(target)
                else:
                    logger.warning(f"No subscriber for target {target}")
                    return False
            
            # Deliver message to subscribers
            for agent_id in subscribers:
                if agent_id == message.source_agent_id:
                    # Skip sending message back to sender
                    continue
                    
                subscriber = self.subscribers.get(agent_id)
                if not subscriber:
                    continue
                    
                # Use callback if available, otherwise queue
                if subscriber['callback']:
                    try:
                        subscriber['callback'](message)
                    except Exception as e:
                        logger.error(f"Error in subscriber callback for {agent_id}: {str(e)}")
                else:
                    subscriber['queue'].put(message)
            
            logger.debug(f"Published message {message.message_id} to {len(subscribers)} subscribers")
            return True
    
    def _worker(self):
        """Worker thread for the message broker"""
        logger.info("Message broker worker thread started")
        
        while self.running:
            # This thread could handle delayed messages, cleanup, etc.
            # For now, it just keeps the broker alive
            time.sleep(1.0)
            
        logger.info("Message broker worker thread stopped")
    
    def get_topic_subscribers(self, topic: str) -> Set[str]:
        """Get the set of subscribers for a specific topic"""
        with self.lock:
            return self.topics.get(topic, set()).copy()
    
    def get_agent_topics(self, agent_id: str) -> Set[str]:
        """Get the set of topics an agent is subscribed to"""
        with self.lock:
            if agent_id not in self.subscribers:
                return set()
            return self.subscribers[agent_id]['topics'].copy()
    
    def get_stats(self) -> Dict[str, Any]:
        """Get statistics about the message broker"""
        with self.lock:
            stats = {
                'running': self.running,
                'num_subscribers': len(self.subscribers),
                'num_topics': len(self.topics),
                'subscribers': {},
                'topics': {}
            }
            
            # Add subscriber stats
            for agent_id, info in self.subscribers.items():
                stats['subscribers'][agent_id] = {
                    'queue_size': info['queue'].qsize(),
                    'has_callback': bool(info['callback']),
                    'num_topics': len(info['topics'])
                }
                
            # Add topic stats
            for topic, subscribers in self.topics.items():
                stats['topics'][topic] = {
                    'num_subscribers': len(subscribers),
                    'subscribers': list(subscribers)
                }
                
            return stats