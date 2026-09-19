import os
from pathlib import Path

downloads_dir = Path("C:/Users/gowda/Downloads")
print(f"Checking directory: {downloads_dir} (exists={downloads_dir.exists()})")

target_uuids = ["25e20bcf", "224b7307", "edef3d0e", "d15c0b09"]

if downloads_dir.exists():
    items = sorted(downloads_dir.iterdir(), key=lambda p: p.stat().st_mtime, reverse=True)
    print(f"Total items in Downloads: {len(items)}")
    
    # 1. Look for matching files
    matched = []
    for item in items:
        if not item.is_file():
            continue
        name = item.name
        if any(u in name for u in target_uuids) or "Satya" in name or "Report" in name:
            matched.append(item)

    print(f"Found {len(matched)} matched files:")
    for item in matched[:15]:
        size = item.stat().st_size
        try:
            with open(item, "rb") as f:
                header = f.read(64)
            print(f"  FILE: {item.name}")
            print(f"    Size: {size} bytes")
            print(f"    First 64 bytes: {header}")
            try:
                text = header.decode("utf-8")
                print(f"    As text: {text}")
            except Exception:
                pass
        except Exception as e:
            print(f"  Error reading {item.name}: {e}")

    # 2. Also print the top 10 most recent files in Downloads
    print("\nMost recent 10 files in Downloads:")
    for item in items[:10]:
        if item.is_file():
            print(f"  {item.name} ({item.stat().st_size} bytes)")
