import requests

def main():
    # Check connectivity to target endpoint
    url = "https://www.ebi.ac.uk/chembl/api/data/target.json?limit=1"
    print(f"Fetching {url}...")
    try:
        resp = requests.get(url, timeout=10)
        print(f"Status: {resp.status_code}")
        print(f"Content length: {len(resp.content)}")
        print("Success!")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    main()

