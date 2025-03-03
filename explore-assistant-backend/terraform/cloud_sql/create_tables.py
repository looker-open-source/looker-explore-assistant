from database import create_db_and_tables, get_database_url

def main():
    print("Creating database and tables...")
    print(f"Using database URL: {get_database_url()}")
    create_db_and_tables()
    print("Tables created successfully!")

if __name__ == "__main__":
    main() 