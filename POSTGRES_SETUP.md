# PostgreSQL Setup Guide

## Installation

### macOS (Homebrew)
```bash
brew install postgresql@15
brew services start postgresql@15
```

### Linux (Ubuntu/Debian)
```bash
sudo apt-get install postgresql postgresql-contrib
sudo systemctl start postgresql
```

### Windows
Download from https://www.postgresql.org/download/windows/

## Initial Setup

### 1. Connect to PostgreSQL
```bash
psql -U postgres
```

### 2. Create Database and User
```sql
-- Create database
CREATE DATABASE films_db;

-- Create user
CREATE USER video_user WITH PASSWORD 'your_secure_password';

-- Grant privileges
GRANT ALL PRIVILEGES ON DATABASE films_db TO video_user;

-- Connect to database
\c films_db

-- Grant schema privileges
GRANT ALL ON SCHEMA public TO video_user;

-- Exit
\q
```

### 3. Install Python PostgreSQL Driver
```bash
pip install psycopg2-binary
```

## Configuration

### 1. Edit `config.py`
```python
DATABASE_CONFIG = {
    'host': 'localhost',           # PostgreSQL host
    'port': 5432,                  # PostgreSQL port
    'user': 'video_user',          # Created user
    'password': 'your_secure_password',  # Your password
    'database': 'films_db',        # Database name
}
```

### 2. Test Connection
```bash
python3 -c "
import psycopg2
from config import DATABASE_CONFIG
try:
    conn = psycopg2.connect(**DATABASE_CONFIG)
    print('✓ Connection successful!')
    conn.close()
except Exception as e:
    print(f'✗ Connection failed: {e}')
"
```

## Running the Tool

### Using PostgreSQL Version
```bash
python3 import_tool_postgres.py
```

### Monitor Logs
```bash
tail -f import_tool.log
```

## Database Queries

### Connect to Database
```bash
psql -U video_user -d films_db -h localhost
```

### List Tables
```sql
\dt
```

### View Films
```sql
SELECT * FROM films;
```

### Count Records
```sql
SELECT COUNT(*) FROM films;
SELECT COUNT(*) FROM episodes;
```

### Find Specific Film
```sql
SELECT * FROM films WHERE film_id = '100000643080';
```

### Exit
```sql
\q
```

## Tools with PostgreSQL

### Query Tool (Update Needed)
Use `query_films_postgres.py` (will be created)

### Backup Tool
Use `backup_db_postgres.py` (will be created)

### Export Tool
Use `export_db_postgres.py` (will be created)

## Troubleshooting

### Connection Refused
- Check PostgreSQL is running: `pg_isready`
- Verify credentials in `config.py`
- Check host and port

### Authentication Failed
```bash
# Reset PostgreSQL password
psql -U postgres -c "ALTER USER video_user WITH PASSWORD 'new_password';"
```

### Database Already Exists
```bash
psql -U postgres -c "DROP DATABASE films_db;"
# Then create again per Initial Setup
```

### Permission Denied
```sql
psql -U postgres -d films_db
GRANT ALL ON ALL TABLES IN SCHEMA public TO video_user;
GRANT ALL ON ALL SEQUENCES IN SCHEMA public TO video_user;
```

## Converting from SQLite

### Export from SQLite
```bash
python3 export_db.py dump > backup.sql
```

### Import to PostgreSQL
```bash
psql -U video_user -d films_db < backup.sql
```

## Advantages of PostgreSQL

✓ Multi-user support
✓ Better concurrency
✓ Server-based (can be remote)
✓ Advanced features (JSON, arrays, etc.)
✓ Better for large datasets
✓ Native Python support
✓ Easier to scale

## Files

- `config.py` - Configuration file
- `import_tool_postgres.py` - Main tool for PostgreSQL
- `query_films_postgres.py` - Query tool (to be created)
- `backup_db_postgres.py` - Backup tool (to be created)
- `export_db_postgres.py` - Export tool (to be created)

## Next Steps

1. ✅ Install PostgreSQL
2. ✅ Create database and user
3. ✅ Install psycopg2: `pip install psycopg2-binary`
4. ✅ Edit `config.py` with your credentials
5. ✅ Run: `python3 import_tool_postgres.py`
6. ✅ Monitor: `tail -f import_tool.log`

Status: Ready to switch to PostgreSQL! 🚀
