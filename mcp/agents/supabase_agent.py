"""
Supabase Agent Module

This module provides the SupabaseAgent class which handles Supabase-specific
operations, including database management, storage management, and authentication
integration for the MCP architecture.
"""

import logging
import os
import time
import json
from typing import Dict, List, Any, Optional, Union, Tuple
from datetime import datetime

from mcp.agents.base_agent import BaseAgent
from supabase_client import (
    get_supabase_client,
    execute_query,
    upload_file_to_storage,
    list_files_in_storage,
    download_file_from_storage,
    delete_file_from_storage
)

# Setup logging
logging.basicConfig(level=logging.INFO,
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

class SupabaseAgent(BaseAgent):
    """
    Agent for managing Supabase integration.
    
    Handles database operations, storage management, and authentication integration
    with Supabase for the GIS data management platform.
    """
    
    def __init__(self, agent_id: Optional[str] = None):
        """Initialize the Supabase agent"""
        super().__init__(agent_id)
        self.status = "initializing"
        
        # Define agent capabilities
        self.capabilities = [
            "supabase.database.query",
            "supabase.database.insert",
            "supabase.database.update",
            "supabase.database.delete",
            "supabase.storage.upload",
            "supabase.storage.download",
            "supabase.storage.list",
            "supabase.storage.delete",
            "supabase.auth.check",
            "supabase.status.check"
        ]
        
        # Bucket configurations
        self.buckets = {
            "documents": {
                "description": "Project documentation and reports",
                "public": False
            },
            "maps": {
                "description": "GIS map exports and shared maps",
                "public": True
            },
            "images": {
                "description": "Images and graphics for the application",
                "public": True
            },
            "exports": {
                "description": "Data exports and backups",
                "public": False
            }
        }
        
        # Cache for query results to reduce duplicate calls
        self.query_cache = {}
        self.cache_ttl = 60  # Cache lifetime in seconds
        
        # Check if Supabase environment is properly configured
        if self._check_supabase_config():
            self.client = get_supabase_client()
            if self.client:
                self.set_status("ready")
            else:
                self.set_status("error_connection")
        else:
            self.set_status("error_config")
    
    def process_task(self, task_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process a task assigned to this agent
        
        Args:
            task_data: Dictionary containing task parameters
                - task_type: Type of task to perform
                - parameters: Parameters for the task
                
        Returns:
            Dictionary with task results
        """
        task_type = task_data.get("task_type")
        parameters = task_data.get("parameters", {})
        
        # Check if this agent can handle the task
        if not self.can_process(task_type):
            return {
                "success": False,
                "error": f"Agent does not support task type: {task_type}",
                "supported_tasks": self.capabilities
            }
        
        try:
            # Database operations
            if task_type == "supabase.database.query":
                return self._handle_db_query(parameters)
            elif task_type == "supabase.database.insert":
                return self._handle_db_insert(parameters)
            elif task_type == "supabase.database.update":
                return self._handle_db_update(parameters)
            elif task_type == "supabase.database.delete":
                return self._handle_db_delete(parameters)
            
            # Storage operations
            elif task_type == "supabase.storage.upload":
                return self._handle_storage_upload(parameters)
            elif task_type == "supabase.storage.download":
                return self._handle_storage_download(parameters)
            elif task_type == "supabase.storage.list":
                return self._handle_storage_list(parameters)
            elif task_type == "supabase.storage.delete":
                return self._handle_storage_delete(parameters)
                
            # Authentication operations
            elif task_type == "supabase.auth.check":
                return self._handle_auth_check(parameters)
                
            # Status operations
            elif task_type == "supabase.status.check":
                return self._handle_status_check(parameters)
            
            # Unknown task type (should not happen due to can_process check)
            return {
                "success": False,
                "error": f"Unknown task type: {task_type}"
            }
        
        except Exception as e:
            self.logger.error(f"Error processing task {task_type}: {str(e)}")
            return {
                "success": False,
                "error": f"Task processing error: {str(e)}"
            }
    
    # Database Operations
    
    def _handle_db_query(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """
        Handle database query task
        
        Args:
            parameters:
                - table: Table to query
                - select: Fields to select
                - filters: Optional query filters
                - order: Optional ordering
                - limit: Optional limit
                - skip_cache: Optional flag to skip cache
                
        Returns:
            Query results
        """
        table = parameters.get("table")
        select = parameters.get("select", "*")
        filters = parameters.get("filters", {})
        order = parameters.get("order")
        limit = parameters.get("limit")
        skip_cache = parameters.get("skip_cache", False)
        
        if not table:
            return {
                "success": False,
                "error": "Missing required parameter: table"
            }
        
        # Check cache first (unless skip_cache is True)
        cache_key = f"{table}:{select}:{json.dumps(filters)}:{order}:{limit}"
        if not skip_cache and cache_key in self.query_cache:
            cache_entry = self.query_cache[cache_key]
            if time.time() - cache_entry["timestamp"] < self.cache_ttl:
                self.logger.info(f"Using cached result for query: {cache_key}")
                return {
                    "success": True,
                    "data": cache_entry["data"],
                    "from_cache": True,
                    "timestamp": cache_entry["timestamp"]
                }
        
        # Execute the query
        try:
            result = execute_query(table, select, filters, order, limit)
            
            if result is not None:
                # Cache the result
                self.query_cache[cache_key] = {
                    "data": result,
                    "timestamp": time.time()
                }
                
                return {
                    "success": True,
                    "data": result,
                    "count": len(result) if isinstance(result, list) else 1,
                    "from_cache": False
                }
            else:
                return {
                    "success": False,
                    "error": "Query returned no results or failed"
                }
        except Exception as e:
            self.logger.error(f"Database query error: {str(e)}")
            return {
                "success": False,
                "error": f"Database query error: {str(e)}"
            }
    
    def _handle_db_insert(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """
        Handle database insert task
        
        Args:
            parameters:
                - table: Table to insert into
                - data: Data to insert (single record or list of records)
                
        Returns:
            Insert results
        """
        table = parameters.get("table")
        data = parameters.get("data", {})
        
        if not table:
            return {
                "success": False,
                "error": "Missing required parameter: table"
            }
        
        if not data:
            return {
                "success": False,
                "error": "Missing required parameter: data"
            }
        
        # Get client
        client = get_supabase_client()
        if not client:
            return {
                "success": False,
                "error": "Failed to get Supabase client"
            }
        
        try:
            response = client.from_(table).insert(data).execute()
            
            if hasattr(response, 'data'):
                return {
                    "success": True,
                    "data": response.data,
                    "count": len(response.data) if isinstance(response.data, list) else 1
                }
            else:
                return {
                    "success": False,
                    "error": "Insert operation did not return expected response format"
                }
        except Exception as e:
            self.logger.error(f"Database insert error: {str(e)}")
            return {
                "success": False,
                "error": f"Database insert error: {str(e)}"
            }
    
    def _handle_db_update(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """
        Handle database update task
        
        Args:
            parameters:
                - table: Table to update
                - data: Update data
                - filters: Update filters
                
        Returns:
            Update results
        """
        table = parameters.get("table")
        data = parameters.get("data", {})
        filters = parameters.get("filters", {})
        
        if not table:
            return {
                "success": False,
                "error": "Missing required parameter: table"
            }
        
        if not data:
            return {
                "success": False,
                "error": "Missing required parameter: data"
            }
        
        # Get client
        client = get_supabase_client()
        if not client:
            return {
                "success": False,
                "error": "Failed to get Supabase client"
            }
        
        try:
            query = client.from_(table).update(data)
            
            # Apply filters
            for field, value in filters.items():
                if isinstance(value, dict):
                    # Handle operators like eq, gt, lt, etc.
                    for op, op_value in value.items():
                        if op == "eq":
                            query = query.eq(field, op_value)
                        elif op == "neq":
                            query = query.neq(field, op_value)
                        elif op == "gt":
                            query = query.gt(field, op_value)
                        elif op == "gte":
                            query = query.gte(field, op_value)
                        elif op == "lt":
                            query = query.lt(field, op_value)
                        elif op == "lte":
                            query = query.lte(field, op_value)
                        elif op == "in":
                            query = query.in_(field, op_value)
                        elif op == "is":
                            query = query.is_(field, op_value)
                else:
                    # Simple equality filter
                    query = query.eq(field, value)
            
            response = query.execute()
            
            if hasattr(response, 'data'):
                # Clear cache entries for this table
                for key in list(self.query_cache.keys()):
                    if key.startswith(f"{table}:"):
                        del self.query_cache[key]
                
                return {
                    "success": True,
                    "data": response.data,
                    "count": len(response.data) if isinstance(response.data, list) else 1
                }
            else:
                return {
                    "success": False,
                    "error": "Update operation did not return expected response format"
                }
        except Exception as e:
            self.logger.error(f"Database update error: {str(e)}")
            return {
                "success": False,
                "error": f"Database update error: {str(e)}"
            }
    
    def _handle_db_delete(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """
        Handle database delete task
        
        Args:
            parameters:
                - table: Table to delete from
                - filters: Delete filters
                
        Returns:
            Delete results
        """
        table = parameters.get("table")
        filters = parameters.get("filters", {})
        
        if not table:
            return {
                "success": False,
                "error": "Missing required parameter: table"
            }
        
        if not filters:
            return {
                "success": False,
                "error": "Missing required parameter: filters (for safety)"
            }
        
        # Get client
        client = get_supabase_client()
        if not client:
            return {
                "success": False,
                "error": "Failed to get Supabase client"
            }
        
        try:
            query = client.from_(table).delete()
            
            # Apply filters
            for field, value in filters.items():
                if isinstance(value, dict):
                    # Handle operators like eq, gt, lt, etc.
                    for op, op_value in value.items():
                        if op == "eq":
                            query = query.eq(field, op_value)
                        elif op == "neq":
                            query = query.neq(field, op_value)
                        elif op == "gt":
                            query = query.gt(field, op_value)
                        elif op == "gte":
                            query = query.gte(field, op_value)
                        elif op == "lt":
                            query = query.lt(field, op_value)
                        elif op == "lte":
                            query = query.lte(field, op_value)
                        elif op == "in":
                            query = query.in_(field, op_value)
                        elif op == "is":
                            query = query.is_(field, op_value)
                else:
                    # Simple equality filter
                    query = query.eq(field, value)
            
            response = query.execute()
            
            if hasattr(response, 'data'):
                # Clear cache entries for this table
                for key in list(self.query_cache.keys()):
                    if key.startswith(f"{table}:"):
                        del self.query_cache[key]
                
                return {
                    "success": True,
                    "data": response.data,
                    "count": len(response.data) if isinstance(response.data, list) else 1
                }
            else:
                return {
                    "success": False,
                    "error": "Delete operation did not return expected response format"
                }
        except Exception as e:
            self.logger.error(f"Database delete error: {str(e)}")
            return {
                "success": False,
                "error": f"Database delete error: {str(e)}"
            }
    
    # Storage Operations
    
    def _handle_storage_upload(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """
        Handle storage upload task
        
        Args:
            parameters:
                - bucket: Bucket to upload to
                - file_path: Path to file
                - storage_path: Path in storage
                - content_type: Optional content type
                
        Returns:
            Upload results
        """
        bucket = parameters.get("bucket")
        file_path = parameters.get("file_path")
        storage_path = parameters.get("storage_path")
        content_type = parameters.get("content_type")
        
        if not bucket:
            return {
                "success": False,
                "error": "Missing required parameter: bucket"
            }
        
        if not file_path:
            return {
                "success": False,
                "error": "Missing required parameter: file_path"
            }
        
        if not storage_path:
            # Use filename as storage path if not provided
            import os
            storage_path = os.path.basename(file_path)
        
        # Check if bucket exists
        if bucket not in self.buckets:
            return {
                "success": False,
                "error": f"Unknown bucket: {bucket}. Available buckets: {', '.join(self.buckets.keys())}"
            }
        
        try:
            public_url = upload_file_to_storage(file_path, bucket, storage_path, content_type)
            
            if public_url:
                return {
                    "success": True,
                    "public_url": public_url,
                    "bucket": bucket,
                    "storage_path": storage_path
                }
            else:
                return {
                    "success": False,
                    "error": "Failed to upload file to storage"
                }
        except Exception as e:
            self.logger.error(f"Storage upload error: {str(e)}")
            return {
                "success": False,
                "error": f"Storage upload error: {str(e)}"
            }
    
    def _handle_storage_download(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """
        Handle storage download task
        
        Args:
            parameters:
                - bucket: Bucket to download from
                - storage_path: Path in storage
                - destination_path: Path to save file
                
        Returns:
            Download results
        """
        bucket = parameters.get("bucket")
        storage_path = parameters.get("storage_path")
        destination_path = parameters.get("destination_path")
        
        if not bucket:
            return {
                "success": False,
                "error": "Missing required parameter: bucket"
            }
        
        if not storage_path:
            return {
                "success": False,
                "error": "Missing required parameter: storage_path"
            }
        
        if not destination_path:
            # Use current directory and filename if destination not specified
            import os
            destination_path = os.path.basename(storage_path)
        
        # Check if bucket exists
        if bucket not in self.buckets:
            return {
                "success": False,
                "error": f"Unknown bucket: {bucket}. Available buckets: {', '.join(self.buckets.keys())}"
            }
        
        try:
            result = download_file_from_storage(bucket, storage_path, destination_path)
            
            if result:
                return {
                    "success": True,
                    "destination_path": destination_path,
                    "bucket": bucket,
                    "storage_path": storage_path
                }
            else:
                return {
                    "success": False,
                    "error": "Failed to download file from storage"
                }
        except Exception as e:
            self.logger.error(f"Storage download error: {str(e)}")
            return {
                "success": False,
                "error": f"Storage download error: {str(e)}"
            }
    
    def _handle_storage_list(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """
        Handle storage list task
        
        Args:
            parameters:
                - bucket: Bucket to list
                - path: Optional path prefix
                
        Returns:
            List results
        """
        bucket = parameters.get("bucket")
        path = parameters.get("path", "")
        
        if not bucket:
            return {
                "success": False,
                "error": "Missing required parameter: bucket"
            }
        
        # Check if bucket exists
        if bucket not in self.buckets:
            return {
                "success": False,
                "error": f"Unknown bucket: {bucket}. Available buckets: {', '.join(self.buckets.keys())}"
            }
        
        try:
            files = list_files_in_storage(bucket, path)
            
            if files is not None:
                return {
                    "success": True,
                    "files": files,
                    "count": len(files),
                    "bucket": bucket,
                    "path": path
                }
            else:
                return {
                    "success": False,
                    "error": "Failed to list files in storage"
                }
        except Exception as e:
            self.logger.error(f"Storage list error: {str(e)}")
            return {
                "success": False,
                "error": f"Storage list error: {str(e)}"
            }
    
    def _handle_storage_delete(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """
        Handle storage delete task
        
        Args:
            parameters:
                - bucket: Bucket to delete from
                - paths: List of paths to delete
                
        Returns:
            Delete results
        """
        bucket = parameters.get("bucket")
        paths = parameters.get("paths", [])
        
        if not bucket:
            return {
                "success": False,
                "error": "Missing required parameter: bucket"
            }
        
        if not paths:
            return {
                "success": False,
                "error": "Missing required parameter: paths"
            }
        
        # Check if bucket exists
        if bucket not in self.buckets:
            return {
                "success": False,
                "error": f"Unknown bucket: {bucket}. Available buckets: {', '.join(self.buckets.keys())}"
            }
        
        try:
            success_count = 0
            failed_paths = []
            
            # Handle both single path and list of paths
            if isinstance(paths, str):
                paths = [paths]
            
            for path in paths:
                result = delete_file_from_storage(bucket, path)
                if result:
                    success_count += 1
                else:
                    failed_paths.append(path)
            
            return {
                "success": success_count > 0,
                "total": len(paths),
                "success_count": success_count,
                "failed_count": len(failed_paths),
                "failed_paths": failed_paths,
                "bucket": bucket
            }
        except Exception as e:
            self.logger.error(f"Storage delete error: {str(e)}")
            return {
                "success": False,
                "error": f"Storage delete error: {str(e)}"
            }
    
    # Authentication Operations
    
    def _handle_auth_check(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """
        Handle authentication check task
        
        Args:
            parameters: (unused)
                
        Returns:
            Auth status
        """
        # Get client
        client = get_supabase_client()
        if not client:
            return {
                "success": False,
                "error": "Failed to get Supabase client"
            }
        
        try:
            # Check auth session
            session = client.auth.get_session()
            
            if session:
                return {
                    "success": True,
                    "authenticated": True,
                    "session_info": {
                        "user_id": session.user.id if hasattr(session, 'user') else None,
                        "expires_at": session.expires_at if hasattr(session, 'expires_at') else None
                    }
                }
            else:
                return {
                    "success": True,
                    "authenticated": False
                }
        except Exception as e:
            self.logger.error(f"Auth check error: {str(e)}")
            return {
                "success": False,
                "error": f"Auth check error: {str(e)}"
            }
    
    # Status Operations
    
    def _handle_status_check(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """
        Check Supabase service status
        
        Args:
            parameters:
                - check_buckets: Whether to check storage buckets
                - check_auth: Whether to check authentication
                - check_database: Whether to check database
                
        Returns:
            Status check results
        """
        check_buckets = parameters.get("check_buckets", True)
        check_auth = parameters.get("check_auth", True)
        check_database = parameters.get("check_database", True)
        
        # Get client
        client = get_supabase_client()
        if not client:
            return {
                "success": False,
                "error": "Failed to get Supabase client",
                "status": "unavailable"
            }
        
        results = {
            "success": True,
            "status": "operational",
            "checks": {}
        }
        
        # Check database if requested
        if check_database:
            try:
                # Simple query to check database availability
                response = client.from_('information_schema.tables')
                                .select('table_name')
                                .limit(1)
                                .execute()
                
                results["checks"]["database"] = {
                    "status": "operational" if hasattr(response, 'data') else "issue",
                    "error": None
                }
            except Exception as e:
                self.logger.warning(f"Database check failed: {str(e)}")
                results["checks"]["database"] = {
                    "status": "issue",
                    "error": str(e)
                }
                results["status"] = "partial_outage"
        
        # Check authentication if requested
        if check_auth:
            try:
                client.auth.get_session()
                results["checks"]["auth"] = {
                    "status": "operational",
                    "error": None
                }
            except Exception as e:
                self.logger.warning(f"Auth check failed: {str(e)}")
                results["checks"]["auth"] = {
                    "status": "issue",
                    "error": str(e)
                }
                results["status"] = "partial_outage"
        
        # Check storage buckets if requested
        if check_buckets:
            bucket_results = {}
            all_buckets_ok = True
            
            for bucket in self.buckets.keys():
                try:
                    files = list_files_in_storage(bucket, limit=1)
                    bucket_results[bucket] = {
                        "status": "operational" if files is not None else "issue",
                        "error": None
                    }
                except Exception as e:
                    self.logger.warning(f"Bucket check failed for {bucket}: {str(e)}")
                    bucket_results[bucket] = {
                        "status": "issue",
                        "error": str(e)
                    }
                    all_buckets_ok = False
            
            results["checks"]["storage"] = {
                "status": "operational" if all_buckets_ok else "partial_outage",
                "buckets": bucket_results
            }
            
            if not all_buckets_ok and results["status"] != "unavailable":
                results["status"] = "partial_outage"
        
        # Overall status
        if not client:
            results["status"] = "unavailable"
        elif "partial_outage" in results["status"]:
            results["status"] = "partial_outage"
        
        return results
    
    def _check_supabase_config(self) -> bool:
        """
        Check if Supabase environment variables are set
        
        Returns:
            True if configuration is complete, False otherwise
        """
        required_vars = ["SUPABASE_URL", "SUPABASE_KEY", "SUPABASE_SERVICE_KEY"]
        missing_vars = []
        
        for var in required_vars:
            if not os.environ.get(var):
                missing_vars.append(var)
        
        if missing_vars:
            self.logger.error(f"Missing Supabase environment variables: {', '.join(missing_vars)}")
            return False
        
        return True
    
    # Agent-to-Agent Protocol Implementation
    
    def _handle_query(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """Handle query message from another agent"""
        content = message.get("content", {})
        query = content.get("query", "")
        context = content.get("context", {})
        
        if "database" in query.lower():
            # Handle database-related queries
            return {
                "message_type": "inform",
                "content": {
                    "information": self._get_database_info(),
                    "query": query
                },
                "sender_id": self.agent_id,
                "receiver_id": message.get("sender_id"),
                "conversation_id": message.get("conversation_id"),
                "reply_to": message.get("id")
            }
        elif "storage" in query.lower():
            # Handle storage-related queries
            return {
                "message_type": "inform",
                "content": {
                    "information": self._get_storage_info(),
                    "query": query
                },
                "sender_id": self.agent_id,
                "receiver_id": message.get("sender_id"),
                "conversation_id": message.get("conversation_id"),
                "reply_to": message.get("id")
            }
        elif "status" in query.lower():
            # Handle status-related queries
            status_info = self._handle_status_check({})
            return {
                "message_type": "inform",
                "content": {
                    "information": status_info,
                    "query": query
                },
                "sender_id": self.agent_id,
                "receiver_id": message.get("sender_id"),
                "conversation_id": message.get("conversation_id"),
                "reply_to": message.get("id")
            }
        else:
            # Default response
            return super()._handle_query(message)
    
    def _handle_request(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """Handle request message from another agent"""
        content = message.get("content", {})
        action = content.get("action", "")
        parameters = content.get("parameters", {})
        
        # Map common request actions to task types
        action_mapping = {
            "database.query": "supabase.database.query",
            "database.insert": "supabase.database.insert",
            "database.update": "supabase.database.update",
            "database.delete": "supabase.database.delete",
            "storage.upload": "supabase.storage.upload",
            "storage.download": "supabase.storage.download",
            "storage.list": "supabase.storage.list",
            "storage.delete": "supabase.storage.delete",
            "check_status": "supabase.status.check"
        }
        
        # Process the request if it maps to a supported task type
        if action in action_mapping:
            task_type = action_mapping[action]
            task_result = self.process_task({
                "task_type": task_type,
                "parameters": parameters
            })
            
            # Convert task result to agent message
            return {
                "message_type": "inform",
                "content": {
                    "information": task_result,
                    "action": action
                },
                "sender_id": self.agent_id,
                "receiver_id": message.get("sender_id"),
                "conversation_id": message.get("conversation_id"),
                "reply_to": message.get("id")
            }
        else:
            # Default response for unsupported actions
            return super()._handle_request(message)
    
    # Utility methods
    
    def _get_database_info(self) -> Dict[str, Any]:
        """Get information about the Supabase database"""
        info = {
            "tables": {}
        }
        
        client = get_supabase_client()
        if not client:
            return {"error": "Supabase client not available"}
        
        try:
            response = client.from_('information_schema.tables')
                            .select('table_name, table_schema')
                            .eq('table_schema', 'public')
                            .execute()
            
            if hasattr(response, 'data'):
                tables = response.data
                for table in tables:
                    table_name = table.get('table_name')
                    if table_name:
                        # Get column information for each table
                        col_response = client.from_('information_schema.columns')
                                            .select('column_name, data_type')
                                            .eq('table_schema', 'public')
                                            .eq('table_name', table_name)
                                            .execute()
                        
                        columns = {}
                        if hasattr(col_response, 'data'):
                            for col in col_response.data:
                                columns[col.get('column_name')] = col.get('data_type')
                                
                        info["tables"][table_name] = {
                            "columns": columns
                        }
        except Exception as e:
            info["error"] = str(e)
        
        return info
    
    def _get_storage_info(self) -> Dict[str, Any]:
        """Get information about Supabase storage buckets"""
        info = {
            "buckets": {}
        }
        
        for bucket_name, bucket_info in self.buckets.items():
            try:
                files = list_files_in_storage(bucket_name)
                info["buckets"][bucket_name] = {
                    "description": bucket_info["description"],
                    "public": bucket_info["public"],
                    "file_count": len(files) if files else 0,
                    "accessible": files is not None
                }
            except Exception as e:
                info["buckets"][bucket_name] = {
                    "description": bucket_info["description"],
                    "public": bucket_info["public"],
                    "accessible": False,
                    "error": str(e)
                }
        
        return info