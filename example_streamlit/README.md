# CCTV Live Monitor - Streamlit Dashboard

An interactive web dashboard built with Streamlit that displays CCTV camera locations on a map and allows real-time viewing of camera feeds from Bangkok's traffic monitoring system.

## Overview

This Streamlit application provides a user-friendly interface to:
- View all CCTV camera locations on an interactive map
- Click on any camera marker to load its live feed in a popup
- Auto-refresh camera feeds at 1 FPS
- Display camera metadata (ID, name, coordinates)

### Key Features

- **Interactive Map**: Click-to-view camera feeds using Folium/Leaflet maps
- **Live Feed Viewer**: Load snapshots with manual or auto-refresh options
- **Database Integration**: Fetches camera metadata from PostgreSQL/Supabase
- **Responsive Design**: Clean, modern UI with gradient styling
- **Error Handling**: Graceful handling of offline cameras and connection issues
- **Caching**: 20-second TTL cache for improved performance

## How It Works

1. **Database Connection**: Connects to PostgreSQL database using psycopg2 with SSL support
2. **Data Loading**: Queries `cctv_meta` table for camera locations and metadata (with 20s cache)
3. **Map Rendering**: Uses Folium to create an interactive map with clickable camera markers
4. **Snapshot Fetching**: When clicked, loads live images from the snapshot microservice (default: `http://127.0.0.1:9000/snapshot`)
5. **Auto-Refresh**: Optional auto-refresh mode updates images every second

### Architecture

```
Streamlit UI → PostgreSQL Database (camera metadata)
              ↓
         Folium Map → User clicks marker
              ↓
    Snapshot Service (http://127.0.0.1:9000/snapshot/{id})
              ↓
         Display Live Feed in Popup
```

## Installation

### Prerequisites

- Python 3.8+
- PostgreSQL database with `cctv_meta` table
- CCTV Snapshot microservice running (see `cctv_app` folder)

### Steps

1. **Navigate to the example_streamlit directory**:
   ```bash
   cd example_streamlit
   ```

2. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

3. **Configure secrets** (see Configuration section below)

4. **Run the application**:
   ```bash
   streamlit run streamlit_app.py
   ```

The app will open in your browser at `http://localhost:8501`

## Configuration

### Secrets File (.streamlit/secrets.toml)

Create a `.streamlit/secrets.toml` file in the `example_streamlit` directory with your database credentials:

```toml
PG_HOST = "your_database_host"
PG_PORT = "5432"
PG_DB = "postgres"
PG_USER = "your_database_user"
PG_PASS = "your_database_password"
PG_SSLMODE = "require"  # or "disable" for localhost
SNAPSHOT_BASE = "http://127.0.0.1:9000/snapshot"  # Optional, defaults to this
```

### Configuration Variables

| Variable | Description | Default | Required |
|----------|-------------|---------|----------|
| `PG_HOST` | PostgreSQL host address | `localhost` | Yes |
| `PG_PORT` | PostgreSQL port | `5432` | Yes |
| `PG_DB` | Database name | - | Yes |
| `PG_USER` | Database username | - | Yes |
| `PG_PASS` | Database password | - | Yes |
| `PG_SSLMODE` | SSL mode (`require`, `disable`, etc.) | Auto-detected | No |
| `SNAPSHOT_BASE` | Base URL for snapshot service | `http://127.0.0.1:9000/snapshot` | No |

### SSL Mode Behavior

The app automatically handles SSL:
- **Localhost** (`127.0.0.1`, `localhost`): Defaults to `disable` unless specified
- **Remote hosts**: Defaults to `require` unless specified
- Override by setting `PG_SSLMODE` in secrets.toml

### Database Schema

The app expects a `cctv_meta` table with this structure:

```sql
CREATE TABLE cctv_meta (
    id INTEGER PRIMARY KEY,
    name_th TEXT,
    name_en TEXT,
    lat NUMERIC,
    lng NUMERIC
    -- other fields...
);
```

## Usage

### Starting the Dashboard

**Development Mode**:
```bash
streamlit run streamlit_app.py
```

**Production Mode (with custom port)**:
```bash
streamlit run streamlit_app.py --server.port 8080
```

**Headless/Server Mode**:
```bash
streamlit run streamlit_app.py --server.headless true
```

### Using the Interface

1. **View Camera Map**: The main page shows all cameras on an interactive map
2. **Click a Camera**: Click any blue circle marker to open the camera popup
3. **Load Feed**: Click "📸 Load Live Feed" button in the popup
4. **Refresh Feed**: Use "🔄 Refresh" button to reload the image
5. **Auto-Refresh**: Check "Auto (1 FPS)" to automatically refresh every second
6. **Camera Info**: View camera ID and coordinates in the info box

### Map Controls

- **Zoom**: Use mouse wheel or +/- buttons
- **Pan**: Click and drag the map
- **Tooltip**: Hover over markers to see camera name
- **Popup**: Click markers to open feed viewer

## Features Explained

### Clickable Camera Markers

Each camera appears as a blue circle marker on the map. Markers include:
- **Tooltip**: Shows camera name on hover
- **Popup**: Interactive HTML popup with live feed viewer
- **Color coding**: Blue (#2c7be5) with semi-transparent fill

### Live Feed Popup

The popup contains:
- **Camera Title**: Shows name (English preferred, Thai fallback)
- **Load Button**: Fetches current snapshot from microservice
- **Image Display**: Shows live camera feed
- **Refresh Controls**: Manual refresh and auto-refresh toggle
- **Camera Info**: ID and GPS coordinates
- **Error Handling**: Shows "Camera Offline" if image fails to load

### Auto-Refresh Mode

When enabled:
- Fetches new snapshot every 1000ms (1 FPS)
- Adds cache-busting timestamp to avoid stale images
- Can be toggled on/off without closing popup

## Troubleshooting

### Database Connection Failed

**Error**: `DB connection/query failed`

**Solutions**:
- Check `.streamlit/secrets.toml` exists and has correct credentials
- Verify database is accessible from your network
- Check SSL mode settings (use `disable` for localhost)
- Test connection: `psql -h HOST -p PORT -U USER -d DB`

### No Cameras Showing

**Error**: `No rows in cctv_meta`

**Solutions**:
- Verify `cctv_meta` table exists and has data
- Check table has `lat` and `lng` columns with valid coordinates
- Run query manually: `SELECT * FROM cctv_meta LIMIT 10;`

### Camera Images Not Loading

**Symptoms**: "Camera Offline" message in popup

**Solutions**:
- Ensure CCTV snapshot service is running on port 9000
- Check `SNAPSHOT_BASE` URL in secrets.toml
- Verify camera ID exists in the snapshot service
- Test URL manually: `curl http://127.0.0.1:9000/snapshot/{id}`
- Check browser console for CORS or network errors

### Map Not Rendering

**Solutions**:
- Check internet connection (Leaflet tiles need to load)
- Try different tile provider in code (line 83)
- Verify `streamlit-folium` is installed correctly
- Clear browser cache

### SSL/TLS Errors

**Error**: `SSL connection failed`

**Solutions**:
- For localhost: Set `PG_SSLMODE = "disable"`
- For remote: Set `PG_SSLMODE = "require"`
- For self-signed certs: Use `PG_SSLMODE = "prefer"`
- Check firewall/VPN settings

## Customization

### Change Map Style

Edit line 83 in `streamlit_app.py`:
```python
tiles='CartoDB positron',  # Options: 'OpenStreetMap', 'CartoDB dark_matter', 'Stamen Terrain'
```

### Adjust Cache Duration

Edit line 36:
```python
@st.cache_data(ttl=20)  # Change 20 to desired seconds
```

### Modify Popup Size

Edit lines 165, 179:
```python
iframe = folium.IFrame(html=popup_html, width=350, height=320)
popup=folium.Popup(iframe, max_width=370)
```

### Change Auto-Refresh Rate

Edit line 151 in popup HTML:
```javascript
autoInterval = setInterval(loadFeed, 1000);  // Change 1000 to milliseconds
```

### Customize Marker Appearance

Edit lines 167-180:
```python
folium.CircleMarker(
    radius=10,  # Marker size
    color="#2c7be5",  # Border color
    fill_color="#4da6ff",  # Fill color
    fill_opacity=0.8,  # Transparency
    weight=3  # Border width
)
```

## Technical Details

### Dependencies

- **streamlit**: Web application framework
- **pandas**: Data manipulation and analysis
- **psycopg2-binary**: PostgreSQL database adapter
- **folium**: Interactive Leaflet maps
- **streamlit-folium**: Streamlit component for Folium maps

### Performance Optimizations

1. **Query Caching**: 20-second TTL cache on database queries
2. **Connection Pooling**: Uses context managers for proper connection cleanup
3. **Lazy Loading**: Images only load when user clicks marker
4. **Efficient Markers**: Uses `prefer_canvas=True` for better performance with many markers

### Security Considerations

- Database credentials stored in `secrets.toml` (gitignored by Streamlit)
- SSL/TLS support for secure database connections
- No sensitive data exposed in client-side code
- Proper error handling prevents credential leakage

## Port Configuration

- **Streamlit Dashboard**: Default `8501` (configurable with `--server.port`)
- **Snapshot Service**: Default `9000` (configured in `SNAPSHOT_BASE`)
- **PostgreSQL**: Default `5432`

## File Structure

```
example_streamlit/
├── .streamlit/
│   └── secrets.toml          # Database credentials (gitignored)
├── streamlit_app.py          # Main application
├── requirements.txt          # Python dependencies
└── README.md                 # This file
```

## Related Services

This dashboard requires:
1. **CCTV Snapshot Microservice** (`cctv_app/`) - Provides live camera images
2. **PostgreSQL Database** - Stores camera metadata

## Support

For issues or questions:
1. Check logs in terminal where `streamlit run` is executed
2. Verify all services (database, snapshot service) are running
3. Test database connection manually
4. Check browser console for client-side errors
5. Ensure `.streamlit/secrets.toml` is properly configured

## License

Educational/research purposes. Respect data provider terms of service.
