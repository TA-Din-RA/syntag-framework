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
PATH_INPUT   = ROOT_DIR / "1-synthetic-data-generation" / "synthetic_output" / "checkpoints" / "abstrak_checkpoint.json"
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
        logging.FileHandler(Path(__file__).resolve().parent / "abstrak-generation.log", encoding="utf-8"),
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

Domain teks yang akan diekstraksi: Abstrak Karya Ilmiah

Dari setiap teks, identifikasi:
1. Entitas : subjek atau objek dalam kalimat.
2. Relasi antar entitas : berupa subjek-predikat-objek dalam teks. Relasi hanya boleh diekstrak antara entitas yang sudah terdaftar pada tahap ekstraksi entitas sebelumnya.
3. Judul penelitian : judul dari penelitian yang hendak diekstraksi informasinya.
4. Masalah penelitian : permasalahan utama yang ingin diselesaikan oleh penelitian.
5. Domain/topik penelitian : bidang ilmu tempat penelitian tersebut berada.
6. Metodologi/pendekatan : cara atau teknis yang digunakan dalam penelitian.
7. Dataset/sumber data (jika ada) : data yang digunakan dalam penelitian. Ini dapat berupa: nama dataset, corpus, benchmark, data eksperimen, jenis data yang digunakan (misalnya: tweets, medical records, sensor data)
8. Pendekatan evaluasi/validasi (jika ada) : cara menilai performa metode penelitian. Ini dapat berupa: metrik evaluasi (accuracy, F1-score, dll.), eksperimen atau pengujian, perbandingan dengan metode lain, teknik validasi (cross-validation, benchmark testing, dll.)
9. Hasil/temuan : poin-poin penting yang diperoleh dari penelitian tersebut.

Sajikan jawaban dengan format berikut:

[Entitas]
- ...
- ...

[Relasi Antar Entitas]
- Entitas A | relasi | Entitas B
- ...

[Judul Penelitian]
...

[Masalah Penelitian]
...

[Domain/Topik]
...

[Metodologi/Pendekatan]
...

[Dataset/Sumber Data] (Hanya tulis jika informasi ditemukan)
...

[Pendekatan Evaluasi/Validasi] (Hanya tulis jika informasi ditemukan)
...

[Hasil/Temuan Utama]
...

---

Sebagai panduan dalam melakukan ekstraksi, berikut 1 buah contoh teks beserta format serta hasil ekstraksi dan analisis teks yang diharapkan:

---

CONTOH JUDUL TEKS: Pengaruh Iklim Sekolah dan Pemantauan Orang Tua terhadap Perilaku Perundungan Pelajar

CONTOH ISI TEKS:
Perilaku perundungan di sekolah masih menjadi persoalan serius di Indonesia. Penelitian untuk memperoleh faktor-faktor yang dapat mengurangi perilaku perundungan pelajar perlu dilakukan sebagai dasar untuk merancang program intervensi. Penelitian ini bertujuan untuk mendapatkan gambaran perundungan yang terjadi pada pelajar sekolah dan kemudian menguji pengaruh iklim sekolah dan pemantauan orang tua terhadap perilaku perundungan. Penelitian ini menggunakan metode penelitian kuantitatif. Data yang digunakan adalah data primer dengan menyebarkan kuesioner kepada para pelajar sekolah. Analisis data dilakukan dengan menerapkan regresi logistik. Hasil penelitian memperlihatkan bahwa jenis perundungan yang menonjol dijumpai adalah perundungan verbal dan relasional. Dengan menerapkan analisis regresi logistik, hasil penelitian menunjukkan bahwa iklim sekolah yang positif menurunkan kemungkinan para pelajar untuk menjadi korban perundungan. Selain itu, iklim sekolah yang positif dan pemantauan orang tua mengurangi kemungkinan pelajar untuk menjadi pelaku perundungan. Pendidikan karakter merupakan salah satu upaya sekolah untuk mencegah terjadinya perundungan di sekolah. Dengan demikian, baik pihak sekolah maupun orang tua berperan dalam mengurangi maraknya perilaku perundungan di kalangan remaja pelajar.

CONTOH HASIL EKSTRAKSI TEKS:
[Entitas]
- Perilaku perundungan
- Indonesia
- Penelitian
- Program intervensi
- Sekolah
- Pelajar
- Iklim sekolah
- Pemantauan orang tua
- Korban perundungan
- Pelaku perundungan
- Pendidikan karakter
- Metode penelitian kuantitatif
- Data primer
- Kuesioner
- Analisis data
- Regresi logistik
- Perundungan verbal
- Perundungan relasional
- Orang tua

[Relasi Antar Entitas]
- Perilaku perundungan | menjadi persoalan di | Indonesia
- Penelitian | untuk memperoleh faktor yang mengurangi | Perilaku - perundungan
- Penelitian | menguji pengaruh | Iklim sekolah
- Penelitian | menguji pengaruh | Pemantauan orang tua
- Penelitian | menggunakan | Metode penelitian kuantitatif
- Penelitian | menggunakan | Data primer
- Penelitian | menggunakan | Kuesioner
- Kuesioner | disebar kepada | Pelajar
- Analisis data | menggunakan | Regresi logistik
- Perundungan | memiliki jenis | Perundungan verbal
- Perundungan | memiliki jenis | Perundungan relasional
- Iklim sekolah | mengurangi kemungkinan menjadi | Korban perundungan
- Iklim sekolah | mengurangi kemungkinan menjadi | Pelaku perundungan
- Pemantauan orang tua | mengurangi kemungkinan menjadi | Pelaku perundungan
- Pendidikan karakter | mencegah terjadinya | Perilaku perundungan
- Sekolah | berperan dalam mengurangi | Perilaku perundungan
- Orang tua | berperan dalam mengurangi | Perilaku perundungan

[Judul Penelitian]
Pengaruh Iklim Sekolah dan Pemantauan Orang Tua terhadap Perilaku Perundungan Pelajar

[Masalah Penelitian]
Perilaku perundungan di sekolah masih menjadi persoalan serius di Indonesia dan perlunya dasar untuk merancang program intervensi melalui identifikasi faktor-faktor yang dapat mengurangi perilaku tersebut.

[Domain/Topik]
Pendidikan / Psikologi Pendidikan

[Metodologi/Pendekatan]
Kuantitatif dengan teknik analisis data regresi logistik

[Dataset/Sumber Data]
Data primer yang diperoleh melalui penyebaran kuesioner kepada para pelajar sekolah

[Hasil/Temuan Utama]
- Jenis perundungan yang menonjol adalah perundungan verbal dan relasional.
- Iklim sekolah yang positif terbukti menurunkan kemungkinan pelajar menjadi korban perundungan.
- Kombinasi iklim sekolah yang positif dan pemantauan orang tua secara efektif mengurangi kemungkinan pelajar menjadi pelaku perundungan.
- Pendidikan karakter diidentifikasi sebagai salah satu upaya pencegahan di lingkungan sekolah.
- Kerja sama antara pihak sekolah dan orang tua sangat krusial dalam mengurangi perilaku perundungan di kalangan remaja pelajar.

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

    TARGET_JSON = OUTPUT_DIR / "extracted_abstrak.json"

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