import json
import os

def generate(id):
    script_dir = os.path.dirname(os.path.abspath(__file__))
    DIR = os.path.join(script_dir, "rdf_dataset")

    input_json_path = os.path.join(DIR, "rdf_berita.json")
    output_ttl_path = os.path.join(DIR, f"berita_{id}.ttl")

    if not os.path.exists(input_json_path):
        print(f"Input file not found: {input_json_path}")
        return

    with open(input_json_path, 'r', encoding='utf-8') as f:
        rdf_data = json.load(f)

    rdf_str = ""

    for item in rdf_data:
        if id == item["id"]:
            rdf_str = item["text"]

    with open(output_ttl_path, 'w', encoding='utf-8') as f:
        f.write(rdf_str)

    if rdf_str == "":
        print(f"Input ID not found: {input_json_path}")
        return

def main():
    inp = int(input("Masukkan ID: "))
    generate(inp)


if __name__ == "__main__":
    main()