#!/usr/bin/env python3
"""
Setup script to initialize directory structure for JSON files
Organizes JSON files into data/, done/, and error/ subdirectories
"""

import shutil
from pathlib import Path

def setup_directories():
    """Initialize directory structure and optionally migrate existing files"""
    base_dir = Path('/Users/eric/Moonova/ShortVideo/Download-Videos')
    idrama_dir = base_dir / 'idrama'

    # Create subdirectories
    data_dir = idrama_dir / 'data'
    done_dir = idrama_dir / 'done'
    error_dir = idrama_dir / 'error'

    print("="*70)
    print("SETTING UP DIRECTORY STRUCTURE")
    print("="*70)

    # Create directories
    for dir_path, name in [(data_dir, 'data'), (done_dir, 'done'), (error_dir, 'error')]:
        if not dir_path.exists():
            dir_path.mkdir(parents=True, exist_ok=True)
            print(f"\n✓ Created directory: idrama/{name}/")
        else:
            print(f"\n✓ Directory already exists: idrama/{name}/")

    # Migrate existing files
    print("\n" + "="*70)
    print("MIGRATING EXISTING FILES")
    print("="*70)

    migrated_data = 0
    migrated_done = 0
    migrated_error = 0

    # Find all JSON files in idrama/ root
    all_json = list(idrama_dir.glob('*.json'))

    if not all_json:
        print("\nℹ No existing JSON files found in idrama/ to migrate")
    else:
        print(f"\nFound {len(all_json)} JSON files to organize:")

        for json_file in all_json:
            # Skip if already in subdirectory
            if json_file.parent != idrama_dir:
                continue

            if json_file.name.endswith('_done.json'):
                # Move to done directory
                new_path = done_dir / json_file.name.replace('_done.json', '.json')
                try:
                    shutil.move(str(json_file), str(new_path))
                    print(f"  ✓ Moved to done/: {json_file.name}")
                    migrated_done += 1
                except Exception as e:
                    print(f"  ✗ Error moving {json_file.name}: {e}")

            elif json_file.name.endswith('_error.json'):
                # Move to error directory
                new_path = error_dir / json_file.name.replace('_error.json', '.json')
                try:
                    shutil.move(str(json_file), str(new_path))
                    print(f"  ✓ Moved to error/: {json_file.name}")
                    migrated_error += 1
                except Exception as e:
                    print(f"  ✗ Error moving {json_file.name}: {e}")

            elif json_file.name.endswith('_processing.json'):
                # Move to data directory for retry
                new_path = data_dir / json_file.name.replace('_processing.json', '.json')
                try:
                    shutil.move(str(json_file), str(new_path))
                    print(f"  ✓ Moved to data/ (will retry): {json_file.name}")
                    migrated_data += 1
                except Exception as e:
                    print(f"  ✗ Error moving {json_file.name}: {e}")

            else:
                # Regular JSON file - move to data directory
                new_path = data_dir / json_file.name
                try:
                    shutil.move(str(json_file), str(new_path))
                    print(f"  ✓ Moved to data/: {json_file.name}")
                    migrated_data += 1
                except Exception as e:
                    print(f"  ✗ Error moving {json_file.name}: {e}")

    # Summary
    print("\n" + "="*70)
    print("SUMMARY")
    print("="*70)
    print(f"\nDirectory Structure Created:")
    print(f"  idrama/data/   (pending - {len(list(data_dir.glob('*.json')))} files)")
    print(f"  idrama/done/   (completed - {len(list(done_dir.glob('*.json')))} files)")
    print(f"  idrama/error/  (errors - {len(list(error_dir.glob('*.json')))} files)")

    if all_json:
        print(f"\nFiles Migrated:")
        print(f"  → data/:  {migrated_data}")
        print(f"  → done/:  {migrated_done}")
        print(f"  → error/: {migrated_error}")

    print("\n" + "="*70)
    print("✅ SETUP COMPLETE")
    print("="*70)
    print("\nNext step: python3 import_tool_postgres.py")

if __name__ == '__main__':
    setup_directories()
