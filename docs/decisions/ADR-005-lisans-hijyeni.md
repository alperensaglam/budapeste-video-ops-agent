# ADR-005 — Lisans hijyeni: Apache-2.0 uyumlu bağımlılık seti

**Durum:** Kabul edildi · **Tarih:** 2026-08-20

## Bağlam

Şartname Bölüm 9, birebir:

> "Yarışmaya katılan herkes, GitHub üzerinde açık kaynak olarak paylaşacakları tüm
> kaynak kodların, veri kümelerin ve diğer bileşenlerin, yarışma bitiş tarihinde
> **Apache lisansı (Apache License 2.0)** ile lisanslanarak Türkiye Açık Kaynak
> Platformu GitHub hesabında paylaşılacağını kabul eder."

Ayrıca ücretli yazılım bağımlılığı ve üçüncü taraftan hizmet satın alma yasak.

Bilgisayarlı görü dünyasındaki en yaygın tuzak **Ultralytics YOLO'dur (AGPL-3.0)**:
neredeyse her öğretici onu kullanır, ama AGPL bir Apache-2.0 repoyla uyumsuzdur.

## Karar

Şu lisanslar **yasaktır** ve `python tasks.py license-check` ile CI'da denetlenir:
AGPL, GNU Affero, SSPL, CC-BY-NC / NonCommercial, CPML, Commons Clause, Proprietary.

Seçilen temiz set:

| İhtiyaç | Seçim | Lisans | Kaçınılan |
|---|---|---|---|
| Nesne tespiti | RT-DETRv2 / D-FINE | Apache-2.0 | Ultralytics YOLO (AGPL-3.0) |
| Takip | ByteTrack / OC-SORT | MIT | — |
| Poz | RTMPose / ViTPose | Apache-2.0 | — |
| ASR | faster-whisper | MIT | — |
| VLM | Qwen3-VL ailesi | Apache-2.0 | Gemma / Llama (kısıtlı özel lisans) |
| Gömme | BGE-M3 | MIT | jina-embeddings-v3 (CC-BY-NC) |
| Yeniden sıralama | bge-reranker-v2-m3 | Apache-2.0 | — |
| Ajan çerçevesi | LangGraph | MIT | — |
| Servisleme | vLLM | Apache-2.0 | — |
| TTS (opsiyonel) | Piper (tr_TR) | MIT | XTTS-v2 (CPML, non-commercial) |

Uyarı üretilenler (kullanılabilir ama `docs/licenses.md` içinde gerekçelendirilir):
LGPL/MPL bileşenler (ör. ffmpeg bağlantılı kütüphaneler).

## Sonuçlar

- **Artı:** teslimde lisans sorunu çıkmaz; Türkiye Açık Kaynak Platformu'na devir
  sorunsuz olur; jüri/organizasyon denetiminde temiz durur.
- **Eksi:** YOLO ekosisteminin hazır ağırlıkları ve öğreticileri kullanılamaz →
  RT-DETR/D-FINE için biraz daha fazla entegrasyon emeği.
- **Denetim:** her PR'da CI `license-check` koşar; yeni bağımlılık eklerken lisans
  kontrolü zorunludur.
