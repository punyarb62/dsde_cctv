import pandas as pd
import streamlit as st
import psycopg2
from psycopg2.extras import RealDictCursor
import folium
from streamlit_folium import st_folium

st.set_page_config(page_title="CCTV Map (psycopg2)", layout="wide")

# ---- Secrets / Config ----
PG_HOST = st.secrets.get("PG_HOST", "localhost")
PG_PORT = st.secrets.get("PG_PORT", "5432")
PG_DB   = st.secrets.get("PG_DB")
PG_USER = st.secrets.get("PG_USER")
PG_PASS = st.secrets.get("PG_PASS")
PG_SSL  = st.secrets.get("PG_SSLMODE")  # optional
SNAPSHOT_BASE = st.secrets.get("SNAPSHOT_BASE", "http://127.0.0.1:9000/snapshot")

def get_conn():
    # Auto SSL: disable for localhost unless explicitly set; require for others by default.
    sslmode = PG_SSL
    if PG_HOST in ("localhost", "127.0.0.1"):
        sslmode = sslmode or "disable"
    else:
        sslmode = sslmode or "require"

    if not all([PG_HOST, PG_PORT, PG_DB, PG_USER, PG_PASS]):
        st.error("Missing DB secrets. Check .streamlit/secrets.toml")
        st.stop()

    return psycopg2.connect(
        host=PG_HOST, port=PG_PORT, dbname=PG_DB, user=PG_USER, password=PG_PASS,
        sslmode=sslmode, cursor_factory=RealDictCursor
    )

@st.cache_data(ttl=20)
def load_cctv_df() -> pd.DataFrame:
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute("""
            SELECT id,
                   COALESCE(NULLIF(name_en, ''), name_th) AS name,
                   lat, lng
            FROM cctv_meta
            WHERE lat IS NOT NULL AND lng IS NOT NULL
            ORDER BY id;
        """)
        rows = cur.fetchall()
    df = pd.DataFrame(rows)
    if df.empty:
        return df
    df["lat"] = pd.to_numeric(df["lat"], errors="coerce")
    df["lng"] = pd.to_numeric(df["lng"], errors="coerce")
    df = df.dropna(subset=["lat", "lng"])
    return df

# ---- UI ----
st.title("🎥 CCTV Live Monitor")
st.markdown("**Click any camera on the map to view its live feed**")

try:
    df = load_cctv_df()
except Exception as e:
    st.error(f"DB connection/query failed: {e}")
    st.stop()

if df.empty:
    st.warning("No rows in cctv_meta.")
    st.stop()

st.markdown(f"**Total Cameras:** {len(df)}")

# ---- CLICKABLE MAP (Leaflet via streamlit-folium) ----
st.markdown("### 🗺️ Camera Locations - Click any camera to view feed in popup")

# Center map on the mean of points (Bangkok fallback)
center_lat = float(df["lat"].mean()) if not df.empty else 13.7563
center_lng = float(df["lng"].mean()) if not df.empty else 100.5018

m = folium.Map(
    location=[center_lat, center_lng],
    zoom_start=12,
    control_scale=True,
    tiles='CartoDB positron',  # Cleaner map style
    prefer_canvas=True
)

# Add markers with tooltip; store id in popup text
for _, row in df.iterrows():
    title = row["name"] if row["name"] else str(row["id"])

    # Create snapshot URL for popup
    snapshot_url = f"{SNAPSHOT_BASE}/{row['id']}"

    # Create HTML with working JavaScript using proper escaping
    popup_html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <style>
            body {{ margin: 0; padding: 10px; font-family: Arial; width: 320px; background: white; }}
            .title {{ margin: 0 0 10px 0; color: #2c7be5; text-align: center; font-size: 16px; }}
            .feed-container {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); border-radius: 8px; padding: 40px 20px; margin: 10px 0; text-align: center; min-height: 180px; display: flex; align-items: center; justify-content: center; flex-direction: column; }}
            .btn {{ padding: 15px 30px; background: white; color: #2c7be5; border: none; border-radius: 8px; cursor: pointer; font-size: 15px; font-weight: bold; box-shadow: 0 4px 8px rgba(0,0,0,0.3); margin: 5px; }}
            .btn:hover {{ transform: scale(1.05); }}
            .btn-small {{ padding: 8px 16px; font-size: 12px; }}
            .info {{ background: #f8f9fa; padding: 8px; border-radius: 5px; font-size: 12px; }}
            .info p {{ margin: 3px 0; }}
            .controls {{ text-align: center; margin-top: 8px; display: none; }}
            img {{ width: 100%; border-radius: 8px; display: block; }}
        </style>
    </head>
    <body>
        <h4 class="title">📹 {title}</h4>
        <div class="feed-container" id="feedbox">
            <button class="btn" onclick="loadFeed()">📸 Load Live Feed</button>
        </div>
        <div class="controls" id="controls">
            <button class="btn btn-small" onclick="loadFeed()">🔄 Refresh</button>
            <label style="font-size: 12px; margin-left: 10px;">
                <input type="checkbox" id="autoRefresh" onchange="toggleAuto()"> Auto (1 FPS)
            </label>
        </div>
        <div class="info">
            <p><b>ID:</b> {row['id']}</p>
            <p><b>Location:</b> {row['lat']:.5f}, {row['lng']:.5f}</p>
        </div>
        <script>
            var autoInterval = null;

            function loadFeed() {{
                var box = document.getElementById('feedbox');
                box.innerHTML = '<p style="color: white; margin: 0;">Loading...</p>';
                box.style.background = 'black';
                box.style.padding = '5px';
                var img = document.createElement('img');
                img.src = '{snapshot_url}?t=' + new Date().getTime();
                img.onerror = function() {{
                    box.innerHTML = '<p style="color: white;">❌ Camera Offline</p>';
                }};
                img.onload = function() {{
                    box.innerHTML = '';
                    box.appendChild(img);
                    document.getElementById('controls').style.display = 'block';
                }};
            }}

            function toggleAuto() {{
                var checkbox = document.getElementById('autoRefresh');
                if (checkbox.checked) {{
                    autoInterval = setInterval(loadFeed, 1000);
                }} else {{
                    if (autoInterval) {{
                        clearInterval(autoInterval);
                        autoInterval = null;
                    }}
                }}
            }}
        </script>
    </body>
    </html>
    """

    # Use IFrame for proper HTML rendering
    iframe = folium.IFrame(html=popup_html, width=350, height=320)

    folium.CircleMarker(
        location=[row["lat"], row["lng"]],
        radius=10,  # Even larger for better clicking
        color="#2c7be5",
        fill=True,
        fill_color="#4da6ff",
        fill_opacity=0.8,
        weight=3,
        tooltip=folium.Tooltip(
            f"<b style='font-size: 14px;'>📹 {title}</b><br><i>Click for live feed</i>",
            sticky=False
        ),
        popup=folium.Popup(iframe, max_width=370),
    ).add_to(m)

# Render map full width
st_folium(m, height=800, width=None)
