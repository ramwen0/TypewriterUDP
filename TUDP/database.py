import sqlite3

connect = sqlite3.connect('userdata.db')
cursor = connect.cursor()
cursor.execute("""
    CREATE TABLE IF NOT EXISTS userdata (
        id INTEGER PRIMARY KEY,
        username VARCHAR(255) NOT NULL,
        password VARCHAR(255) NOT NULL
    )
""")

# Commit the changes
connect.commit()

# Close the connection
connect.close()