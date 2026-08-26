#!/usr/bin/env python3
"""
Video Import Tool - Download and import videos from JSON config files
"""
import json
import os
import sqlite3
import time
import logging
from pathlib import Path
from datetime import datetime
import urllib.request
import urllib.error
from urllib.parse import urlparse
import shutil
from concurrent.futures import ThreadPoolExecutor, as_completed

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('import_tool.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Configuration
BASE_DIR = Path('/Users/eric/Moonova/ShortVideo/Download-Videos')
JSON_DIR = BASE_DIR / 'idrama'
DOWNLOAD_DIR = BASE_DIR / 'videos'
DB_PATH = BASE_DIR / 'films.db'
SCAN_INTERVAL = 600  # 10 minutes

class FilmDatabase:
    def __init__(self, db_path):
        self.db_path = db_path
        self.init_db()

    def init_db(self):
        """Initialize database schema"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Films table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS films (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                film_id TEXT UNIQUE NOT NULL,
                name TEXT NOT NULL,
                description TEXT,
                cover_path TEXT,
                cover_path_source TEXT,
                total_episodes INTEGER,
                lang TEXT,
                is_ai INTEGER DEFAULT 0,
                source TEXT,
                scraped_at TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        # Episodes table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS episodes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                film_id INTEGER NOT NULL,
                ep_number INTEGER NOT NULL,
                video_path TEXT,
                video_path_source TEXT,
                url TEXT,
                status TEXT DEFAULT 'pending',
                downloaded_at TIMESTAMP,
                FOREIGN KEY (film_id) REFERENCES films(id),
                UNIQUE(film_id, ep_number)
            )
        ''')

        conn.commit()
        conn.close()
        logger.info("Database initialized")

    def insert_film(self, film_data):
        """Insert film metadata into database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        try:
            # Convert boolean to integer (0 or 1)
            is_ai = 1 if film_data.get('is_ai') else 0

            cursor.execute('''
                INSERT OR REPLACE INTO films
                (film_id, name, description, cover_path, cover_path_source, total_episodes, lang, is_ai, source, scraped_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                film_data['id'],
                film_data['name'],
                film_data.get('description'),
                film_data.get('cover_path'),
                film_data.get('cover_path_source'),
                film_data.get('total_episodes'),
                film_data.get('lang'),
                is_ai,
                film_data.get('source'),
                film_data.get('scraped_at')
            ))
            conn.commit()
            logger.info(f"Inserted film: {film_data['id']} - {film_data['name']}")
        except Exception as e:
            logger.error(f"Error inserting film: {e}")
            conn.rollback()
        finally:
            conn.close()

    def get_film_pk(self, film_id):
        """Get internal ID (pk) for a film by film_id"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('SELECT id FROM films WHERE film_id = ?', (film_id,))
        result = cursor.fetchone()
        conn.close()
        return result[0] if result else None

    def insert_episode(self, film_pk, ep_number, video_path, video_path_source, url):
        """Insert episode into database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        try:
            cursor.execute('''
                INSERT OR REPLACE INTO episodes
                (film_id, ep_number, video_path, video_path_source, url, status, downloaded_at)
                VALUES (?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            ''', (film_pk, ep_number, video_path, video_path_source, url, 'completed'))
            conn.commit()
        except Exception as e:
            logger.error(f"Error inserting episode: {e}")
            conn.rollback()
        finally:
            conn.close()

class VideoDownloader:
    def __init__(self, download_dir, max_retries=3):
        self.download_dir = Path(download_dir)
        self.download_dir.mkdir(parents=True, exist_ok=True)
        self.max_retries = max_retries

    def download_file(self, url, output_path):
        """Download file from URL with retry logic"""
        output_path.parent.mkdir(parents=True, exist_ok=True)

        if output_path.exists():
            logger.info(f"File already exists: {output_path}")
            return True

        for attempt in range(1, self.max_retries + 1):
            try:
                logger.info(f"Downloading (attempt {attempt}/{self.max_retries}): {url} -> {output_path}")
                urllib.request.urlretrieve(url, output_path)
                logger.info(f"Downloaded successfully: {output_path}")
                return True
            except urllib.error.URLError as e:
                logger.warning(f"Attempt {attempt} failed - URL Error: {e}")
                if attempt < self.max_retries:
                    time.sleep(2 ** attempt)  # Exponential backoff: 2s, 4s, 8s
                else:
                    logger.error(f"Failed to download {url} after {self.max_retries} attempts")
            except Exception as e:
                logger.warning(f"Attempt {attempt} failed - Error: {e}")
                if attempt < self.max_retries:
                    time.sleep(2 ** attempt)
                else:
                    logger.error(f"Failed to download {url} after {self.max_retries} attempts")

        return False

    def download_cover(self, url, film_id, source):
        """Download film cover"""
        # Extract filename from URL
        parsed_url = urlparse(url)
        filename = Path(parsed_url.path).name

        output_dir = self.download_dir / source / film_id / 'cover'
        output_path = output_dir / filename

        if self.download_file(url, output_path):
            return str(output_path)
        return None

    def download_episode(self, url, film_id, ep_number, source):
        """Download episode video"""
        # Extract path from URL (remove query params)
        url_path = urlparse(url).path.strip('/')
        parts = url_path.split('/')

        # Create directory structure: source/id/ep/episode_number/...
        output_dir = self.download_dir / source / film_id / 'ep' / str(ep_number)
        output_dir.mkdir(parents=True, exist_ok=True)

        # Keep the subdirectory structure from URL
        if len(parts) >= 2:
            subdir = output_dir / parts[-2]
            subdir.mkdir(parents=True, exist_ok=True)
            output_path = subdir / parts[-1]
        else:
            output_path = output_dir / 'video.m3u8'

        if self.download_file(url, output_path):
            return str(output_path)
        return None

class ImportProcessor:
    def __init__(self, db, downloader):
        self.db = db
        self.downloader = downloader

    def process_json_file(self, json_file):
        """Process a single JSON file"""
        logger.info(f"Processing: {json_file}")

        # Mark as processing to prevent re-processing if crashed
        processing_file = json_file.with_name(json_file.stem + '_processing.json')
        try:
            json_file.rename(processing_file)
            logger.info(f"Marked as processing: {processing_file.name}")
        except Exception as e:
            logger.error(f"Error marking file as processing: {e}")
            return False

        try:
            with open(processing_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
        except Exception as e:
            logger.error(f"Error reading JSON file {processing_file}: {e}")
            # Restore original filename for retry
            try:
                processing_file.rename(json_file)
            except:
                pass
            return False

        # Extract film info
        source = data.get('source', 'unknown')
        film_data = data.get('drama', {})
        episodes = data.get('episodes', [])

        film_id = film_data.get('id')
        if not film_id:
            logger.error("No film ID in JSON file")
            # Restore original filename
            try:
                processing_file.rename(json_file)
            except:
                pass
            return False

        # Check if film already exists in database
        existing_film = self.db.get_film_pk(film_id)
        if existing_film:
            logger.warning(f"Film {film_id} already exists in database (skipping to avoid duplicates)")
            try:
                processing_file.rename(json_file.with_name(json_file.stem + '_done.json'))
            except:
                pass
            return True

        # Download cover
        cover_url = film_data.get('cover')
        cover_path = None
        if cover_url:
            cover_path = self.downloader.download_cover(cover_url, film_id, source)

        # Prepare film data for database
        db_film_data = {
            'id': film_id,
            'name': film_data.get('name', 'Unknown'),
            'description': film_data.get('description'),
            'cover_path': cover_path,
            'cover_path_source': film_data.get('cover'),
            'total_episodes': film_data.get('total_episodes'),
            'lang': film_data.get('lang'),
            'is_ai': film_data.get('is_ai', False),
            'source': source,
            'scraped_at': data.get('scraped_at')
        }

        # Insert film into database
        self.db.insert_film(db_film_data)

        # Get the internal film ID (pk)
        film_pk = self.db.get_film_pk(film_id)
        if not film_pk:
            logger.error(f"Failed to get film pk for {film_id}")
            return False

        # Download episodes
        logger.info(f"Downloading {len(episodes)} episodes for film {film_id}")

        for episode in episodes:
            ep_number = episode.get('ep')
            url = episode.get('url')

            if not url:
                logger.warning(f"No URL for episode {ep_number}")
                continue

            video_path = self.downloader.download_episode(url, film_id, ep_number, source)
            if video_path:
                self.db.insert_episode(film_pk, ep_number, video_path, url, url)

        # Rename _processing file to _done (mark as completed)
        done_file = processing_file.with_name(processing_file.stem.replace('_processing', '') + '_done.json')
        try:
            processing_file.rename(done_file)
            logger.info(f"Renamed to: {done_file}")
        except Exception as e:
            logger.error(f"Error renaming file to done: {e}")
            # Restore original filename if rename fails
            try:
                processing_file.rename(json_file)
            except:
                pass
            return False

        logger.info(f"Successfully processed: {json_file.name}")
        return True

    def scan_and_process(self):
        """Scan for unprocessed JSON files and process them"""
        logger.info("Scanning for JSON files...")

        # Find all JSON files (exclude .done and .processing)
        json_files = list(self.downloader.download_dir.parent.glob('idrama/*.json'))
        json_files = [f for f in json_files
                     if not f.name.endswith('_done.json')
                     and not f.name.endswith('_processing.json')]

        if not json_files:
            logger.info("No JSON files to process")
            return

        # Check for recovery files (.processing)
        processing_files = list(self.downloader.download_dir.parent.glob('idrama/*_processing.json'))
        if processing_files:
            logger.info(f"Found {len(processing_files)} incomplete processing files")
            # Handle recovery of crashed processing
            for pfile in processing_files:
                original_file = pfile.with_name(pfile.stem.replace('_processing', '') + '.json')
                if original_file.exists():
                    logger.warning(f"Recovering incomplete process: {original_file.name}")
                    pfile.unlink()  # Remove .processing marker
                else:
                    logger.info(f"Restoring: {pfile.name}")
                    # Rename back to normal .json for reprocessing
                    pfile.rename(original_file)

        json_files = list(self.downloader.download_dir.parent.glob('idrama/*.json'))
        json_files = [f for f in json_files
                     if not f.name.endswith('_done.json')
                     and not f.name.endswith('_processing.json')]

        if not json_files:
            logger.info("No JSON files to process")
            return

        logger.info(f"Found {len(json_files)} JSON files to process")

        for json_file in json_files:
            try:
                self.process_json_file(json_file)
            except Exception as e:
                logger.error(f"Error processing {json_file}: {e}")

def main():
    """Main function"""
    logger.info("Starting Import Tool")

    # Initialize components
    db = FilmDatabase(DB_PATH)
    downloader = VideoDownloader(DOWNLOAD_DIR)
    processor = ImportProcessor(db, downloader)

    # Initial scan
    processor.scan_and_process()

    # Periodic scanning
    logger.info(f"Starting periodic scan (interval: {SCAN_INTERVAL}s)")
    try:
        while True:
            time.sleep(SCAN_INTERVAL)
            processor.scan_and_process()
    except KeyboardInterrupt:
        logger.info("Shutting down...")

if __name__ == '__main__':
    main()
