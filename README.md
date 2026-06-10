# SYNTAG: Synthetic Data and Graph

SYNTAG is an automated framework for generating synthetic text datasets and corresponding knowledge graphs in Indonesian. The framework supports multiple text types, including news articles, paper abstracts, and social media posts (tweets).

The framework consists of three main stages:

## 1. Synthetic Data Generation

This stage focuses on generating synthetic textual data using GPT-OSS-120B.

### Workflow

For each text type, the framework performs the following steps:

1. Sample a topic from a predefined topic pool to ensure content diversity.
2. Generate a user prompt based on the sampled topic.
3. Send a request to the LLM through the Groq API using the system prompt and generated user prompt.
4. Parse the model response and extract the generated JSON data.
5. Save a checkpoint to record the current generation progress.
6. Store the generated data in a JSON file.

### How to Run

#### Install Dependencies

```bash
pip install requests tqdm python-dotenv
```

#### Configure Environment Variables

Create a `.env` file in the project root directory:

```env
GROQ_API_KEY=your_groq_api_key
```

#### Run the Generator

Navigate to the `1-synthetic-data-generation` directory and execute:

```bash
python synthetic_data_gen.py
```

---

## 2. Text-to-Graph

This stage converts the generated synthetic text into a standardized knowledge graph representation using the Resource Description Framework (RDF).

### Workflow

1. Load the generated synthetic text data.
2. Extract informations using GPT-OSS-120B.
3. Convert the extracted information into a markdown-based representation.
4. Convert the markdown representation into RDF format.
5. Generate and store the final RDF graph.

### How to Run

#### Install Dependencies

```bash
pip install requests tqdm python-dotenv
```

#### Configure Environment Variables

Create a `.env` file in the project root directory:

```env
GROQ_API_KEY=your_groq_api_key
```

#### Run the Pipeline

Navigate to the `2-text-to-graph` directory and select the desired text type (e.g., berita, abstrak, or tweet).

Execute the following scripts sequentially:

```bash
python 1-text-to-information.py
python 2-information-to-markdown.py
python 3-markdown-to-rdf.py
python 4-rdf-generator.py
```

---

## 3. Fine-Tuning Small Language Model

This stage fine-tunes smaller language model using the generated synthetic data and its RDF format.

### Limitations

This notebook is specifically designed to be run using Google Colab. To run the code using local computer, the code needs further adjustments.

### Workflow

1. Load model to be fine-tuned using Unsloth.
2. Load input and output dataset created in the past steps for fine-tuning dataset.
3. Form instructions for fine-tuning.
4. Fine-tune the model using instructions, input, and output.
5. Infer the results of fine-tuning using prepared test dataset.

### How to Run

#### Install Dependencies

Dependencies are written in the notebook and could immediately be ran.

#### Configure Environment Variables

Add a new secret through the Secret menu in Google Colab (on the sidebar) and choose Add New Secret. Fill the following columns with the following values:

```
Name = GROQ_API_KEY
Value = <your_groq_api_key>
```

#### Adjust the Paths

Adjust the paths for input, output, testing datasets, and other needed files based on the paths of folder in Google Drive.

#### Run the Pipeline

Run all of the cells one by one based on the order in the file.

---

## Output

The framework produces:

* Synthetic textual datasets in JSON format.
* RDF graph representations in Turtle (.ttl) format.
* Fine-tuned small language model.

---
