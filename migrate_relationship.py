#!/usr/bin/env python3
"""
Migration script to add relationship field to existing users
Run this script after updating the User model
"""

import sys
import os
import sqlite3

# Add the project directory to the Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def migrate_relationships():
    """Add relationship field to existing users"""
    try:
        # Get database path from config
        from config.settings import config
        db_path = os.path.join(os.path.dirname(config.LOG_FILE), 'rtsp_monitor.db')
        
        print(f"🗄️  Database path: {db_path}")
        
        # Connect directly to SQLite database
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Check if users table exists
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='users'")
        table_exists = cursor.fetchone()
        
        if not table_exists:
            print("❌ Users table doesn't exist yet. Please run the application first to create initial database.")
            return False
        
        # Check if relationship column already exists
        cursor.execute("PRAGMA table_info(users)")
        columns = [row[1] for row in cursor.fetchall()]
        
        if 'relationship' not in columns:
            print("➕ Adding relationship column to users table...")
            cursor.execute("ALTER TABLE users ADD COLUMN relationship VARCHAR(50) DEFAULT 'Guardian'")
            conn.commit()
            print("✅ Relationship column added successfully!")
        else:
            print("ℹ️  Relationship column already exists.")
        
        # Update existing users
        cursor.execute("SELECT id, username, is_admin FROM users WHERE relationship IS NULL OR relationship = ''")
        users_to_update = cursor.fetchall()
        
        users_updated = 0
        for user_id, username, is_admin in users_to_update:
            if is_admin:
                relationship = 'Father'
            else:
                relationship = 'Guardian'
            
            cursor.execute("UPDATE users SET relationship = ? WHERE id = ?", (relationship, user_id))
            users_updated += 1
            print(f"   📝 Updated user '{username}' → {relationship}")
        
        conn.commit()
        
        print(f"\n✅ Migration completed successfully!")
        print(f"📊 Updated {users_updated} users with relationship field")
        
        # Display all users and their relationships
        cursor.execute("SELECT username, email, relationship, is_admin, active FROM users")
        all_users = cursor.fetchall()
        
        print(f"\n👥 Current users:")
        for username, email, relationship, is_admin, active in all_users:
            status = "Active" if active else "Inactive"
            role = "Admin" if is_admin else "User"
            print(f"   • {username} ({email}) - {relationship or 'Guardian'} - {role} - {status}")
        
        conn.close()
        
    except Exception as e:
        print(f"❌ Migration failed: {e}")
        return False
    
    return True

if __name__ == '__main__':
    print("🚀 Starting relationship field migration...")
    success = migrate_relationships()
    
    if success:
        print("\n✨ Migration completed! You can now restart your application.")
    else:
        print("\n💥 Migration failed! Please check the errors above.")
        sys.exit(1)
