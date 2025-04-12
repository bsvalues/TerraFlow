import os
from set_supabase_env import ensure_supabase_env

# Set up Supabase environment variables
supabase_config = ensure_supabase_env()

# Set BYPASS_LDAP environment variable to true for development
os.environ['BYPASS_LDAP'] = 'true'

from app import app  # noqa: F401

