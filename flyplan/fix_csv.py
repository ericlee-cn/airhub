import csv

# 读取原CSV
with open('route_library.csv', 'r', encoding='utf-8') as f:
    reader = csv.DictReader(f)
    rows = list(reader)

# 修复geojson字段
for row in rows:
    if row.get('geojson'):
        json_str = row['geojson']
        # 去掉首尾引号
        if json_str.startswith('"') and json_str.endswith('"'):
            json_str = json_str[1:-1]
        # 给键名加引号
        json_str = json_str.replace('type:', '"type":')
        json_str = json_str.replace('coordinates:', '"coordinates":')
        row['geojson'] = json_str

# 写回CSV
with open('route_library.csv', 'w', encoding='utf-8', newline='') as f:
    writer = csv.DictWriter(f, fieldnames=rows[0].keys())
    writer.writeheader()
    writer.writerows(rows)

print('CSV已修复')
print('第一条geojson:', rows[0]['geojson'][:100])
