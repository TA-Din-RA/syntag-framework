import json
import os
import glob
import re
from collections import defaultdict

def to_camel_case(text):
    """
    Mengubah teks label relasi menjadi camelCase untuk Predikat RDF.
    Contoh: 'mengurangi kemungkinan menjadi' -> 'mengurangiKemungkinanMenjadi'
    """
    # Hapus karakter khusus, sisakan huruf, angka, dan spasi
    clean_text = re.sub(r'[^\w\s]', '', text.strip())
    words = clean_text.split()
    if not words:
        return "relatedTo" # Fallback jika kosong
    
    # Kata pertama kecil, sisa kata depannya kapital
    return words[0].lower() + "".join(word.capitalize() for word in words[1:])

def parse_markdown_to_rdf(markdown_content):
    nodes = {}
    # edges_dict[source][predicate] = set(target1, target2)
    edges_dict = defaultdict(lambda: defaultdict(set))

    # Pecah konten berdasarkan garis putus-putus pembatas (-- atau ---)
    blocks = re.split(r'\n\s*[-–]+\s*\n', markdown_content)

    for block in blocks:
        if "### Node ID:" in block:
            node_id, label, node_type = None, None, None
            for line in block.split('\n'):
                line = line.strip()
                if line.startswith("### Node ID:"):
                    node_id = line.replace("### Node ID:", "").strip().replace("*", "")
                elif line.startswith("**Label**:"):
                    label = line.replace("**Label**:", "").strip().replace("*", "")
                elif line.startswith("**Type**:"):
                    node_type = line.replace("**Type**:", "").strip().replace("*", "")
            
            if node_id:
                nodes[node_id] = {'label': label, 'type': node_type}

        elif "**Source**:" in block:
            source, target, label = None, None, None
            for line in block.split('\n'):
                line = line.strip()
                if line.startswith("**Source**:"):
                    source = line.replace("**Source**:", "").strip().replace("*", "")
                elif line.startswith("**Target**:"):
                    target = line.replace("**Target**:", "").strip().replace("*", "")
                elif line.startswith("**Label**:"):
                    label = line.replace("**Label**:", "").strip().replace("*", "")
            
            if source and target and label:
                predicate = to_camel_case(label)
                edges_dict[source][predicate].add(target)

    rdf_lines = []
    
    rdf_lines.append("@prefix : <http://example.org/> .")
    rdf_lines.append("@prefix rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#> .")
    rdf_lines.append("@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .")
    rdf_lines.append("@prefix xsd: <http://www.w3.org/2001/XMLSchema#> .\n")

    rdf_lines.append("# Triples")
    for source, predicates in edges_dict.items():
        for predicate, targets in predicates.items():
            targets_str = ", ".join([f":{t}" for t in sorted(list(targets))])
            rdf_lines.append(f":{source} :{predicate} {targets_str} .")

    rdf_lines.append("\n# Definisi Node Non-Entity")
    for node_id, data in nodes.items():
        if data['type'].lower() != 'entity':
            rdf_lines.append(f":{node_id} rdf:type :{data['type']} ;")
            safe_label = data['label'].replace('"', '\\"')
            rdf_lines.append(f'    rdfs:label "{safe_label}" .\n')

    final_output = "\n".join(rdf_lines)
    return final_output

def main():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    
    INPUT_DIR = os.path.join(script_dir, "markdown_dataset")
    OUTPUT_DIR = os.path.join(script_dir, "rdf_dataset")
    
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    
    input_json_path = os.path.join(INPUT_DIR, "markdown_berita.json")
    output_json_path = os.path.join(OUTPUT_DIR, "rdf_berita.json")

    if not os.path.exists(input_json_path):
        print(f"Input file not found: {input_json_path}")
        return
    
    with open(input_json_path, 'r', encoding='utf-8') as f:
        markdown_data = json.load(f)

    rdf_results = []

    for item in markdown_data:
        text_id = item["id"]
        markdown_content = item["text"]
        
        try:
            rdf_str = parse_markdown_to_rdf(markdown_content)

            rdf_results.append({
                "id": text_id,
                "text": rdf_str
            })
        except Exception as e:
            print(f"Error processing ID {text_id}: {e}")

    rdf_results = sorted(rdf_results, key=lambda x: x["id"])

    with open(output_json_path, 'w', encoding='utf-8') as f:
        json.dump(rdf_results, f, ensure_ascii=False, indent=2)

    print(f"Berhasil mengkonversi {len(rdf_results)} data ke {output_json_path}")

if __name__ == "__main__":
    main()