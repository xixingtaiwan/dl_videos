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
                    video_format TEXT DEFAULT 'unknown',
                    status TEXT DEFAULT 'pending',
                    downloaded_at TIMESTAMP,
                    UNIQUE(film_id, ep_number)
                )
            ''')

            # Add video_format column if it doesn't exist (for existing tables)
            cursor.execute('''
                ALTER TABLE episodes
                ADD COLUMN IF NOT EXISTS video_format TEXT DEFAULT 'unknown'
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

    def insert_episode(self, film_pk, ep_number, video_path, video_path_source, url, video_format='unknown'):
        """Insert episode into database"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()

            cursor.execute('''
                INSERT INTO episodes
                (film_id, ep_number, video_path, video_path_source, url, video_format, status, downloaded_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s, CURRENT_TIMESTAMP)
                ON CONFLICT (film_id, ep_number) DO UPDATE SET
                    video_path = EXCLUDED.video_path,
                    video_path_source = EXCLUDED.video_path_source,
                    url = EXCLUDED.url,
                    video_format = EXCLUDED.video_format,
                    status = 'completed',
                    downloaded_at = CURRENT_TIMESTAMP
            ''', (film_pk, ep_number, video_path, video_path_source, url, video_format, 'completed'))
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

    def detect_video_format(self, url):
        """Detect video format from URL"""
        url_lower = url.lower()

        if '.m3u8' in url_lower or 'hls' in url_lower:
            return 'hls'
        elif '.mpd' in url_lower or 'dash' in url_lower:
            return 'dash'
        elif '.mp4' in url_lower:
            return 'mp4'
        elif '.mkv' in url_lower:
            return 'mkv'
        elif '.webm' in url_lower:
            return 'webm'
        elif '.flv' in url_lower:
            return 'flv'
        elif '.mov' in url_lower:
            return 'mov'
        else:
            # Default fallback - try to guess from URL structure
            if url_lower.endswith('.ts') or '.ts?' in url_lower:
                return 'hls'
            return 'unknown'

    def download_hls_episode(self, url, output_dir):
        """Download HLS M3U8 playlist and all segments"""
        url_path = urlparse(url).path.strip('/')
        parts = url_path.split('/')

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

            segments = [line.strip() for line in m3u8_content.split('\n')
                       if line.strip().startswith('/')]

            logger.info(f"Found {len(segments)} video segments in M3U8")

            parsed = urlparse(url)
            base_url = f"{parsed.scheme}://{parsed.netloc}"

            for segment_path in segments:
                segment_url = base_url + segment_path
                segment_file = segment_path.split('/')[-1].split('?')[0]
                segment_out = subdir / segment_file
                self.download_file(segment_url, segment_out)
        except Exception as e:
            logger.warning(f"Error downloading HLS segments: {e}")

        return str(m3u8_path)

    def download_dash_episode(self, url, output_dir):
        """Download DASH MPD manifest and all segments"""
        try:
            import xml.etree.ElementTree as ET
        except ImportError:
            logger.error("XML parsing not available for DASH")
            return None

        url_path = urlparse(url).path.strip('/')
        parts = url_path.split('/')

        subdir = output_dir / 'dash'
        subdir.mkdir(parents=True, exist_ok=True)
        mpd_filename = parts[-1] if parts else 'video.mpd'
        mpd_path = subdir / mpd_filename

        # Download MPD manifest
        if not self.download_file(url, mpd_path):
            return None

        # Parse MPD and download segments
        try:
            tree = ET.parse(mpd_path)
            root = tree.getroot()

            # Extract segment URLs from MPD (simplified parsing)
            segments = []
            for elem in root.iter():
                if 'media' in elem.tag.lower() or 'representation' in elem.tag.lower():
                    for child in elem:
                        if 'segmenturl' in child.tag.lower():
                            media_attr = child.get('media')
                            if media_attr:
                                segments.append(media_attr)

            logger.info(f"Found {len(segments)} video segments in DASH MPD")

            parsed = urlparse(url)
            base_url = f"{parsed.scheme}://{parsed.netloc}"
            # Get base path from MPD URL
            mpd_path_parts = urlparse(url).path.rsplit('/', 1)
            base_path = mpd_path_parts[0] if len(mpd_path_parts) > 1 else ''

            for segment in segments:
                if not segment:
                    continue

                if segment.startswith('http'):
                    segment_url = segment
                elif segment.startswith('/'):
                    segment_url = base_url + segment
                else:
                    segment_url = base_url + base_path + '/' + segment

                segment_file = segment.split('/')[-1].split('?')[0]
                segment_out = subdir / segment_file
                self.download_file(segment_url, segment_out)
        except Exception as e:
            logger.warning(f"Error downloading DASH segments: {e}")

        return str(mpd_path)

    def download_direct_video(self, url, output_dir, format_type):
        """Download direct video file (MP4, MKV, WebM, etc.)"""
        url_path = urlparse(url).path.strip('/')

        # Determine filename
        filename = url_path.split('/')[-1].split('?')[0]
        if not filename or '.' not in filename:
            filename = f'video.{format_type}'

        output_path = output_dir / filename

        if self.download_file(url, output_path):
            return str(output_path)
        return None

    def download_episode(self, url, film_id, ep_number, source):
        """Download episode video in any supported format"""
        output_dir = self.download_dir / source / film_id / 'ep' / str(ep_number)
        output_dir.mkdir(parents=True, exist_ok=True)

        # Detect format
        video_format = self.detect_video_format(url)
        logger.info(f"Detected video format: {video_format} for episode {ep_number}")

        # Route to appropriate handler
        if video_format == 'hls':
            return self.download_hls_episode(url, output_dir)
        elif video_format == 'dash':
            return self.download_dash_episode(url, output_dir)
        elif video_format in ['mp4', 'mkv', 'webm', 'flv', 'mov']:
            return self.download_direct_video(url, output_dir, video_format)
        else:
            # Fallback: try direct download
            logger.info(f"Using fallback download for: {url}")
            return self.download_direct_video(url, output_dir, 'mp4')

class ImportProcessor:
    def __init__(self, db, downloader):
        self.db = db
        self.downloader = downloader
        self.download_errors = []

    def process_json_file(self, json_file, data_dir, done_dir, error_dir):
        """Process a single JSON file"""
        logger.info(f"Processing: {json_file.name}")
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
                done_file = done_dir / json_file.name
                processing_file.rename(done_file)
                logger.info(f"Moved to: idrama/done/{done_file.name}")
            except Exception as e:
                logger.error(f"Error moving file to done: {e}")
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

            video_format = self.downloader.detect_video_format(url)
            video_path = self.downloader.download_episode(url, film_id, ep_number, source)
            if video_path:
                self.db.insert_episode(film_pk, ep_number, video_path, url, url, video_format)
                episodes_success += 1
            else:
                self.download_errors.append(f"Episode {ep_number} download failed: {url}")

        # Check if all episodes downloaded successfully
        if self.download_errors:
            logger.error(f"❌ Download errors detected ({len(self.download_errors)} errors)")
            for err in self.download_errors:
                logger.error(f"   - {err}")
            return self._handle_error(film_id, processing_file, error_dir)

        # Move to done directory
        try:
            done_file = done_dir / json_file.name
            processing_file.rename(done_file)
            logger.info(f"✅ Moved to: idrama/done/{done_file.name}")
        except Exception as e:
            logger.error(f"Error moving file to done: {e}")
            return self._handle_error(film_id, processing_file, error_dir)

        logger.info(f"✅ Successfully processed: {json_file.name} ({episodes_success} episodes)")
        return True

    def _handle_error(self, film_id, processing_file, error_dir):
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

        # Move to error directory
        try:
            # Get original filename without _processing suffix
            original_name = processing_file.stem.replace('_processing', '') + '.json'
            error_file = error_dir / original_name
            processing_file.rename(error_file)
            logger.error(f"   ✓ Moved to: idrama/error/{error_file.name}")
        except Exception as e:
            logger.error(f"   ⚠ Error moving to error directory: {e}")
            try:
                # Fallback: remove _processing suffix and keep in data dir
                processing_file.rename(processing_file.with_name(processing_file.stem.replace('_processing', '') + '.json'))
            except:
                pass

        return False

    def _init_directories(self):
        """Initialize data, done, and error directories"""
        data_dir = JSON_DIR / 'data'
        done_dir = JSON_DIR / 'done'
        error_dir = JSON_DIR / 'error'

        data_dir.mkdir(parents=True, exist_ok=True)
        done_dir.mkdir(parents=True, exist_ok=True)
        error_dir.mkdir(parents=True, exist_ok=True)

        return data_dir, done_dir, error_dir

    def scan_and_process(self):
        """Scan for unprocessed JSON files in data directory"""
        logger.info("Scanning for JSON files...")

        # Initialize directories
        data_dir, done_dir, error_dir = self._init_directories()

        # Handle recovery files (_processing) in data directory
        processing_files = list(data_dir.glob('*_processing.json'))
        if processing_files:
            logger.info(f"Found {len(processing_files)} incomplete processing files - recovering...")
            for pfile in processing_files:
                # Remove _processing marker to retry
                original_file = pfile.with_name(pfile.stem.replace('_processing', '') + '.json')
                try:
                    pfile.unlink()
                    logger.warning(f"Recovered: {original_file.name} - will retry")
                except Exception as e:
                    logger.error(f"Error recovering {pfile.name}: {e}")

        # Find all JSON files in data directory
        json_files = list(data_dir.glob('*.json'))
        json_files = [f for f in json_files if not f.name.endswith('_processing.json')]

        if not json_files:
            logger.info("No JSON files to process in idrama/data/")
            return

        logger.info(f"Found {len(json_files)} JSON files to process in idrama/data/")

        for json_file in json_files:
            try:
                self.process_json_file(json_file, data_dir, done_dir, error_dir)
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
