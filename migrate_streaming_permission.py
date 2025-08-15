#!/usr/bin/env python3
"""
Migration script to add streaming_enabled column to existing users
"""

import os
import sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from flask import Flask
from models.auth import db, User
from config.settings import config
from sqlalchemy import text

def migrate_streaming_permission():
    """Add streaming_enabled column to existing users"""
    
    # Create Flask app context
    app = Flask(__name__)
    db_path = os.path.join(os.path.dirname(config.LOG_FILE), 'rtsp_monitor.db')
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///{}'.format(db_path)
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    
    # Initialize database
    db.init_app(app)
    
    with app.app_context():
        try:
            # Check if column exists
            inspector = db.inspect(db.engine)
            columns = [col['name'] for col in inspector.get_columns('users')]
            
            if 'streaming_enabled' not in columns:
                # Add the column using raw SQL
                db.session.execute(text('ALTER TABLE users ADD COLUMN streaming_enabled BOOLEAN DEFAULT 1 NOT NULL'))
                db.session.commit()
                print("[INFO] Added streaming_enabled column to users table")
            else:
                print("[INFO] Column streaming_enabled already exists")
            
            # Update all existing users to have streaming enabled by default
            db.session.execute(text("UPDATE users SET streaming_enabled = 1 WHERE streaming_enabled IS NULL"))
            db.session.commit()
            
            # Count users
            result = db.session.execute(text("SELECT COUNT(*) FROM users"))
            user_count = result.scalar()
            print(f"[INFO] Updated {user_count} users with streaming permissions")
            
        except Exception as e:
            print(f"[ERROR] Migration failed: {e}")
            db.session.rollback()
            return False
    
    return True

if __name__ == '__main__':
    print("[INFO] Starting streaming permission migration...")
    if migrate_streaming_permission():
        print("[INFO] Migration completed successfully!")
    else:
        print("[ERROR] Migration failed!")
        sys.exit(1)
