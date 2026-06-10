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
        "Topik": "",
        "Sentimen": []
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

        elif current_section == "Topik Utama" or current_section == "Topik":
            data["Topik"] += clean_line + " "

        elif current_section == "Sentimen":
            if clean_line.startswith('-'):
                data["Sentimen"].append(clean_line[1:].strip())

    return data

# converting information to markdown function
def process_information_to_markdown(text_content):
    data = parse_input_file(text_content)

    nodes_markdown = "# Nodes\n"
    edges_markdown = "# Edges\n"
    
    created_nodes = set()

    nodes_markdown += format_node("Unggahan", "Unggahan", "Entity")
    created_nodes.add("Unggahan")

    # inputting entities
    for ent in data["Entitas"]:
        if ent.lower() == "unggahan":
            node_id = "Unggahan"
        else:
            node_id = generate_node_id(ent)
            
        if node_id not in created_nodes:
            nodes_markdown += format_node(node_id, ent, "Entity")
            created_nodes.add(node_id)

    # mapping mandatory relation
    if data["Entitas"]:
        subjek_utama = data["Entitas"][0]
        if subjek_utama.lower() == "unggahan":
            subjek_id = "Unggahan"
        else:
            subjek_id = generate_node_id(subjek_utama)
            
        edges_markdown += format_edge("Unggahan", subjek_id, "mengenai")

    # mapping additional information
    if data["Topik"].strip():
        topik_id = "Topik"
        nodes_markdown += format_node(topik_id, data["Topik"].strip(), "Topic")
        edges_markdown += format_edge("Unggahan", topik_id, "memilikiTopik")
        created_nodes.add(topik_id)

    for sentimen_text in data["Sentimen"]:
    
        if ":" in sentimen_text:
            label_part = sentimen_text.split(":", 1)[0].strip()
            reason_part = sentimen_text.split(":", 1)[1].strip()
            
            sentimen_id = generate_node_id(label_part)
            if sentimen_id not in created_nodes:
                nodes_markdown += format_node(sentimen_id, label_part, "Sentiment")
                created_nodes.add(sentimen_id)
                
            edges_markdown += format_edge("Unggahan", sentimen_id, "memilikiSentimen")
            
            if reason_part:
                alasan_id = generate_node_id(reason_part)
                if alasan_id not in created_nodes:
                    nodes_markdown += format_node(alasan_id, reason_part, "Sentiment")
                    created_nodes.add(alasan_id)
                    
                edges_markdown += format_edge(sentimen_id, alasan_id, "memiliki alasan")
                
        else:
            sentimen_id = generate_node_id(sentimen_text)
            if sentimen_id not in created_nodes:
                nodes_markdown += format_node(sentimen_id, sentimen_text, "Sentiment")
                created_nodes.add(sentimen_id)
                
            edges_markdown += format_edge("Unggahan", sentimen_id, "memilikiSentimen")

    # inputting relations
    for rel in data["Relasi"]:
        parts = [p.strip() for p in rel.split("|")]
        if len(parts) == 3:
            raw_source = parts[0]
            raw_label = parts[1]
            raw_target = parts[2]
            
            if raw_source.lower() == "unggahan":
                source_id = "Unggahan"
            else:
                source_id = generate_node_id(raw_source)

            if raw_target.lower() == "unggahan":
                target_id = "Unggahan"
            else:
                target_id = generate_node_id(raw_target)
                
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
    
    input_json_path = os.path.join(INPUT_DIR, "extracted_tweet.json")
    output_json_path = os.path.join(OUTPUT_DIR, "markdown_tweet.json")

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