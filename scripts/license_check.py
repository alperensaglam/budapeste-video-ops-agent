#!/usr/bin/env python3
"""Lisans hijyeni denetimi — Apache-2.0 uyumluluğunu korur.

NEDEN VAR (şartname, Bölüm 9):
    "Yarışmaya katılan herkes, GitHub üzerinde açık kaynak olarak paylaşacakları tüm
     kaynak kodların ... Apache lisansı (Apache License 2.0) ile lisanslanarak
     Türkiye Açık Kaynak Platformu GitHub hesabında paylaşılacağını kabul eder."

Apache-2.0 ile yayınlanacak bir repo AGPL bağımlılık taşıyamaz. En yaygın tuzak
Ultralytics YOLO'dur (AGPL-3.0) — bu yüzden mimaride RT-DETR / D-FINE (Apache-2.0)
tercih edildi. Non-commercial lisanslı modeller de yasaktır (şartname ayrıca
"ücretli yazılım" ve "3. taraflardan hizmet satın alma" yasağı getiriyor).

Kullanım:
    python tasks.py license-check
"""

from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

#: Apache-2.0 bir repoda ASLA bulunmaması gereken lisanslar.
YASAK_LISANSLAR: tuple[str, ...] = (
    "AGPL",
    "GNU Affero",
    "SSPL",
    "Server Side Public License",
    "CC-BY-NC",
    "CC BY-NC",
    "NonCommercial",
    "CPML",
    "Coqui Public Model License",
    "Proprietary",
    "Commons Clause",
)

#: İsimden tanınan riskli paketler (lisans metni yanıltıcı olabilir).
YASAK_PAKETLER: dict[str, str] = {
    "ultralytics": "AGPL-3.0 — RT-DETRv2 / D-FINE (Apache-2.0) kullanın",
    "yolov5": "AGPL-3.0 — RT-DETRv2 / D-FINE kullanın",
    "TTS": "Coqui TTS / XTTS-v2 CPML (non-commercial) — Piper TTS (MIT) kullanın",
    "pyannote.audio": "gated model şartları — dikkatli inceleyin veya kaçının",
}

#: Yalnızca uyarı üretenler (kullanılabilir ama dokümante edilmeli).
DIKKAT_LISANSLARI: tuple[str, ...] = ("GPL", "LGPL", "MPL")


def paket_lisanslari() -> list[dict[str, str]]:
    """pip-licenses varsa onu, yoksa importlib.metadata'yı kullan."""
    try:
        out = subprocess.check_output(
            [sys.executable, "-m", "piplicenses", "--format=json", "--with-urls"],
            cwd=ROOT,
            stderr=subprocess.DEVNULL,
            text=True,
        )
        return json.loads(out)
    except Exception:
        pass

    from importlib import metadata

    sonuc = []
    for dist in metadata.distributions():
        ad = dist.metadata.get("Name") or "?"
        lisans = dist.metadata.get("License") or ""
        if not lisans or len(lisans) > 200:
            siniflar = dist.metadata.get_all("Classifier") or []
            lisans = next(
                (c.split("::")[-1].strip() for c in siniflar if c.startswith("License ::")),
                "UNKNOWN",
            )
        sonuc.append({"Name": ad, "Version": dist.version or "?", "License": lisans})
    return sonuc


def main() -> int:
    paketler = paket_lisanslari()
    ihlaller: list[str] = []
    uyarilar: list[str] = []

    for p in paketler:
        ad, lisans = p.get("Name", "?"), p.get("License", "")
        if ad.lower() in {k.lower() for k in YASAK_PAKETLER}:
            gerekce = next(v for k, v in YASAK_PAKETLER.items() if k.lower() == ad.lower())
            ihlaller.append(f"  YASAK PAKET  {ad} — {gerekce}")
            continue
        for yasak in YASAK_LISANSLAR:
            if re.search(re.escape(yasak), lisans, re.IGNORECASE):
                ihlaller.append(f"  YASAK LİSANS {ad} ({p.get('Version', '?')}) -> {lisans}")
                break
        else:
            for dikkat in DIKKAT_LISANSLARI:
                if re.search(rf"\b{dikkat}\b", lisans, re.IGNORECASE):
                    uyarilar.append(f"  dikkat      {ad} -> {lisans}")
                    break

    print(f"[lisans] {len(paketler)} paket denetlendi\n")
    if uyarilar:
        print("UYARILAR (kullanılabilir, docs/licenses.md içinde gerekçelendirin):")
        print("\n".join(sorted(set(uyarilar))))
        print()
    if ihlaller:
        print("İHLALLER — Apache-2.0 repo bunları taşıyamaz:")
        print("\n".join(sorted(set(ihlaller))))
        print("\nŞartname Bölüm 9: tüm kod Apache-2.0 ile yayınlanacak.")
        return 1
    print("Temiz: AGPL / non-commercial bağımlılık yok.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
