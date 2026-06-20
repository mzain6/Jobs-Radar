import sqlite3
conn = sqlite3.connect('backend/radar.db')
rows = conn.execute("SELECT DISTINCT source, COUNT(*) as n FROM jobs GROUP BY source").fetchall()
for r in rows:
    print(r[0], r[1])
print('---')
rows2 = conn.execute("SELECT source, url FROM jobs WHERE source='linkedin' LIMIT 5").fetchall()
for r in rows2:
    print(r[0], '|', r[1])
conn.close()
