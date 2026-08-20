# ADR-001 — Ajan merkezli mimari (pipeline değil)

**Durum:** Kabul edildi · **Tarih:** 2026-08-20 · **Karar verenler:** Alperen, Hasan, Emre, İbrahim

## Bağlam

Şartname Bölüm 3 bir video analiz sistemi tarif ediyor. Ancak Bölüm 7'deki
değerlendirme kriterleri neredeyse tamamen **agentic** terimlerle yazılmış:

- "Mock fonksiyonların **ajanın araçları** olarak başarıyla kullanılması"
- "agent, tools, memory, prompt engineering etkin kullanımı"
- "dinamik araç seçimi, bağlam yönetimi, çok adımlı karar zincirleri, hata işleme"
- "Ajanın müşteri niyetini anlama ve **akıl yürütme** yeteneği"
- "Diyalog sırasında **inisiyatif alma ve doğru soruları sorma**"
- "Diyalogun **doğal ve insansı** bir akışta ilerlemesi"

Bölüm 6 (teslim edilecekler) de "agent, mock fonksiyonlar" diyor; demo videosunda
"bağlam değişimi denemesi" ile "sesli veya metin tabanlı etkileşim" istiyor.

Yani puanın yaklaşık %70'i (Teknik %35 + Otonomi %20 + Fonksiyonellik'in araç kısmı)
ajan davranışında yaşıyor.

## Karar

Sistemi **operatörle Türkçe konuşan bir ajan** olarak inşa ediyoruz. Video, ajanın
kanıt kaynağıdır; analiz boru hattı ajanın **araçlarından biridir**, ürünün kendisi
değildir.

Somut sonuçları:

1. Birincil arayüz **diyalogdur** (sohbet + sesli), tek atımlık dosya yükleme değil.
2. Her algı yeteneği bir `Tool` olarak paketlenir; ajan bunları *seçer*.
3. Kurumsal sistemler (sağlık ekibi, güvenlik, olay kaydı) mock araçlardır.
4. Her demo bir diyalogla başlar, JSON dökümüyle değil.
5. Mimari diyagramda merkez ajandır.

## Alternatifler

**A. Klasik pipeline + sonda JSON.** Basit ve hızlı. Reddedildi: rubriğin ajan
maddeleri karşılıksız kalır, "Otonomi ve Zekâ" (%20) neredeyse tamamen kaybedilir.

**B. Pipeline + üzerine ince sohbet katmanı.** Orta yol. Reddedildi: araç seçimi
gerçek olmaz; "dinamik araç seçimi" ve "çok adımlı karar zincirleri" savunulamaz,
jüri sorularında yapaylık ortaya çıkar.

## Sonuçlar

- **Artı:** rubriğin ağır maddeleri doğrudan karşılanır; ürün gerçek bir karar
  destek sistemi gibi davranır.
- **Eksi:** ajan katmanı ek karmaşıklık ve gecikme getirir → prefix caching, küçük
  planner modeli ve araç sonucu önbelleği ile telafi edilir.
- **Risk:** ajan turları belirsizlik yaratır → `verify` düğümü ve
  `integrity_issues()` ile sınırlanır.
