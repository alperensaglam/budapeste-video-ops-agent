# ADR-003 — Model tabanlı risk + ince emniyet bariyeri

**Durum:** Kabul edildi · **Tarih:** 2026-08-20

## Bağlam

Şartname Bölüm 4, birebir:

> "Sistem, sabit kurallara dayalı basit bir pipeline yerine dinamik analiz yapabilen,
> bağlama göre farklı çıktılar üretebilen, model tabanlı karar mekanizmaları içeren bir
> mimariye sahip olmalıdır. **Statik, yalnızca kural tabanlı çözümler düşük
> puanlanacaktır.**"

Aynı anda bu bir **güvenlik** sistemidir: "yerde hareketsiz kişi" varken riski "Düşük"
demek kabul edilemez bir hatadır. Bu iki gereksinim gerilim halindedir.

## Karar

**Risk seviyesini model belirler; emniyet bariyeri yalnızca ALT SINIR koyar.**

- `RiskAssessment` bir LLM çıktısıdır: `level`, `score`, `factors[]`, `rationale`,
  `uncertainty` alanlarını model üretir.
- `SafetyGuardRule` yalnızca "şu olay doğrulanmışsa risk şu seviyenin altına inemez"
  biçiminde tanımlanır. **Riski asla düşüremez.**
- Bariyer devreye girerse iz bırakılır: `model_level` (bariyer öncesi karar) ve
  `guard_applied` alanları raporda görünür, UI'da rozet olarak gösterilir.
- **Bariyer kuralı sayısı 6'yı geçmeyecek.** Sayı arttıkça "kural tabanlı sistem"
  eleştirisine açık hale geliriz.

## Alternatifler

**A. Saf kural motoru.** Reddedildi: şartname açıkça düşük puanlanacağını söylüyor.

**B. Saf model, bariyer yok.** Reddedildi: güvenlik-kritik bir alanda modelin
küçümseme hatası kabul edilemez; jüri "peki model yanılırsa?" sorusunu mutlaka sorar.

## Sonuçlar

- **Artı:** hem "statik değil" hem "güvenli" iddiası aynı anda savunulabilir; şeffaflık
  izi sayesinde jüriye müdahalenin nerede olduğu gösterilebilir.
- **Eksi:** iki karar kaynağı (model + bariyer) uyumsuz kalırsa kafa karışıklığı doğar
  → `integrity_issues()` risk uyuşmazlığını yakalar.
- **Sunum notu:** bu bariyer "kural motoru" değil "güvenlik bariyeri" olarak anlatılır;
  her kuralın `justification` alanı slaytta gösterilir.
