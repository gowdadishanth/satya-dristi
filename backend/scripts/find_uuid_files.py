import os
from pathlib import Path

target_uuids = ["25e20bcf", "224b7307", "edef3d0e", "d15c0b09"]

search_roots = [
    Path("C:/Users/gowda/Downloads"),
    Path("D:/SIH 2026"),
    Path("C:/Users/gowda/AppData/Local/Temp"),
]

for root in search_roots:
    print(f"Scanning {root}...")
    if not root.exists():
        continue
    for dirpath, dirnames, filenames in os.walk(root):
        for f in filenames:
            if any(u in f for u in target_uuids):
                full_path = os.path.join(dirpath, f)
                size = os.path.getsize(full_path)
                print(f"FOUND MATCH: {full_path} (size: {size} bytes)")
                try:
                    with open(full_path, "rb") as fp:
                        raw = fp.read(256)
                    print(f"  First 256 bytes: {raw}")
                except Exception as e:
                    print(f"  Read error: {e}")
print("Scan complete.")
