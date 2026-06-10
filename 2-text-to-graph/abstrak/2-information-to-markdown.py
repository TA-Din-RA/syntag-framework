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
        "Judul": "",
        "Masalah": "",
        "Topik": "",
        "Metodologi": "",
        "Dataset": "",
        "Evaluasi": "",
        "Hasil": []
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

        if current_section == "Entitas":
            if clean_line.startswith('-'):
                data["Entitas"].append(clean_line[1:].strip())

        elif current_section == "Relasi Antar Entitas":
            if clean_line.startswith('-'):
                data["Relasi"].append(clean_line[1:].strip())

        elif current_section == "Masalah Penelitian":
            data["Masalah"] += clean_line

        elif current_section == "Judul Penelitian":
            data["Judul"] += clean_line

        elif current_section == "Domain/Topik":
            data["Topik"] += clean_line

        elif current_section == "Metodologi/Pendekatan":
            data["Metodologi"] += clean_line

        elif current_section == "Dataset/Sumber Data":
            data["Dataset"] += clean_line

        elif current_section == "Pendekatan Evaluasi/Validasi":
            data["Evaluasi"] += clean_line

        elif current_section == "Hasil/Temuan Utama":
            if line.startswith('-'):
                data["Hasil"].append(clean_line[1:].strip())

    return data

# converting information to markdown function
def process_information_to_markdown(text_content):
    data = parse_input_file(text_content)

    nodes_markdown = "# Nodes\n"
    edges_markdown = "# Edges\n"
    
    created_nodes = set()

    # if the result from extraction has yet to have "Penelitian"
    nodes_markdown += format_node("Penelitian", "Penelitian", "Entity")
    created_nodes.add("Penelitian")

    # inputting entities
    for ent in data["Entitas"]:
        if ent.lower() == "penelitian":
            node_id = "Penelitian"
        else:
            node_id = generate_node_id(ent)
            
        if node_id not in created_nodes:
            nodes_markdown += format_node(node_id, ent, "Entity")
            created_nodes.add(node_id)

    # mapping additional information
    metadata_map = [
        ("Masalah", "Masalah_Penelitian", "Problem", "memiliki masalah"),
        ("Topik", "Topik_Penelitian", "Topic", "bertopik"),
        ("Judul", "Judul_Penelitian", "Title", "berjudul"),
        ("Metodologi", "Metodologi_Penelitian", "Methodology", "menggunakan metodologi"),
        ("Dataset", "Sumber_Data_Penelitian", "DataSource", "menggunakan sumber data"),
        ("Evaluasi", "Indikator_Evaluasi", "EvaluationIndicator", "dievaluasi menggunakan")
    ]

    for key, node_id, node_type, edge_label in metadata_map:
        if data[key]:
            cek_teks = data[key].strip().lower().replace(".", "")
            # no need to convert to markdown if no information was found
            if cek_teks not in ["tidak disebutkan", "-"]:
                nodes_markdown += format_node(node_id, data[key], node_type)
                edges_markdown += format_edge("Penelitian", node_id, edge_label)

    # inputting results
    for idx, hasil in enumerate(data["Hasil"], start=1):
        node_id = f"Hasil_Penelitian_{idx}"
        nodes_markdown += format_node(node_id, hasil, "Result")
        edges_markdown += format_edge("Penelitian", node_id, "menghasilkan")

    # inputting relations
    for rel in data["Relasi"]:
        parts = [p.strip() for p in rel.split("|")]
        if len(parts) == 3:
            raw_source = parts[0]
            raw_label = parts[1]
            raw_target = parts[2]
            
            if raw_source.lower() == "penelitian":
                source_id = "Penelitian"
            else:
                source_id = generate_node_id(raw_source)

            if raw_target.lower() == "penelitian":
                target_id = "Penelitian"
            else:
                target_id = generate_node_id(raw_target)
                
            # if there are entities not predefined but used in relations 
            if source_id not in created_nodes:
                nodes_markdown += format_node(source_id, raw_source, "Entity")
                created_nodes.add(source_id)

            if target_id not in created_nodes:
                nodes_markdown += format_node(target_id, raw_target, "Entity")
                created_nodes.add(target_id)
            
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
    
    input_json_path = os.path.join(INPUT_DIR, "extracted_abstrak.json")
    output_json_path = os.path.join(OUTPUT_DIR, "markdown_abstrak.json")

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