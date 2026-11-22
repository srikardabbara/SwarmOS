# SwarmOS Backend API

FastAPI backend for SwarmOS with SQLite persistence.

## Setup

```bash
# Install dependencies
pip install -r requirements.txt

# Or install with main package
cd ..
pip install -e ".[backend]"
```

## Run Development Server

```bash
# From backend directory
python -m uvicorn api.main:app --reload --port 8000

# Or use the convenience script
python run.py
```

The API will be available at:
- **API**: http://localhost:8000
- **Docs**: http://localhost:8000/docs (Swagger UI)
- **ReDoc**: http://localhost:8000/redoc

## API Endpoints

### Health Check
- `GET /` - API information
- `GET /health` - Health check

### Traces
- `POST /traces` - Create a new trace
- `GET /traces` - List traces (with optional filtering)
- `GET /traces/{trace_id}` - Get trace with full details
- `DELETE /traces/{trace_id}` - Delete a trace

### Query Parameters for List Traces
- `workflow_id` - Filter by workflow ID
- `status` - Filter by status (running, completed, failed)
- `limit` - Number of results (default: 100, max: 1000)
- `offset` - Offset for pagination (default: 0)

## Database

SQLite database stored at: `./swarmos.db`

The database is automatically initialized on first run.

## Example Usage

```python
import httpx
from swarmos import SwarmOSAdapter

# Configure adapter to send to backend
adapter = SwarmOSAdapter(
    workflow_id="my-workflow",
    api_url="http://localhost:8000",
    auto_send=True
)

# Run your workflow
result = app.invoke(input_data, config={"callbacks": [adapter.callback_handler]})

# Traces are automatically sent to backend
```

## Production Deployment

For production, consider:
1. **Database**: Migrate to PostgreSQL (Render, Supabase, Neon free tiers)
2. **Hosting**: Deploy on Render.com free tier
3. **Environment Variables**: Use `.env` for configuration
4. **Authentication**: Add API key authentication if needed

### Deploy to Render

1. Push code to GitHub
2. Create new Web Service on Render
3. Set build command: `pip install -r requirements.txt`
4. Set start command: `uvicorn api.main:app --host 0.0.0.0 --port $PORT`
5. Done! Free tier includes 750 hours/month

## Development

Run tests:
```bash
pytest
```

Format code:
```bash
black .
ruff check .
```
