# GÖZCÜ

**Görüntü Tabanlı Operasyonel Zekâ ve Karar Ünitesi**

Video kayıtlarından olay çıkaran, Türkçe konuşan ve operatöre uygulanabilir aksiyon
öneren, **tamamen yerel çalışan** bir yapay zekâ ajanı.

> TEKNOFEST 2026 · Yapay Zekâ Dil Ajanları Yarışması · **3. Senaryo**
> Etiketler: `BilisimVadisi2026` · `Türkiye Açık Kaynak Platformu`

[![CI](https://github.com/alperensaglam/budapeste-video-ops-agent/actions/workflows/ci.yml/badge.svg)](https://github.com/alperensaglam/budapeste-video-ops-agent/actions/workflows/ci.yml)
[![License](https://img.shields.io/badge/license-Apache--2.0-blue.svg)](LICENSE)

---

## Ne yapar?

GÖZCÜ bir "video → JSON" boru hattı **değildir**. Operatörle Türkçe konuşan, araç
kullanan, çok adımlı akıl yürüten bir **ajandır**; video onun kanıt kaynağıdır.

```
Operatör:  Depo kamerasının son kaydına bak, bir sorun var mı?

GÖZCÜ:     Kaydı işledim (48 sn, RTF 0.18). İki kritik olay buldum:
           • 00:15 — Forklift devrildi        (kritik, güven 0.88)
           • 00:20 — Yerde hareketsiz kişi    (kritik, güven 0.82)

           Risk: Yüksek. Devrilme sonrası kişi 15 saniyedir hareketsiz.

           Bir belirsizlik var: kişinin bilinç durumunu görüntüden
           doğrulayamıyorum. 2 numaralı kameranın kaydı da var mı?

           Önerim (ISG-PR-014 §4.2 uyarınca):
           1. [P0] Sağlık ekibini çağır  — onayınızı bekliyorum
           2. [P1] Alanı güvenlik altına al

Operatör:  Birinciyi onayla.

GÖZCÜ:     dispatch_medical_team çağrıldı... servis 503 döndü.
           Yedek kanala geçtim: notify_supervisor başarılı (312 ms).
           Vardiya amiri bilgilendirildi, sağlık birimi tekrar deneniyor.
```

Her iddia **kanıta bağlıdır**; kanıtsız olay rapora giremez, desteklenmeyen olay için
aksiyon üretilmez. Olaysız bir videoda sistem kaza uydurmaz — *"kritik olay tespit
edilmedi"* der.

---

## Hızlı başlangıç

**Gereksinim:** Python 3.11+ · **GPU gerekmez.**

```bash
git clone https://github.com/alperensaglam/budapeste-video-ops-agent.git
cd budapeste-video-ops-agent

python tasks.py setup      # .venv + bağımlılıklar
python tasks.py check      # lint + test + sözleşme + lisans denetimi
python tasks.py demo       # uçtan uca demo
```

Linux/macOS/Colab'da `make setup`, `make check`, `make demo` de çalışır (aynı
komutlara delege eder). Windows'ta `make` olmadığı için kanonik koşucu `tasks.py`'dir.

### Profil seçimi

```bash
GOZCU_PROFILE=cpu-dev    python tasks.py test    # varsayılan — GPU yok, kasetten oynatma
GOZCU_PROFILE=colab-t4   python tasks.py demo    # Kaggle/Colab ücretsiz T4
GOZCU_PROFILE=h200-prod  python tasks.py bench   # yarışma donanımı
```

```bash
python tasks.py profiles   # mevcut profilleri listeler
python tasks.py --list     # tüm görevler
```

---

## Çıktı formatı

Şartname Bölüm 5'teki dört anahtar **birebir** korunur; zenginleştirme üzerine eklenir.

```jsonc
{
  // ── ŞARTNAME SÖZLEŞMESİ ──────────────────────────────
  "summary": "Videoda forklift kazası ve yaralanma riski gözlenmiştir.",
  "events":  [{"time": "00:15", "event": "Forklift devrildi"}],
  "risk":    "Yüksek",
  "actions": ["Sağlık ekibini çağır", "Alanı güvenlik altına al"],

  // ── GÖZCÜ ZENGİNLEŞTİRMESİ ───────────────────────────
  "events_detail":   [ /* kanıt, güven, faz, aktörler, support_score */ ],
  "risk_assessment": { /* faktörler, gerekçe, belirsizlik */ },
  "actions_detail":  [ /* öncelik, sorumlu, SOP atfı, araç, durum */ ],
  "abstentions":     [ /* bilerek karar verilmeyen noktalar */ ],
  "open_questions":  [ /* ajanın operatöre soracakları */ ],
  "metrics":         { /* rtf, gecikme, token, VRAM */ }
}
```

`events` ve `actions` **türetilmiş** alanlardır — tek doğruluk kaynağı `*_detail`
listeleridir, böylece asla birbirinden ayrışamazlar. Sözleşme
[`tests/contracts/test_sartname_contract.py`](tests/contracts/test_sartname_contract.py)
ile kilitlidir.

---

## Mimari (özet)

```
L0  Alım & uyarlanabilir örnekleme  ─ hareket/ses enerjisine göre kare bütçesi
L1  Deterministik algı              ─ tespit·takip·poz·bölge·ASR·ses olayı
L2  ★ KANIT GRAFİĞİ                 ─ "algı ↔ anlam köprüsü" (şartname maddesi)
L3  Anlamsal kavrayış (VLM @ vLLM)  ─ segment→sahne→video, kaba→ince temellendirme
L4  ★ AJAN ÇEKİRDEĞİ (LangGraph)    ─ plan·route·execute·verify·reflect·report
L5  Karar & aksiyon                 ─ model tabanlı risk + SOP + mock araçlar + HITL
L6  Yüzeyler                        ─ JSON · REST/SSE · Operatör Konsolu · CLI
L7  Değerlendirme                   ─ KPI · ablation · kaos testi · yük testi
```

Ayrıntı ve diyagramlar: **[docs/architecture.md](docs/architecture.md)**
Karar gerekçeleri: **[docs/decisions/](docs/decisions/)**

---

## Teknoloji ve lisanslar

Tümü açık kaynak, tümü Apache-2.0 uyumlu. **AGPL ve non-commercial bağımlılık yoktur**
(`python tasks.py license-check` her PR'da CI'da koşar).

| Katman | Seçim | Lisans |
|---|---|---|
| Model servisleme | **vLLM** | Apache-2.0 |
| Görsel-dil modeli | **Qwen3-VL** (2B/8B/32B) | Apache-2.0 |
| Ajan çerçevesi | **LangGraph** | MIT |
| Nesne tespiti | RT-DETRv2 / D-FINE | Apache-2.0 |
| Takip | ByteTrack | MIT |
| Poz kestirimi | RTMPose | Apache-2.0 |
| Türkçe ASR | faster-whisper | MIT |
| Gömme / yeniden sıralama | BGE-M3 / bge-reranker-v2-m3 | MIT / Apache-2.0 |
| Backend | FastAPI | MIT |

> Ultralytics YOLO **kullanılmamıştır** (AGPL-3.0, Apache-2.0 repoyla uyumsuz).
> Gerekçe: [ADR-005](docs/decisions/ADR-005-lisans-hijyeni.md)

---

## Yerel çalışma garantisi

Şartname: *"Harici API, kapalı servis veya bulut bağımlılığı kabul edilmez. Tüm model
ve bileşenler lokal olarak çalıştırılmalıdır."*

- Tüm modeller yerelde çalışır; ağ çağrısı yalnızca `localhost` vLLM endpoint'inedir.
- `openai` istemci kütüphanesi **yalnızca** vLLM'in OpenAI-uyumlu yerel arayüzü için
  kullanılır; OpenAI servisine hiçbir istek gitmez.
- `make offline-demo` ağ bağlantısı olmadan çalışır ve final provasında zorunludur.
- Kullanılan hiçbir ücretli yazılım veya satın alınmış üçüncü taraf hizmeti yoktur.

---

## Veri seti

Değerlendirme seti ve anotasyonlar: **[eval/datasets/](eval/datasets/)**
İndirme betikleri, herkese açık kaynaklar ve anotasyon formatı orada belgelenmiştir.

---

## Geliştirme

```bash
python tasks.py fmt            # otomatik biçimlendirme
python tasks.py lint           # ruff + mypy
python tasks.py test           # testler (GPU gerekmez)
python tasks.py cov            # kapsam raporu (hedef %70)
python tasks.py schema-check   # sözleşme kararlılığı
python tasks.py license-check  # AGPL / non-commercial avı
python tasks.py check          # PR öncesi hepsi birden
```

**Sözleşmeler dondurulmuştur.** `src/gozcu/contracts/` altında kırıcı bir değişiklik
yapmadan önce: ADR yaz → `schema_version` artır → dört katman sahibinin onayını al.
Ayrıntı: [docs/architecture.md §8](docs/architecture.md).

---

## Takım ve sorumluluklar

| Üye | Sahip olduğu katman | Paketler |
|---|---|---|
| **Alperen** | L4 — Ajan çekirdeği | `agent/` |
| **Hasan** | L0–L2 — Algı & Kanıt Grafiği | `ingest/`, `perception/`, `evidence/` |
| **Emre** | L3 + servisleme + performans | `understanding/`, `serving/` |
| **İbrahim** | L5–L6 — Karar, aksiyon & ürün | `decision/`, `mocks/`, `api/`, `ui/` |

Dönüşümlü roller (her fazda el değiştirir): Sürüm Kaptanı · Eval Kaptanı · Uyum Kaptanı.
Haftalık ilerleme kayıtları: [docs/weekly/](docs/weekly/)

---

## Lisans

[Apache License 2.0](LICENSE) — yarışma bitiş tarihinde Türkiye Açık Kaynak Platformu
GitHub hesabında paylaşılacaktır.


## Yapılanlar 

Faz 0 Tamamlandı.