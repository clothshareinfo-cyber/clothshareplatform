import os
import django
import sqlite3

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'clothingshareprj.settings')
django.setup()

from core.models import ClothingItem, ItemImage
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
    print("   Creating a superuser first...")
    print("   Run: python manage.py createsuperuser")
    sqlite_conn.close()
    exit()

print(f"✅ Using user: {default_user.email} (ID: {default_user.id})")

# Migrate Clothing Items
print("\n" + "=" * 60)
print("STEP 1: Migrating Clothing Items")
print("=" * 60)

sqlite_cursor.execute("""
    SELECT id, title, description, category, gender, size, 
           condition_id, donor_id, status, mode
    FROM core_clothingitem
""")
items = sqlite_cursor.fetchall()
print(f"Found {len(items)} items to migrate")

items_migrated = 0
items_skipped = 0

for item in items:
    item_id, title, desc, cat, gender, size, cond, donor_id, status, mode = item
    
    # Check if already exists in PostgreSQL
    if ClothingItem.objects.filter(id=item_id).exists():
        print(f"  ⏭️ Item ID {item_id} already exists: {title}")
        items_skipped += 1
        continue
    
    # Find donor
    donor = User.objects.filter(id=donor_id).first()
    if not donor:
        donor = default_user
        print(f"  👤 Using default user for: {title}")
    
    try:
        new_item = ClothingItem(
            id=item_id,
            title=title,
            description=desc or "",
            category=cat or "women",
            gender=gender or "unisex",
            size=size or "",
            condition=cond or "good",
            donor=donor,
            status=status or "available",
            mode=mode or "donation",
        )
        new_item.save()
        items_migrated += 1
        print(f"  ✅ Migrated: {title} (ID: {item_id})")
    except Exception as e:
        print(f"  ❌ Error with {title}: {e}")

print(f"\n✅ Items migrated: {items_migrated}")
print(f"📊 Total items in PostgreSQL: {ClothingItem.objects.count()}")

# Migrate Images
print("\n" + "=" * 60)
print("STEP 2: Migrating Images")
print("=" * 60)

sqlite_cursor.execute("""
    SELECT id, clothing_item_id, image, is_primary
    FROM core_itemimage
""")
images = sqlite_cursor.fetchall()
print(f"Found {len(images)} images to migrate")

images_migrated = 0
images_skipped = 0

for img in images:
    img_id, item_id, image_path, is_primary = img
    
    # Check if already exists
    if ItemImage.objects.filter(id=img_id).exists():
        print(f"  ⏭️ Image ID {img_id} already exists")
        images_skipped += 1
        continue
    
    # Find the associated item
    item = ClothingItem.objects.filter(id=item_id).first()
    if not item:
        print(f"  ⚠️ Item {item_id} not found for image {img_id}, skipping")
        images_skipped += 1
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
        print(f"  ❌ Error migrating image {img_id}: {e}")

print(f"\n✅ Images migrated: {images_migrated}")
print(f"📊 Total images in PostgreSQL: {ItemImage.objects.count()}")

sqlite_conn.close()

print("\n" + "=" * 60)
print("MIGRATION COMPLETE!")
print("=" * 60)
print(f"Items: {ClothingItem.objects.count()}")
print(f"Images: {ItemImage.objects.count()}")
print("=" * 60)

if ClothingItem.objects.count() > 0:
    print("\n🎉 Success! Run: python manage.py runserver")
else:
    print("\n⚠️ No items were migrated. Please check the errors above.")