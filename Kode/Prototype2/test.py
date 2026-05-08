from database import get_connection

try:
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT 1;")
    print("Database connection works!")
except Exception as e:
    print("Database connection failed:", e)
"""
create table device(
id serial primary key,
mac_adresse varchar(100) not null,
last_seen timestamp
);

create table positions(
id serial primary key,
device_id int references device(id),
x float not null,
y float not null,
z float not null,
timestamp TIMESTAMP not null
);
"""