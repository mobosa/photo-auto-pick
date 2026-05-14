import urllib.request, json

req = urllib.request.Request("http://localhost:8000/api/results/df508517?sort_by=final_score")
resp = urllib.request.urlopen(req)
data = json.loads(resp.read().decode())

results = data.get("results", [])
if results:
    first = results[0]
    print(f"Filename: {first.get('filename')}")
    print(f"exif key exists: {'exif' in first}")
    print(f"exif value: {first.get('exif')}")
    print(f"\nAll keys: {list(first.keys())}")
else:
    print("No results found")
