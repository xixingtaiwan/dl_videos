#!/usr/bin/env python3
"""
Video Import Tool - PostgreSQL Version
Download and import videos from JSON config files
"""
import json
import time
import logging
import glob
import shutil
from pathlib import Path
from datetime import datetime
import urllib.request
import urllib.error
from urllib.parse import urlparse

try:
    import psycopg2
    from psycopg2.extras import RealDictCursor
except ImportError:
    print("Error: psycopg2 not installed")
    print("Install with: pip install psycopg2-binary")
    exit(1)

from config import (
    BASE_DIR, JSON_DIR, DOWNLOAD_DIR, DATABASE_CONFIG,
    SCAN_INTERVAL, LOG_FILE, MAX_RETRIES, RETRY_BACKOFF
)

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(LOG_FILE),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class FilmDatabase:
    def __init__(self, db_config):
        self.db_config = db_config
        self.init_db()

    def get_connection(self):
        """Get database connection"""
        return psycopg2.connect(**self.db_config)

    def init_db(self):
        """Initialize database schema"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()

            # Films table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS films (
                    id SERIAL PRIMARY KEY,
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
                    id SERIAL PRIMARY KEY,
                    film_id INTEGER NOT NULL REFERENCES films(id),
                    ep_number INTEGER NOT NULL,
                    video_path TEXT,
                    video_path_source TEXT,
                    url TEXT,
                    status TEXT DEFAULT 'pending',
                    downloaded_at TIMESTAMP,
                    UNIQUE(film_id, ep_number)
                )
            ''')

            conn.commit()
            conn.close()
            logger.info("Database initialized successfully")
        except psycopg2.Error as e:
            logger.error(f"Database error: {e}")
            raise

    def insert_film(self, film_data):
        """Insert film metadata into database"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()

            # Convert boolean to integer
            is_ai = 1 if film_data.get('is_ai') else 0

            cursor.execute('''
                INSERT INTO films
                (film_id, name, description, cover_path, cover_path_source,
                 total_episodes, lang, is_ai, source, scraped_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (film_id) DO UPDATE SET
                    name = EXCLUDED.name,
                    description = EXCLUDED.description,
                    cover_path = EXCLUDED.cover_path,
                    cover_path_source = EXCLUDED.cover_path_source,
                    total_episodes = EXCLUDED.total_episodes,
                    lang = EXCLUDED.lang,
                    is_ai = EXCLUDED.is_ai,
                    source = EXCLUDED.source,
                    scraped_at = EXCLUDED.scraped_at
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
            conn.close()
            logger.info(f"Inserted film: {film_data['id']} - {film_data['name']}")
        except psycopg2.Error as e:
            logger.error(f"Error inserting film: {e}")
            conn.rollback()
            conn.close()

    def get_film_pk(self, film_id):
        """Get internal ID for a film by film_id"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            cursor.execute('SELECT id FROM films WHERE film_id = %s', (film_id,))
            result = cursor.fetchone()
            conn.close()
            return result[0] if result else None
        except psycopg2.Error as e:
            logger.error(f"Error getting film pk: {e}")
            return None

    def insert_episode(self, film_pk, ep_number, video_path, video_path_source, url):
        """Insert episode into database"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()

            cursor.execute('''
                INSERT INTO episodes
                (film_id, ep_number, video_path, video_path_source, url, status, downloaded_at)
                VALUES (%s, %s, %s, %s, %s, %s, CURRENT_TIMESTAMP)
                ON CONFLICT (film_id, ep_number) DO UPDATE SET
                    video_path = EXCLUDED.video_path,
                    video_path_source = EXCLUDED.video_path_source,
                    url = EXCLUDED.url,
                    status = 'completed',
                    downloaded_at = CURRENT_TIMESTAMP
            ''', (film_pk, ep_number, video_path, video_path_source, url, 'completed'))
            conn.commit()
            conn.close()
        except psycopg2.Error as e:
            logger.error(f"Error inserting episode: {e}")
            conn.rollback()
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
                logger.info(f"Downloading (attempt {attempt}/{self.max_retries}): {url}")
                urllib.request.urlretrieve(url, output_path)
                logger.info(f"Downloaded successfully: {output_path}")
                return True
            except urllib.error.URLError as e:
                logger.warning(f"Attempt {attempt} failed - URL Error: {e}")
                if attempt < self.max_retries:
                    wait_time = 2 ** attempt
                    time.sleep(wait_time)
                else:
                    logger.error(f"Failed to download {url} after {self.max_retries} attempts")
            except Exception as e:
                logger.warning(f"Attempt {attempt} failed - Error: {e}")
                if attempt < self.max_retries:
                    wait_time = 2 ** attempt
                    time.sleep(wait_time)
                else:
                    logger.error(f"Failed to download {url} after {self.max_retries} attempts")

        return False

    def download_cover(self, url, film_id, source):
        """Download film cover"""
        parsed_url = urlparse(url)
        filename = Path(parsed_url.path).name
        output_dir = self.download_dir / source / film_id / 'cover'
        output_path = output_dir / filename

        if self.download_file(url, output_path):
            return str(output_path)
        return None

    def download_episode(self, url, film_id, ep_number, source):
        """Download episode video (HLS M3U8 + segments)"""
        url_path = urlparse(url).path.strip('/')
        parts = url_path.split('/')
        output_dir = self.download_dir / source / film_id / 'ep' / str(ep_number)
        output_dir.mkdir(parents=True, exist_ok=True)

        if len(parts) >= 2:
            subdir = output_dir / parts[-2]
            subdir.mkdir(parents=True, exist_ok=True)
            m3u8_path = subdir / parts[-1]
        else:
            subdir = output_dir
            m3u8_path = output_dir / 'video.m3u8'

        # Download M3U8 playlist
        if not self.download_file(url, m3u8_path):
            return None

        # Parse and download all video segments
        try:
            with open(m3u8_path, 'r') as f:
                m3u8_content = f.read()

            # Extract segment URLs (lines starting with /)
            segments = [line.strip() for line in m3u8_content.split('\n')
                       if line.strip().startswith('/')]

            logger.info(f"Found {len(segments)} video segments in M3U8")

            # Build base URL (domain only: https://v-a.idrama.video)
            parsed = urlparse(url)
            base_url = f"{parsed.scheme}://{parsed.netloc}"

            # Download each segment
            for segment_path in segments:
                # Segment path is absolute from domain: /hash1/hash2.ts?ts=...&secret=...
                segment_url = base_url + segment_path
                # Extract filename from segment URL (remove query params)
                segment_file = segment_path.split('/')[-1].split('?')[0]
                segment_out = subdir / segment_file
                self.download_file(segment_url, segment_out)
        except Exception as e:
            logger.warning(f"Error downloading segments: {e}")

        return str(m3u8_path)

class ImportProcessor:
    def __init__(self, db, downloader):
        self.db = db
        self.downloader = downloader
        self.download_errors = []

    def process_json_file(self, json_file):
        """Process a single JSON file"""
        logger.info(f"Processing: {json_file}")
        self.download_errors = []  # Reset errors for this file

        # Mark as processing
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
            logger.error(f"Error reading JSON file: {e}")
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
            try:
                processing_file.rename(json_file)
            except:
                pass
            return False

        # Check if film already exists
        existing_film = self.db.get_film_pk(film_id)
        if existing_film:
            logger.warning(f"Film {film_id} already exists (skipping to avoid duplicates)")
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
            if not cover_path:
                self.download_errors.append(f"Cover download failed: {cover_url}")

        # Prepare film data
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

        # Insert film
        self.db.insert_film(db_film_data)

        # Get internal film ID
        film_pk = self.db.get_film_pk(film_id)
        if not film_pk:
            logger.error(f"Failed to get film pk for {film_id}")
            return self._handle_error(film_id, processing_file)

        # Download episodes
        logger.info(f"Downloading {len(episodes)} episodes for film {film_id}")
        episodes_success = 0

        for episode in episodes:
            ep_number = episode.get('ep')
            url = episode.get('url')

            if not url:
                logger.warning(f"No URL for episode {ep_number}")
                continue

            video_path = self.downloader.download_episode(url, film_id, ep_number, source)
            if video_path:
                self.db.insert_episode(film_pk, ep_number, video_path, url, url)
                episodes_success += 1
            else:
                self.download_errors.append(f"Episode {ep_number} download failed: {url}")

        # Check if all episodes downloaded successfully
        if self.download_errors:
            logger.error(f"❌ Download errors detected ({len(self.download_errors)} errors)")
            for err in self.download_errors:
                logger.error(f"   - {err}")
            return self._handle_error(film_id, processing_file)

        # Rename to done
        done_file = processing_file.with_name(processing_file.stem.replace('_processing', '') + '_done.json')
        try:
            processing_file.rename(done_file)
            logger.info(f"Renamed to: {done_file}")
        except Exception as e:
            logger.error(f"Error renaming file: {e}")
            return self._handle_error(film_id, processing_file)

        logger.info(f"✅ Successfully processed: {json_file.name} ({episodes_success} episodes)")
        return True

    def _handle_error(self, film_id, processing_file):
        """Handle processing error: rollback database and files"""
        logger.error(f"🔄 Rolling back for film {film_id}...")

        # Delete from database
        try:
            conn = self.db.get_connection()
            cursor = conn.cursor()
            cursor.execute("DELETE FROM episodes WHERE film_id IN (SELECT id FROM films WHERE film_id = %s)", (film_id,))
            cursor.execute("DELETE FROM films WHERE film_id = %s", (film_id,))
            conn.commit()
            conn.close()
            logger.info(f"   ✓ Database records deleted")
        except Exception as e:
            logger.warning(f"   ⚠ Error deleting database records: {e}")

        # Delete downloaded files
        try:
            video_dir = self.downloader.download_dir / '*' / film_id
            import glob
            for path in glob.glob(str(video_dir)):
                if Path(path).is_dir():
                    import shutil
                    shutil.rmtree(path)
                    logger.info(f"   ✓ Deleted: {path}")
        except Exception as e:
            logger.warning(f"   ⚠ Error deleting video files: {e}")

        # Rename to error
        error_file = processing_file.with_name(processing_file.stem.replace('_processing', '') + '_error.json')
        try:
            processing_file.rename(error_file)
            logger.error(f"   ✓ Renamed to: {error_file.name}")
        except Exception as e:
            logger.error(f"   ⚠ Error renaming to error file: {e}")
            try:
                processing_file.rename(processing_file.with_name(processing_file.stem.replace('_processing', '') + '.json'))
            except:
                pass

        return False

    def scan_and_process(self):
        """Scan for unprocessed JSON files"""
        logger.info("Scanning for JSON files...")

        # Find all JSON files
        json_files = list(JSON_DIR.glob('*.json'))
        json_files = [f for f in json_files
                     if not f.name.endswith('_done.json')
                     and not f.name.endswith('_processing.json')]

        # Handle recovery files
        processing_files = list(JSON_DIR.glob('*_processing.json'))
        if processing_files:
            logger.info(f"Found {len(processing_files)} incomplete processing files")
            for pfile in processing_files:
                original_file = pfile.with_name(pfile.stem.replace('_processing', '') + '.json')
                if original_file.exists():
                    logger.warning(f"Recovering: {original_file.name}")
                    pfile.unlink()
                else:
                    logger.info(f"Restoring: {pfile.name}")
                    pfile.rename(original_file)

        json_files = list(JSON_DIR.glob('*.json'))
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
    logger.info("Starting Import Tool (PostgreSQL)")

    # Check database config
    if DATABASE_CONFIG['password'] == 'your_password':
        logger.error("❌ ERROR: PostgreSQL password not configured!")
        logger.error("   Edit config.py and set your PostgreSQL password")
        logger.error("   Then run: python3 import_tool_postgres.py")
        return

    # Initialize components
    try:
        db = FilmDatabase(DATABASE_CONFIG)
        downloader = VideoDownloader(DOWNLOAD_DIR, MAX_RETRIES)
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

    except Exception as e:
        logger.error(f"Fatal error: {e}")

if __name__ == '__main__':
    main()
