#!/usr/bin/env python3
"""
Database Restore Utility - Restore from backup or SQL dump
"""
import sqlite3
import shutil
import sys
from pathlib import Path
from datetime import datetime

DB_PATH = Path('/Users/eric/Moonova/ShortVideo/Download-Videos/films.db')
BACKUP_DIR = Path('/Users/eric/Moonova/ShortVideo/Download-Videos/backups')
EXPORT_DIR = Path('/Users/eric/Moonova/ShortVideo/Download-Videos/exports')

def list_backups():
    """List available backups"""
    if not BACKUP_DIR.exists():
        print("No backups found.")
        return []

    backups = sorted(BACKUP_DIR.glob('films_backup_*.db'), reverse=True)
    return backups

def restore_from_backup(backup_file):
    """Restore database from backup file"""
    backup_path = BACKUP_DIR / backup_file if not backup_file.startswith('/') else Path(backup_file)

    if not backup_path.exists():
        print(f"Error: Backup file not found: {backup_path}")
        return False

    # Confirm action
    print(f"Warning: This will overwrite current database!")
    print(f"Current DB: {DB_PATH}")
    print(f"Restore from: {backup_path}")
    response = input("Continue? (yes/no): ").strip().lower()

    if response != 'yes':
        print("Restore cancelled.")
        return False

    try:
        # Create backup of current database before restore
        if DB_PATH.exists():
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            current_backup = BACKUP_DIR / f'films_before_restore_{timestamp}.db'
            BACKUP_DIR.mkdir(parents=True, exist_ok=True)
            shutil.copy2(DB_PATH, current_backup)
            print(f"Current database backed up to: {current_backup}")

        # Restore
        shutil.copy2(backup_path, DB_PATH)
        print(f"✓ Database restored from: {backup_path}")

        # Verify
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute('SELECT COUNT(*) FROM films')
        film_count = cursor.fetchone()[0]
        cursor.execute('SELECT COUNT(*) FROM episodes')
        episode_count = cursor.fetchone()[0]
        conn.close()

        print(f"✓ Restore successful!")
        print(f"  Films: {film_count}")
        print(f"  Episodes: {episode_count}")
        return True

    except Exception as e:
        print(f"✗ Error during restore: {e}")
        return False

def restore_from_sql_dump(sql_file):
    """Restore database from SQL dump"""
    sql_path = EXPORT_DIR / sql_file if not sql_file.startswith('/') else Path(sql_file)

    if not sql_path.exists():
        print(f"Error: SQL file not found: {sql_path}")
        return False

    # Confirm action
    print(f"Warning: This will overwrite current database!")
    print(f"Current DB: {DB_PATH}")
    print(f"Restore from: {sql_path}")
    response = input("Continue? (yes/no): ").strip().lower()

    if response != 'yes':
        print("Restore cancelled.")
        return False

    try:
        # Create backup of current database
        if DB_PATH.exists():
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            current_backup = BACKUP_DIR / f'films_before_restore_{timestamp}.db'
            BACKUP_DIR.mkdir(parents=True, exist_ok=True)
            shutil.copy2(DB_PATH, current_backup)
            print(f"Current database backed up to: {current_backup}")

            # Remove old database
            DB_PATH.unlink()

        # Create new database from SQL dump
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

        with open(sql_path, 'r', encoding='utf-8') as f:
            sql_script = f.read()

        cursor.executescript(sql_script)
        conn.commit()
        conn.close()

        print(f"✓ Database restored from SQL dump: {sql_path}")

        # Verify
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute('SELECT COUNT(*) FROM films')
        film_count = cursor.fetchone()[0]
        cursor.execute('SELECT COUNT(*) FROM episodes')
        episode_count = cursor.fetchone()[0]
        conn.close()

        print(f"✓ Restore successful!")
        print(f"  Films: {film_count}")
        print(f"  Episodes: {episode_count}")
        return True

    except Exception as e:
        print(f"✗ Error during restore: {e}")
        return False

def show_backup_info(backup_file):
    """Show information about a backup"""
    backup_path = BACKUP_DIR / backup_file

    if not backup_path.exists():
        print(f"Backup not found: {backup_file}")
        return False

    try:
        conn = sqlite3.connect(backup_path)
        cursor = conn.cursor()

        cursor.execute('SELECT COUNT(*) FROM films')
        film_count = cursor.fetchone()[0]

        cursor.execute('SELECT COUNT(*) FROM episodes')
        episode_count = cursor.fetchone()[0]

        cursor.execute('SELECT COUNT(*) FROM episodes WHERE status = "completed"')
        completed = cursor.fetchone()[0]

        conn.close()

        size_mb = backup_path.stat().st_size / 1024 / 1024
        mtime = datetime.fromtimestamp(backup_path.stat().st_mtime)

        print(f"\nBackup: {backup_file}")
        print(f"Size: {size_mb:.2f} MB")
        print(f"Created: {mtime.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"Films: {film_count}")
        print(f"Episodes: {episode_count}")
        print(f"Completed: {completed}")
        if episode_count > 0:
            progress = (completed / episode_count) * 100
            print(f"Progress: {progress:.1f}%")

        return True

    except Exception as e:
        print(f"Error reading backup: {e}")
        return False

def print_help():
    print("""
Usage: python3 restore_db.py <command> [options]

Commands:
  list                      List all available backups
  info <backup_file>        Show backup information
  restore <backup_file>     Restore from backup
  restore-sql <sql_file>    Restore from SQL dump
  help                      Show this help message

Examples:
  python3 restore_db.py list
  python3 restore_db.py info films_backup_20260826_165030.db
  python3 restore_db.py restore films_backup_20260826_165030.db
  python3 restore_db.py restore-sql films_dump_20260826_165030.sql
""")

def main():
    if len(sys.argv) < 2:
        print_help()
        return 0

    command = sys.argv[1].lower()

    if command == 'list':
        print("\nAvailable Backups:")
        print("-" * 60)
        backups = list_backups()
        if not backups:
            print("No backups found.")
            return 0

        for i, backup in enumerate(backups, 1):
            size_mb = backup.stat().st_size / 1024 / 1024
            mtime = datetime.fromtimestamp(backup.stat().st_mtime)
            print(f"{i}. {backup.name}")
            print(f"   Size: {size_mb:.2f} MB | Created: {mtime.strftime('%Y-%m-%d %H:%M:%S')}")

    elif command == 'info':
        if len(sys.argv) < 3:
            print("Error: backup_file required")
            print_help()
            return 1
        show_backup_info(sys.argv[2])

    elif command == 'restore':
        if len(sys.argv) < 3:
            print("Error: backup_file required")
            print_help()
            return 1
        return 0 if restore_from_backup(sys.argv[2]) else 1

    elif command == 'restore-sql':
        if len(sys.argv) < 3:
            print("Error: sql_file required")
            print_help()
            return 1
        return 0 if restore_from_sql_dump(sys.argv[2]) else 1

    elif command == 'help' or command == '-h' or command == '--help':
        print_help()
        return 0

    else:
        print(f"Unknown command: {command}")
        print_help()
        return 1

    return 0

if __name__ == '__main__':
    sys.exit(main())
