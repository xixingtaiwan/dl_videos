# Supported Video Formats

## Overview
The video download tool now supports multiple video streaming and storage formats.

## Supported Formats

### Streaming Protocols

#### 1. **HLS (HTTP Live Streaming)** - `.m3u8`
- **Description**: Apple's HTTP Live Streaming protocol
- **Detection**: `.m3u8` extension or `hls` in URL
- **How it works**:
  - Downloads the M3U8 playlist
  - Automatically finds and downloads all `.ts` video segments
  - Reconstructs the full video from segments
- **Common use**: Live streaming, on-demand video

#### 2. **DASH (Dynamic Adaptive Streaming over HTTP)** - `.mpd`
- **Description**: MPEG-DASH streaming protocol with adaptive bitrate
- **Detection**: `.mpd` extension or `dash` in URL
- **How it works**:
  - Parses the MPD (Media Presentation Description) XML manifest
  - Extracts segment URLs from the manifest
  - Downloads all video segments
  - Supports multiple quality levels
- **Common use**: Professional streaming services, adaptive quality streaming

### Progressive Download (Direct Download)

#### 3. **MP4** - `.mp4`
- **Description**: MPEG-4 video container format
- **Detection**: `.mp4` extension in URL
- **How it works**: Direct download of complete video file
- **Common use**: Most common video format

#### 4. **Matroska** - `.mkv`
- **Description**: Open-source container format supporting multiple codecs
- **Detection**: `.mkv` extension in URL
- **How it works**: Direct download of complete video file
- **Common use**: High-quality archival, flexible container

#### 5. **WebM** - `.webm`
- **Description**: Open web media format
- **Detection**: `.webm` extension in URL
- **How it works**: Direct download of complete video file
- **Common use**: Web video, VP8/VP9 codec videos

#### 6. **Flash Video** - `.flv`
- **Description**: Flash video format
- **Detection**: `.flv` extension in URL
- **How it works**: Direct download of complete video file
- **Common use**: Legacy videos

#### 7. **QuickTime** - `.mov`
- **Description**: Apple QuickTime video format
- **Detection**: `.mov` extension in URL
- **How it works**: Direct download of complete video file
- **Common use**: Apple ecosystem videos

### Fallback

#### 8. **Unknown Format**
- If format cannot be detected, the tool:
  1. Attempts direct download as MP4
  2. Logs the attempt with original URL
  3. Stores as generic video file

## Format Detection

The tool automatically detects the video format by:
1. Checking for `.m3u8`, `.mpd`, `.mp4`, `.mkv`, `.webm`, `.flv`, `.mov` extensions
2. Looking for format keywords in the URL (`hls`, `dash`)
3. Analyzing URL patterns (e.g., `.ts?` files indicate HLS)
4. Falling back to generic handler if unknown

## Database Storage

The `episodes` table now includes a `video_format` column that stores:
- `hls` - HLS/M3U8 streaming
- `dash` - DASH streaming
- `mp4` - MPEG-4 format
- `mkv` - Matroska format
- `webm` - WebM format
- `flv` - Flash video
- `mov` - QuickTime format
- `unknown` - Could not determine format

## Example Usage

```python
# The tool automatically handles these URLs:

# HLS
https://example.com/videos/episode.m3u8

# DASH
https://example.com/videos/episode.mpd

# Direct MP4
https://example.com/videos/episode.mp4

# Mixed URLs - auto-detected
https://example.com/stream.m3u8?token=xyz
https://example.com/dash/manifest.mpd?quality=hd
https://example.com/direct/video.mp4
```

## Implementation Details

### VideoDownloader Class Methods

- `detect_video_format(url)` - Identifies video format from URL
- `download_hls_episode(url, output_dir)` - Handles HLS streams
- `download_dash_episode(url, output_dir)` - Handles DASH streams  
- `download_direct_video(url, output_dir, format_type)` - Handles direct file downloads
- `download_episode(url, film_id, ep_number, source)` - Main entry point, routes to appropriate handler

### Database Changes

Added `video_format` column to `episodes` table to track format type for each downloaded video.

## Limitations

- DASH parsing is simplified; complex MPD structures may not be fully supported
- Segment encryption/DRM is not handled
- Adaptive bitrate selection is not automatic (highest quality assumed)
- Requires internet access for all download operations

## Future Enhancements

Possible improvements:
- Add video format conversion support (HLS to MP4 muxing)
- Implement adaptive bitrate selection for DASH
- Add support for more streaming protocols (RTMP, HDS)
- Add subtitle/caption download support
