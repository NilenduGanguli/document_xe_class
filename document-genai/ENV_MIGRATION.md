# Environment Configuration Migration

## Overview

The `document-services` module has been updated to use `env.sh` for environment configuration instead of `.env` files, matching the pattern used in the `document-extraction` module.

## What Changed

### Before (Old Approach)
- Used `.env` file for environment variables
- Required `python-dotenv` package
- `load_dotenv()` calls in Python code
- Docker Compose read from `.env` file

### After (New Approach)
- Uses `env.sh` shell script for environment variables
- No `python-dotenv` dependency
- Environment sourced in `entrypoint.sh`
- Docker Compose uses explicit environment injection

## Files Modified

### 1. Created: `env.sh`
```bash
#!/bin/bash
# Environment variables for document services

export PORT=8000
export FRONTEND_PORT=8501
export GOOGLE_API_KEY="${GOOGLE_API_KEY:-your_api_key_here}"
export DATABASE_URL="${DATABASE_URL:-postgresql+asyncpg://admin:password123@postgres:5432/document_services}"
# ... more variables
```

### 2. Created: `run.sh`
Service management script with commands:
- `./run.sh build` - Build Docker images
- `./run.sh up` - Start services
- `./run.sh down` - Stop services
- `./run.sh status` - Check service status
- `./run.sh logs` - View logs

### 3. Modified: `entrypoint.sh`
Now sources `env.sh` at startup:
```bash
#!/bin/bash
set -e

# Source environment variables
source /app/env.sh

# ... rest of startup logic
```

### 4. Modified: Python Files
Removed `load_dotenv()` calls from:
- `backend/src/config/llm_config.py`
- `backend/src/extractors/classifier.py`

### 5. Modified: `requirements.txt`
Removed:
```
python-dotenv>=1.0.0
```

### 6. Modified: `docker-compose.yml`
Simplified environment configuration with explicit values from `env.sh`.

### 7. Deleted: `.env.example`
No longer needed - `env.sh` serves as both template and configuration.

## How to Use

### Setup

1. **Edit `env.sh` with your API key:**
   ```bash
   nano env.sh
   ```
   
   Update this line:
   ```bash
   export GOOGLE_API_KEY="your_actual_api_key_here"
   ```

2. **Build and start services:**
   ```bash
   ./run.sh build
   ./run.sh up
   ```

3. **Check status:**
   ```bash
   ./run.sh status
   ```

### Alternative: Docker Compose Directly

If you prefer using docker-compose directly:

```bash
# Set environment variables first
export GOOGLE_API_KEY="your_api_key_here"

# Start services
docker-compose up -d

# View logs
docker-compose logs -f
```

## Benefits of This Approach

1. **Consistency**: Matches the pattern used in `document-extraction`
2. **Simplicity**: No need for separate `.env` files
3. **Transparency**: All environment variables visible in one shell script
4. **Flexibility**: Can source `env.sh` for local development
5. **Reduced Dependencies**: No `python-dotenv` package needed

## Local Development

For local development (without Docker):

```bash
# Source environment variables
source env.sh

# Run backend
cd backend
python main.py

# In another terminal
source env.sh
cd frontend
streamlit run app.py
```

## Migration from Old Setup

If you were using the old `.env` approach:

1. Copy your `GOOGLE_API_KEY` from `.env`
2. Edit `env.sh` and paste the key
3. Delete the old `.env` file
4. Rebuild containers: `./run.sh build`
5. Start services: `./run.sh up`

## Environment Variables Reference

All environment variables are defined in `env.sh`:

| Variable | Default | Description |
|----------|---------|-------------|
| `PORT` | 8000 | Backend API port |
| `FRONTEND_PORT` | 8501 | Frontend UI port |
| `GOOGLE_API_KEY` | (required) | Google Gemini API key |
| `DATABASE_URL` | postgresql+asyncpg://... | PostgreSQL connection string |
| `MIN_CLASSIFICATION_CONFIDENCE` | 0.7 | Minimum confidence for classification |
| `LANGSMITH_TRACING` | false | Enable LangSmith tracing |
| `LANGSMITH_API_KEY` | - | LangSmith API key (optional) |
| `LANGSMITH_PROJECT` | - | LangSmith project name (optional) |

## Troubleshooting

### Issue: Services won't start

**Solution**: Check if `GOOGLE_API_KEY` is set in `env.sh`
```bash
grep GOOGLE_API_KEY env.sh
```

### Issue: Environment variables not loaded

**Solution**: Ensure `entrypoint.sh` sources `env.sh`
```bash
docker exec document-services cat /app/env.sh
```

### Issue: Permission denied on scripts

**Solution**: Make scripts executable
```bash
chmod +x env.sh run.sh entrypoint.sh check_structure.sh
```

## Verification

Run the structure check to verify everything is in place:

```bash
./check_structure.sh
```

You should see:
- ✓ env.sh exists
- ✓ run.sh exists
- ⚠ GOOGLE_API_KEY needs configuration (if not set yet)

## Summary

The migration to `env.sh` provides a cleaner, more consistent approach to environment configuration that:
- Eliminates the need for `.env` files
- Removes the `python-dotenv` dependency
- Matches the pattern used in other modules
- Simplifies the configuration process
- Provides better visibility into environment settings
