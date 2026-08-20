#!/usr/bin/env python3
"""Sözleşme (şema) değişiklik denetimi.

NEDEN VAR: Dört kişinin paralel çalışması, ``src/gozcu/contracts/`` altındaki
şemaların KARARLI kalmasına bağlı. Bu script, mevcut şemaları
``docs/contracts.lock.json`` içindeki referansla karşılaştırır ve sessiz kırıcı
değişiklikleri yakalar.

Kırıcı sayılan değişiklikler:
  * bir modelin silinmesi,
  * zorunlu (required) alan eklenmesi,
  * mevcut alanın silinmesi veya tipinin değişmesi.

Kırıcı bir değişiklik gerçekten gerekliyse:
  1. ``docs/decisions/`` altına ADR yaz,
  2. ``AnalysisReport.schema_version`` alanını artır,
  3. dört katman sahibinin de PR onayını al,
  4. ``python tasks.py schema-check --update`` ile kilidi tazele.

Kullanım:
    python tasks.py schema-check            # denetle
    python tasks.py schema-check --update   # kilidi güncelle (ADR ile birlikte)
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

LOCK_PATH = ROOT / "docs" / "contracts.lock.json"

#: Kilitlenen modeller. Yeni bir sözleşme eklendiğinde buraya da eklenir.
KILITLI_MODELLER = [
    "AnalysisReport",
    "DetectedEvent",
    "EvidenceItem",
    "EvidenceQuery",
    "EvidenceQueryResult",
    "EvidenceGraphStats",
    "RecommendedAction",
    "RiskAssessment",
    "SegmentAnalysis",
    "ToolSpec",
    "ToolCall",
    "ToolResult",
    "TrackSegment",
    "VLMRequest",
    "VLMResponse",
    "CassetteEntry",
]


def mevcut_semalar() -> dict[str, Any]:
    import gozcu.contracts as c

    out: dict[str, Any] = {}
    for ad in KILITLI_MODELLER:
        model = getattr(c, ad)
        out[ad] = model.model_json_schema()
    return out


def _alanlar(sema: dict[str, Any]) -> dict[str, Any]:
    return sema.get("properties", {}) or {}


def _zorunlular(sema: dict[str, Any]) -> set[str]:
    return set(sema.get("required", []) or [])


def _tip_imzasi(alan: dict[str, Any]) -> str:
    """Alanın tip imzasını kaba ama kararlı biçimde özetler."""
    for anahtar in ("type", "$ref", "anyOf", "allOf", "enum"):
        if anahtar in alan:
            return json.dumps({anahtar: alan[anahtar]}, sort_keys=True, ensure_ascii=False)
    return "?"


def karsilastir(eski: dict[str, Any], yeni: dict[str, Any]) -> list[str]:
    kirici: list[str] = []

    for ad in eski:
        if ad not in yeni:
            kirici.append(f"MODEL SİLİNDİ: {ad}")
            continue
        e_alan, y_alan = _alanlar(eski[ad]), _alanlar(yeni[ad])
        e_zor, y_zor = _zorunlular(eski[ad]), _zorunlular(yeni[ad])

        for alan in e_alan:
            if alan not in y_alan:
                kirici.append(f"ALAN SİLİNDİ: {ad}.{alan}")
            elif _tip_imzasi(e_alan[alan]) != _tip_imzasi(y_alan[alan]):
                kirici.append(
                    f"TİP DEĞİŞTİ: {ad}.{alan}\n"
                    f"    eski: {_tip_imzasi(e_alan[alan])}\n"
                    f"    yeni: {_tip_imzasi(y_alan[alan])}"
                )
        for alan in y_zor - e_zor:
            kirici.append(f"YENİ ZORUNLU ALAN: {ad}.{alan} (mevcut tüketicileri kırar)")

    return kirici


def main() -> int:
    guncelle = "--update" in sys.argv
    yeni = mevcut_semalar()

    if not LOCK_PATH.is_file():
        LOCK_PATH.parent.mkdir(parents=True, exist_ok=True)
        LOCK_PATH.write_text(
            json.dumps(yeni, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        print(f"[şema] kilit oluşturuldu: {LOCK_PATH.relative_to(ROOT)}")
        print(f"[şema] {len(yeni)} model kilitlendi.")
        return 0

    eski = json.loads(LOCK_PATH.read_text(encoding="utf-8"))
    kirici = karsilastir(eski, yeni)
    yeni_modeller = sorted(set(yeni) - set(eski))

    if yeni_modeller:
        print("Yeni modeller (kırıcı değil):")
        for ad in yeni_modeller:
            print(f"  + {ad}")
        print()

    if guncelle:
        LOCK_PATH.write_text(
            json.dumps(yeni, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        print(f"[şema] kilit güncellendi ({len(yeni)} model).")
        if kirici:
            print("UYARI: kırıcı değişiklikler kilide işlendi — ADR yazdığınızdan emin olun:")
            for k in kirici:
                print(f"  {k}")
        return 0

    if kirici:
        print("KIRICI SÖZLEŞME DEĞİŞİKLİĞİ TESPİT EDİLDİ:\n")
        for k in kirici:
            print(f"  {k}")
        print(
            "\nSözleşmeler dört kişinin paralel çalışmasının temelidir.\n"
            "Gerçekten gerekliyse: ADR yaz + schema_version artır + 4 onay al,\n"
            "sonra: python tasks.py schema-check --update"
        )
        return 1

    print(f"[şema] {len(yeni)} model kilitle uyumlu. Sözleşme kararlı.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
