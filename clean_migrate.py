import os
import django
import sqlite3
import psycopg2
from psycopg2.extras import execute_values

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'clothingshareprj.settings')
django.setup()

from core.models import ClothingItem, ItemImage
from django.contrib.auth import get_user_model
from django.core.files import File

User = get_user_model()

print("=" * 60)
print("CLEAN MIGRATION - NO TRANSACTIONS")
print("=" * 60)

# Connect to SQLite
sqlite_conn = sqlite3.connect('db.sqlite3')
sqlite_cursor = sqlite_conn.cursor()

# Get first user
user = User.objects.first()
if not user:
    print("❌ No user found! Creating superuser...")
    os.system('python manage.py createsuperuser')
    user = User.objects.first()

print(f"✅ Using donor: {user.email}")

# Direct PostgreSQL connection
pg_conn = psycopg2.connect(
    database="clothshare_db",
    user="postgres",
    password="0769116880JK",
    host="localhost",
    port="5432"
)
pg_cursor = pg_conn.cursor()

# Clear existing data
pg_cursor.execute("TRUNCATE TABLE core_clothingitem CASCADE;")
pg_conn.commit()
print("✅ Cleared existing items")

# Insert items directly via SQL
print("\n📦 Inserting items...")
sqlite_cursor.execute("""
    SELECT id, title, description, mode, status, created_at
    FROM core_clothingitem
""")
items = sqlite_cursor.fetchall()
print(f"Found {len(items)} items")

for item in items:
    item_id = str(item[0])
    title = item[1]
    description = item[2] or ""
    mode = item[3] or "donation"
    status = item[4] or "available"
    created_at = item[5]
    
    try:
        pg_cursor.execute("""
            INSERT INTO core_clothingitem (
                id, title, description, mode, status, created_at, updated_at,
                donor_id, category_id, condition_id, gender_id, is_active
            ) VALUES (%s, %s, %s, %s, %s, %s, NOW(), %s, 1, 3, 1, true)
        """, (item_id, title, description, mode, status, created_at, user.id))
        print(f"  ✅ Inserted: {title[:30]}")
    except Exception as e:
        print(f"  ❌ Error: {e}")

pg_conn.commit()
print(f"\n✅ Items inserted: {len(items)}")

# Insert images
print("\n🖼️ Inserting images...")
sqlite_cursor.execute("""
    SELECT id, item_id, image, is_primary
    FROM core_itemimage
""")
images = sqlite_cursor.fetchall()
print(f"Found {len(images)} images")

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
        print(f"  ✅ Inserted image for item: {item_id[:8]}...")
    except Exception as e:
        print(f"  ❌ Error: {e}")

pg_conn.commit()
print(f"\n✅ Images inserted: {len(images)}")

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

pg_cursor.close()
pg_conn.close()
sqlite_conn.close()

if item_count > 0:
    print("\n🎉 SUCCESS! Now run: python manage.py runserver")
else:
    print("\n⚠️ No items were inserted.")