# Multi-Format Video Download Support

## Summary of Changes

The video download tool has been upgraded to support **8 different video formats** instead of just M3U8. This allows downloading videos from a much wider range of sources and streaming services.

## What Changed

### Removed
- ❌ `import_tool.py` (SQLite version) - No longer needed, using PostgreSQL exclusively

### Updated
- ✅ `import_tool_postgres.py` - Enhanced with multi-format support
  - Added format detection system
  - Added format-specific download handlers
  - Added database schema to track video format

### Added
- ✅ `SUPPORTED_FORMATS.md` - Comprehensive guide to all supported formats
- ✅ `migrate_db.py` - Database migration script for existing installations
- ✅ `test_video_formats.py` - Test suite for format detection
- ✅ `MULTI_FORMAT_SUPPORT.md` - This file

## Supported Video Formats

| Format | Type | Detection | Handler |
|--------|------|-----------|---------|
| **HLS/M3U8** | Streaming | `.m3u8`, `hls` in URL | Parse playlist + download segments |
| **DASH/MPD** | Streaming | `.mpd`, `dash` in URL | Parse manifest + download segments |
| **MP4** | Progressive | `.mp4` extension | Direct download |
| **MKV** | Progressive | `.mkv` extension | Direct download |
| **WebM** | Progressive | `.webm` extension | Direct download |
| **FLV** | Progressive | `.flv` extension | Direct download |
| **MOV** | Progressive | `.mov` extension | Direct download |
| **Unknown** | Fallback | No match | Attempt direct download |

## Key Implementation Details

### 1. Format Detection (`detect_video_format()`)
```python
def detect_video_format(self, url):
    # Returns: 'hls', 'dash', 'mp4', 'mkv', 'webm', 'flv', 'mov', or 'unknown'
    # Checks URL extensions and keywords
    # Falls back to unknown for ambiguous URLs
```

### 2. Format-Specific Handlers

**HLS Handler** (`download_hls_episode()`)
- Downloads M3U8 playlist
- Parses for `.ts` segment URLs
- Downloads all video segments
- Reconstructs from segments

**DASH Handler** (`download_dash_episode()`)
- Downloads MPD XML manifest
- Parses segment information
- Downloads video segments
- Supports adaptive bitrate

**Direct Handler** (`download_direct_video()`)
- Downloads complete video file in one request
- Supports MP4, MKV, WebM, FLV, MOV formats
- Simple and reliable for progressive downloads

### 3. Database Schema Changes

**New Column in `episodes` table:**
```sql
ALTER TABLE episodes
ADD COLUMN video_format TEXT DEFAULT 'unknown';
```

This tracks the format of each downloaded video:
- `hls` - HTTP Live Streaming
- `dash` - Dynamic Adaptive Streaming  
- `mp4`, `mkv`, `webm`, `flv`, `mov` - Direct download formats
- `unknown` - Could not determine format

## Migration Guide

### For New Installations
No action needed. The schema is created automatically with the new column.

### For Existing Installations

Run the migration script to add the new column:

```bash
python3 migrate_db.py
```

This will:
1. ✓ Add the `video_format` column to the `episodes` table
2. ✓ Attempt to infer formats from existing file paths
3. ✓ Show statistics of detected formats

**Migration Logic:**
- Files ending in `.m3u8` → marked as `hls`
- Files ending in `.mpd` → marked as `dash`
- Files ending in `.ts` → marked as `hls`
- Etc. for other formats
- Unknown formats → marked as `unknown`

## Testing

Run the comprehensive test suite:

```bash
python3 test_video_formats.py
```

This will verify:
- ✓ 13 format detection test cases
- ✓ 25+ URL pattern coverage tests
- ✓ All supported formats are recognized

**Test Results:**
```
Format Detection: ✓ PASS
Format Coverage:  ✓ PASS
```

## Usage Examples

The tool now automatically handles these video URLs:

```python
# HLS/M3U8 Streaming
https://example.com/videos/episode.m3u8
https://cdn.streaming.tv/stream.m3u8?token=xyz123

# DASH Streaming
https://example.com/dash/manifest.mpd
https://premium.video/dash?quality=hd&auth=token

# Direct MP4
https://example.com/videos/episode.mp4
https://cdn.example.com/media/1080p.mp4?v=123

# Other Formats
https://example.com/archive/video.mkv
https://example.com/web/player.webm
https://example.com/legacy/old.flv
https://example.com/mac/quicktime.mov
```

## Architecture

```
import_tool_postgres.py
    │
    ├─ VideoDownloader class
    │   ├─ detect_video_format(url) → format type
    │   ├─ download_episode(url, ...) → main entry point
    │   │   ├─ download_hls_episode() → for HLS
    │   │   ├─ download_dash_episode() → for DASH
    │   │   ├─ download_direct_video() → for MP4, MKV, etc.
    │   │   └─ (fallback to direct) → for unknown
    │   └─ download_file(url, path) → generic download with retries
    │
    ├─ ImportProcessor class
    │   └─ process_json_file() → orchestrates downloads
    │       └─ Detects format for each episode
    │       └─ Routes to appropriate handler
    │       └─ Saves format info to database
    │
    └─ FilmDatabase class
        └─ insert_episode() → stores video_format column
```

## Benefits

1. **Wider Source Support** - Can now download from more streaming services
2. **Automatic Format Detection** - No manual configuration needed
3. **Format Tracking** - Database tracks what format each video is
4. **Fallback Handling** - Unknown formats attempted as direct downloads
5. **Extensible Design** - Easy to add more formats in future

## Future Enhancements

Possible improvements:
- Add video format conversion (HLS → MP4 muxing)
- Implement adaptive bitrate selection for DASH
- Add support for RTMP, HDS, or other protocols
- Download subtitles and captions
- Parallel segment downloading for faster speeds
- Handle DRM-protected content (where legal)

## Troubleshooting

**Q: Why isn't my URL being detected?**
A: Check `test_video_formats.py` output. URL must contain format extension or keyword.

**Q: How do I add support for a new format?**
A: 
1. Add detection logic to `detect_video_format()`
2. Create download handler method
3. Add routing in `download_episode()`
4. Update tests and documentation

**Q: What if a video is in a format not listed?**
A: The tool attempts direct download as MP4 fallback.

**Q: Does this work with DRM/encrypted videos?**
A: No - only for publicly accessible, unencrypted videos.

## Files Modified

- `import_tool_postgres.py` - Core downloader with format support (+190 lines)
- `config.py` - Configuration (unchanged)
- `migrate_db.py` - NEW: Database migration script
- `test_video_formats.py` - NEW: Comprehensive test suite
- `SUPPORTED_FORMATS.md` - NEW: Format documentation
- `MULTI_FORMAT_SUPPORT.md` - NEW: This guide

## Backward Compatibility

✓ Fully backward compatible
- Existing HLS/M3U8 downloads work exactly as before
- Database migration is non-destructive
- Can be rolled back if needed

## Questions?

See:
- `SUPPORTED_FORMATS.md` - Format specifications
- `test_video_formats.py` - Working examples
- `import_tool_postgres.py` - Implementation details
