import psycopg2

MY_PASSWORD = "0769116880JK"

print("Testing PostgreSQL connection...")

try:
    conn = psycopg2.connect(
        database="postgres",
        user="postgres",
        password=MY_PASSWORD,
        host="localhost",
        port="5432"
    )
    print("✅ SUCCESS! Password works!")
    
    # Create database if it doesn't exist
    cur = conn.cursor()
    cur.execute("SELECT 1 FROM pg_database WHERE datname='clothshare_db'")
    exists = cur.fetchone()
    
    if not exists:
        cur.execute("CREATE DATABASE clothshare_db")
        print("✅ Database 'clothshare_db' created!")
    else:
        print("✅ Database 'clothshare_db' already exists")
    
    conn.close()
    
except Exception as e:
    print(f"❌ Error: {e}")