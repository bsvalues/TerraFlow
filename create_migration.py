import os
import sys
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from sqlalchemy.orm import DeclarativeBase

# Set up Flask app for migrations
class Base(DeclarativeBase):
    pass

db = SQLAlchemy(model_class=Base)
app = Flask(__name__)

# Use the DATABASE_URL environment variable
app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get("DATABASE_URL")
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

# Initialize the database and migrations
db.init_app(app)
migrate = Migrate(app, db)

# Import models to make them available to the migration
with app.app_context():
    # Import all models to ensure they are registered with the metadata
    from models import *
    
    print("Models imported successfully")
    
    # Initialize migrations directory if it doesn't exist
    from flask_migrate import init, migrate as migrate_cmd
    
    if not os.path.exists('migrations'):
        print("Initializing Flask-Migrate...")
        init()
    
    print("Creating migration...")
    migrate_cmd(message="Initial database schema")
    
    print("Migration created successfully")