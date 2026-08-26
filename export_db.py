#!/usr/bin/env python3
"""
Database Export Utility - Export data to CSV, JSON, SQL
"""
import sqlite3
import json
import csv
import sys
from pathlib import Path
from datetime import datetime

DB_PATH = Path('/Users/eric/Moonova/ShortVideo/Download-Videos/films.db')
EXPORT_DIR = Path('/Users/eric/Moonova/ShortVideo/Download-Videos/exports')

class DatabaseExporter:
    def __init__(self):
        if not DB_PATH.exists():
            print(f"Error: Database not found at {DB_PATH}")
            sys.exit(1)
        EXPORT_DIR.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(DB_PATH)
        self.conn.row_factory = sqlite3.Row

    def export_csv(self, table_name, filename=None):
        """Export table to CSV"""
        if filename is None:
            filename = f'{table_name}_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv'

        filepath = EXPORT_DIR / filename
        cursor = self.conn.cursor()

        try:
            cursor.execute(f'SELECT * FROM {table_name}')
            rows = cursor.fetchall()

            if not rows:
                print(f"No data in {table_name} table.")
                return False

            # Get column names
            columns = [description[0] for description in cursor.description]

            # Write CSV
            with open(filepath, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow(columns)
                for row in rows:
                    writer.writerow(row)

            print(f"✓ Exported to CSV: {filepath}")
            print(f"  Records: {len(rows)}")
            return True

        except Exception as e:
            print(f"✗ Error exporting {table_name}: {e}")
            return False

    def export_json(self, table_name, filename=None):
        """Export table to JSON"""
        if filename is None:
            filename = f'{table_name}_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json'

        filepath = EXPORT_DIR / filename
        cursor = self.conn.cursor()

        try:
            cursor.execute(f'SELECT * FROM {table_name}')
            rows = cursor.fetchall()

            if not rows:
                print(f"No data in {table_name} table.")
                return False

            # Convert rows to dictionaries
            data = [dict(row) for row in rows]

            # Write JSON
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)

            print(f"✓ Exported to JSON: {filepath}")
            print(f"  Records: {len(data)}")
            return True

        except Exception as e:
            print(f"✗ Error exporting {table_name}: {e}")
            return False

    def export_all_json(self, filename=None):
        """Export all tables to single JSON file"""
        if filename is None:
            filename = f'all_films_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json'

        filepath = EXPORT_DIR / filename
        cursor = self.conn.cursor()

        try:
            # Get films
            cursor.execute('SELECT * FROM films')
            films = [dict(row) for row in cursor.fetchall()]

            # Get episodes
            cursor.execute('SELECT * FROM episodes')
            episodes = [dict(row) for row in cursor.fetchall()]

            # Combine with structure
            data = {
                'export_date': datetime.now().isoformat(),
                'films': films,
                'episodes': episodes,
                'summary': {
                    'total_films': len(films),
                    'total_episodes': len(episodes)
                }
            }

            # Write JSON
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)

            print(f"✓ Exported to JSON: {filepath}")
            print(f"  Films: {len(films)}")
            print(f"  Episodes: {len(episodes)}")
            return True

        except Exception as e:
            print(f"✗ Error exporting: {e}")
            return False

    def export_sql_dump(self, filename=None):
        """Export database as SQL dump"""
        if filename is None:
            filename = f'films_dump_{datetime.now().strftime("%Y%m%d_%H%M%S")}.sql'

        filepath = EXPORT_DIR / filename

        try:
            # Get SQL dump
            cursor = self.conn.cursor()
            dump = '\n'.join(self.conn.iterdump())

            # Write SQL file
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(dump)

            print(f"✓ Exported to SQL: {filepath}")
            file_size = filepath.stat().st_size / 1024
            print(f"  Size: {file_size:.2f} KB")
            return True

        except Exception as e:
            print(f"✗ Error exporting SQL dump: {e}")
            return False

    def export_film_episodes(self, film_id, format='json'):
        """Export all episodes for a specific film"""
        cursor = self.conn.cursor()

        try:
            # Get film info
            cursor.execute('SELECT * FROM films WHERE film_id = ?', (film_id,))
            film = cursor.fetchone()

            if not film:
                print(f"Film {film_id} not found.")
                return False

            film_name = film['name'].replace(' ', '_').replace('/', '_')
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')

            # Get episodes
            cursor.execute(
                'SELECT * FROM episodes WHERE film_id = (SELECT id FROM films WHERE film_id = ?) ORDER BY ep_number',
                (film_id,)
            )
            episodes = [dict(row) for row in cursor.fetchall()]

            if format == 'json':
                filename = f'{film_name}_{film_id}_{timestamp}.json'
                filepath = EXPORT_DIR / filename

                data = {
                    'film': dict(film),
                    'episodes': episodes,
                    'export_date': datetime.now().isoformat()
                }

                with open(filepath, 'w', encoding='utf-8') as f:
                    json.dump(data, f, indent=2, ensure_ascii=False)

            elif format == 'csv':
                filename = f'{film_name}_{film_id}_{timestamp}.csv'
                filepath = EXPORT_DIR / filename

                with open(filepath, 'w', newline='', encoding='utf-8') as f:
                    writer = csv.writer(f)
                    writer.writerow(['Episode', 'Video Path', 'URL', 'Status', 'Downloaded'])
                    for ep in episodes:
                        writer.writerow([
                            ep['ep_number'],
                            ep['video_path'],
                            ep['url'],
                            ep['status'],
                            ep['downloaded_at']
                        ])

            print(f"✓ Exported {film['name']} to {format.upper()}: {filepath}")
            print(f"  Episodes: {len(episodes)}")
            return True

        except Exception as e:
            print(f"✗ Error exporting film: {e}")
            return False

    def list_exports(self):
        """List all exported files"""
        if not EXPORT_DIR.exists():
            print("No exports found.")
            return

        files = sorted(EXPORT_DIR.glob('*'), key=lambda x: x.stat().st_mtime, reverse=True)

        if not files:
            print("No export files found.")
            return

        print(f"\n{'Export File':<50} {'Size':<12} {'Created':<20}")
        print("-" * 85)

        for file in files:
            size_kb = file.stat().st_size / 1024
            mtime = datetime.fromtimestamp(file.stat().st_mtime)
            mtime_str = mtime.strftime('%Y-%m-%d %H:%M:%S')
            print(f"{file.name:<50} {size_kb:>10.2f} KB {mtime_str:<20}")

        print(f"\nTotal exports: {len(files)}")

    def close(self):
        """Close database connection"""
        self.conn.close()

def print_help():
    print("""
Usage: python3 export_db.py <command> [options]

Commands:
  films csv                 Export films to CSV
  films json                Export films to JSON
  episodes csv              Export episodes to CSV
  episodes json             Export episodes to JSON
  all json                  Export all data to JSON
  dump                      Export SQL dump
  film <film_id> json       Export specific film (JSON)
  film <film_id> csv        Export specific film (CSV)
  list                      List all exports
  help                      Show this help message

Examples:
  python3 export_db.py films json
  python3 export_db.py episodes csv
  python3 export_db.py all json
  python3 export_db.py dump
  python3 export_db.py film 100000643080 json
  python3 export_db.py list
""")

def main():
    if len(sys.argv) < 2:
        print_help()
        return 0

    exporter = DatabaseExporter()

    try:
        command = sys.argv[1].lower()

        if command == 'films':
            format = sys.argv[2].lower() if len(sys.argv) > 2 else 'json'
            if format == 'csv':
                exporter.export_csv('films')
            elif format == 'json':
                exporter.export_json('films')

        elif command == 'episodes':
            format = sys.argv[2].lower() if len(sys.argv) > 2 else 'json'
            if format == 'csv':
                exporter.export_csv('episodes')
            elif format == 'json':
                exporter.export_json('episodes')

        elif command == 'all':
            format = sys.argv[2].lower() if len(sys.argv) > 2 else 'json'
            if format == 'json':
                exporter.export_all_json()

        elif command == 'dump':
            exporter.export_sql_dump()

        elif command == 'film':
            if len(sys.argv) < 3:
                print("Error: film_id required")
                print_help()
                return 1
            film_id = sys.argv[2]
            format = sys.argv[3].lower() if len(sys.argv) > 3 else 'json'
            exporter.export_film_episodes(film_id, format)

        elif command == 'list':
            exporter.list_exports()

        elif command == 'help' or command == '-h' or command == '--help':
            print_help()

        else:
            print(f"Unknown command: {command}")
            print_help()
            return 1

    finally:
        exporter.close()

    return 0

if __name__ == '__main__':
    sys.exit(main())
