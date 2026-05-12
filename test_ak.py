import sys
sys.path.insert(0, 'server')
from getAkshare import get_akshare_data

print("=== 开始 ===", flush=True)
df = get_akshare_data('300308', 2024, 2026)
print(f"=== 结束: {len(df)} 行 ===", flush=True)
if not df.empty:
    for _, row in df.iterrows():
        print(row.to_dict())