"""
Example script to view cctv_meta database data
This demonstrates how to connect to the database and retrieve camera metadata
"""

import pandas as pd
import psycopg2
from psycopg2.extras import RealDictCursor

# ---- Database Configuration ----
# Replace these with your actual database credentials
PG_HOST = "your_database_host"
PG_PORT = "5432"
PG_DB = "postgres"
PG_USER = "your_database_user"
PG_PASS = "your_database_password"
PG_SSLMODE = "require"  # Use "disable" for localhost


def get_conn():
    """
    Create a database connection with SSL support
    """
    try:
        conn = psycopg2.connect(
            host=PG_HOST,
            port=PG_PORT,
            dbname=PG_DB,
            user=PG_USER,
            password=PG_PASS,
            sslmode=PG_SSLMODE,
            cursor_factory=RealDictCursor
        )
        print("✅ Database connection successful!")
        return conn
    except Exception as e:
        print(f"❌ Database connection failed: {e}")
        raise


def load_cctv_df() -> pd.DataFrame:
    """
    Load CCTV camera metadata from database
    Returns a pandas DataFrame with camera information
    """
    with get_conn() as conn, conn.cursor() as cur:
        # Query to get camera data with name, location
        cur.execute("""
            SELECT id,
                   COALESCE(NULLIF(name_en, ''), name_th) AS name,
                   lat, lng
            FROM cctv_meta
            WHERE lat IS NOT NULL AND lng IS NOT NULL
            ORDER BY id;
        """)
        rows = cur.fetchall()

    # Convert to DataFrame
    df = pd.DataFrame(rows)

    if df.empty:
        print("⚠️ No data found in cctv_meta table")
        return df

    # Ensure lat/lng are numeric
    df["lat"] = pd.to_numeric(df["lat"], errors="coerce")
    df["lng"] = pd.to_numeric(df["lng"], errors="coerce")

    # Drop any rows with invalid coordinates
    df = df.dropna(subset=["lat", "lng"])

    return df


def load_all_cctv_data() -> pd.DataFrame:
    """
    Load ALL columns from cctv_meta table
    Useful for exploring the complete dataset
    """
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute("""
            SELECT *
            FROM cctv_meta
            ORDER BY id;
        """)
        rows = cur.fetchall()

    df = pd.DataFrame(rows)
    print(f"✅ Loaded {len(df)} rows from cctv_meta")
    return df


def get_camera_by_id(camera_id: int) -> dict:
    """
    Get specific camera details by ID
    """
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute("""
            SELECT *
            FROM cctv_meta
            WHERE id = %s;
        """, (camera_id,))
        row = cur.fetchone()

    if row:
        print(f"✅ Found camera {camera_id}")
        return dict(row)
    else:
        print(f"❌ Camera {camera_id} not found")
        return None


def get_cameras_in_area(min_lat: float, max_lat: float, min_lng: float, max_lng: float) -> pd.DataFrame:
    """
    Get cameras within a specific geographic area
    """
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute("""
            SELECT id,
                   COALESCE(NULLIF(name_en, ''), name_th) AS name,
                   lat, lng
            FROM cctv_meta
            WHERE lat BETWEEN %s AND %s
              AND lng BETWEEN %s AND %s
            ORDER BY id;
        """, (min_lat, max_lat, min_lng, max_lng))
        rows = cur.fetchall()

    df = pd.DataFrame(rows)
    print(f"✅ Found {len(df)} cameras in the specified area")
    return df


def get_table_stats():
    """
    Get statistics about the cctv_meta table
    """
    with get_conn() as conn, conn.cursor() as cur:
        # Total count
        cur.execute("SELECT COUNT(*) as total FROM cctv_meta;")
        total = cur.fetchone()['total']

        # Cameras with coordinates
        cur.execute("""
            SELECT COUNT(*) as with_coords
            FROM cctv_meta
            WHERE lat IS NOT NULL AND lng IS NOT NULL;
        """)
        with_coords = cur.fetchone()['with_coords']

        # Cameras with English names
        cur.execute("""
            SELECT COUNT(*) as with_en_name
            FROM cctv_meta
            WHERE name_en IS NOT NULL AND name_en != '';
        """)
        with_en = cur.fetchone()['with_en_name']

        print("\n📊 Database Statistics:")
        print(f"  Total cameras: {total}")
        print(f"  With coordinates: {with_coords}")
        print(f"  With English names: {with_en}")
        print(f"  Missing coordinates: {total - with_coords}")


# ---- Example Usage ----
if __name__ == "__main__":
    print("=" * 60)
    print("CCTV Database Viewer")
    print("=" * 60)

    try:
        # Example 1: Load basic camera data (like in Streamlit app)
        print("\n1️⃣ Loading basic camera data...")
        df = load_cctv_df()
        print(f"   Loaded {len(df)} cameras")
        print("\n   First 5 cameras:")
        print(df.head())

        # Example 2: Load all data with all columns
        print("\n\n2️⃣ Loading complete dataset...")
        df_all = load_all_cctv_data()
        print("\n   Column names:")
        print(f"   {list(df_all.columns)}")
        print("\n   First camera (all fields):")
        print(df_all.iloc[0].to_dict())

        # Example 3: Get specific camera
        print("\n\n3️⃣ Getting specific camera (ID=1301)...")
        camera = get_camera_by_id(1301)
        if camera:
            print(f"   {camera}")

        # Example 4: Get cameras in Bangkok downtown area
        print("\n\n4️⃣ Getting cameras in Bangkok downtown area...")
        # Bangkok approximate coordinates: 13.7-13.8 lat, 100.4-100.6 lng
        df_area = get_cameras_in_area(13.7, 13.8, 100.4, 100.6)
        print(df_area.head())

        # Example 5: Show table statistics
        print("\n\n5️⃣ Database statistics...")
        get_table_stats()

        # Example 6: Export to CSV
        print("\n\n6️⃣ Exporting to CSV...")
        output_file = "cctv_data_export.csv"
        df.to_csv(output_file, index=False)
        print(f"   ✅ Data exported to {output_file}")

        print("\n" + "=" * 60)
        print("✅ All examples completed successfully!")
        print("=" * 60)

    except Exception as e:
        print(f"\n❌ Error: {e}")
        print("\nMake sure to update the database credentials at the top of this file!")
