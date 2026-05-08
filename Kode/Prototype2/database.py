import psycopg2

try:
    conn = psycopg2.connect(
        host="192.168.0.100",      # DIN IP (serveren)
        database="Drone_detektion",
        user="postgres",           # eller den bruger du har lavet
        password="Monster123"    # dit postgres password
    )
    print("Forbindelse virker!")
    conn.close()
except Exception as e:
    print("Fejl:", e)

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