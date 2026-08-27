#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Scrive `battuti.json`: chi e' stato aggiudicato e a quanto.

E' il fratello leggero di `esporta_catalogo_web.py`. Quello ricostruisce
tutto il catalogo e serve prima dell'asta; questo legge un campo solo e
produce pochi KB, perche' e' l'unica cosa che cambia *durante* l'asta.

Serve a girare su GitHub Actions, dove non ci sono ne' le foto in
`cache_foto/` ne' Pillow: le uniche dipendenze sono `requests` e la libreria
standard, e il token arriva da `AIRTABLE_TOKEN` (un secret del repository).

    python esporta_battuti.py [percorso/battuti.json]

Formato prodotto:

    {"aggiornato": "2026-08-27T14:32:11Z",
     "battuti": {"363": 11, "398": 33}}

Le chiavi sono i numeri sequenziali, i valori il prezzo di aggiudicazione.
Chi non compare non e' stato battuto: la pagina lo tiene nella sua sezione.
"""

import os
import sys
import json
import time
import datetime

import requests

BASE_ID  = "appWlt9AQjxOLG5l1"
TABLE_ID = "tblRShphfDd7TnvmP"

F_SEQ     = "fld398RttJkyapmla"   # Numero Sequenziale
F_BATTUTO = "fldkLSBGM8AmqbluY"   # Valore Battuto

PREDEFINITO = os.path.join(os.path.dirname(os.path.abspath(__file__)), "battuti.json")


def token():
    t = os.environ.get("AIRTABLE_TOKEN")
    if t:
        return t.strip()
    # in locale si riusa il file gia' presente; su Actions esiste solo il secret
    percorso = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                            ".airtable_token")
    if os.path.exists(percorso):
        with open(percorso, encoding="utf-8-sig") as f:   # utf-8-sig: BOM di PowerShell
            return f.read().strip()
    sys.exit("Token assente: serve la variabile d'ambiente AIRTABLE_TOKEN.")


def scarica(tok):
    url = f"https://api.airtable.com/v0/{BASE_ID}/{TABLE_ID}"
    intestazioni = {"Authorization": f"Bearer {tok}"}
    parametri = [("pageSize", 100), ("returnFieldsByFieldId", "true"),
                 ("fields[]", F_SEQ), ("fields[]", F_BATTUTO)]
    tutti, offset = [], None
    while True:
        p = list(parametri) + ([("offset", offset)] if offset else [])
        r = requests.get(url, headers=intestazioni, params=p, timeout=30)
        if r.status_code != 200:
            sys.exit(f"Airtable ha risposto {r.status_code}: {r.text[:200]}")
        dati = r.json()
        tutti.extend(dati.get("records", []))
        offset = dati.get("offset")
        if not offset:
            return tutti
        time.sleep(0.25)          # limite di 5 richieste/secondo


def main():
    destinazione = sys.argv[1] if len(sys.argv) > 1 else PREDEFINITO

    battuti = {}
    for rec in scarica(token()):
        campi = rec.get("fields", {})
        seq, valore = campi.get(F_SEQ), campi.get(F_BATTUTO)
        if seq is not None and valore is not None:
            battuti[str(seq)] = valore

    documento = {
        "aggiornato": datetime.datetime.now(datetime.timezone.utc)
                      .strftime("%Y-%m-%dT%H:%M:%SZ"),
        "battuti": dict(sorted(battuti.items(), key=lambda kv: int(kv[0]))),
    }

    with open(destinazione, "w", encoding="utf8", newline="\n") as f:
        json.dump(documento, f, ensure_ascii=False, indent=1)
        f.write("\n")

    incasso = sum(battuti.values())
    print(f"Battuti: {len(battuti)}" + (f"  incasso {incasso:g} EUR" if battuti else ""))
    print(f"Scritto: {destinazione} ({os.path.getsize(destinazione)} byte)")


if __name__ == "__main__":
    main()
