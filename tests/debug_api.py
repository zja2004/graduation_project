
import requests
import json

def debug_api():
    url = "https://myvariant.info/v1/variant/chr7:g.140753336A>T?assembly=hg38&fields=clinvar"
    r = requests.get(url)
    data = r.json()
    
    print("Keys in data:", data.keys())
    if "clinvar" in data:
        cv = data["clinvar"]
        print("Type of clinvar:", type(cv))
        if isinstance(cv, dict):
            print("Keys in clinvar:", cv.keys())
            if "rcv" in cv:
                print("Type of rcv:", type(cv["rcv"]))
                if isinstance(cv["rcv"], list) and len(cv["rcv"]) > 0:
                    print("First RCV:", cv["rcv"][0].keys())
    else:
        print("clinvar key not found")

if __name__ == "__main__":
    debug_api()
