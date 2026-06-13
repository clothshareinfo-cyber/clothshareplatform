import os
import django
import sqlite3
import psycopg2
from psycopg2.extras import execute_values

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'clothingshareprj.settings')
django.setup()

print("=" * 60)
print("DIRECT SQL COPY FROM SQLITE TO POSTGRESQL")
print("=" * 60)

# Connect to SQLite
sqlite_conn = sqlite3.connect('db.sqlite3')
sqlite_cursor = sqlite_conn.cursor()

# Connect to PostgreSQL
pg_conn = psycopg2.connect(
    database="clothshare_db",
    user="postgres",
    password="0769116880JK",
    host="localhost",
    port="5432"
)
pg_cursor = pg_conn.cursor()

# Get the first user ID
pg_cursor.execute("SELECT id FROM userauths_user LIMIT 1")
user_id = pg_cursor.fetchone()[0]
print(f"Using donor ID: {user_id}")

# Get all items from SQLite
sqlite_cursor.execute("""
    SELECT id, title, description, mode, status, created_at,
           category_id, condition_id, gender_id, size_id
    FROM core_clothingitem
""")
items = sqlite_cursor.fetchall()
print(f"Found {len(items)} items to copy")

# Copy items to PostgreSQL
items_copied = 0
for item in items:
    item_id = str(item[0])  # Convert UUID to string
    title = item[1]
    description = item[2] or ""
    mode = item[3] or "donation"
    status = item[4] or "available"
    created_at = item[5]
    category_id = item[6]
    condition_id = item[7]
    gender_id = item[8]
    size_id = item[9]
    
    try:
        pg_cursor.execute("""
            INSERT INTO core_clothingitem (
                id, title, description, mode, status, created_at, updated_at,
                donor_id, category_id, condition_id, gender_id, size_id, is_active
            ) VALUES (%s, %s, %s, %s, %s, %s, NOW(), %s, %s, %s, %s, %s, true)
            ON CONFLICT (id) DO NOTHING
        """, (item_id, title, description, mode, status, created_at, user_id, 
              category_id, condition_id, gender_id, size_id))
        items_copied += 1
        print(f"  ✅ Copied: {title}")
    except Exception as e:
        print(f"  ❌ Error with {title}: {e}")

pg_conn.commit()
print(f"\n✅ Items copied: {items_copied}")

# Copy images
sqlite_cursor.execute("SELECT id, item_id, image, is_primary FROM core_itemimage")
images = sqlite_cursor.fetchall()
print(f"\nFound {len(images)} images to copy")

images_copied = 0
for img in images:
    img_id = str(img[0])
    item_id = str(img[1])
    image_path = img[2]
    is_primary = 1 if img[3] else 0
    
    try:
        pg_cursor.execute("""
            INSERT INTO core_itemimage (id, item_id, image, is_primary)
            VALUES (%s, %s, %s, %s)
            ON CONFLICT (id) DO NOTHING
        """, (img_id, item_id, image_path, is_primary))
        images_copied += 1
        print(f"  ✅ Copied image for item: {item_id}")
    except Exception as e:
        print(f"  ❌ Error with image {img_id}: {e}")

pg_conn.commit()
print(f"\n✅ Images copied: {images_copied}")

# Verify
pg_cursor.execute("SELECT COUNT(*) FROM core_clothingitem")
item_count = pg_cursor.fetchone()[0]
pg_cursor.execute("SELECT COUNT(*) FROM core_itemimage")
image_count = pg_cursor.fetchone()[0]

print("\n" + "=" * 60)
print("VERIFICATION")
print("=" * 60)
print(f"Items in PostgreSQL: {item_count}")
print(f"Images in PostgreSQL: {image_count}")

sqlite_conn.close()
pg_conn.close()

if item_count > 0:
    print("\n🎉 SUCCESS! Run: python manage.py runserver")
else:
    print("\n⚠️ No items were copied. Check the errors above.")