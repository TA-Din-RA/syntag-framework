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
PATH_INPUT   = ROOT_DIR / "1-synthetic-data-generation" / "synthetic_output" / "checkpoints" / "berita_checkpoint.json"
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
        logging.FileHandler(Path(__file__).resolve().parent / "berita-generation.log", encoding="utf-8"),
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

Domain teks yang akan diekstraksi: Berita

Dari setiap teks, identifikasi:
1. Entitas : subjek atau objek dalam kalimat.
2. Relasi antar entitas : subjek-predikat-objek dalam teks. Relasi hanya boleh diekstrak antara entitas yang sudah terdaftar pada tahap ekstraksi entitas sebelumnya.
3. Sentimen : sentimen peristiwa (Positif / Negatif / Netral).
4. Kutipan dalam berita (jika ada) : berisi ucapan langsung dari tokoh
5. 5W1H : berisi unsur What, Who, When, Where, Why, dan How.
6. Urutan kronologis (jika ada) : berisi urutan kejadian penting.
7. Hubungan bagian-keseluruhan (mereologi) (jika ada): berisi keterkaitan bagian dan keseluruhan.

Sajikan jawaban dengan format berikut:

[Entitas]
- ...
- ...

[Relasi Antar Entitas]
- Entitas A | relasi | Entitas B
- ...

[Sentimen]
- [Positif/Netral/Negatif]: Alasan

[Kutipan Dalam Berita] (Hanya tulis jika informasi ditemukan)
- "Isi kutipan" - Nama Tokoh

[5W1H]
- What: ...
- Who: ...
- When: ...
- Where: ...
- Why: ...
- How: ...

[Urutan Kronologis] (Hanya tulis jika informasi ditemukan)
- Kejadian 1
- Kejadian 2

[Hubungan Bagian-Keseluruhan (Mereologi)] (Hanya tulis jika informasi ditemukan)
- Bagian X | bagian dari | Keseluruhan Y

---

Sebagai panduan dalam melakukan ekstraksi, berikut 1 buah contoh teks beserta format serta hasil ekstraksi dan analisis teks yang diharapkan:

---


CONTOH JUDUL TEKS: Jokowi Lantik KSAD Baru di Istana Hari Ini


CONTOH ISI TEKS:
Presiden Joko Widodo (Jokowi) dijadwalkan akan melantik Kepala Staf Angkatan Darat (KSAD) pada Rabu (29/11) di Istana Negara, Jakarta. Informasi itu dibenarkan oleh Ketua Komisi I DPR RI Meutya Hafid. "Ya betul (Jokowi lantik KSAD)," kata Meutya lewat pesan singkat, Selasa (28/11) malam. Namun demikian, Meutya belum memberitahu siapa perwira tinggi yang bakal mengisi kursi KSAD. Sebelumnya, salah satu yang disebut berpeluang besar menjadi KSAD adalah Panglima Komando Cadangan Strategis Angkatan Darat (Pangkostrad) Letjen Maruli Simanjuntak. Presiden Joko Widodo turut membenarkan Maruli merupakan satu dari sejumlah nama jenderal yang masuk dalam bursa KSAD. "Salah satu kandidat," kata Jokowi di Indonesia Arena, Jakarta, Sabtu (25/11). Posisi KSAD kosong setelah Jenderal Agus Subiyanto dilantik menjadi Panglima TNI. Agus sempat menjabat sebagai KSAD menggantikan Jenderal Dudung Abdurachman yang pensiun. Beberapa hari menjabat KSAD, Agus diusulkan Presiden Jokowi menjadi Panglima TNI. Ia baru dilantik pada pekan lalu.

CONTOH HASIL EKSTRAKSI TEKS:
[Entitas]
- Presiden Joko Widodo (Jokowi)
- Kepala Staf Angkatan Darat (KSAD)
- Pelantikan KSAD
- Rabu (29/11)
- Istana Negara
- Jakarta
- Ketua Komisi I DPR RI Meutya Hafid
- Pesan singkat
- Selasa (28/11) malam
- Perwira tinggi
- Panglima Komando Cadangan Strategis Angkatan Darat (Pangkostrad) Letjen Maruli Simanjuntak
- Bursa KSAD
- Kandidat KSAD
- Indonesia Arena
- Sabtu (25/11)
- Posisi KSAD
- Jenderal Agus Subiyanto
- Panglima TNI
- Jenderal Dudung Abdurachman
- Pensiun
- Pekan lalu

[Relasi Antar Entitas]
- Presiden Joko Widodo (Jokowi) | akan melantik | Kepala Staf Angkatan Darat (KSAD)
- Pelantikan KSAD | berlangsung pada | Rabu (29/11)
- Pelantikan KSAD | berlangsung di | Istana Negara
- Istana Negara | berada di | Jakarta
- Ketua Komisi I DPR RI Meutya Hafid | membenarkan | Pelantikan KSAD
- Ketua Komisi I DPR RI Meutya Hafid | menyampaikan lewat | Pesan singkat
- Ketua Komisi I DPR RI Meutya Hafid | menyampaikan pada | Selasa (28/11) malam
- Perwira tinggi | mengisi | Posisi KSAD
- Panglima Komando Cadangan Strategis Angkatan Darat (Pangkostrad) Letjen Maruli Simanjuntak | masuk dalam | Bursa KSAD
- Presiden Joko Widodo (Jokowi) | membenarkan | Panglima Komando Cadangan Strategis Angkatan Darat (Pangkostrad) Letjen Maruli Simanjuntak
- Panglima Komando Cadangan Strategis Angkatan Darat (Pangkostrad) Letjen Maruli Simanjuntak | merupakan | kandidat KSAD
- Presiden Joko Widodo (Jokowi) | menyampaikan di | Indonesia Arena
- Indonesia Arena | berada di | Jakarta
- Presiden Joko Widodo (Jokowi) | menyampaikan pada | Sabtu (25/11)
- Posisi KSAD | kosong setelah | Jenderal Agus Subiyanto
- Jenderal Agus Subiyanto | dilantik menjadi | Panglima TNI
- Jenderal Agus Subiyanto | sebelumnya menjabat sebagai | Kepala Staf Angkatan Darat (KSAD)
- Jenderal Agus Subiyanto | menggantikan | Jenderal Dudung Abdurachman
- Jenderal Dudung Abdurachman | mengalami | Pensiun
- Presiden Joko Widodo (Jokowi) | mengusulkan | Jenderal Agus Subiyanto
- Jenderal Agus Subiyanto | diusulkan menjadi | Panglima TNI
- Jenderal Agus Subiyanto | dilantik pada | Pekan lalu

[Sentimen]
- Positif: Proses pelantikan menunjukkan keberlanjutan kepemimpinan dan pengisian posisi strategis di TNI

[Kutipan Dalam Berita]
- "Ya betul (Jokowi lantik KSAD)" - Ketua Komisi I DPR RI Meutya Hafid
- "Salah satu kandidat" - Presiden Joko Widodo (Jokowi)

[5W1H]
- What: Presiden Joko Widodo dijadwalkan melantik Kepala Staf Angkatan Darat (KSAD) baru
- Who: Presiden Joko Widodo, Meutya Hafid, Letjen Maruli Simanjuntak, Jenderal Agus Subiyanto, Jenderal Dudung Abdurachman
- When: Rabu (29/11) untuk pelantikan, Selasa (28/11) malam untuk konfirmasi Meutya, Sabtu (25/11) untuk pernyataan Jokowi
- Where: Istana Negara, Jakarta; Indonesia Arena, Jakarta
- Why: Karena posisi KSAD kosong setelah Jenderal Agus Subiyanto dilantik menjadi Panglima TNI
- How: Jokowi akan melantik KSAD baru di Istana Negara setelah mempertimbangkan sejumlah kandidat dari bursa KSAD, salah satunya Letjen Maruli Simanjuntak

[Urutan Kronologis]
- Jenderal Dudung Abdurachman pensiun dari jabatan KSAD
- Jenderal Agus Subiyanto menjabat sebagai KSAD menggantikan Dudung
- Beberapa hari setelah menjabat KSAD, Agus diusulkan Presiden Jokowi menjadi Panglima TNI
- Jenderal Agus Subiyanto dilantik menjadi Panglima TNI pada pekan lalu
- Posisi KSAD menjadi kosong
- Letjen Maruli Simanjuntak disebut sebagai salah satu kandidat kuat KSAD
- Jokowi membenarkan Maruli masuk dalam bursa KSAD pada Sabtu (25/11)
- Meutya Hafid membenarkan Jokowi akan melantik KSAD pada Rabu (29/11)

[Hubungan Bagian-Keseluruhan (Mereologi)]
- Istana Negara | bagian dari | lokasi pemerintahan di Jakarta
- Indonesia Arena | bagian dari | lokasi kegiatan Presiden di Jakarta
- Panglima Komando Cadangan Strategis Angkatan Darat (Pangkostrad) Letjen Maruli Simanjuntak | bagian dari | bursa KSAD
- Jenderal Agus Subiyanto | bagian dari | pergantian jabatan KSAD dan Panglima TNI
- Ketua Komisi I DPR RI Meutya Hafid | bagian dari | DPR RI
---""",

    "user_template": """Ekstrak informasi untuk teks berikut:
Judul: {judul}
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

    TARGET_JSON = OUTPUT_DIR / "extracted_berita.json"

    extracted_data = []
    existing_ids = set()

    if TARGET_JSON.exists():
        with open(TARGET_JSON, "r", encoding="utf-8") as f:
            extracted_data = json.load(f)
            existing_ids = {item["id"] for item in extracted_data}

    success_count = 0
    
    for item in tqdm(dataset, desc="Extraction Process", unit="data"):
        text_id  = item.get("id")
        raw_title = item.get("title", "Tidak ada judul")
        raw_text = item.get("text", "")

        if not raw_text:
            continue

        if text_id in existing_ids:
            success_count += 1
            continue

        try:
            user_prompt = PROMPT["user_template"].format(judul=raw_title, teks=raw_text)
            
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