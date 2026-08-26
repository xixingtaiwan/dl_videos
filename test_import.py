#!/usr/bin/env python3
"""
Test script for the Import Tool
"""
import json
import sqlite3
from pathlib import Path
import sys

BASE_DIR = Path('/Users/eric/Moonova/ShortVideo/Download-Videos')
DB_PATH = BASE_DIR / 'films.db'
JSON_PATH = BASE_DIR / 'idrama' / 'idrama_100000643080.json'

def test_json_structure():
    """Test JSON file structure"""
    print("Testing JSON structure...")
    try:
        with open(JSON_PATH, 'r') as f:
            data = json.load(f)

        assert 'source' in data, "Missing 'source' field"
        assert 'drama' in data, "Missing 'drama' field (should be renamed to 'film' in DB)"
        assert 'episodes' in data, "Missing 'episodes' field"

        drama = data['drama']
        assert 'id' in drama, "Missing film ID"
        assert 'name' in drama, "Missing film name"
        assert 'cover' in drama, "Missing cover URL"
        assert 'total_episodes' in drama, "Missing total_episodes"

        print(f"✓ JSON structure valid")
        print(f"  - Source: {data['source']}")
        print(f"  - Film ID: {drama['id']}")
        print(f"  - Film Name: {drama['name']}")
        print(f"  - Total Episodes: {drama['total_episodes']}")
        print(f"  - Episodes in JSON: {len(data['episodes'])}")

        return data
    except Exception as e:
        print(f"✗ JSON validation failed: {e}")
        return None

def test_database_schema():
    """Test database schema"""
    print("\nTesting database schema...")
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

        # Check films table
        cursor.execute("SELECT sql FROM sqlite_master WHERE type='table' AND name='films'")
        films_schema = cursor.fetchone()
        if films_schema:
            print("✓ Films table exists")
            # Verify key columns
            cursor.execute("PRAGMA table_info(films)")
            columns = {row[1]: row[2] for row in cursor.fetchall()}
            assert 'id' in columns, "Missing 'id' column"
            assert 'name' in columns, "Missing 'name' column"
            assert 'cover_path' in columns, "Missing 'cover_path' column"
            print("  - All required columns present")

        # Check episodes table
        cursor.execute("SELECT sql FROM sqlite_master WHERE type='table' AND name='episodes'")
        episodes_schema = cursor.fetchone()
        if episodes_schema:
            print("✓ Episodes table exists")
            cursor.execute("PRAGMA table_info(episodes)")
            columns = {row[1]: row[2] for row in cursor.fetchall()}
            assert 'film_id' in columns, "Missing 'film_id' column"
            assert 'ep_number' in columns, "Missing 'ep_number' column"
            assert 'video_path' in columns, "Missing 'video_path' column"
            print("  - All required columns present")

        conn.close()
        return True
    except Exception as e:
        print(f"✗ Database schema test failed: {e}")
        return False

def test_download_paths():
    """Test download path generation"""
    print("\nTesting download paths...")
    try:
        data = json.load(open(JSON_PATH))
        film_id = data['drama']['id']
        source = data['source']

        # Cover path
        cover_filename = Path(data['drama']['cover']).name
        cover_path = f"videos/{source}/{film_id}/cover/{cover_filename}"
        print(f"✓ Cover path: {cover_path}")

        # Episode paths
        for ep_idx, episode in enumerate(data['episodes'][:3]):  # Test first 3
            ep_num = episode['ep']
            url = episode['url']
            url_path = Path(url.split('?')[0])
            parts = url_path.parts[-2:]  # Last 2 parts
            ep_path = f"videos/{source}/{film_id}/ep/{ep_num}/{parts[0]}/{parts[1]}"
            print(f"✓ Episode {ep_num} path: {ep_path}")

        print(f"... (total {len(data['episodes'])} episodes)")
        return True
    except Exception as e:
        print(f"✗ Download path test failed: {e}")
        return False

def main():
    print("=" * 60)
    print("Import Tool Verification Test")
    print("=" * 60)

    results = []

    # Test JSON structure
    json_data = test_json_structure()
    results.append(json_data is not None)

    # Test database schema
    db_valid = test_database_schema()
    results.append(db_valid)

    # Test download paths
    paths_valid = test_download_paths()
    results.append(paths_valid)

    print("\n" + "=" * 60)
    print(f"Results: {sum(results)}/{len(results)} tests passed")
    print("=" * 60)

    if all(results):
        print("\n✓ All tests passed! Tool is ready to use.")
        print("\nNext steps:")
        print("1. Run: python3 import_tool.py")
        print("2. Monitor import_tool.log for progress")
        print("3. Check films.db for imported data")
        return 0
    else:
        print("\n✗ Some tests failed. Please review the errors above.")
        return 1

if __name__ == '__main__':
    sys.exit(main())
