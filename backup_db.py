#!/usr/bin/env python3
"""
Database Backup Utility - Create timestamped backups
"""
import sqlite3
import shutil
import sys
from pathlib import Path
from datetime import datetime
import os

DB_PATH = Path('/Users/eric/Moonova/ShortVideo/Download-Videos/films.db')
BACKUP_DIR = Path('/Users/eric/Moonova/ShortVideo/Download-Videos/backups')

def backup_db(backup_name=None):
    """Create a backup of the database"""
    if not DB_PATH.exists():
        print(f"Error: Database not found at {DB_PATH}")
        return False

    # Create backup directory if it doesn't exist
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)

    # Generate backup filename
    if backup_name is None:
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_name = f'films_backup_{timestamp}.db'

    backup_path = BACKUP_DIR / backup_name

    try:
        # Copy database file
        shutil.copy2(DB_PATH, backup_path)
        file_size = backup_path.stat().st_size
        print(f"✓ Backup created: {backup_path}")
        print(f"  Size: {file_size / 1024:.2f} KB")
        print(f"  Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        return True
    except Exception as e:
        print(f"✗ Error creating backup: {e}")
        return False

def list_backups():
    """List all available backups"""
    if not BACKUP_DIR.exists():
        print("No backups found.")
        return

    backups = sorted(BACKUP_DIR.glob('films_backup_*.db'), reverse=True)

    if not backups:
        print("No backups found in backup directory.")
        return

    print(f"\n{'Backup File':<35} {'Size':<12} {'Created':<20}")
    print("-" * 70)

    for backup_file in backups:
        size_kb = backup_file.stat().st_size / 1024
        mtime = datetime.fromtimestamp(backup_file.stat().st_mtime)
        mtime_str = mtime.strftime('%Y-%m-%d %H:%M:%S')
        print(f"{backup_file.name:<35} {size_kb:>10.2f} KB {mtime_str:<20}")

    print(f"\nTotal backups: {len(backups)}")

def get_db_stats():
    """Get database statistics"""
    if not DB_PATH.exists():
        print("Database not found.")
        return

    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

        # Count records
        cursor.execute('SELECT COUNT(*) FROM films')
        film_count = cursor.fetchone()[0]

        cursor.execute('SELECT COUNT(*) FROM episodes')
        episode_count = cursor.fetchone()[0]

        cursor.execute('SELECT COUNT(*) FROM episodes WHERE status = "completed"')
        completed_count = cursor.fetchone()[0]

        conn.close()

        db_size = DB_PATH.stat().st_size / 1024 / 1024

        print(f"\n{'Database Statistics':<40}")
        print("-" * 40)
        print(f"Database Size: {db_size:.2f} MB")
        print(f"Total Films: {film_count}")
        print(f"Total Episodes: {episode_count}")
        print(f"Completed Episodes: {completed_count}")
        print(f"Pending Episodes: {episode_count - completed_count}")
        if episode_count > 0:
            progress = (completed_count / episode_count) * 100
            print(f"Progress: {progress:.1f}%")

    except Exception as e:
        print(f"Error getting statistics: {e}")

def cleanup_old_backups(keep=5):
    """Remove old backups, keeping only the most recent ones"""
    if not BACKUP_DIR.exists():
        print("Backup directory not found.")
        return

    backups = sorted(BACKUP_DIR.glob('films_backup_*.db'), reverse=True)

    if len(backups) <= keep:
        print(f"No cleanup needed. Current backups: {len(backups)}, Keep: {keep}")
        return

    to_remove = backups[keep:]
    print(f"Removing {len(to_remove)} old backups (keeping {keep})...")

    for backup_file in to_remove:
        try:
            backup_file.unlink()
            print(f"  Removed: {backup_file.name}")
        except Exception as e:
            print(f"  Error removing {backup_file.name}: {e}")

def print_help():
    print("""
Usage: python3 backup_db.py <command> [options]

Commands:
  backup                    Create a new backup
  backup <name>             Create backup with custom name
  list                      List all backups
  stats                     Show database statistics
  cleanup [keep]            Remove old backups (default: keep 5)
  help                      Show this help message

Examples:
  python3 backup_db.py backup
  python3 backup_db.py backup my_backup.db
  python3 backup_db.py list
  python3 backup_db.py stats
  python3 backup_db.py cleanup
  python3 backup_db.py cleanup 10
""")

def main():
    if len(sys.argv) < 2:
        print_help()
        return 0

    command = sys.argv[1].lower()

    if command == 'backup':
        backup_name = sys.argv[2] if len(sys.argv) > 2 else None
        return 0 if backup_db(backup_name) else 1

    elif command == 'list':
        list_backups()
        return 0

    elif command == 'stats':
        get_db_stats()
        return 0

    elif command == 'cleanup':
        keep = int(sys.argv[2]) if len(sys.argv) > 2 else 5
        cleanup_old_backups(keep)
        return 0

    elif command == 'help' or command == '-h' or command == '--help':
        print_help()
        return 0

    else:
        print(f"Unknown command: {command}")
        print_help()
        return 1

if __name__ == '__main__':
    sys.exit(main())
