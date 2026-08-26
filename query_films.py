#!/usr/bin/env python3
"""
Query utility for films database
"""
import sqlite3
from pathlib import Path
import sys

DB_PATH = Path('/Users/eric/Moonova/ShortVideo/Download-Videos/films.db')

class FilmsQuery:
    def __init__(self):
        if not DB_PATH.exists():
            print("Error: films.db not found. Run import_tool.py first.")
            sys.exit(1)
        self.conn = sqlite3.connect(DB_PATH)
        self.conn.row_factory = sqlite3.Row

    def list_films(self):
        """List all films"""
        cursor = self.conn.cursor()
        cursor.execute('SELECT id, name, total_episodes, lang FROM films')
        films = cursor.fetchall()

        if not films:
            print("No films found in database.")
            return

        print(f"\n{'ID':<20} {'Name':<50} {'Episodes':<10} {'Lang':<5}")
        print("-" * 90)
        for film in films:
            print(f"{film['id']:<20} {film['name']:<50} {film['total_episodes']:<10} {film['lang']:<5}")
        print(f"\nTotal: {len(films)} films")

    def list_episodes(self, film_id=None):
        """List episodes for a film"""
        cursor = self.conn.cursor()

        if film_id:
            cursor.execute('''
                SELECT ep_number, status, downloaded_at, url
                FROM episodes
                WHERE film_id = ?
                ORDER BY ep_number
            ''', (film_id,))
        else:
            cursor.execute('''
                SELECT film_id, ep_number, status, downloaded_at
                FROM episodes
                ORDER BY film_id, ep_number
            ''')

        episodes = cursor.fetchall()

        if not episodes:
            print(f"No episodes found{' for film ' + film_id if film_id else ''}.")
            return

        if film_id:
            print(f"\n{'Episode':<10} {'Status':<12} {'Downloaded':<25} {'URL':<60}")
            print("-" * 110)
            for ep in episodes:
                url = ep['url'][:60] + "..." if len(ep['url']) > 60 else ep['url']
                print(f"{ep['ep_number']:<10} {ep['status']:<12} {str(ep['downloaded_at']):<25} {url:<60}")
        else:
            print(f"\n{'Film ID':<20} {'Episode':<10} {'Status':<12} {'Downloaded':<25}")
            print("-" * 70)
            for ep in episodes:
                print(f"{ep['film_id']:<20} {ep['ep_number']:<10} {ep['status']:<12} {str(ep['downloaded_at']):<25}")

        print(f"\nTotal: {len(episodes)} episodes")

    def film_details(self, film_id):
        """Get detailed info for a film"""
        cursor = self.conn.cursor()

        cursor.execute('SELECT * FROM films WHERE id = ?', (film_id,))
        film = cursor.fetchone()

        if not film:
            print(f"Film {film_id} not found.")
            return

        cursor.execute('SELECT COUNT(*) as count FROM episodes WHERE film_id = ?', (film_id,))
        ep_count = cursor.fetchone()['count']

        cursor.execute('''
            SELECT status, COUNT(*) as count
            FROM episodes
            WHERE film_id = ?
            GROUP BY status
        ''', (film_id,))
        status_count = cursor.fetchall()

        print(f"\nFilm: {film['name']}")
        print(f"ID: {film['id']}")
        print(f"Language: {film['lang']}")
        print(f"Source: {film['source']}")
        print(f"Total Episodes: {film['total_episodes']}")
        print(f"Description: {film['description'][:100]}..." if film['description'] and len(film['description']) > 100 else f"Description: {film['description']}")
        print(f"Cover Path: {film['cover_path']}")
        print(f"Scraped At: {film['scraped_at']}")
        print(f"Created At: {film['created_at']}")
        print(f"\nDownloaded Episodes: {ep_count}/{film['total_episodes']}")

        if status_count:
            print("\nStatus breakdown:")
            for row in status_count:
                print(f"  {row['status']}: {row['count']}")

    def stats(self):
        """Show database statistics"""
        cursor = self.conn.cursor()

        cursor.execute('SELECT COUNT(*) as count FROM films')
        film_count = cursor.fetchone()['count']

        cursor.execute('SELECT COUNT(*) as count FROM episodes')
        ep_count = cursor.fetchone()['count']

        cursor.execute('SELECT COUNT(*) as count FROM episodes WHERE status = "completed"')
        completed = cursor.fetchone()['count']

        cursor.execute('''
            SELECT SUM(total_episodes) as total
            FROM films
        ''')
        total_eps = cursor.fetchone()['total'] or 0

        print(f"\n{'Database Statistics':<40}")
        print("-" * 40)
        print(f"Total Films: {film_count}")
        print(f"Total Episodes (expected): {total_eps}")
        print(f"Downloaded Episodes: {completed}")
        print(f"Pending Episodes: {ep_count - completed}")
        print(f"Progress: {completed}/{ep_count} ({100*completed//max(ep_count, 1)}%)")

    def close(self):
        """Close database connection"""
        self.conn.close()

def print_help():
    print("""
Usage: python3 query_films.py <command> [options]

Commands:
  list                      List all films
  episodes [film_id]        List episodes (optionally for a specific film)
  details <film_id>         Show detailed info for a film
  stats                     Show database statistics
  help                      Show this help message

Examples:
  python3 query_films.py list
  python3 query_films.py episodes
  python3 query_films.py episodes 100000643080
  python3 query_films.py details 100000643080
  python3 query_films.py stats
""")

def main():
    if len(sys.argv) < 2:
        print_help()
        return 1

    query = FilmsQuery()
    command = sys.argv[1].lower()

    try:
        if command == 'list':
            query.list_films()
        elif command == 'episodes':
            film_id = sys.argv[2] if len(sys.argv) > 2 else None
            query.list_episodes(film_id)
        elif command == 'details':
            if len(sys.argv) < 3:
                print("Error: film_id required")
                print_help()
                return 1
            query.film_details(sys.argv[2])
        elif command == 'stats':
            query.stats()
        elif command == 'help' or command == '-h' or command == '--help':
            print_help()
        else:
            print(f"Unknown command: {command}")
            print_help()
            return 1
    finally:
        query.close()

    return 0

if __name__ == '__main__':
    sys.exit(main())
