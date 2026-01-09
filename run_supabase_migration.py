import psycopg2
import os

# Database connection URL
DB_URL = "postgresql://postgres:H9w5U2c%3FidnMw%25f@db.dpalspcavpcfamivjlbm.supabase.co:5432/postgres"

def run_migration():
    print("Starting migration to Supabase Cloud...")
    try:
        # Connect to the remote database
        conn = psycopg2.connect(DB_URL)
        conn.autocommit = True
        cursor = conn.cursor()
        
        # Read the migration SQL script
        with open('migration.sql', 'r') as f:
            sql = f.read()
            
        print("Executing SQL commands...")
        # Since migration.sql might have multiple commands, we'll split or execute as one
        # psycopg2 can execute multiple commands separated by ;
        cursor.execute(sql)
        
        print("Migration completed successfully!")
        cursor.close()
        conn.close()
    except Exception as e:
        print(f"Error during migration: {e}")

if __name__ == '__main__':
    run_migration()
