#!/usr/bin/env python3
"""GÖZCÜ görev koşucusu — platformdan bağımsız `make` yerine geçer.

Windows'ta `make` yok, Linux/Colab/Kaggle'da var. Tek komut seti olsun diye
kanonik koşucu BUDUR; `Makefile` sadece buraya delege eder.

    python tasks.py <görev> [argümanlar]
    python tasks.py --list

Sıfır bağımlılığı vardır (yalnızca stdlib) — repo klonlanır klonlanmaz çalışır.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
from collections.abc import Callable
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SRC = ROOT / "src"

TASKS: dict[str, Callable[[list[str]], int]] = {}
HELP: dict[str, str] = {}


def task(
    name: str, help_text: str
) -> Callable[[Callable[[list[str]], int]], Callable[[list[str]], int]]:
    def deco(fn: Callable[[list[str]], int]) -> Callable[[list[str]], int]:
        TASKS[name] = fn
        HELP[name] = help_text
        return fn

    return deco


def python_exe() -> str:
    """Varsa .venv içindeki yorumlayıcıyı, yoksa mevcut olanı kullan."""
    for candidate in (ROOT / ".venv" / "Scripts" / "python.exe", ROOT / ".venv" / "bin" / "python"):
        if candidate.is_file():
            return str(candidate)
    return sys.executable


def run(cmd: list[str], **kwargs: object) -> int:
    env = dict(os.environ)
    existing = env.get("PYTHONPATH", "")
    env["PYTHONPATH"] = f"{SRC}{os.pathsep}{existing}" if existing else str(SRC)
    env.setdefault("PYTHONIOENCODING", "utf-8")
    print(f"$ {' '.join(cmd)}", flush=True)
    return subprocess.call(cmd, cwd=ROOT, env=env, **kwargs)  # type: ignore[arg-type]


def py(*args: str) -> int:
    return run([python_exe(), *args])


def module(name: str, *args: str) -> int:
    return run([python_exe(), "-m", name, *args])


# ── Kurulum ──────────────────────────────────────────────────────────


@task("setup", "Sanal ortamı kurar ve çekirdek + dev bağımlılıklarını yükler")
def _setup(argv: list[str]) -> int:
    extras = argv[0] if argv else "dev"
    venv = ROOT / ".venv"
    if not venv.is_dir():
        print("[setup] .venv oluşturuluyor...")
        if subprocess.call([sys.executable, "-m", "venv", str(venv)]) != 0:
            return 1
    pip = [python_exe(), "-m", "pip", "install", "--upgrade"]
    if run([*pip, "pip"]) != 0:
        return 1
    return run([*pip, "-e", f".[{extras}]"])


# ── Kalite kapıları ──────────────────────────────────────────────────


@task("lint", "ruff (stil/hata) + mypy (tip) denetimi")
def _lint(argv: list[str]) -> int:
    rc = module("ruff", "check", "src", "tests", "scripts", "tasks.py", *argv)
    rc |= module("ruff", "format", "--check", "src", "tests", "scripts", "tasks.py")
    rc |= module("mypy")
    return rc


@task("fmt", "Kodu otomatik biçimlendirir ve düzeltilebilir hataları giderir")
def _fmt(argv: list[str]) -> int:
    rc = module("ruff", "check", "--fix", "src", "tests", "scripts", "tasks.py")
    rc |= module("ruff", "format", "src", "tests", "scripts", "tasks.py")
    return rc


@task("test", "Testleri koşar (cpu-dev profili, GPU gerekmez)")
def _test(argv: list[str]) -> int:
    os.environ.setdefault("GOZCU_PROFILE", "cpu-dev")
    return module("pytest", *(argv or ["tests"]))


@task("cov", "Testleri kapsam raporuyla koşar (hedef: %70)")
def _cov(argv: list[str]) -> int:
    os.environ.setdefault("GOZCU_PROFILE", "cpu-dev")
    return module(
        "pytest", "tests", "--cov=gozcu", "--cov-report=term-missing", "--cov-report=html", *argv
    )


@task("schema-check", "Sözleşmelerin geriye dönük uyumluluğunu denetler")
def _schema_check(argv: list[str]) -> int:
    return py("scripts/schema_check.py", *argv)


@task("license-check", "AGPL / non-commercial bağımlılık avı (Apache-2.0 hijyeni)")
def _license_check(argv: list[str]) -> int:
    return py("scripts/license_check.py", *argv)


@task("check", "lint + test + schema-check + license-check (PR öncesi tek komut)")
def _check(argv: list[str]) -> int:
    rc = 0
    for name in ("lint", "test", "schema-check", "license-check"):
        print(f"\n===== {name} =====")
        rc |= TASKS[name]([])
    print("\n" + ("TÜMÜ GEÇTİ" if rc == 0 else "BAŞARISIZ — yukarıdaki çıktıya bakın"))
    return rc


# ── Çalıştırma ───────────────────────────────────────────────────────


@task("demo", "Uçtan uca demo (Faz 1'de gelir). SCENARIO=... ile senaryo seçilir")
def _demo(argv: list[str]) -> int:
    print("[demo] Faz 1 kapısında gelecek: video -> ajan diyaloğu -> şartname JSON")
    return 0


@task("record-cassettes", "GPU'da (colab-t4) kaset üretir — ekibin CPU'da çalışması için")
def _record(argv: list[str]) -> int:
    print("[kaset] Faz 1 kapısında gelecek. Kullanım: GOZCU_PROFILE=colab-t4 ...")
    return 0


@task("profiles", "Mevcut donanım profillerini listeler")
def _profiles(argv: list[str]) -> int:
    sys.path.insert(0, str(SRC))
    from gozcu.config import available_profiles, load_profile

    for name in available_profiles():
        p = load_profile(name)
        print(f"{p.name:11s} | vlm={p.vlm.backend.value:9s} | {p.vlm.model:38s} | gpu={p.is_gpu}")
        print(f"{'':11s} | {p.description}")
    return 0


@task("clean", "Üretilmiş dosyaları temizler (venv hariç)")
def _clean(argv: list[str]) -> int:
    hedefler = [".pytest_cache", ".mypy_cache", ".ruff_cache", "htmlcov", ".coverage", "dist"]
    for h in hedefler:
        p = ROOT / h
        if p.is_dir():
            shutil.rmtree(p, ignore_errors=True)
        elif p.is_file():
            p.unlink()
    for pycache in ROOT.rglob("__pycache__"):
        if ".venv" not in str(pycache):
            shutil.rmtree(pycache, ignore_errors=True)
    print("temizlendi")
    return 0


# ── Giriş noktası ────────────────────────────────────────────────────


def usage() -> int:
    print(__doc__)
    print("Görevler:\n")
    for name in sorted(TASKS):
        print(f"  {name:18s} {HELP[name]}")
    print("\nProfil seçimi: GOZCU_PROFILE=cpu-dev | colab-t4 | h200-prod")
    return 0


def main(argv: list[str]) -> int:
    if not argv or argv[0] in {"-h", "--help", "--list", "help"}:
        return usage()
    name, rest = argv[0], argv[1:]
    if name not in TASKS:
        print(f"bilinmeyen görev: {name}\n")
        return usage() or 1
    return TASKS[name](rest)


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
