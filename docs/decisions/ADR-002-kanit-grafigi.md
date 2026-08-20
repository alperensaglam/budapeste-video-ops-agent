# ADR-002 — Kanıt Grafiği: algı ile anlam arasındaki köprü

**Durum:** Kabul edildi · **Tarih:** 2026-08-20

## Bağlam

Şartname Bölüm 4 birebir şunu istiyor:

> "Sistem, düşük seviyeli algı (object detection vb.) ile yüksek seviyeli çıkarım
> (olay yorumlama) arasında bir **köprü** kurabilmelidir."

Ayrıca "Sistem çıktıları mümkün olduğunca açıklanabilir olmalıdır" diyor.

Bu senaryonun en büyük teknik riski VLM halüsinasyonudur: model olmayan bir kaza
uydurursa sistem yanlış alarm üretir ve jüri demosunda bu yakalanır.

## Karar

Algı ile VLM arasına **Kanıt Grafiği** adında açıkça isimlendirilmiş bir katman
koyuyoruz (`src/gozcu/evidence/`, sözleşmesi `contracts/evidence.py`).

İki değişmez kural:

1. **Her olgu zaman damgalı ve kaynaklıdır.** Kaynağı olmayan olgu grafiğe giremez.
   `EvidenceSource.is_deterministic` ile VLM çıkarımları deterministik gözlemlerden
   ayrılır.
2. **Grafik LLM bağlamına dökülmez.** Ajan onu `EvidenceQuery` üreten araçlarla
   sorgular. Bu hem bağlam verimliliği (uzun videoda kritik) hem doğrulanabilirlik sağlar.

`verify` düğümü VLM iddialarını yalnızca **deterministik** olgulara karşı doğrular ve
`support_score` üretir.

## Alternatifler

**A. Algı çıktısını doğrudan prompt'a gömmek.** Reddedildi: uzun videoda bağlam
patlar, iddialar doğrulanamaz, "köprü" maddesi somutlaşmaz.

**B. Sadece VLM'e güvenmek.** Reddedildi: halüsinasyon savunması kalmaz, zaman
damgaları kayar, açıklanabilirlik iddiası boş olur.

## Sonuçlar

- **Artı:** şartnamedeki "köprü" maddesi mimaride adı konmuş bir bileşenle karşılanır;
  her rapor satırı kanıta bağlanabilir; bağlam bütçesi kontrol altına alınır.
- **Eksi:** ek şema ve depolama karmaşıklığı; olgu-olay eşleme (verifier) bulanık bir
  problem ve kalibrasyon gerektirir.
- **Ölçüm:** ablation çalışmasında "verifier kapalı" koşusu ile halüsinasyon oranı
  farkı raporlanacak.
