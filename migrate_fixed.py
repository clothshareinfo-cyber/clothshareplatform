import os
import django
import sqlite3

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'clothingshareprj.settings')
django.setup()

from core.models import ClothingItem, ItemImage, Category, Condition, Gender, Size
from django.contrib.auth import get_user_model

User = get_user_model()

print("=" * 60)
print("MIGRATING DATA FROM SQLITE TO POSTGRESQL")
print("=" * 60)

# Connect to SQLite
sqlite_conn = sqlite3.connect('db.sqlite3')
sqlite_cursor = sqlite_conn.cursor()

# Check SQLite data
sqlite_cursor.execute("SELECT COUNT(*) FROM core_clothingitem")
sqlite_item_count = sqlite_cursor.fetchone()[0]
print(f"\n📊 SQLite has {sqlite_item_count} items")

if sqlite_item_count == 0:
    print("❌ No data found in SQLite!")
    sqlite_conn.close()
    exit()

# Get first user
default_user = User.objects.first()
if not default_user:
    print("\n❌ No users found in PostgreSQL!")
    print("   Run: python manage.py createsuperuser")
    sqlite_conn.close()
    exit()

print(f"✅ Using user: {default_user.email} (ID: {default_user.id})")

# Get all reference objects
category_map = {cat.name: cat for cat in Category.objects.all()}
condition_map = {cond.name: cond for cond in Condition.objects.all()}
gender_map = {gen.name: gen for gen in Gender.objects.all()}
size_map = {size.name: size for size in Size.objects.all()}

print(f"✅ Categories available: {list(category_map.keys())}")
print(f"✅ Conditions available: {list(condition_map.keys())}")
print(f"✅ Genders available: {list(gender_map.keys())}")

# Migrate Clothing Items
print("\n" + "=" * 60)
print("STEP 1: Migrating Clothing Items")
print("=" * 60)

sqlite_cursor.execute("""
    SELECT id, title, description, mode, status, 
           category_id, donor_id, condition_id, gender_id, size_id
    FROM core_clothingitem
""")
items = sqlite_cursor.fetchall()
print(f"Found {len(items)} items to migrate")

items_migrated = 0

# Map IDs to names (you need to check your SQLite reference tables)
# First, let's see what's in your reference tables
sqlite_cursor.execute("SELECT id, name FROM core_category")
cat_ref = {row[0]: row[1] for row in sqlite_cursor.fetchall()}
print(f"Category mapping from SQLite: {cat_ref}")

sqlite_cursor.execute("SELECT id, name FROM core_condition")
cond_ref = {row[0]: row[1] for row in sqlite_cursor.fetchall()}
print(f"Condition mapping: {cond_ref}")

sqlite_cursor.execute("SELECT id, name FROM core_gender")
gender_ref = {row[0]: row[1] for row in sqlite_cursor.fetchall()}
print(f"Gender mapping: {gender_ref}")

sqlite_cursor.execute("SELECT id, name FROM core_size")
size_ref = {row[0]: row[1] for row in sqlite_cursor.fetchall()}
print(f"Size mapping: {size_ref}")

# Now migrate items
sqlite_cursor.execute("""
    SELECT id, title, description, mode, status, 
           category_id, donor_id, condition_id, gender_id, size_id
    FROM core_clothingitem
""")
items = sqlite_cursor.fetchall()

for item in items:
    (item_id, title, description, mode, status,
     cat_id, donor_id, cond_id, gender_id, size_id) = item
    
    # Check if already exists
    if ClothingItem.objects.filter(id=item_id).exists():
        print(f"  ⏭️ Item ID {item_id} already exists: {title}")
        continue
    
    # Get foreign key objects
    category_name = cat_ref.get(cat_id, 'women')
    category = category_map.get(category_name)
    
    condition_name = cond_ref.get(cond_id, 'good')
    condition = condition_map.get(condition_name)
    
    gender_name = gender_ref.get(gender_id, 'unisex')
    gender = gender_map.get(gender_name)
    
    size = None
    if size_id and size_id in size_ref:
        size_name = size_ref[size_id]
        size = size_map.get(size_name)
    
    # Find donor
    donor = User.objects.filter(id=donor_id).first() if donor_id else None
    if not donor:
        donor = default_user
    
    try:
        new_item = ClothingItem(
            id=item_id,
            title=title,
            description=description or "",
            category=category,
            condition=condition,
            gender=gender,
            size=size,
            donor=donor,
            status=status or "available",
            mode=mode or "donation",
        )
        new_item.save()
        items_migrated += 1
        print(f"  ✅ Migrated: {title}")
    except Exception as e:
        print(f"  ❌ Error with {title}: {e}")

print(f"\n✅ Items migrated: {items_migrated}")
print(f"📊 Total items in PostgreSQL: {ClothingItem.objects.count()}")

# Migrate Images
print("\n" + "=" * 60)
print("STEP 2: Migrating Images")
print("=" * 60)

# Check correct column name for image table
sqlite_cursor.execute("PRAGMA table_info(core_itemimage)")
image_columns = [col[1] for col in sqlite_cursor.fetchall()]
print(f"Image table columns: {image_columns}")

# Find the correct column name for item foreign key
item_fk_column = None
for col in image_columns:
    if 'item' in col.lower():
        item_fk_column = col
        break

if item_fk_column:
    sqlite_cursor.execute(f"""
        SELECT id, {item_fk_column}, image, is_primary
        FROM core_itemimage
    """)
    images = sqlite_cursor.fetchall()
    print(f"Found {len(images)} images to migrate")

    images_migrated = 0
    for img in images:
        img_id, item_id, image_path, is_primary = img
        
        if ItemImage.objects.filter(id=img_id).exists():
            continue
        
        item = ClothingItem.objects.filter(id=item_id).first()
        if not item:
            print(f"  ⚠️ Item {item_id} not found")
            continue
        
        try:
            new_image = ItemImage(
                id=img_id,
                clothing_item=item,
                is_primary=(is_primary == 1),
            )
            new_image.save()
            images_migrated += 1
            print(f"  ✅ Migrated image for: {item.title}")
        except Exception as e:
            print(f"  ❌ Error: {e}")
    
    print(f"\n✅ Images migrated: {images_migrated}")
else:
    print("⚠️ Could not find item foreign key column in image table")

sqlite_conn.close()

print("\n" + "=" * 60)
print("MIGRATION COMPLETE!")
print("=" * 60)
print(f"Items: {ClothingItem.objects.count()}")
print(f"Images: {ItemImage.objects.count()}")
print("=" * 60)