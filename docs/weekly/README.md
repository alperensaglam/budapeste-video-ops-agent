# Haftalık İlerleme Günlüğü

**Bu klasör zorunludur.** Şartname Bölüm 10:

> "Proje kapsamında yapılan geliştirmelerin ... **en az haftalık olarak
> güncellemelerin sisteme yüklemesi zorunludur.**"

## Kural

Her **cuma**, o haftanın Sürüm Kaptanı `YYYY-WW.md` dosyasını oluşturur, dört üye de
kendi bölümünü doldurur, kaptan commit'ler ve push'lar.

Dosya adı ISO hafta numarasıyla: `2026-34.md`, `2026-35.md`, ...

## Şablon

```markdown
# Hafta YYYY-WW (GG.AA - GG.AA)

**Sürüm Kaptanı:** … · **Eval Kaptanı:** … · **Uyum Kaptanı:** …
**Faz:** Faz N · **Kapı durumu:** açık / yeşil

## Bu hafta tamamlananlar
| Üye | Katman | Yapılan | PR |
|---|---|---|---|
| Alperen | L4 | … | #… |
| Hasan | L0-L2 | … | #… |
| Emre | L3/serving | … | #… |
| İbrahim | L5-L6 | … | #… |

## KPI anlık durumu
| Metrik | Geçen hafta | Bu hafta | Hedef |
|---|---|---|---|
| Kritik Olay Yakalama (CER) | – | – | ≥ 0.95 |
| Halüsinasyon oranı | – | – | ≤ 0.05 |
| Geçerli JSON oranı | – | – | 1.00 |
| RTF | – | – | ≤ 0.20 (H200) |
| Test kapsamı | – | – | ≥ %70 |

## Engeller
- …

## Gelecek hafta
- …
```
