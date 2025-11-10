# BMA CCTV Snapshot Microservice

A FastAPI-based microservice that fetches real-time snapshots from Bangkok Metropolitan Administration (BMA) traffic cameras. This service acts as a proxy to retrieve CCTV images from the BMA traffic monitoring system.

## Overview

This microservice provides a simple REST API to fetch CCTV camera snapshots from BMA's traffic system. It handles session management, cookie warming, and filters out placeholder images to ensure you get valid snapshots.

### Key Features

- **Automatic Session Management**: Maintains warm sessions with the BMA server to ensure fast response times
- **Smart Retry Logic**: Detects placeholder/blank images and automatically retries
- **CORS Enabled**: Ready for cross-origin requests from web applications
- **Concurrent Safety**: Uses asyncio locks to prevent race conditions on session warming
- **Health Check Endpoint**: Monitor service status easily

## How It Works

1. **Session Warming**: The service periodically visits the BMA website to maintain an active session, keeping cookies fresh
2. **Snapshot Fetching**: When a snapshot is requested, it fetches the image from BMA's `show.aspx` endpoint
3. **Placeholder Detection**: Uses NumPy to analyze pixel values and detect blank/white placeholder images
4. **Automatic Retry**: If a placeholder is detected, it re-warms the session and retries the fetch
5. **Image Delivery**: Returns the JPEG image with proper headers and caching controls

### Architecture

```
Client Request → FastAPI Endpoint → Session Check → Fetch Image → Validate → Return JPEG
                                         ↓
                                   (if stale/invalid)
                                         ↓
                                   Warmup Session → Retry Fetch
```

## Installation

### Prerequisites

- Python 3.8+
- pip

### Steps

1. **Navigate to the cctv_app directory**:
   ```bash
   cd cctv_app
   ```

2. **Install dependencies**:
   ```bash
   pip install fastapi uvicorn httpx numpy
   ```

   Or install all project dependencies from the root:
   ```bash
   cd ..
   pip install -r requirements.txt
   ```

3. **Configure environment variables** (see Configuration section below)

4. **Run the service**:
   ```bash
   uvicorn app:app --host 0.0.0.0 --port 9000
   ```

## Configuration (.env)

Create a `.env` file in the `cctv_app` directory with the following variables:

### Required Variables

None - all variables are optional with sensible defaults.

### Optional Variables

| Variable | Description | Default Value |
|----------|-------------|---------------|
| `BMA_BASE` | Base URL for BMA traffic website | `http://www.bmatraffic.com` |
| `BMA_UA` | User-Agent header for requests | `Mozilla/5.0 (Windows NT 10.0; Win64; x64)...` |
| `REWARM_SECONDS` | Seconds before session needs rewarming | `25` |
| `TIMEOUT` | HTTP request timeout in seconds | `10` |

### Example .env File

```env
# Database credentials (used by other services in the project)
user=your_database_user
password=your_database_password
host=your_database_host
port=5432
dbname=postgres

# BMA CCTV Service Configuration (optional)
BMA_BASE=http://www.bmatraffic.com
BMA_UA=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/142.0.0.0 Safari/537.36
REWARM_SECONDS=25
TIMEOUT=10
```

### Configuration Tips

- **BMA_BASE**: Don't change unless BMA changes their domain
- **REWARM_SECONDS**: Lower values = more session warmups (slower), higher values = risk of stale sessions
- **TIMEOUT**: Increase if experiencing timeout errors on slow connections
- **BMA_UA**: Keep updated with a modern browser User-Agent to avoid blocking

## Usage

### Starting the Service

**Development Mode**:
```bash
uvicorn app:app --reload --host 0.0.0.0 --port 9000
```

**Production Mode**:
```bash
uvicorn app:app --host 0.0.0.0 --port 9000 --workers 4
```

### API Endpoints

#### 1. Health Check
```http
GET /health
```

**Response**:
```json
{
  "ok": true,
  "base": "http://www.bmatraffic.com"
}
```

#### 2. Snapshot (Same ID)
When play_id and image_id are the same:
```http
GET /snapshot/{id}
```

**Example**:
```bash
curl http://localhost:9000/snapshot/1301 --output camera_1301.jpg
```

#### 3. Snapshot (Different IDs)
When play_id and image_id differ:
```http
GET /snapshot/{play_id}/{image_id}
```

**Example**:
```bash
curl http://localhost:9000/snapshot/1301/1302 --output camera.jpg
```

**Response**: JPEG image with headers:
- `Content-Type: image/jpeg`
- `Cache-Control: no-store, no-cache, must-revalidate`
- `X-Source: bma_min_flow_microservice`
- `X-Ids: {play_id}/{image_id}`

### Usage Examples

#### Python Client
```python
import requests

# Fetch snapshot
response = requests.get("http://localhost:8000/snapshot/1301")
if response.status_code == 200:
    with open("snapshot.jpg", "wb") as f:
        f.write(response.content)
```

#### JavaScript/Fetch
```javascript
fetch('http://localhost:8000/snapshot/1301')
  .then(response => response.blob())
  .then(blob => {
    const img = document.createElement('img');
    img.src = URL.createObjectURL(blob);
    document.body.appendChild(img);
  });
```

#### Command Line
```bash
# Download single snapshot
curl http://localhost:8000/snapshot/1301 -o snapshot.jpg

# Check service health
curl http://localhost:8000/health
```

## Error Handling

### HTTP 502 - Bad Gateway
**Cause**: Failed to fetch valid snapshot after retry
**Solution**:
- Check if the camera ID is valid
- Verify BMA website is accessible
- Increase TIMEOUT in .env

### HTTP 500 - Internal Server Error
**Cause**: Network issues or BMA server problems
**Solution**:
- Check your internet connection
- Verify BMA_BASE URL is correct
- Check logs for specific error messages

## Troubleshooting

### Service won't start
- Ensure port 8000 is not in use: `netstat -ano | findstr :8000` (Windows)
- Check Python version: `python --version` (should be 3.8+)
- Verify all dependencies installed: `pip list`

### Getting blank/white images
- The service should auto-detect and retry
- If persisting, try lowering REWARM_SECONDS
- Check if camera ID is valid on BMA website

### Slow response times
- Increase TIMEOUT value
- Check your network connection
- Consider reducing REWARM_SECONDS for more frequent warmups

### CORS errors in browser
- Service allows all origins by default
- If still having issues, check browser console for specific errors

## Technical Details

### Dependencies
- **FastAPI**: Modern async web framework
- **httpx**: Async HTTP client for fetching images
- **NumPy**: Image placeholder detection
- **Uvicorn**: ASGI server

### Session Management
The service maintains a session cache with timestamps. When a camera is accessed:
1. Check if last warmup was < 2 seconds ago (skip if yes)
2. Check if last warmup was < REWARM_SECONDS (use existing session if yes)
3. Otherwise, perform full warmup (visit index + PlayVideo pages)

### Concurrency
Uses `asyncio.Lock` per camera ID to prevent multiple simultaneous warmups for the same camera, improving efficiency under load.

## License

This is a utility service for educational/research purposes. Please respect BMA's terms of service when using their traffic camera data.

## Support

For issues or questions, please check the logs and ensure:
1. All environment variables are properly configured
2. Network connectivity to BMA website is available
3. Required Python packages are installed
4. Port is not blocked by firewall
