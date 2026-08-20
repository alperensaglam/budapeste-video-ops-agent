# ADR-004 — Kaset (record/replay) ile GPU'suz paralel geliştirme

**Durum:** Kabul edildi · **Tarih:** 2026-08-20

## Bağlam

Ekipte dört geliştirici var ama **hiçbirinde GPU yok**. Yarışma donanımı (H200)
belirsiz bir tarihte gelebilir. Elimizdeki tek gerçek GPU kaynağı Kaggle'ın ücretsiz
katmanı (hesap başına haftada yaklaşık 30 saat T4).

Naif yaklaşımda dört kişi tek GPU kuyruğuna girer ve üçü bekler.

**Not:** Colab Pro gibi ücretli katmanlar satın **alınamaz** — şartname Bölüm 9:
"Yarışmacılar proje geliştirme süresince projenin bağımlı olduğu ücretli herhangi bir
yazılım kullanamaz" ve "üçüncü taraflardan hizmet ya da ürün satın alamaz ve kullanamaz."

## Karar

**Sözleşme-önce + kayıt/oynatma.**

1. Faz 0'da tüm Pydantic şemaları dondurulur (`contracts/`).
2. `VLMClient` bir **protokoldür**, somut sınıf değil.
3. Emre `colab-t4` profilinde `RecordingVLM` ile gerçek Qwen3-VL çıktılarını
   `data/cassettes/*.jsonl` içine kaydeder ve repo'ya push'lar.
4. Diğer üçü `cpu-dev` profilinde `CassetteVLM` ile aynı kasetten oynatır.
5. CI de `cpu-dev` profilinde koşar → GPU gerektirmeyen, deterministik, saniyelik testler.

Kaset anahtarı isteğin **içerik hash'idir** (`VLMRequest.cache_key()`). Dosya yolu gibi
ortama bağlı alanlar hash'e girmez, böylece kaset her makinede tutar. Prompt sürümü
(`prompt_id`) hash'e girer: prompt v1 → v2 değişince eski kaset kullanılmaz.

`RecordingVLM` mevcut kaydı bulursa modeli hiç çağırmaz → Kaggle kotası boşa gitmez.

## Alternatifler

**A. Herkes kendi Kaggle hesabında koşsun.** Reddedildi: yavaş (her değişiklikte
notebook başlatma), deterministik değil, CI'da işe yaramaz.

**B. Mock yanıtları elle yazmak.** Reddedildi: gerçek model davranışını yansıtmaz;
"CPU'da çalışıyor ama GPU'da bozuluyor" sınıfı hatalar geç yakalanır.

## Sonuçlar

- **Artı:** dört kişi paralel çalışır; testler hızlı ve deterministik; CI ücretsiz;
  gerçek koşularda kaset cache görevi görüp RTF'i düşürür ve demoyu hızlandırır.
- **Eksi:** kaset dosyaları repo'da yer kaplar → `compact()` ve haftalık bakım gerekir.
- **Risk:** kaset ıskalaması sessizce boş yanıt dönerse yalancı yeşil testler doğar →
  `CassetteMissError` **bilerek gürültülüdür** ve çözümü mesajında söyler.
