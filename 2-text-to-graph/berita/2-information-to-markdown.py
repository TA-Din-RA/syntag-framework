import json
import os
import glob
import re

# generating node ID function
def generate_node_id(label):
    clean_label = re.sub(r'[^\w\s-]', '', str(label))
    words = clean_label.split()
    return "_".join([word.capitalize() for word in words])

# formatting nodes markdown function
def format_node(node_id, label, node_type):
    return f"### Node ID: {node_id}\n**Label**: {label}\n**Type**: {node_type}\n--\n\n"

# formatting edges markdown function
def format_edge(source_id, target_id, label):
    return f"**Source**: {source_id}\n**Target**: {target_id}\n**Label**: {label}\n--\n\n"

# parse input function
def parse_input_file(text_content):
    data = {
        "Entitas": [],
        "Relasi": [],
        "Sentimen": [],
        "Kutipan": [],
        "5W1H": {},
        "Kronologi": [],
        "Mereologi": []
    }
    
    lines = text_content.strip().split('\n')

    current_section = None

    for line in lines:
        line = line.strip()
        if not line:
            continue

        clean_line = line.strip('*').strip()
            
        # if the row is determined as header (in between [])
        if clean_line.startswith('[') and clean_line.endswith(']'):
            current_section = clean_line[1:-1]
            continue

        # inserting data from input into data list
        if current_section == "Entitas":
            if clean_line.startswith('-'):
                data["Entitas"].append(clean_line[1:].strip())

        elif current_section == "Relasi Antar Entitas":
            if clean_line.startswith('-'):
                data["Relasi"].append(clean_line[1:].strip())

        elif current_section == "Sentimen":
            if clean_line.startswith('-'):
                data["Sentimen"].append(clean_line[1:].strip())

        elif current_section == "Kutipan Dalam Berita":
            if clean_line.startswith('-'):
                data["Kutipan"].append(clean_line[1:].strip())

        elif current_section == "5W1H":
            if clean_line.startswith('-'):
                parts = clean_line[1:].strip().split(':', 1)
                if len(parts) == 2:
                    data["5W1H"][parts[0].strip()] = parts[1].strip()

        elif current_section == "Urutan Kronologis":
            if clean_line.startswith('-'):
                data["Kronologi"].append(clean_line[1:].strip())

        elif current_section == "Hubungan Bagian‑Keseluruhan (Mereologi)" or current_section == "Hubungan Bagian‑Keseluruhan":
            if clean_line.startswith('-'):
                data["Mereologi"].append(clean_line[1:].strip())

    return data

# converting information to markdown function
def process_information_to_markdown(text_content):
    data = parse_input_file(text_content)

    nodes_markdown = "# Nodes\n"
    edges_markdown = "# Edges\n"
    
    created_nodes = set()
    entity_ids = [] # to store entity IDs for linking with 'What' and 'Who'

    nodes_markdown += format_node("Teks_Berita", "Teks Berita", "Entity")
    created_nodes.add("Teks_Berita")

    # inputting entities
    for ent in data["Entitas"]:
        if ent.lower() == "teks berita":
            node_id = "Teks_Berita"
        else:
            node_id = generate_node_id(ent)
            
        if node_id not in created_nodes:
            nodes_markdown += format_node(node_id, ent, "Entity")
            created_nodes.add(node_id)
            entity_ids.append(node_id)

    nodes_markdown += format_node("Node_5W1H", "5W1H", "5W1H_Utama")
    created_nodes.add("Node_5W1H")
    edges_markdown += format_edge("Teks_Berita", "Node_5W1H", "memiliki5W1H")

    # inputting 5W1H nodes
    for key, val in data["5W1H"].items():
        element_id = generate_node_id(key)
        if element_id not in created_nodes:
            nodes_markdown += format_node(element_id, key, "5W1H_Elemen")
            created_nodes.add(element_id)

        edges_markdown += format_edge("Node_5W1H", element_id, "memiliki")

        items = [item.strip() for item in val.split(',')]
        for item in items:
            if not item:
                continue
            
            item_id = generate_node_id(item)

            if item_id not in created_nodes:
                nodes_markdown += format_node(item_id, item, "Entity")
                created_nodes.add(item_id)
                entity_ids.append(item_id)
            
            edges_markdown += format_edge(element_id, item_id, "merujuk_pada")

    # inputting sentiment nodes
    for idx, sent in enumerate(data["Sentimen"], start=1):
        sent_type = sent.split(":")[0].strip() if ":" in sent else f"{idx}"
        node_id = f"Sentimen_{generate_node_id(sent_type)}"
        if node_id not in created_nodes:
            nodes_markdown += format_node(node_id, sent, "Sentiment")
            created_nodes.add(node_id)
            
            # Teks_Berita -> memilikiSentimen -> Sentimen
            edges_markdown += format_edge("Teks_Berita", node_id, "memilikiSentimen")
            
            for ent_id in entity_ids:
                ent_label_clean = ent_id.replace("_", " ").lower()
                if ent_label_clean in sent.lower():
                    edges_markdown += format_edge(node_id, ent_id, "Sentimen")
                    break

    # inputting quotes nodes
    for idx, quote in enumerate(data["Kutipan"], start=1):
        node_id = f"Kutipan_{idx}"
        
        if "-" in quote:
            parts = quote.rsplit("-", 1)
            isi_kutipan = parts[0].strip()
            speaker = parts[1].strip()
        else:
            isi_kutipan = quote.strip()
            speaker = ""

        if node_id not in created_nodes:
            nodes_markdown += format_node(node_id, isi_kutipan, "Quotes")
            created_nodes.add(node_id)
            
            edges_markdown += format_edge("Teks_Berita", node_id, "berisiKutipan")
            
            if speaker:
                speaker_id = generate_node_id(speaker)

                if speaker_id not in created_nodes:
                    nodes_markdown += format_node(speaker_id, speaker, "Entity")
                    created_nodes.add(speaker_id)
                    entity_ids.append(speaker_id)

                edges_markdown += format_edge(node_id, speaker_id, "Pernyataan")

    # inputting chronology nodes
    kronologi_ids = []
    for idx, kron in enumerate(data["Kronologi"], start=1):
        node_id = f"Kronologi_{idx}"
        if node_id not in created_nodes:
            nodes_markdown += format_node(node_id, kron, "Chronology")
            created_nodes.add(node_id)
            kronologi_ids.append(node_id)
            
            edges_markdown += format_edge("Teks_Berita", node_id, "memilikiKronologi")

    # mapping chronology edges relations (Sequential)
    for i in range(len(kronologi_ids) - 1):
        label = "Berakhir dengan" if i == len(kronologi_ids) - 2 else "Dilanjutkan dengan"
        edges_markdown += format_edge(kronologi_ids[i], kronologi_ids[i+1], label)

    # inputting relations & mereology (combining both lists)
    all_relations = data["Relasi"] + data["Mereologi"]
    for rel in all_relations:
        parts = [p.strip() for p in rel.split("|")]
        if len(parts) == 3:
            raw_source = parts[0]
            raw_label = parts[1]
            raw_target = parts[2]
            
            if raw_source.lower() == "teks berita":
                source_id = "Teks_Berita"
            else:
                source_id = generate_node_id(raw_source)

            if raw_target.lower() == "teks berita":
                target_id = "Teks_Berita"
            else:
                target_id = generate_node_id(raw_target)
                
            if source_id not in created_nodes:
                nodes_markdown += format_node(source_id, raw_source, "Entity")
                created_nodes.add(source_id)
                entity_ids.append(source_id)

            if target_id not in created_nodes:
                nodes_markdown += format_node(target_id, raw_target, "Entity")
                created_nodes.add(target_id)
                entity_ids.append(target_id)
            
            edges_markdown += format_edge(source_id, target_id, raw_label)

    # insert into output
    final_output = nodes_markdown + "\n" + edges_markdown
    return final_output

# main program function
def main():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    INPUT_DIR = os.path.join(script_dir, "information_dataset")
    OUTPUT_DIR = os.path.join(script_dir, "markdown_dataset")
    
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    
    input_json_path = os.path.join(INPUT_DIR, "extracted_berita.json")
    output_json_path = os.path.join(OUTPUT_DIR, "markdown_berita.json")

    if not os.path.exists(input_json_path):
        print(f"Input file not found: {input_json_path}")
        return
    
    with open(input_json_path, 'r', encoding='utf-8') as f:
        extracted_data = json.load(f)

    markdown_results = []

    for item in extracted_data:

        text_id = item["id"]
        text_content = item["text"]

        try:
            markdown_str = process_information_to_markdown(text_content)
            markdown_results.append({
                "id": int(text_id),
                "text": markdown_str
            })
            
        except Exception as e:
            print(f"Error processing ID {text_id}: {e}")

    markdown_results = sorted(markdown_results, key=lambda x: x["id"])

    with open(output_json_path, 'w', encoding='utf-8') as f:
        json.dump(markdown_results, f, ensure_ascii=False, indent=2)


# calling main program function
if __name__ == "__main__":
    main()