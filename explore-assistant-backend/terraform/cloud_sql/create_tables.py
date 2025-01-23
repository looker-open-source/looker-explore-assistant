import json
import mysql.connector

def get_cloudsql_config():
    with open("cloudsql_outputs.json", "r") as f:
        data = json.load(f)
    return data["cloudsql_instance_info"]["value"]

def create_tables():
    config = get_cloudsql_config()

    conn = mysql.connector.connect(
        host=config["public_ip"],
        user=config["username"],
        password=config["password"],
        database=config["database"]
    )
    cursor = conn.cursor()

    with open("schema.sql", "r") as sql_file:
        sql_commands = sql_file.read().split(";")

        for command in sql_commands:
            if command.strip():
                cursor.execute(command)
                print(f"Executed: {command.strip()}")

    conn.commit()
    cursor.close()
    conn.close()
    print("Tables created successfully!")

if __name__ == "__main__":
    create_tables()
