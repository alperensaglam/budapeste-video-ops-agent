# Değerlendirme Veri Seti

**Şartname Bölüm 10 zorunlu maddesi:** repo, "kullanılan veri setinin
indirilebileceği **herkese açık bir bağlantısını**" içermelidir.

## Yaklaşım

Veri setimiz iki kaynaktan oluşur:

### 1. Kendi çektiğimiz sahneli klipler (ana kaynak)

Telif tamamen bizde olduğu için **Apache-2.0 / CC-BY ile yeniden yayınlanabilir** ve
herkese açık indirme bağlantısı verilebilir. Ayrıca senaryoyu tam kontrol ederiz:
gündüz/gece, tıkanma, kamera sarsıntısı, olaysız kontrol grubu.

> Etik: tüm kliplerde görünen kişiler takım üyeleridir ve kayda açık rıza
> vermiştir. Üçüncü şahıs veya gerçek iş kazası görüntüsü kullanılmaz.

### 2. Kamuya açık araştırma setleri (destekleyici)

Bu setlerin **videolarını yeniden dağıtmayız** — yalnızca kendi **anotasyonlarımızı**
(zaman damgalı olay sınırları, risk seviyesi, altın aksiyon kümesi) Apache-2.0 ile
yayınlar ve indirme betiği sağlarız. Kullanılan setlerin lisans şartları
`licenses.md` içinde tek tek belgelenir.

## Dizin yapısı

```
eval/datasets/
├── README.md              # bu dosya
├── download.py            # kamuya açık setleri indirir (lisans onayı ister)
├── manifest.yaml          # klip listesi + kaynak + lisans + checksum
└── annotations/           # BİZİM ürettiğimiz altın etiketler (Apache-2.0)
    ├── <klip_id>.json
    └── ...
```

## Anotasyon formatı

```jsonc
{
  "clip_id": "depo_forklift_01",
  "source": "self_recorded",          // veya kamuya açık setin adı
  "license": "Apache-2.0",
  "duration_s": 48.0,
  "annotators": ["hasan", "emre"],     // %20 örtüşme → Cohen kappa hesaplanır
  "gold_events": [
    {"t_start": 15.0, "t_end": 18.9, "type": "arac_devrilmesi",
     "label": "Forklift devrildi", "severity": "kritik", "critical": true}
  ],
  "gold_risk": "Yüksek",
  "gold_actions": ["Sağlık ekibini çağır", "Alanı güvenlik altına al"],
  "gold_summary_points": ["forklift devrildi", "kişi yaralandı", "müdahale gerekli"],
  "notes": "gece çekimi, düşük ışık"
}
```

## Anotasyon iş bölümü

Toplam 40-60 klip, **dört kişiye eşit bölünür** (kişi başı 10-15 klip).
Kliplerin **%20'si iki kişi tarafından** etiketlenir → **Cohen kappa** raporlanır
(anotasyon güvenilirliğinin bilimsel kanıtı, `docs/evaluation.md` içinde).

## Kalite kuralları

- Olay sınırları saniye hassasiyetinde; belirsizse `t_start`/`t_end` aralığı genişletilir
- `critical: true` yalnızca can güvenliği riski taşıyan olaylar için
- **Olaysız kontrol klipleri zorunludur** (setin en az %25'i) — yanlış alarm oranı
  ve çekimserlik davranışı bunlarla ölçülür
