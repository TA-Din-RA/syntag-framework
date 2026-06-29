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
# KONFIGURASI
# ─────────────────────────────────────────────
load_dotenv()

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
MODEL        = "openai/gpt-oss-120b" 
BASE_URL     = "https://api.groq.com/openai/v1/chat/completions"

# Code testing ────────────────────────────────
# TARGET_PER_TYPE = 15       
# BATCH_SIZE      = 3 
# ───────────────────────────────────────────── 

TARGET_PER_TYPE = 5      
BATCH_SIZE      = 5  
ROOT_DIR        = Path(__file__).resolve().parent
OUTPUT_DIR      = ROOT_DIR / "synthetic_output"
CHECKPOINT_DIR  = OUTPUT_DIR / "checkpoints"
MAX_RETRIES     = 8
BASE_DELAY      = 2.0      
MAX_DELAY       = 120.0     
REQUEST_DELAY   = 2.5        

# ─────────────────────────────────────────────
# TOPIC Pool
# ─────────────────────────────────────────────

TOPIK_BERITA = [
    "Kriminal", "Politik", "Ekonomi", "Pendidikan", "Kesehatan",
    "Teknologi", "Lingkungan Hidup", "Olahraga", "Sosial", "Hukum",
    "Infrastruktur", "Pertanian", "Budaya", "Bencana Alam", "Pariwisata",
    "Transportasi", "Energi", "Industri", "Perdagangan", "Keuangan",
    "Perbankan", "Investasi", "Startup", "Telekomunikasi", "Siber",
    "Keamanan Nasional", "Militer", "Diplomasi", "Hubungan Internasional",
    "Pemilu", "Kebijakan Publik", "Pemerintahan Daerah", "Urbanisasi",
    "Perumahan", "Ketahanan Pangan", "Perubahan Iklim", "Konservasi Alam",
    "Kelautan", "Perikanan", "Peternakan", "Ketahanan Energi",
    "UMKM", "Ekonomi Digital", "Ekonomi Kreatif", "Logistik",
    "Ketenagakerjaan", "Migrasi", "Demografi", "Gender", "Disabilitas",
    "Anak dan Remaja", "Literasi", "Media", "Film dan Hiburan",
    "Musik", "Seni Pertunjukan", "Kuliner", "Warisan Budaya"
]

TOPIK_ABSTRAK = [
    "Ilmu Komputer", "Kecerdasan Buatan", "Data Science", "Sistem Informasi",
    "Keamanan Siber", "Rekayasa Perangkat Lunak", "Machine Learning",
    "Pemrosesan Bahasa Alami",
    "Ekonomi", "Ekonomi Pembangunan", "Ekonomi Digital", "Ekonomi Perilaku",
    "Manajemen", "Akuntansi", "Keuangan", "Perbankan",
    "Ilmu Politik", "Kebijakan Publik", "Administrasi Publik",
    "Hubungan Internasional", "Tata Negara", "Hukum", "Kriminologi",
    "Psikologi", "Sosiologi", "Antropologi", "Ilmu Komunikasi",
    "Studi Media", "Kajian Gender",
    "Pendidikan", "Teknologi Pendidikan", "Manajemen Pendidikan",
    "Kesehatan Masyarakat", "Kedokteran", "Epidemiologi",
    "Farmasi", "Keperawatan", "Gizi",
    "Teknik Informatika", "Teknik Elektro", "Teknik Industri",
    "Teknik Sipil", "Teknik Mesin",
    "Ilmu Lingkungan", "Perubahan Iklim", "Konservasi Alam",
    "Ilmu Bahasa", "Linguistik", "Sastra", "Ilmu Perpustakaan",
    "Pariwisata", "Manajemen Pariwisata", "Hospitality"
]

TOPIK_TWEET = [
    "K-Pop", "Konser", "Playlist Spotify", "Politik", "Ekonomi", "Teknologi", "Startup", "AI",
    "Kriminal", "Hukum", "Kebijakan Publik", "Makanan Viral", "Fashion",
    "Pendidikan", "Mahasiswa", "Beasiswa", "Kampus",
    "Kesehatan", "Kesehatan Mental", "Gaya Hidup Sehat",
    "Lingkungan", "Perubahan Iklim", "Energi Terbarukan",
    "Transportasi", "Kemacetan", "Transportasi Publik",
    "Olahraga", "Sepak Bola", "Badminton", "Esports",
    "Film", "Musik", "Drama Korea", "Anime", "Game",
    "Kuliner", "Wisata", "Pariwisata",
    "Media Sosial", "Influencer", "Digital Culture",
    "Startup Lokal", "Fintech", "E-commerce",
    "Bencana Alam", "Cuaca Ekstrem",
    "Sosial", "Komunitas", "Relawan"
]

# ─────────────────────────────────────────────
# SETUP LOGGING & DIRECTORY
# ─────────────────────────────────────────────

OUTPUT_DIR.mkdir(exist_ok=True)
CHECKPOINT_DIR.mkdir(exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(OUTPUT_DIR / "generation.log", encoding="utf-8"),
        logging.StreamHandler()
    ]
)
log = logging.getLogger(__name__)

# ─────────────────────────────────────────────
# PROMPT TEMPLATES
# ─────────────────────────────────────────────

PROMPTS = {
    "berita": {
        "system": """
            Anda adalah penulis berita yang bertugas menghasilkan teks berita yang realistis dalam bahasa Indonesia.

            Generation Condition:
            1. Tulis dalam bahasa indonesia
            2. Panjang teks antara 200 - 250 kata
            3. Gunakan gaya bahasa jurnalistik yang formal dan objektif
            4. Hindari informasi yang terlalu fiktif atau tidak realistis
            5. Pastikan terdapat hubungan yang jelas antar entitas
            6. Setiap artikel harus memiliki peristiwa dan entitas berbeda
            7. Jangan gunakan markdown atau code block seperti ```json```, keluarkan teks biasa saja

            Keberagaman tulisan:
            - Variasikan kalimat pembuka.
            - Variasikan struktur penyampaian informasi.
            - Variasikan urutan penyajian fakta, kutipan, dan konteks.
            - Hindari pola paragraf yang sama antar artikel.

            Pastikan struktur tulisan berbeda dari teks sebelumnya. Setiap berita harus terasa seperti ditulis oleh orang yang berbeda.

            Berikut ini adalah contoh teks berita:
            Topik: Kriminal

            Berita:
            Kediaman mantan Menteri Lingkungan Hidup dan Kehutanan (LHK) Siti Nurbaya Bakar digeledah Kejaksaan Agung (Kejagung) beberapa waktu lalu. Direktur Penyidikan Jaksa Agung Muda Bidang Tindak Pidana Khusus Syarief Sulaeman Nahdi mengatakan penggeledahan dilakukan terkait kasus dugaan korupsi pada tata kelola perkebunan dan industri sawit. "Benar bahwa memang ada penggeledahan, beberapa waktu lalu di beberapa tempat. Mungkin salah satunya di rumah yang disebutkan tadi," ujar Syarief kepada wartawan, Jumat (30/1). "Apakah itu masalah tata kelola tambang? Itu bukan. Itu adalah penyidikan tata kelola perkebunan dan industri sawit," lanjutnya. Syarief menjelaskan penggeledahan dilakukan penyidik pada Rabu (28/1) dan Kamis (29/1). Setidaknya enam lokasi digeledah di wilayah Jakarta dan Bogor. Syarief tidak merinci soal lokasi yang digeledah tersebut. Ia hanya mengatakan penggeledahan dilakukan di sejumlah lokasi pihak swasta hingga pejabat kementerian terkait. "Ya, pejabat Kementerian. Belum bisa kita buka, tapi ada beberapa (lokasi), ada swasta, ada pemerintahan," tuturnya. Ia menambahkan aksi dugaan korupsi terkait tata kelola perkebunan dan industri sawit itu terjadi selama periode 2015 hingga 2024. Penyidik telah menyita sejumlah barang bukti berupa dokumen hingga alat elektronik dalam penggeledahan. "Ada beberapa, ada dokumen, ada barang bukti elektronik. Itu adalah memang yang kita perlukan. (Aset) belum," imbuhnya. Syarief berujar Siti Nurbaya akan dipanggil untuk diperiksa terkait kasus dugaan korupsi ini. "Nanti saya jadwalkan (pemeriksaan Siti Nurbaya)," ujarnya.  Sebelum ini, Kejagung menggeledah empat lokasi terkait dugaan korupsi yang terjadi di Kementerian Kehutanan (Kemenhut). Kabar penggeledahan itu dikonfirmasi Jaksa Agung Muda Bidang Tindak Pidana Khusus Febrie Adriansyah. Penggeledahan disebut dilakukan pada Rabu dan Kamis kemarin. Berdasarkan informasi yang dihimpun, penggeledahan terjadi di kawasan Matraman, Jakarta Timur, dan Kemang, Jakarta Selatan, pada Rabu. Kemudian, lanjut ke kawasan Rawamangun, Jakarta Timur, dan Bogor, Jawa Barat. "Terkait kasus Korupsi di Kemenhut," ujarnya saat dikonfirmasi lewat pesan singkat, Jumat (30/1).""",
                
        "user_template": """
            Buatlah {n} teks berita baru untuk topik: {topik}

            Format output JSON:

            [
                {{"id": {start_id}, "topik": "{topik}", "title": "...", "text": "..."}}
            ]

            Keluarkan HANYA array JSON di atas, tanpa teks tambahan, tanpa markdown, tanpa code block."""
    },

    "abstrak": {
        "system":  """
            Anda adalah asisten penulisan akademik yang bertugas menghasilkan abstrak penelitian yang realistis dan koheren dalam bahasa Indonesia.

            Generation Condition:
            1. Gunakan gaya bahasa akademik formal yang umum digunakan dalam publikasi ilmiah.
            2. Panjang teks antara 100–150 kata.
            3. Abstrak harus memiliki alur logis penelitian yang jelas.
            4. Setiap abstrak harus menggambarkan topik penelitian, pendekatan, dan temuan yang berbeda dari abstrak lain.
            5. Abstrak yang dihasilkan harus mencakup komponen berikut:
            - Latar belakang atau masalah penelitian
            - Pendekatan atau metode penelitian
            - Hasil utama atau kontribusi penelitian
            6. Komponen berikut bersifat opsional namun boleh disertakan:
            - penyebutan dataset atau sumber data
            - metode evaluasi atau validasi
            7. Jangan gunakan markdown atau code block seperti ```json```, keluarkan teks biasa saja

            Keberagaman tulisan:
            - Variasikan kalimat pembuka.
            - Variasikan struktur penyampaian informasi.
            - Variasikan urutan penyajian fakta, kutipan, dan konteks.
            - Hindari pola paragraf yang sama antar artikel.

            Pastikan struktur tulisan berbeda dari teks sebelumnya. Setiap abstrak harus terasa seperti ditulis oleh orang yang berbeda.

            Berikut ini adalah contoh teks abstrak:

            Kanker payudara merupakan keganasan tersering pada wanita dan menjadi penyebab utama kematian terkait kanker di seluruh dunia. Heterogenitas biologis kanker payudara memengaruhi respon terapi dan prognosis. Salah satu pendekatan penting dalam pengobatan kanker adalah induksi apoptosis, mengingat disregulasi jalur kematian sel berperan besar dalam proliferasi sel tumor yang tidak terkontrol. Melatonin, hormon endogen yang diproduksi terutama oleh kelenjar pineal, telah banyak diteliti karena sifat antioksidan dan efek antikankernya. Untuk itu, tinjauan ini bertujuan untuk merangkum hasil penelitian yang menilai efek apoptosis dari melatonin pada kanker payudara. Tinjauan sistematis ini dilakukan sesuai dengan kriteria PRISMA. Data dikumpulkan dari database PubMed dan ScienceDirect mulai Januari 2015 hingga Oktober 2025. Sebanyak 14 artikel yang ditinjau terdiri dari dua penelitian in vivo dan 13 in vitro. Jenis sel kanker yang diteliti meliputi positif reseptor ER, reseptor ER dan PR, HER2-overexpression, dan TNBC. Studi menunjukkan peningkatan apoptosis sel kanker payudara setelah pemberian melatonin, baik tunggal maupun kombinasi dengan agen lainnya secara in vitro maupun in vivo. Mekanisme apoptosis yang dimediasi melatonin melibatkan peningkatan stres oksidatif, induksi stres retikulum endoplasma, modulasi jalur inflamasi, serta inhibisi jalur survival sel seperti PI3K/Akt/mTOR. Melatonin juga memengaruhi keseimbangan protein pro-apoptotik dan anti-apoptotik, termasuk peningkatan Bax, caspase-3/9, serta penurunan Bcl-2 dan survivin. Respon apoptosis tertinggi ditemukan pada subtipe kanker payudara positif ER, menunjukkan bahwa status hormonal berperan penting dalam efektivitas melatonin. Namun, masih dibutuhkan penelitian lebih lanjut untuk membandingkan efek dan mekanisme apoptosis antara berbagai subtipe kanker payudara.
        """,
        "user_template": """
            Buatlah {n} teks abstrak baru untuk topik: {topik}

            Format output JSON:

            [
                {{"id": {start_id}, "topik": "{topik}", "title": "...", "text": "..."}}
            ]

            Keluarkan HANYA array JSON di atas, tanpa teks tambahan, tanpa markdown, tanpa code block."""
    },

    "tweet": {
        "system":  """
            Anda adalah pengguna media sosial yang menulis unggahan singkat di platform mikroblog seperti X. Tugas Anda adalah menghasilkan tweet yang realistis dalam bahasa Indonesia.

            Generation Condition:
            1. Gunakan bahasa santai seperti percakapan sehari-hari di media sosial.
            2. Panjang teks antara 20–100 kata.
            3. Tweet dapat berupa:
            - opini
            - komentar terhadap suatu peristiwa
            - reaksi terhadap berita atau kebijakan
            - pengalaman pribadi
            4. Setiap tweet harus menggambarkan peristiwa, individu, organisasi, atau lokasi yang berbeda.
            5. Tweet yang dihasilkan boleh mengandung:
            - hashtag
            - mention akun
            - opini atau sentimen pribadi
            - slang, singkatan, atau gaya informal
            Namun tetap pastikan bahwa isi tweet masih realistis dan relevan dengan suatu peristiwa
            6. Jangan gunakan markdown atau code block seperti ```json```, keluarkan teks biasa saja

            Keberagaman tulisan:
            - Variasikan kalimat pembuka.
            - Variasikan struktur penyampaian informasi.
            - Variasikan urutan penyajian fakta, kutipan, dan konteks.
            - Hindari pola paragraf yang sama antar artikel.

            Pastikan struktur tulisan berbeda dari teks sebelumnya. Setiap tweet harus terasa seperti ditulis oleh orang yang berbeda.

            Berikut ini adalah contoh tweet:

            I GOT RACIAL BULLYING FOR THE VERY FIRST TIME HERE IN THE US.
            Aku ga nyangka dapet tindakan rasisme dari SESAMA ORANG INDONESIA, ORANG BALI. Disclaimer: Aku gak menjelekkan orang Bali disini, aku cuma cerita tindakan kurang mengenakkan yang aku dapatkan dari seseorang, hari ini.
            """,
        "user_template": """
            Buatlah {n} tweet baru untuk topik: {topik}

            Format output JSON:

            [
                {{"id": {start_id}, "topik": "{topik}", "text": "..."}}
            ]

            Keluarkan HANYA array JSON di atas, tanpa teks tambahan, tanpa markdown, tanpa code block."""
    }
}

# ─────────────────────────────────────────────
# Main Function
# ─────────────────────────────────────────────

def load_checkpoint(data_type: str) -> list:
    """Load last saved successful batch"""
    ckpt_file = CHECKPOINT_DIR / f"{data_type}_checkpoint.json"
    if ckpt_file.exists():
        with open(ckpt_file, "r", encoding="utf-8") as f:
            data = json.load(f)
        log.info(f"[{data_type}] Melanjutkan dari checkpoint: {len(data)} data sudah ada.")
        return data
    return []


def save_checkpoint(data_type: str, data: list):
    """Save every checkpoint after every batch"""
    ckpt_file = CHECKPOINT_DIR / f"{data_type}_checkpoint.json"
    with open(ckpt_file, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def call_llm_api(system_prompt: str, user_prompt: str) -> str:
    """
    Call Groq API with exponential backoff for rate limit

    Return: response model
    """
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
        "temperature": 0.9,
        "top_p": 0.8,
        "max_tokens":  3000,
    }

    delay = BASE_DELAY
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            resp = requests.post(BASE_URL, headers=headers, json=payload, timeout=60)

            # ── Rate limit (429) ──────────────────────────
            if resp.status_code == 429:
                retry_after = float(resp.headers.get("Retry-After", delay))
                wait = min(retry_after + random.uniform(0.5, 2.0), MAX_DELAY)
                log.warning(f"  Rate limit 429. Waits for {wait:.1f}s... (attempt {attempt}/{MAX_RETRIES})")
                time.sleep(wait)
                delay = min(delay * 2, MAX_DELAY)
                continue

            # ── Server error (5xx) ────────────────────────
            if resp.status_code >= 500:
                wait = min(delay + random.uniform(0, 1), MAX_DELAY)
                log.warning(f"  Server error {resp.status_code}. Retry in {wait:.1f}s...")
                time.sleep(wait)
                delay = min(delay * 2, MAX_DELAY)
                continue

            resp.raise_for_status()
            return resp.json()["choices"][0]["message"]["content"]

        except requests.exceptions.Timeout:
            wait = min(delay + random.uniform(0, 2), MAX_DELAY)
            log.warning(f"  Timeout. Retry dalam {wait:.1f}s... (attempt {attempt}/{MAX_RETRIES})")
            time.sleep(wait)
            delay = min(delay * 2, MAX_DELAY)

        except requests.exceptions.RequestException as e:
            wait = min(delay + random.uniform(0, 1), MAX_DELAY)
            log.error(f"  Request error: {e}. Retry dalam {wait:.1f}s...")
            time.sleep(wait)
            delay = min(delay * 2, MAX_DELAY)

    raise RuntimeError(f"Fail after {MAX_RETRIES} try.")


def parse_json_response(raw: str) -> list:
    """
    Parse JSON from model's response.
    Handle cases where model generate additional text beside JSON format
    """
    start = raw.find("[")
    end   = raw.rfind("]")
    if start == -1 or end == -1:
        raise ValueError("Tidak ditemukan JSON array dalam respons.")
    json_str = raw[start:end+1]
    return json.loads(json_str)


def build_user_prompt(data_type: str, batch_n: int, start_id: int, batch_index: int) -> str:
    """
    Generate user prompt with topic sampling from topic pool
    """
    template = PROMPTS[data_type]["user_template"]

    if data_type == "berita":
        topik = TOPIK_BERITA[batch_index % len(TOPIK_BERITA)]
        return template.format(
            n=batch_n,
            topik=topik,
            start_id=start_id
        )
    elif data_type == "abstrak":
        topik = TOPIK_ABSTRAK[batch_index % len(TOPIK_ABSTRAK)]
        return template.format(
            n=batch_n,
            topik=topik,
            start_id=start_id
        )
    else:
        topik = TOPIK_TWEET[batch_index % len(TOPIK_TWEET)]
        return template.format(
            n=batch_n,
            topik=topik,
            start_id=start_id
        )


def generate_data(data_type: str, target: int = TARGET_PER_TYPE) -> list:
    """
    Generate synthetic data for one type of text.
    Support resume from saved checkpoint.
    """
    prompt_cfg = PROMPTS[data_type]
    results    = load_checkpoint(data_type)
    start_id   = len(results) + 1
    batch_index = len(results) // BATCH_SIZE

    failed_batches = 0

    log.info(f"\n{'='*60}")
    log.info(f"[{data_type.upper()}] Mulai generate. Target: {target}, Sudah ada: {len(results)}")
    log.info(f"{'='*60}")

    with tqdm(total=target, initial=len(results),
              desc=f"[{data_type}]", unit="data", ncols=80) as pbar:

        while len(results) < target:
            remaining = target - len(results)
            batch_n   = min(BATCH_SIZE, remaining)

            user_prompt = build_user_prompt(data_type, batch_n, start_id, batch_index)

            try:
                raw   = call_llm_api(prompt_cfg["system"], user_prompt)
                batch = parse_json_response(raw)

                for i, item in enumerate(batch):
                    item["id"] = start_id + i

                results.extend(batch)
                save_checkpoint(data_type, results)

                start_id    += len(batch)
                batch_index += 1
                pbar.update(len(batch))

                if data_type == "berita":
                    topik_digunakan = TOPIK_BERITA[(batch_index - 1) % len(TOPIK_BERITA)]
                    log.info(f"  Batch OK [{topik_digunakan}]: +{len(batch)} data | Total: {len(results)}/{target}")
                elif data_type == "abstrak":
                    topik_digunakan = TOPIK_ABSTRAK[(batch_index - 1) % len(TOPIK_ABSTRAK)]
                    log.info(f"  Batch OK [{topik_digunakan}]: +{len(batch)} data | Total: {len(results)}/{target}")
                elif data_type == "tweet":
                    topik_digunakan = TOPIK_TWEET[(batch_index - 1) % len(TOPIK_TWEET)]
                    log.info(f"  Batch OK [{topik_digunakan}]: +{len(batch)} data | Total: {len(results)}/{target}")
                else:
                    log.info(f"  Batch OK: +{len(batch)} data | Total: {len(results)}/{target}")

            except (ValueError, json.JSONDecodeError) as e:
                failed_batches += 1
                log.error(f"  Parse error (batch dilewati): {e}")
                start_id    += batch_n
                batch_index += 1

            except RuntimeError as e:
                log.error(f"  API gagal total: {e}")
                log.info(f"  Checkpoint tersimpan: {len(results)} data. Jalankan ulang untuk melanjutkan.")
                break

            if len(results) < target:
                time.sleep(REQUEST_DELAY)

    log.info(f"[{data_type}] Selesai: {len(results)} data. Batch gagal: {failed_batches}")
    return results


def save_final(data_type: str, data: list):
    """Save final dataset into separate JSON file with timestamp."""
    ts       = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_file = OUTPUT_DIR / f"{data_type}_{ts}.json"
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    log.info(f"  Tersimpan: {out_file}  ({len(data)} entri)")
    return out_file


# ─────────────────────────────────────────────
# ENTRY POINT
# ─────────────────────────────────────────────

def main():
    log.info("=" * 60)
    log.info("SYNTHETIC DATA GENERATOR - Groq API")
    log.info(f"Model  : {MODEL}")
    log.info(f"Target : {TARGET_PER_TYPE} data per jenis")
    log.info(f"Output : {OUTPUT_DIR.resolve()}")
    log.info("=" * 60)

    data_types = ["berita", "abstrak", "tweet"]
    summary    = {}

    for dtype in data_types:
        data = generate_data(dtype, TARGET_PER_TYPE)
        if data:
            out = save_final(dtype, data)
            summary[dtype] = {"jumlah": len(data), "file": str(out)}
        else:
            summary[dtype] = {"jumlah": 0, "file": None}

    # ── SUMMARY ─────────────────────────────────────
    log.info("\n" + "=" * 60)
    log.info("SUMMARY")
    log.info("=" * 60)
    for dtype, info in summary.items():
        status = "✓" if info["jumlah"] >= TARGET_PER_TYPE else f"⚠ ({info['jumlah']}/{TARGET_PER_TYPE})"
        log.info(f"  {dtype.upper():10s}  {status}  →  {info['file']}")
    log.info("=" * 60)


if __name__ == "__main__":
    main()