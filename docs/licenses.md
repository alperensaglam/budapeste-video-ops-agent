# Lisans Envanteri

**Bu repo Apache License 2.0 ile yayınlanır** (şartname Bölüm 9 zorunluluğu:
yarışma bitiminde Türkiye Açık Kaynak Platformu GitHub hesabında paylaşılacaktır).

Denetim otomatiktir: `python tasks.py license-check` her PR'da CI'da koşar.
Politika ve gerekçeler: [ADR-005](decisions/ADR-005-lisans-hijyeni.md)

## Yasaklı lisanslar

Apache-2.0 bir repo bunları taşıyamaz; CI ihlalde kırmızı verir:

`AGPL` · `GNU Affero` · `SSPL` · `CC-BY-NC` / `NonCommercial` · `CPML` ·
`Commons Clause` · `Proprietary`

## Bilinçli kaçınılanlar

| Kaçınılan | Lisansı | Neden | Yerine |
|---|---|---|---|
| Ultralytics YOLO (v8/v11) | AGPL-3.0 | Apache-2.0 ile uyumsuz; en yaygın tuzak | **RT-DETRv2 / D-FINE** (Apache-2.0) |
| Coqui TTS / XTTS-v2 | CPML | Non-commercial kısıtı | **Piper TTS** `tr_TR` (MIT) |
| jina-embeddings-v3 | CC-BY-NC-4.0 | Non-commercial kısıtı | **BGE-M3** (MIT) |
| Gemma / Llama | Özel kısıtlı lisans | OSI onaylı değil, kullanım kısıtları var | **Qwen3 / Qwen3-VL** (Apache-2.0) |
| Colab Pro ve paralı bulut | Ücretli hizmet | Şartname Bölüm 9: ücretli yazılım/hizmet yasağı | **Kaggle ücretsiz katman** |

## Kabul edilen bağımlılıklar

| Bileşen | Lisans | Rol |
|---|---|---|
| vLLM | Apache-2.0 | Yerel model servisleme (şartname birebir istiyor) |
| Qwen3-VL (2B / 8B / 32B) | Apache-2.0 | Görsel-dil modeli |
| Qwen3 (4B / 8B) | Apache-2.0 | Planner / yargıç modeli |
| LangGraph | MIT | Ajan durum makinesi |
| Pydantic | MIT | Veri sözleşmeleri |
| FastAPI · Uvicorn | MIT · BSD-3 | Backend |
| RT-DETRv2 / D-FINE | Apache-2.0 | Nesne tespiti |
| ByteTrack / OC-SORT | MIT | Çoklu nesne takibi |
| RTMPose (MMPose) | Apache-2.0 | Poz kestirimi, düşme tespiti |
| faster-whisper | MIT | Türkçe ASR |
| BEATs / AST | MIT | Ses olayı etiketleme |
| BGE-M3 | MIT | Çok dilli gömme |
| bge-reranker-v2-m3 | Apache-2.0 | Yeniden sıralama |
| Chroma | Apache-2.0 | Yerel vektör deposu |
| ONNX Runtime | MIT | CPU/GPU çıkarım |
| PySceneDetect | BSD-3 | Sahne kesiti |
| PyAV · ffmpeg | BSD-3 · LGPL-2.1 | Video decode |
| Piper TTS (opsiyonel) | MIT | Türkçe seslendirme |

## Uyarı üreten ama kabul edilenler

| Bileşen | Lisans | Gerekçe |
|---|---|---|
| pathspec (geçişli bağımlılık) | MPL-2.0 | Dosya bazlı copyleft; kaynak kodumuzu etkilemez, yalnızca kendi dosyalarını kapsar. |
| ffmpeg (sistem kütüphanesi) | LGPL-2.1 | Dinamik bağlanır, değiştirilmez; LGPL dinamik bağlama için izin verir. Statik derleme yapılmaz. |

## Veri seti lisansları

Kendi çektiğimiz klipler Apache-2.0 / CC-BY ile yayınlanır. Kamuya açık araştırma
setlerinin **videoları yeniden dağıtılmaz**; yalnızca kendi anotasyonlarımız
yayınlanır. Ayrıntı: [`eval/datasets/README.md`](../eval/datasets/README.md)
