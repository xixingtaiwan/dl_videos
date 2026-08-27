# Directory Structure for JSON Files

## Overview

The JSON file organization has been optimized for faster scanning and better file management:

```
idrama/
├── data/              ← New files to process (scanned by tool)
├── done/              ← Successfully processed files
├── error/             ← Files with processing errors
└── .DS_Store         (macOS, ignore)
```

## Benefits

✅ **Faster Scanning**: Only scan `idrama/data/` instead of entire `idrama/` directory
✅ **Better Organization**: Separate views for pending, completed, and failed files
✅ **Easier Debugging**: Error files grouped in one place
✅ **Scalability**: Efficient with thousands of files
✅ **Automatic Cleanup**: Processed files automatically moved away

## Directory Descriptions

### `idrama/data/`
- **Purpose**: JSON files awaiting processing
- **Typical files**: `idrama_12345.json`, `idrama_67890.json`
- **Auto-scan**: Tool scans this directory every 10 minutes
- **Recovery**: Files with `_processing` suffix are automatically recovered

### `idrama/done/`
- **Purpose**: Successfully processed files
- **Typical files**: `idrama_12345.json` (renamed from `idrama_12345_done.json`)
- **Content**: Video metadata + all episodes downloaded successfully
- **Action**: Manual archive or cleanup as needed

### `idrama/error/`
- **Purpose**: Files that failed during processing
- **Typical files**: `idrama_12345.json` (renamed from `idrama_12345_error.json`)
- **Why it failed**: Check `import_tool.log` for details
- **Action**: Fix issue and move back to `data/` to retry

## File Lifecycle

```
User adds file
    ↓
idrama/data/
    ↓
Tool starts processing
    ↓
Rename to *_processing.json (temporary)
    ↓
┌─────────────────────────┬────────────────────────┐
│                         │                        │
Download files succeed   OR  Download files fail
│                         │                        │
↓                         ↓
idrama/done/           idrama/error/
(Rename back to         (Rename back to
 normal .json)          normal .json)
│                        │
✓ Completed            ✗ Needs retry
```

## Usage Examples

### Add new files for processing
```bash
# Copy JSON files to data/ directory
cp /path/to/idrama_12345.json idrama/data/
cp /path/to/idrama_67890.json idrama/data/

# Tool will automatically process them
```

### Check processing status
```bash
# Pending files
ls -la idrama/data/

# Successfully processed
ls -la idrama/done/

# Failed files
ls -la idrama/error/
```

### Retry a failed file
```bash
# Move error file back to data/ to retry
mv idrama/error/idrama_12345.json idrama/data/

# Optionally remove *_processing suffix if present
rm idrama/data/idrama_12345_processing.json 2>/dev/null

# Tool will retry on next scan
```

### Archive completed files (optional)
```bash
# Keep only recent done files
ls -lt idrama/done/ | tail -n +50 | awk '{print $NF}' | xargs -I {} mv idrama/done/{} /archive/
```

## Setup

### For New Installations
Directories are created automatically on first run.

### For Existing Installations
Run the setup script:

```bash
python3 setup_directories.py
```

This will:
1. ✓ Create `data/`, `done/`, `error/` directories
2. ✓ Migrate existing `*_done.json` → `done/`
3. ✓ Migrate existing `*_error.json` → `error/`
4. ✓ Migrate incomplete `*_processing.json` → `data/` (for retry)
5. ✓ Show summary statistics

## Performance Impact

### Before (Single directory with all files)
```
Scanning 1000 files:
  • Check each file's suffix: 1000 operations
  • Filter results: 1000 filter checks
  • Time: ~100ms+ with many files
```

### After (Separate data, done, error directories)
```
Scanning 1000 files (100 pending, 850 done, 50 error):
  • Scan only idrama/data/: 100 operations
  • No filtering needed
  • Time: ~10ms
  • 10x faster!
```

## Monitoring

### Watch processing progress
```bash
watch -n 2 'echo "Pending:"; ls idrama/data/ 2>/dev/null | wc -l; \
             echo "Done:"; ls idrama/done/ 2>/dev/null | wc -l; \
             echo "Error:"; ls idrama/error/ 2>/dev/null | wc -l'
```

### Check log in real-time
```bash
tail -f import_tool.log
```

### Count files by status
```bash
echo "Summary:"; \
echo "  Data:  $(ls idrama/data 2>/dev/null | wc -l) files"; \
echo "  Done:  $(ls idrama/done 2>/dev/null | wc -l) files"; \
echo "  Error: $(ls idrama/error 2>/dev/null | wc -l) files"
```

## Troubleshooting

### Files stuck in processing
If files have `_processing.json` suffix:
- Tool crashed while processing
- Automatic recovery runs on next start
- Or manually remove `_processing` suffix

```bash
# List processing files
find idrama/data -name "*_processing.json"

# Manual recovery (rename them back)
for f in idrama/data/*_processing.json; do
  mv "$f" "${f%_processing.json}.json"
done
```

### Files not being processed
Check:
1. File is in `idrama/data/` ✓
2. File has `.json` extension ✓
3. Tool is running: `tail -f import_tool.log` ✓
4. Database configured properly ✓
5. Permissions: `ls -la idrama/data/` ✓

### Error directory keeps growing
Solution:
1. Check `import_tool.log` for actual errors
2. Fix the issue (URL expired, network error, etc.)
3. Move fixed files back to `data/` to retry
4. Or archive if unrecoverable

## File Naming Convention

| File Type | Format | Example | Location |
|-----------|--------|---------|----------|
| Pending | `{film_id}.json` | `idrama_12345.json` | `data/` |
| Processing (temp) | `{film_id}_processing.json` | `idrama_12345_processing.json` | `data/` |
| Completed | `{film_id}.json` | `idrama_12345.json` | `done/` |
| Error | `{film_id}.json` | `idrama_12345.json` | `error/` |

Note: The old suffixes (`_done`, `_error`) are no longer used. Files are now organized by directory instead.

## Best Practices

1. **Regular Cleanup**: Archive `done/` files periodically
2. **Error Investigation**: Check log before retrying `error/` files
3. **Backup**: Keep backups of important JSON files
4. **Monitoring**: Set up alerts for growing `error/` directory
5. **Testing**: Test with single file before bulk imports

## Backward Compatibility

✓ Fully backward compatible with old single-directory system
✓ Automatic migration via `setup_directories.py`
✓ Manual recovery for edge cases

## File Location Examples

```
Before:
  idrama/idrama_12345.json
  idrama/idrama_67890_done.json
  idrama/idrama_11111_error.json
  idrama/idrama_22222_processing.json

After:
  idrama/data/idrama_22222.json (recovered for retry)
  idrama/done/idrama_67890.json
  idrama/done/idrama_12345.json (if already processed)
  idrama/error/idrama_11111.json
```
