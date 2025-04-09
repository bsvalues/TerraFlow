import os
from app import app  # noqa: F401

# Set BYPASS_LDAP environment variable to true for development
os.environ['BYPASS_LDAP'] = 'true'

