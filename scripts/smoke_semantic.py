#!/usr/bin/env python3
"""
smoke_semantic.py — Verifica el recall semántico de MemoryStore (offline).

Comprueba que:
  • encuentra ítems por similitud (variantes morfológicas / orden), no solo subcadena;
  • garantiza los aciertos por subcadena;
  • rankea primero el ítem más parecido a la consulta;
  • una consulta sin relación no devuelve ruido.

Uso:  python scripts/smoke_semantic.py
"""

import os
import sys
import tempfile

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src"))

from services.memory_store import MemoryStore

store = MemoryStore(tempfile.mkdtemp(prefix="lia_sem_"))
store.set_fact("proyecto lia", "asistente en python con skills")
store.set_fact("color favorito", "azul")
store.set_fact("cumpleaños", "15 de marzo")
store.remember_short("user", "quiero aprender programación avanzada en python")

fallos = 0


def check(cond, desc):
    global fallos
    print(f"  [{'OK ' if cond else 'FAIL'}] {desc}")
    if not cond:
        fallos += 1


r_prog = store.recall("programar en python")
check(any("python" in x.lower() for x in r_prog),
      f"'programar en python' recupera ítems de python  -> {r_prog}")

r_azul = store.recall("azul")
check(any("azul" in x.lower() for x in r_azul),
      f"subcadena 'azul' garantizada  -> {r_azul}")

r_lia = store.recall("proyecto lia")
check(bool(r_lia) and "lia" in r_lia[0].lower(),
      f"'proyecto lia' rankea primero el hecho de lia  -> {r_lia}")

r_none = store.recall("xkcd qwerty zzz")
check(all("python" not in x.lower() and "azul" not in x.lower() for x in r_none),
      f"consulta sin relación no trae ruido fuerte  -> {r_none}")

print(f"\nFallos: {fallos}")
sys.exit(1 if fallos else 0)
