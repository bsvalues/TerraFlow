#!/usr/bin/env python
"""
Secrets Manager for GeoAssessmentPro

This module provides secure secrets management capabilities, including
encrypted storage, environment-specific secrets, and integration with
external secrets management services.
"""

import os
import sys
import json
import base64
import logging
import getpass
import threading
import tempfile
from typing import Dict, Any, Optional, Union, List
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

# Configure logging
logging.basicConfig(level=logging.INFO, 
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Constants
DEFAULT_ENV = "development"
SECRET_FILE = "secrets.enc"
CONFIG_FILE = "secrets_config.json"
SALT_FILE = "salt.bin"
KEY_ITERATIONS = 100000
SECRET_CACHE_TTL = 600  # 10 minutes

class SecretsManager:
    """Secrets manager for secure storage and retrieval of secrets"""
    
    def __init__(self, 
                secret_file: str = SECRET_FILE,
                config_file: str = CONFIG_FILE,
                salt_file: str = SALT_FILE,
                env: Optional[str] = None,
                master_password: Optional[str] = None):
        """
        Initialize secrets manager
        
        Args:
            secret_file: Path to encrypted secrets file
            config_file: Path to secrets configuration file
            salt_file: Path to salt file for key derivation
            env: Environment (development, training, production)
            master_password: Master password for encryption/decryption
        """
        self.secret_file = secret_file
        self.config_file = config_file
        self.salt_file = salt_file
        self.env = env or os.environ.get("ENV_MODE", DEFAULT_ENV)
        self.master_password = master_password
        self.cipher = None
        self.lock = threading.Lock()
        self.secrets_cache = {}
        self.last_cache_time = 0
        
        # Create config directories if they don't exist
        config_dir = os.path.dirname(os.path.abspath(self.config_file))
        os.makedirs(config_dir, exist_ok=True)
        
        # Initialize cipher
        self._initialize_cipher()
    
    def _initialize_cipher(self) -> None:
        """Initialize cipher for encryption/decryption"""
        try:
            # Get master password
            if not self.master_password:
                # Try to get from environment variable
                self.master_password = os.environ.get("SECRETS_MASTER_PASSWORD")
                
                # If not in environment, prompt user (only in interactive mode)
                if not self.master_password and sys.stdin.isatty():
                    self.master_password = getpass.getpass("Enter master password for secrets: ")
                
                # If still no password, generate a random one and save to a file
                if not self.master_password:
                    logger.warning("No master password provided, generating a random one")
                    import secrets
                    self.master_password = secrets.token_hex(16)
                    
                    # Save the password to a file in the user's home directory
                    pwd_file = os.path.expanduser("~/.geoassessmentpro_secrets_pwd")
                    with open(pwd_file, "w") as f:
                        f.write(self.master_password)
                    
                    logger.warning(f"Random master password saved to {pwd_file}")
            
            # Get or create salt
            if os.path.exists(self.salt_file):
                with open(self.salt_file, "rb") as f:
                    salt = f.read()
            else:
                import os
                salt = os.urandom(16)
                with open(self.salt_file, "wb") as f:
                    f.write(salt)
            
            # Derive key from password
            kdf = PBKDF2HMAC(
                algorithm=hashes.SHA256(),
                length=32,
                salt=salt,
                iterations=KEY_ITERATIONS
            )
            key = base64.urlsafe_b64encode(kdf.derive(self.master_password.encode()))
            
            # Create cipher
            self.cipher = Fernet(key)
            
            logger.info("Initialized secrets manager cipher")
        except Exception as e:
            logger.error(f"Error initializing cipher: {str(e)}")
    
    def _load_secrets(self) -> Dict[str, Dict[str, Any]]:
        """
        Load secrets from file
        
        Returns:
            Dict with secrets for all environments
        """
        # Check if cached secrets are still valid
        current_time = time.time()
        if current_time - self.last_cache_time < SECRET_CACHE_TTL and self.secrets_cache:
            return self.secrets_cache
        
        secrets = {}
        try:
            # Load encrypted secrets
            if os.path.exists(self.secret_file):
                with open(self.secret_file, "rb") as f:
                    encrypted_data = f.read()
                
                # Decrypt secrets
                if self.cipher:
                    decrypted_data = self.cipher.decrypt(encrypted_data)
                    secrets = json.loads(decrypted_data.decode())
            
            # Update cache
            self.secrets_cache = secrets
            self.last_cache_time = current_time
            
            return secrets
        except Exception as e:
            logger.error(f"Error loading secrets: {str(e)}")
            return {}
    
    def _save_secrets(self, secrets: Dict[str, Dict[str, Any]]) -> bool:
        """
        Save secrets to file
        
        Args:
            secrets: Dict with secrets for all environments
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Encrypt secrets
            if self.cipher:
                encrypted_data = self.cipher.encrypt(json.dumps(secrets).encode())
                
                # Save to file
                with open(self.secret_file, "wb") as f:
                    f.write(encrypted_data)
                
                # Update cache
                self.secrets_cache = secrets
                self.last_cache_time = time.time()
                
                return True
            else:
                logger.error("Cipher not initialized")
                return False
        except Exception as e:
            logger.error(f"Error saving secrets: {str(e)}")
            return False
    
    def set_secret(self, name: str, value: str, env: Optional[str] = None) -> bool:
        """
        Set a secret value
        
        Args:
            name: Secret name
            value: Secret value
            env: Environment (development, training, production)
            
        Returns:
            True if successful, False otherwise
        """
        env = env or self.env
        
        with self.lock:
            # Load existing secrets
            secrets = self._load_secrets()
            
            # Create environment if it doesn't exist
            if env not in secrets:
                secrets[env] = {}
            
            # Set secret
            secrets[env][name] = value
            
            # Save secrets
            return self._save_secrets(secrets)
    
    def get_secret(self, name: str, env: Optional[str] = None, 
                  default: Optional[str] = None) -> Optional[str]:
        """
        Get a secret value
        
        Args:
            name: Secret name
            env: Environment (development, training, production)
            default: Default value if secret not found
            
        Returns:
            Secret value or default if not found
        """
        env = env or self.env
        
        with self.lock:
            # Load secrets
            secrets = self._load_secrets()
            
            # Get secret
            if env in secrets and name in secrets[env]:
                return secrets[env][name]
            
            # Check if secret exists in .env file
            env_var_name = f"{name.upper()}"
            if os.environ.get(env_var_name):
                return os.environ.get(env_var_name)
            
            # Try environment-specific env var
            env_specific_var = f"{name.upper()}_{env.upper()}"
            if os.environ.get(env_specific_var):
                return os.environ.get(env_specific_var)
            
            return default
    
    def delete_secret(self, name: str, env: Optional[str] = None) -> bool:
        """
        Delete a secret
        
        Args:
            name: Secret name
            env: Environment (development, training, production)
            
        Returns:
            True if successful, False otherwise
        """
        env = env or self.env
        
        with self.lock:
            # Load secrets
            secrets = self._load_secrets()
            
            # Delete secret
            if env in secrets and name in secrets[env]:
                del secrets[env][name]
                
                # Save secrets
                return self._save_secrets(secrets)
            
            return False
    
    def list_secrets(self, env: Optional[str] = None) -> List[str]:
        """
        List all secrets for an environment
        
        Args:
            env: Environment (development, training, production)
            
        Returns:
            List of secret names
        """
        env = env or self.env
        
        with self.lock:
            # Load secrets
            secrets = self._load_secrets()
            
            # Get secrets for environment
            if env in secrets:
                return list(secrets[env].keys())
            
            return []
    
    def rotate_master_password(self, new_password: str) -> bool:
        """
        Rotate master password
        
        Args:
            new_password: New master password
            
        Returns:
            True if successful, False otherwise
        """
        with self.lock:
            # Load secrets with old password
            old_secrets = self._load_secrets()
            
            # Change password
            old_master_password = self.master_password
            self.master_password = new_password
            
            # Reinitialize cipher with new password
            self._initialize_cipher()
            
            # Save secrets with new password
            result = self._save_secrets(old_secrets)
            
            # If failed, revert to old password
            if not result:
                self.master_password = old_master_password
                self._initialize_cipher()
            
            return result
    
    def export_secrets(self, filepath: str, env: Optional[str] = None, 
                      format: str = "json") -> bool:
        """
        Export secrets to a file
        
        Args:
            filepath: Path to export file
            env: Environment to export (development, training, production)
            format: Export format (json, env)
            
        Returns:
            True if successful, False otherwise
        """
        env = env or self.env
        
        with self.lock:
            # Load secrets
            secrets = self._load_secrets()
            
            # Get secrets for environment
            env_secrets = secrets.get(env, {})
            
            try:
                # Export based on format
                if format == "json":
                    with open(filepath, "w") as f:
                        json.dump(env_secrets, f, indent=2)
                elif format == "env":
                    with open(filepath, "w") as f:
                        for name, value in env_secrets.items():
                            f.write(f"{name.upper()}={value}\n")
                else:
                    logger.error(f"Unsupported export format: {format}")
                    return False
                
                logger.info(f"Exported secrets for {env} environment to {filepath}")
                return True
            except Exception as e:
                logger.error(f"Error exporting secrets: {str(e)}")
                return False
    
    def import_secrets(self, filepath: str, env: Optional[str] = None, 
                      format: str = "json", overwrite: bool = False) -> bool:
        """
        Import secrets from a file
        
        Args:
            filepath: Path to import file
            env: Environment to import into (development, training, production)
            format: Import format (json, env)
            overwrite: Whether to overwrite existing secrets
            
        Returns:
            True if successful, False otherwise
        """
        env = env or self.env
        
        with self.lock:
            # Load existing secrets
            secrets = self._load_secrets()
            
            # Create environment if it doesn't exist
            if env not in secrets:
                secrets[env] = {}
            
            try:
                # Import based on format
                if format == "json":
                    with open(filepath, "r") as f:
                        imported_secrets = json.load(f)
                elif format == "env":
                    imported_secrets = {}
                    with open(filepath, "r") as f:
                        for line in f:
                            line = line.strip()
                            if line and not line.startswith("#"):
                                key, value = line.split("=", 1)
                                imported_secrets[key.lower()] = value
                else:
                    logger.error(f"Unsupported import format: {format}")
                    return False
                
                # Add imported secrets
                for name, value in imported_secrets.items():
                    if name not in secrets[env] or overwrite:
                        secrets[env][name] = value
                
                # Save secrets
                result = self._save_secrets(secrets)
                
                if result:
                    logger.info(f"Imported secrets for {env} environment from {filepath}")
                
                return result
            except Exception as e:
                logger.error(f"Error importing secrets: {str(e)}")
                return False
    
    def sync_with_env_file(self, env_file: str, env: Optional[str] = None,
                          prefix: Optional[str] = None, overwrite: bool = False) -> bool:
        """
        Sync secrets with an environment file
        
        Args:
            env_file: Path to environment file
            env: Environment to sync with (development, training, production)
            prefix: Only sync variables with this prefix
            overwrite: Whether to overwrite existing secrets
            
        Returns:
            True if successful, False otherwise
        """
        env = env or self.env
        
        # Load env file
        try:
            env_vars = {}
            with open(env_file, "r") as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith("#"):
                        try:
                            key, value = line.split("=", 1)
                            if not prefix or key.startswith(prefix):
                                # Remove prefix if specified
                                if prefix:
                                    key = key[len(prefix):]
                                env_vars[key.lower()] = value
                        except ValueError:
                            # Skip lines that don't have a key-value pair
                            pass
            
            # Sync secrets
            with self.lock:
                # Load existing secrets
                secrets = self._load_secrets()
                
                # Create environment if it doesn't exist
                if env not in secrets:
                    secrets[env] = {}
                
                # Add env vars as secrets
                for name, value in env_vars.items():
                    if name not in secrets[env] or overwrite:
                        secrets[env][name] = value
                
                # Save secrets
                result = self._save_secrets(secrets)
                
                if result:
                    logger.info(f"Synced secrets for {env} environment from {env_file}")
                
                return result
        except Exception as e:
            logger.error(f"Error syncing secrets: {str(e)}")
            return False
    
    def get_database_url(self, env: Optional[str] = None) -> Optional[str]:
        """
        Get database URL for an environment
        
        Args:
            env: Environment (development, training, production)
            
        Returns:
            Database URL or None if not found
        """
        env = env or self.env
        
        # Try to get from secrets
        db_url = self.get_secret("database_url", env)
        
        # If not found, try environment-specific database URL
        if not db_url and env != "development":
            db_url = self.get_secret(f"database_url_{env}", env)
        
        # If still not found, try environment variables
        if not db_url:
            db_url = os.environ.get("DATABASE_URL")
        
        # If still not found, try environment-specific environment variable
        if not db_url and env != "development":
            db_url = os.environ.get(f"DATABASE_URL_{env.upper()}")
        
        return db_url
    
    def get_supabase_credentials(self, env: Optional[str] = None) -> Dict[str, str]:
        """
        Get Supabase credentials for an environment
        
        Args:
            env: Environment (development, training, production)
            
        Returns:
            Dict with Supabase credentials
        """
        env = env or self.env
        
        credentials = {}
        
        # Get URL
        supabase_url = self.get_secret("supabase_url", env)
        if not supabase_url and env != "development":
            supabase_url = self.get_secret(f"supabase_url_{env}", env)
        if not supabase_url:
            supabase_url = os.environ.get("SUPABASE_URL")
        if not supabase_url and env != "development":
            supabase_url = os.environ.get(f"SUPABASE_URL_{env.upper()}")
        credentials["url"] = supabase_url
        
        # Get key
        supabase_key = self.get_secret("supabase_key", env)
        if not supabase_key and env != "development":
            supabase_key = self.get_secret(f"supabase_key_{env}", env)
        if not supabase_key:
            supabase_key = os.environ.get("SUPABASE_KEY")
        if not supabase_key and env != "development":
            supabase_key = os.environ.get(f"SUPABASE_KEY_{env.upper()}")
        credentials["key"] = supabase_key
        
        # Get service key
        service_key = self.get_secret("supabase_service_key", env)
        if not service_key and env != "development":
            service_key = self.get_secret(f"supabase_service_key_{env}", env)
        if not service_key:
            service_key = os.environ.get("SUPABASE_SERVICE_KEY")
        if not service_key and env != "development":
            service_key = os.environ.get(f"SUPABASE_SERVICE_KEY_{env.upper()}")
        credentials["service_key"] = service_key
        
        return credentials
    
    def get_jwt_secret(self, env: Optional[str] = None) -> Optional[str]:
        """
        Get JWT secret for an environment
        
        Args:
            env: Environment (development, training, production)
            
        Returns:
            JWT secret or None if not found
        """
        env = env or self.env
        
        # Try to get from secrets
        jwt_secret = self.get_secret("jwt_secret", env)
        
        # If not found, try environment variable
        if not jwt_secret:
            jwt_secret = os.environ.get("JWT_SECRET")
        
        # If still not found, generate a random one
        if not jwt_secret and env == "development":
            import secrets
            jwt_secret = secrets.token_hex(32)
            self.set_secret("jwt_secret", jwt_secret, env)
            logger.warning(f"Generated random JWT secret for {env} environment")
        
        return jwt_secret

# Create global secrets manager
secrets_manager = SecretsManager()

def initialize_secrets():
    """Initialize secrets if they don't exist"""
    # Just access the global instance to make sure it's initialized
    global secrets_manager
    return secrets_manager

def get_secret(name: str, env: Optional[str] = None, 
             default: Optional[str] = None) -> Optional[str]:
    """
    Get a secret value
    
    Args:
        name: Secret name
        env: Environment (development, training, production)
        default: Default value if secret not found
        
    Returns:
        Secret value or default if not found
    """
    return secrets_manager.get_secret(name, env, default)

def set_secret(name: str, value: str, env: Optional[str] = None) -> bool:
    """
    Set a secret value
    
    Args:
        name: Secret name
        value: Secret value
        env: Environment (development, training, production)
        
    Returns:
        True if successful, False otherwise
    """
    return secrets_manager.set_secret(name, value, env)

def delete_secret(name: str, env: Optional[str] = None) -> bool:
    """
    Delete a secret
    
    Args:
        name: Secret name
        env: Environment (development, training, production)
        
    Returns:
        True if successful, False otherwise
    """
    return secrets_manager.delete_secret(name, env)

def list_secrets(env: Optional[str] = None) -> List[str]:
    """
    List all secrets for an environment
    
    Args:
        env: Environment (development, training, production)
        
    Returns:
        List of secret names
    """
    return secrets_manager.list_secrets(env)

def get_database_url(env: Optional[str] = None) -> Optional[str]:
    """
    Get database URL for an environment
    
    Args:
        env: Environment (development, training, production)
        
    Returns:
        Database URL or None if not found
    """
    return secrets_manager.get_database_url(env)

def get_supabase_credentials(env: Optional[str] = None) -> Dict[str, str]:
    """
    Get Supabase credentials for an environment
    
    Args:
        env: Environment (development, training, production)
        
    Returns:
        Dict with Supabase credentials
    """
    return secrets_manager.get_supabase_credentials(env)

def get_jwt_secret(env: Optional[str] = None) -> Optional[str]:
    """
    Get JWT secret for an environment
    
    Args:
        env: Environment (development, training, production)
        
    Returns:
        JWT secret or None if not found
    """
    return secrets_manager.get_jwt_secret(env)

def sync_with_env_file(env_file: str, env: Optional[str] = None,
                      prefix: Optional[str] = None, overwrite: bool = False) -> bool:
    """
    Sync secrets with an environment file
    
    Args:
        env_file: Path to environment file
        env: Environment to sync with (development, training, production)
        prefix: Only sync variables with this prefix
        overwrite: Whether to overwrite existing secrets
        
    Returns:
        True if successful, False otherwise
    """
    return secrets_manager.sync_with_env_file(env_file, env, prefix, overwrite)

if __name__ == "__main__":
    import time
    import argparse
    
    parser = argparse.ArgumentParser(description="GeoAssessmentPro Secrets Manager")
    subparsers = parser.add_subparsers(dest="command", help="Command to run")
    
    # Set secret command
    set_parser = subparsers.add_parser("set", help="Set a secret")
    set_parser.add_argument("name", help="Secret name")
    set_parser.add_argument("value", help="Secret value")
    set_parser.add_argument("--env", help="Environment (development, training, production)")
    
    # Get secret command
    get_parser = subparsers.add_parser("get", help="Get a secret")
    get_parser.add_argument("name", help="Secret name")
    get_parser.add_argument("--env", help="Environment (development, training, production)")
    
    # Delete secret command
    delete_parser = subparsers.add_parser("delete", help="Delete a secret")
    delete_parser.add_argument("name", help="Secret name")
    delete_parser.add_argument("--env", help="Environment (development, training, production)")
    
    # List secrets command
    list_parser = subparsers.add_parser("list", help="List secrets")
    list_parser.add_argument("--env", help="Environment (development, training, production)")
    
    # Export secrets command
    export_parser = subparsers.add_parser("export", help="Export secrets")
    export_parser.add_argument("filepath", help="Path to export file")
    export_parser.add_argument("--env", help="Environment to export (development, training, production)")
    export_parser.add_argument("--format", choices=["json", "env"], default="json", help="Export format")
    
    # Import secrets command
    import_parser = subparsers.add_parser("import", help="Import secrets")
    import_parser.add_argument("filepath", help="Path to import file")
    import_parser.add_argument("--env", help="Environment to import into (development, training, production)")
    import_parser.add_argument("--format", choices=["json", "env"], default="json", help="Import format")
    import_parser.add_argument("--overwrite", action="store_true", help="Overwrite existing secrets")
    
    # Sync with env file command
    sync_parser = subparsers.add_parser("sync", help="Sync secrets with an environment file")
    sync_parser.add_argument("env_file", help="Path to environment file")
    sync_parser.add_argument("--env", help="Environment to sync with (development, training, production)")
    sync_parser.add_argument("--prefix", help="Only sync variables with this prefix")
    sync_parser.add_argument("--overwrite", action="store_true", help="Overwrite existing secrets")
    
    # Parse arguments
    args = parser.parse_args()
    
    # Initialize secrets manager
    if "SECRETS_MASTER_PASSWORD" not in os.environ:
        print("Warning: SECRETS_MASTER_PASSWORD environment variable not set")
        print("You will be prompted for a password or a random one will be generated")
    
    # Run command
    if args.command == "set":
        if secrets_manager.set_secret(args.name, args.value, args.env):
            print(f"Secret {args.name} set successfully")
        else:
            print(f"Error setting secret {args.name}")
            sys.exit(1)
    elif args.command == "get":
        value = secrets_manager.get_secret(args.name, args.env)
        if value:
            print(value)
        else:
            print(f"Secret {args.name} not found")
            sys.exit(1)
    elif args.command == "delete":
        if secrets_manager.delete_secret(args.name, args.env):
            print(f"Secret {args.name} deleted successfully")
        else:
            print(f"Error deleting secret {args.name}")
            sys.exit(1)
    elif args.command == "list":
        names = secrets_manager.list_secrets(args.env)
        if names:
            print(f"Secrets for {args.env or secrets_manager.env} environment:")
            for name in names:
                print(f"  - {name}")
        else:
            print(f"No secrets found for {args.env or secrets_manager.env} environment")
    elif args.command == "export":
        if secrets_manager.export_secrets(args.filepath, args.env, args.format):
            print(f"Secrets exported to {args.filepath}")
        else:
            print(f"Error exporting secrets to {args.filepath}")
            sys.exit(1)
    elif args.command == "import":
        if secrets_manager.import_secrets(args.filepath, args.env, args.format, args.overwrite):
            print(f"Secrets imported from {args.filepath}")
        else:
            print(f"Error importing secrets from {args.filepath}")
            sys.exit(1)
    elif args.command == "sync":
        if secrets_manager.sync_with_env_file(args.env_file, args.env, args.prefix, args.overwrite):
            print(f"Secrets synced with {args.env_file}")
        else:
            print(f"Error syncing secrets with {args.env_file}")
            sys.exit(1)
    else:
        # If no command provided, show help
        parser.print_help()
        # Also show some basic information
        print("\nEnvironment:", secrets_manager.env)
        print("Secret file:", secrets_manager.secret_file)
        print("Config file:", secrets_manager.config_file)
        print("Salt file:", secrets_manager.salt_file)