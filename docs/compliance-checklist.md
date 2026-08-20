# Şartname Uyum Kontrol Listesi

**Uyum Kaptanı her faz sonunda bu listeyi işaretler.**
Dönüşüm: Faz 0-1 İbrahim · Faz 2 Alperen · Faz 3 Hasan · Faz 4-5 Emre

---

## A. Teknik gereksinimler (Bölüm 3 ve 4)

- [ ] Video girdisi alır ve içeriği analiz eder
- [ ] Olay / kişi / riskli durum tespiti yapar
- [ ] Kritik anları **zaman bilgisi** ile belirler
- [ ] Kısa, anlaşılır **Türkçe** özet üretir
- [ ] Operatöre **aksiyon önerileri** sunar
- [ ] **JSON** yapılandırılmış çıktı (şartname anahtarları birebir) — `test_sartname_contract.py`
- [ ] **Offline + yerel** çalışır; dış API / kapalı servis / bulut bağımlılığı yok
- [ ] **vLLM** veya benzeri yerel servisleme altyapısı kullanır
- [ ] Olayın **başlangıç / gelişim / sonuç** aşamalarını ayırt eder (`EventPhase`)
- [ ] Düşük seviye algı ↔ yüksek seviye çıkarım **köprüsü** (Kanıt Grafiği)
- [ ] Model tabanlı, **statik olmayan** pipeline (`triage` düğümü stratejiyi seçer)
- [ ] Çıktılar **açıklanabilir** (`evidence[]`, `support_score`, `rationale`)
- [ ] Düşük gecikme, kaynak optimizasyonu, gerçeğe yakın senaryoda çalışabilir
- [ ] Açık kaynak, **tekrar üretilebilir**, kurulum/çalıştırma dokümante
- [ ] **Kendi KPI metriklerimiz** tanımlı ve raporlanmış

## B. Teslim kalemleri (Bölüm 6)

- [ ] Çalışan kod: **agent** + **mock fonksiyonlar** + arayüz kodu + **benchmark kodu**
- [ ] Kurulum adımları (gereksinimler, çevre değişkenleri) net
- [ ] **Maksimum 10 dakikalık demo videosu**
  - [ ] Seçilen senaryolar gösteriliyor
  - [ ] **Bağlam değişimi denemesi** gösteriliyor
  - [ ] Metin (ve varsa sesli) etkileşim net gösteriliyor
- [ ] Proje dokümantasyonu:
  - [ ] Sistem mimarisi özeti **ve diyagramı**
  - [ ] Kullanılan **agentic framework ve LLM'ler**
  - [ ] İmplemente edilen **senaryolar ve mock fonksiyonlar**
  - [ ] Adım adım çalıştırma talimatları
  - [ ] **Karşılaşılan zorluklar ve çözümler** (`docs/challenges.md`)
  - [ ] Eklenen ek özellikler / senaryolar
  - [ ] **Ölçümleme sonuçları** (`docs/evaluation.md`)
  - [ ] **Ölçekleme noktasında gerekli ihtiyaçlar** (`docs/scaling.md`)
- [ ] Sunum materyali: **PDF ve PPTX**
- [ ] Sunumda **tüm takım üyelerinin görev tanımları** var (Bölüm 9)

## C. Final sunumu (Bölüm 11)

- [ ] **4 dakika** sunum hazır ve provalı (4 kişi × 1 dakika)
- [ ] **1 dakikalık** demo videosu (10 dakikalıktan ayrı!)
- [ ] Sunum GitHub hesabına da yüklendi
- [ ] Bilişim Vadisi Kocaeli fizikî katılım planlandı (son 24 saat)
- [ ] **Offline demo paketi** internetsiz bir dizüstünde denendi

## D. Süreç ve uyum (Bölüm 9 ve 10)

- [ ] GitHub deposu açık ve **Apache-2.0** lisanslı
- [ ] Repo etiketleri: **`BilisimVadisi2026`** + **takım adı** + Türkiye Açık Kaynak Platformu
- [ ] **En az haftalık** güncelleme yükleniyor (`docs/weekly/`)
- [ ] Repo içinde:
  - [ ] (1) Çalıştırma için gerekli **tüm bağımlılıkların eksiksiz listesi**
  - [ ] (2) İzlenecek **tüm adımlar**
  - [ ] (3) Kullanılan veri setinin **herkese açık indirme bağlantısı**
- [ ] Ücretli yazılım bağımlılığı **yok** (Colab Pro vb. satın alınmadı)
- [ ] Üçüncü taraflardan hizmet/ürün satın alınmadı
- [ ] AGPL / non-commercial bağımlılık **yok** (`license-check` CI'da yeşil)
- [ ] Proje yalnızca yarışma dönemi içinde geliştirildi (önceki proje üzerine değil)
- [ ] İntihal yok; alıntılar kaynak gösterildi (Turnitin denetimi yapılacak)
- [ ] TEKNOFEST duyuru grubuna **en az 1 takım üyesi** kayıtlı
- [ ] KYS (t3kys.com) üzerinden takım kaydı tamamlandı, davetler kabul edildi

---

## Kapı özeti

| Kapı | Ne zaman yeşil sayılır |
|---|---|
| **KAPI 0** | Her geliştirici `python tasks.py check` ile CPU'da yeşil alıyor; sözleşmeler kilitli |
| **KAPI 1** | `make demo` → video yükle, ajanla Türkçe konuş, şartname JSON'u üret |
| **KAPI 2** | A bölümündeki tüm teknik maddeler işaretli; eval setinde ilk tam rapor |
| **KAPI 3** | Kaos testinde hata kurtarma ≥ %85; ablation tablosu hazır |
| **KAPI 4** | B bölümündeki tüm teslim kalemleri repo'da |
| **KAPI 5** | `make offline-demo` internetsiz çalışıyor; 4 dk sunum provalı |
