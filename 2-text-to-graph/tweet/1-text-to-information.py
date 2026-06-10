import os
import json
import time
import random
import logging
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv

import requests
from tqdm import tqdm

# ─────────────────────────────────────────────
# KONFIGURASI PATH & ENV
# ─────────────────────────────────────────────
load_dotenv()

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
MODEL        = "openai/gpt-oss-120b" 

ROOT_DIR     = Path(__file__).resolve().parent.parent.parent
PATH_INPUT   = ROOT_DIR / "1-synthetic-data-generation" / "synthetic_output" / "checkpoints" / "tweet_checkpoint.json"
OUTPUT_DIR   = Path(__file__).resolve().parent / "information_dataset"

# Rate limit settings
MAX_RETRIES     = 8
BASE_DELAY      = 2.0      
MAX_DELAY       = 120.0     
REQUEST_DELAY   = 2.5      

# ─────────────────────────────────────────────
# SETUP LOGGING & DIRECTORY
# ─────────────────────────────────────────────

OUTPUT_DIR.mkdir(exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(Path(__file__).resolve().parent / "tweet-generation.log", encoding="utf-8"),
        logging.StreamHandler()
    ]
)
log = logging.getLogger(__name__)
# ─────────────────────────────────────────────
# PROMPT TEMPLATE
# ─────────────────────────────────────────────
PROMPT = {
    "system": """Kamu adalah asisten yang ahli dalam ekstraksi informasi teks. Tugasmu adalah mengekstrak informasi secara akurat, eksplisit, dan terstruktur dari teks.

Instruksi:
- Gunakan hanya informasi yang benar-benar ada di teks.
- Jangan melakukan asumsi atau inferensi yang membutuhkan pengetahuan di luar teks.
- Jangan menambahkan informasi yang tidak didukung oleh teks.
- Lakukan ekstraksi dengan teliti dan akurat berdasarkan teks.
- Jika suatu kategori benar-benar tidak ditemukan dalam teks, lewati bagian tersebut tanpa menuliskan labelnya.

Domain teks yang akan diekstraksi: Media Sosial (Tweet)

Dari setiap teks, identifikasi:
1. Entitas : subjek atau objek dalam kalimat.
2. Relasi antar entitas : berupa subjek-predikat-objek dalam teks. Relasi hanya boleh diekstrak antara entitas yang sudah terdaftar pada tahap ekstraksi entitas sebelumnya.
3. Topik utama tweet : isu atau pembahasan inti dalam tweet.
4. Sentimen : sikap atau opini penulis terhadap entitas atau peristiwa (Positif / Negatif / Netral). Jika memungkinkan, sebutkan sentimen terhadap masing-masing entitas yang relevan.



Sajikan jawaban dengan format berikut:

[Entitas]
- ...
- ...

[Relasi Antar Entitas]
- Entitas A | relasi | Entitas B
- ...

[Topik Utama]
 ...

[Sentimen]
- [Positif/Netral/Negatif]: Alasan

---

Sebagai panduan dalam melakukan ekstraksi, berikut 1 buah contoh teks beserta format serta hasil ekstraksi dan analisis teks yang diharapkan:


---


CONTOH TEKS 1:
I GOT RACIAL BULLYING FOR THE VERY FIRST TIME HERE IN THE US.
Aku ga nyangka dapet tindakan rasisme dari SESAMA ORANG INDONESIA, ORANG BALI.


Disclaimer:
Aku gak menjelekkan orang Bali disini, aku cuma cerita tindakan kurang mengenakkan yang aku dapatkan dari seseorang, hari ini.


CONTOH HASIL EKSTRAKSI TEKS 1:
[Entitas]
- Aku
- Racial Bullying/tindakan rasisme
- US
- Orang Indonesia
- Orang Bali


[Relasi Antar Entitas]
- Aku | mendapatkan | racial bullying
- Racial bullying | terjadi di | US
- Racial bullying | dilakukan oleh | orang Indonesia
- Racial bullying | dilakukan oleh | orang Bali
- Aku | tidak menjelekkan | orang Bali


[Topik]
Aku mengalami racial bullying oleh sesama orang Indonesia, secara spesifik orang Bali


[Sentimen]
- Negatif: penulis tidak menyangka akan mendapatkan perilaku rasisme oleh sesama orang indonesia

---""",

    "user_template": """Ekstrak informasi untuk teks berikut:
Teks: {teks}

Jawaban:"""
}

# ─────────────────────────────────────────────
# API CALL FUNCTION
# ─────────────────────────────────────────────

def call_groq_api(system_prompt: str, user_prompt: str) -> str:
    """
    Call Groq API with exponential backoff + jitter for rate limit
    """
    url     = "https://api.groq.com/openai/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type":  "application/json"
    }
    payload = {
        "model": MODEL,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user",   "content": user_prompt}
        ],
        "temperature": 0,
        "max_tokens":  2000,
    }

    delay = BASE_DELAY
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            resp = requests.post(url, headers=headers, json=payload, timeout=60)

            if resp.status_code == 429:
                retry_after = float(resp.headers.get("Retry-After", delay))
                wait = min(retry_after + random.uniform(0.5, 2.0), MAX_DELAY)
                log.warning(f"  Rate limit 429. Tunggu {wait:.1f}s... (percobaan {attempt}/{MAX_RETRIES})")
                time.sleep(wait)
                delay = min(delay * 2, MAX_DELAY)
                continue

            resp.raise_for_status()
            return resp.json()["choices"][0]["message"]["content"]

        except Exception as e:
            wait = min(delay + random.uniform(0, 2), MAX_DELAY)
            log.error(f"  Error: {e}. Retry dalam {wait:.1f}s... (percobaan {attempt}/{MAX_RETRIES})")
            time.sleep(wait)
            delay = min(delay * 2, MAX_DELAY)

    raise RuntimeError(f"Gagal setelah {MAX_RETRIES} percobaan.")

# ─────────────────────────────────────────────
# MAIN PROCESSING
# ─────────────────────────────────────────────

def main():
    log.info("=" * 60)
    log.info("TEXT TO INFORMATION EXTRACTION")
    log.info(f"Model : {MODEL}")
    log.info(f"Input : {PATH_INPUT}")
    log.info(f"Output: {OUTPUT_DIR}")
    log.info("=" * 60)

    if not PATH_INPUT.exists():
        log.error(f"File {PATH_INPUT} not found.")
        return

    # load dataset from synthetic data JSON
    with open(PATH_INPUT, "r", encoding="utf-8") as f:
        dataset = json.load(f)

    TARGET_JSON = OUTPUT_DIR / "extracted_tweet.json"

    extracted_data = []
    existing_ids = set()

    if TARGET_JSON.exists():
        with open(TARGET_JSON, "r", encoding="utf-8") as f:
            extracted_data = json.load(f)
            existing_ids = {item["id"] for item in extracted_data}

    success_count = 0
    
    for item in tqdm(dataset, desc="Extraction Process", unit="data"):
        text_id  = item.get("id")
        raw_text = item.get("text", "")

        if not raw_text:
            continue

        if text_id in existing_ids:
            success_count += 1
            continue

        try:
            user_prompt = PROMPT["user_template"].format(teks=raw_text)
            
            extracted_info = call_groq_api(PROMPT["system"], user_prompt)
            
            extracted_data.append({
                "id": text_id,
                "text": extracted_info
            })
            existing_ids.add(text_id)
            
            with open(TARGET_JSON, "w", encoding="utf-8") as f:
                json.dump(extracted_data, f, ensure_ascii=False, indent=2)
            
            success_count += 1
            
            time.sleep(REQUEST_DELAY)

        except Exception as e:
            log.error(f"  ID {text_id} Gagal: {e}")
            if "Gagal setelah" in str(e):
                log.info("Berhenti karena API gagal total.")
                break


if __name__ == "__main__":
    main()