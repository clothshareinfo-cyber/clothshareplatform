import psycopg2

print("=" * 60)
print("Testing PostgreSQL Connection")
print("=" * 60)

# Try different passwords
passwords_to_try = [
    "postgres",
    "admin",
    "password",
    "",
    "root",
    "1234",
]

print("\n🔍 Trying to connect to PostgreSQL...")
print(f"Database: clothshare_db")
print(f"User: postgres")
print(f"Host: localhost")
print(f"Port: 5432")
print("-" * 60)

connection_successful = False
working_password = None

for password in passwords_to_try:
    try:
        print(f"\n📝 Trying password: '{password}'")
        
        conn = psycopg2.connect(
            database="clothshare_db",
            user="postgres",
            password=password,
            host="localhost",
            port="5432"
        )
        
        connection_successful = True
        working_password = password
        print("\n" + "=" * 60)
        print("✅ SUCCESS! Connected to PostgreSQL!")
        print("=" * 60)
        print(f"🔑 Working password is: '{password}'")
        print("-" * 60)
        
        cur = conn.cursor()
        
        cur.execute("SELECT version();")
        version = cur.fetchone()[0]
        print(f"📊 PostgreSQL Version: {version[:50]}...")
        
        cur.execute("SELECT current_database();")
        db_name = cur.fetchone()[0]
        print(f"💾 Database Name: {db_name}")
        
        cur.execute("SELECT current_user;")
        user = cur.fetchone()[0]
        print(f"👤 Current User: {user}")
        
        conn.close()
        print("\n" + "=" * 60)
        print("✅ Your Django can now use PostgreSQL!")
        print(f"📝 Use this password in settings.py: '{password}'")
        print("=" * 60)
        break
        
    except psycopg2.OperationalError as e:
        error_msg = str(e)
        if "password authentication failed" in error_msg:
            print(f"   ❌ Wrong password")
        elif "database \"clothshare_db\" does not exist" in error_msg:
            print(f"   ❌ Database 'clothshare_db' doesn't exist")
            print("   📌 Create it in pgAdmin first")
            break
        elif "Connection refused" in error_msg:
            print(f"   ❌ PostgreSQL is not running")
            print("   📌 Start PostgreSQL service or open pgAdmin")
            break
        else:
            print(f"   ❌ Error: {error_msg[:50]}...")
    except Exception as e:
        print(f"   ❌ Other error: {e}")
        break

if not connection_successful:
    print("\n" + "=" * 60)
    print("❌ COULD NOT CONNECT TO POSTGRESQL")
    print("=" * 60)