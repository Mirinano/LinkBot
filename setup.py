import sqlite3

conn=sqlite3.connect("Link.db", isolation_level=None)

sql = "CREATE TABLE IF NOT EXISTS unit(channel INTEGER, unit VARCHAR(25), webhook VARCHAR(150));"

conn.execute(sql)

sql = "CREATE TABLE IF NOT EXISTS message(message INTEGER, channel INTEGER, server INTEGER, unit VARCHAR(25));"

conn.execute(sql)

sql = "CREATE TABLE IF NOT EXISTS master(unit VARCHAR(25), channel INTEGER, webhook VARCHAR(150));"

conn.execute(sql)

sql = "CREATE TABLE IF NOT EXISTS black(user INTEGER, name VARCHAR(25));"

c = conn.execute(sql)
