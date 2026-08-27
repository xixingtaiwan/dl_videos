#!/usr/bin/env python3
"""
Database migration script to add video_format column
Upgrades existing PostgreSQL database schema to support multiple video formats
"""

import logging
from pathlib import Path
import psycopg2
from config import DATABASE_CONFIG

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class DatabaseMigration:
    def __init__(self, db_config):
        self.db_config = db_config

    def get_connection(self):
        """Get database connection"""
        return psycopg2.connect(**self.db_config)

    def run_migration(self):
        """Run database migration"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()

            logger.info("Starting database migration...")

            # Check if video_format column exists
            cursor.execute("""
                SELECT column_name FROM information_schema.columns
                WHERE table_name = 'episodes' AND column_name = 'video_format'
            """)

            if cursor.fetchone():
                logger.info("✓ Column 'video_format' already exists")
                conn.close()
                return True

            # Add video_format column
            logger.info("Adding 'video_format' column to episodes table...")
            cursor.execute("""
                ALTER TABLE episodes
                ADD COLUMN video_format TEXT DEFAULT 'unknown'
            """)
            logger.info("✓ Column 'video_format' added successfully")

            # Set default format based on file extension (best guess migration)
            logger.info("Attempting to infer video formats from existing file paths...")
            cursor.execute("""
                UPDATE episodes
                SET video_format = CASE
                    WHEN video_path LIKE '%.m3u8' THEN 'hls'
                    WHEN video_path LIKE '%.mpd' THEN 'dash'
                    WHEN video_path LIKE '%.mp4' THEN 'mp4'
                    WHEN video_path LIKE '%.mkv' THEN 'mkv'
                    WHEN video_path LIKE '%.webm' THEN 'webm'
                    WHEN video_path LIKE '%.flv' THEN 'flv'
                    WHEN video_path LIKE '%.mov' THEN 'mov'
                    WHEN video_path LIKE '%.ts' THEN 'hls'
                    ELSE 'unknown'
                END
                WHERE video_format = 'unknown'
            """)

            rows_updated = cursor.rowcount
            logger.info(f"✓ Updated {rows_updated} episode records with inferred formats")

            # Log statistics
            cursor.execute("""
                SELECT video_format, COUNT(*) as count
                FROM episodes
                GROUP BY video_format
                ORDER BY count DESC
            """)

            logger.info("\nVideo format distribution:")
            for format_type, count in cursor.fetchall():
                logger.info(f"  {format_type:10} - {count} episodes")

            conn.commit()
            conn.close()
            logger.info("\n✓ Migration completed successfully!")
            return True

        except psycopg2.Error as e:
            logger.error(f"✗ Database error: {e}")
            if conn:
                conn.rollback()
                conn.close()
            return False
        except Exception as e:
            logger.error(f"✗ Error: {e}")
            return False

def main():
    """Main function"""
    migration = DatabaseMigration(DATABASE_CONFIG)

    # Validate config
    if DATABASE_CONFIG['password'] == 'your_password':
        logger.error("✗ ERROR: PostgreSQL password not configured!")
        logger.error("  Edit config.py and set your PostgreSQL password")
        return

    if migration.run_migration():
        exit(0)
    else:
        exit(1)

if __name__ == '__main__':
    main()
