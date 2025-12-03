import requests
import json

url = "https://www.ebi.ac.uk/chembl/api/data/assay.json?limit=1"
try:
    response = requests.get(url)
    response.raise_for_status()
    data = response.json()
    print("Keys:", list(data.keys()))
    if "assays" in data:
        assays = data["assays"]
        print(f"Number of assays: {len(assays)}")
        if assays:
            print(json.dumps(assays[0], indent=2))
    else:
        print("Key 'assays' not found. Full data:")
        print(json.dumps(data, indent=2))
except Exception as e:
    print(f"Error: {e}")
