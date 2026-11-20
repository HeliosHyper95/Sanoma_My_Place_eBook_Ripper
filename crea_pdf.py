#!/usr/bin/env python3
"""Conversione delle pagine HTML locali in PDF.

Funzioni:
- Conversione HTML tramite Chromium.
- Conservazione dei livelli SVG con clipPath.
- Rimozione delle copie HTML duplicate tramite SHA256.
- Gestione della cache temporanea.
- Etichette personalizzate per le copertine.
- OCR facoltativo per rendere il testo selezionabile.
"""

from __future__ import annotations

import argparse
import base64
import hashlib
import math
import os
import queue
import re
import shlex
import shutil
import subprocess
import sys

from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from urllib.parse import quote, unquote


# ============================================================
# VERSIONE
# ============================================================

VERSIONE_SCRIPT = "4.2.1"
BUILD_ID = "SANOMA-PDF-20261118-WINDOWS-CHROME"
SCHEMA_CACHE = "4.2.1-svg-clippath-ocr-pagelabels-letters-windows-browser"

# Changelog 4.2.1:
# - Rilevamento automatico di Chrome e Chromium nei percorsi standard Windows.
# - Supporto per --browser chrome e percorsi Windows con spazi.
# - Verifica preventiva del browser e gestione degli errori di avvio.
# - Compatibilità Linux e Flatpak mantenuta.

BROWSER_NAMES = [
    "google-chrome-stable",
    "google-chrome",
    "chromium",
    "chromium-browser",
    "chrome",
]

FLATPAK_NOTI = [
    "io.github.ungoogled_software.ungoogled_chromium",
    "com.github.Eloston.UngoogledChromium",
    "org.chromium.Chromium",
    "com.google.Chrome",
]


# ============================================================
# REGEX
# ============================================================

PAGE_CSS_RE = re.compile(
    r"\.page-container\s*\{([^}]*)\}",
    re.I | re.S,
)

CSS_DIM_RE = re.compile(
    r"\b(width|height)\s*:\s*([\d.]+)px",
    re.I,
)

IMAGE_TAG_RE = re.compile(
    r"<image\b[^>]*?/?>",
    re.I | re.S,
)

IMG_TAG_RE = re.compile(
    r"<img\b[^>]*>",
    re.I | re.S,
)

ATTR_RE = re.compile(
    r"([:\w-]+)\s*=\s*([\"'])(.*?)\2",
    re.S,
)

LOCAL_ATTR_RE = re.compile(
    r"(?P<prefix>\b(?:src|href|xlink:href)\s*=\s*)"
    r"(?P<quote>[\"'])"
    r"(?P<path>img/[^\"']+)"
    r"(?P=quote)",
    re.I,
)


# ============================================================
# CSS DI STAMPA
# ============================================================

PRINT_CSS = """<style id="pdf-print">
@page {{ size: {w}px {h}px; margin: 0; }}

html, body {{
  margin: 0 !important;
  padding: 0 !important;
  width: {w}px !important;
  height: {h}px !important;
  min-width: {w}px !important;
  min-height: {h}px !important;
  overflow: hidden !important;
  background: #fff !important;
  page-break-after: avoid !important;
  break-after: avoid !important;
}}

body {{ display: block !important; }}

.header, .nav-container, .zoom-controls {{
  display: none !important;
}}

.page-wrapper {{
  display: block !important;
  position: relative !important;
  width: {w}px !important;
  height: {h}px !important;
  min-width: {w}px !important;
  min-height: {h}px !important;
  margin: 0 !important;
  padding: 0 !important;
  overflow: hidden !important;
  page-break-inside: avoid !important;
  break-inside: avoid !important;
}}

.page-container {{
  position: relative !important;
  width: {w}px !important;
  height: {h}px !important;
  min-width: {w}px !important;
  min-height: {h}px !important;
  transform: none !important;
  box-shadow: none !important;
  margin: 0 !important;
  padding: 0 !important;
  overflow: hidden !important;
  page-break-inside: avoid !important;
  break-inside: avoid !important;
}}

* {{
  -webkit-print-color-adjust: exact !important;
  print-color-adjust: exact !important;
}}
</style>"""


# ============================================================
# BROWSER
# ============================================================

def trova_flatpak():

    if not shutil.which("flatpak"):
        return None

    r = subprocess.run(
        ["flatpak", "list", "--app", "--columns=application"],
        capture_output=True,
        text=True,
        check=False,
    )

    if r.returncode != 0:
        return None

    app = [
        x.strip()
        for x in r.stdout.splitlines()
        if x.strip()
    ]

    for known in FLATPAK_NOTI:
        if known in app:
            return known

    return next(
        (
            x for x in app
            if "chromium" in x.lower()
            or "chrome" in x.lower()
        ),
        None,
    )


def percorsi_browser_windows():
    """Restituisce i percorsi standard di Chrome, Chromium ed Edge."""

    if os.name != "nt":
        return []

    percorsi = []
    for base in (
        os.environ.get("ProgramFiles"),
        os.environ.get("ProgramFiles(x86)"),
        os.environ.get("LOCALAPPDATA"),
    ):
        if base:
            percorsi.extend([
                Path(base) / "Google" / "Chrome" / "Application" / "chrome.exe",
                Path(base) / "Chromium" / "Application" / "chrome.exe",
                Path(base) / "Microsoft" / "Edge" / "Application" / "msedge.exe",
            ])

    risultato = []
    viste = set()
    for p in percorsi:
        chiave = os.path.normcase(str(p))
        if chiave not in viste:
            viste.add(chiave)
            risultato.append(p)
    return risultato


def risolvi_browser_esplicito(scelto):
    """Gestisce alias, comandi e percorsi Windows contenenti spazi."""

    valore = str(scelto).strip()
    if not valore:
        raise ValueError("Il valore di --browser è vuoto.")

    pulito = valore.strip().strip('"').strip("'")
    percorso = Path(pulito).expanduser()

    # Non dividere un percorso esistente sugli spazi.
    if percorso.is_file():
        return [str(percorso.resolve())]

    alias = {
        "chrome": ("chrome.exe", "chrome"),
        "google-chrome": ("google-chrome",),
        "google-chrome-stable": ("google-chrome-stable",),
        "chromium": ("chromium", "chromium-browser", "chromium.exe"),
        "chromium-browser": ("chromium-browser", "chromium"),
        "edge": ("msedge.exe", "msedge"),
        "msedge": ("msedge.exe", "msedge"),
    }
    nome = pulito.lower()

    if nome in alias:
        for candidato in alias[nome]:
            trovato = shutil.which(candidato)
            if trovato:
                return [trovato]

        if os.name == "nt":
            for candidato in percorsi_browser_windows():
                if not candidato.is_file():
                    continue
                e_edge = candidato.name.lower() == "msedge.exe"
                if (nome in ("edge", "msedge")) == e_edge:
                    return [str(candidato.resolve())]

        raise FileNotFoundError(
            f"Browser '{scelto}' non trovato. Indica il percorso completo con --browser."
        )

    # Se sembra un percorso, segnala subito se non esiste.
    if (
        os.path.sep in pulito
        or (os.path.altsep and os.path.altsep in pulito)
        or percorso.suffix.lower() in (".exe", ".com", ".bat", ".cmd")
    ):
        raise FileNotFoundError(f"Il browser indicato non esiste: {pulito}")

    try:
        parti = shlex.split(valore, posix=(os.name != "nt"))
    except ValueError as errore:
        raise ValueError(f"Valore --browser non valido: {errore}") from errore

    if parti:
        eseguibile = shutil.which(parti[0])
        if eseguibile:
            return [eseguibile] + parti[1:]

    raise FileNotFoundError(
        f"Comando browser non trovato: {pulito}. Indica il percorso completo con --browser."
    )


def trova_browser(scelto=None):

    if scelto:
        return risolvi_browser_esplicito(scelto)

    # Chrome Windows normalmente non è incluso nel PATH.
    if os.name == "nt":
        for percorso in percorsi_browser_windows():
            if percorso.is_file():
                return [str(percorso.resolve())]

    for nome in BROWSER_NAMES:
        percorso = shutil.which(nome)
        if percorso:
            return [percorso]

    app = trova_flatpak()
    if app:
        return ["flatpak", "run", app]

    return None


def verifica_browser(browser):
    """Verifica la disponibilità dell'eseguibile prima della conversione."""

    if not browser:
        raise FileNotFoundError("Nessun browser Chromium trovato.")

    eseguibile = browser[0]
    if os.path.isabs(eseguibile) or os.path.dirname(eseguibile):
        if not Path(eseguibile).is_file():
            raise FileNotFoundError(f"Eseguibile browser inesistente: {eseguibile}")
    elif not shutil.which(eseguibile):
        raise FileNotFoundError(
            f"Impossibile trovare '{eseguibile}' nel PATH."
        )

    if os.name != "nt" and not os.access(eseguibile, os.X_OK):
        raise PermissionError(f"Il browser non è eseguibile: {eseguibile}")

    return True


def con_permessi(cmd, radice):

    if Path(cmd[0]).name != "flatpak" or "run" not in cmd:
        return cmd

    i = cmd.index("run") + 1
    permesso = f"--filesystem={radice}"

    if not any(x.startswith("--filesystem=") for x in cmd):
        cmd = cmd[:i] + [permesso] + cmd[i:]

    return cmd


# ============================================================
# PAGINE
# ============================================================

def elenco_pagine(radice, da, a):

    pagine = []

    for d in radice.iterdir():

        if not d.is_dir() or not d.name.isdigit():
            continue

        html = d / "composite.html"

        if not html.is_file():
            continue

        n = int(d.name)

        if da is not None and n < da:
            continue

        if a is not None and n > a:
            continue

        pagine.append((n, html))

    return sorted(pagine, key=lambda x: x[0])


def dimensioni(html):

    m = PAGE_CSS_RE.search(html)

    if m:

        props = {
            k.lower(): float(v)
            for k, v in CSS_DIM_RE.findall(m.group(1))
        }

        if "width" in props and "height" in props:
            w, h = props["width"], props["height"]
        else:
            w, h = 794.0, 1123.0

    else:
        w, h = 794.0, 1123.0

    svg = re.search(r"<svg\b[^>]*>", html, re.I | re.S)

    if svg and re.search(
        r"<(?:image|path|rect|text|polygon|use)\b",
        html[svg.end():],
        re.I,
    ):

        attrs = {
            k.lower(): v
            for k, _, v in ATTR_RE.findall(svg.group(0))
        }

        viewbox = attrs.get("viewbox")

        if viewbox:

            values = re.findall(r"-?[\d.]+", viewbox)

            if len(values) == 4:

                x, y, vw, vh = map(float, values)

                w = max(w, x + vw)
                h = max(h, y + vh)

    return math.ceil(w), math.ceil(h)


# ============================================================
# ASSET
# ============================================================

def risolvi_asset(href, cartella_pagina):

    relativo = Path(unquote(href))

    diretto = (cartella_pagina / relativo).resolve()

    if diretto.is_file():
        return diretto, False

    if href.startswith("img/"):

        piatto = (
            cartella_pagina / relativo.name
        ).resolve()

        if piatto.is_file():
            return piatto, True

    return None, False


def hash_immagini_svg(html, cartella_pagina):

    hashes = set()
    mancanti = []
    trovati = []

    for match in IMAGE_TAG_RE.finditer(html):

        attrs = {
            k.lower(): v
            for k, _, v in ATTR_RE.findall(match.group(0))
        }

        href = attrs.get("xlink:href") or attrs.get("href")

        if not href or not href.startswith(("img/", "shade/")):
            continue

        asset, _ = risolvi_asset(href, cartella_pagina)

        if asset is None:
            mancanti.append(href)
            continue

        try:
            dati = asset.read_bytes()
        except OSError:
            mancanti.append(href)
            continue

        hashes.add(hashlib.sha256(dati).hexdigest())
        trovati.append(str(asset))

    return hashes, sorted(set(mancanti)), sorted(set(trovati))


def decodifica_data_uri(src):

    if not src.startswith("data:") or "," not in src:
        return None

    intestazione, payload = src.split(",", 1)

    if ";base64" not in intestazione.lower():
        return None

    try:
        return base64.b64decode(payload, validate=False)
    except (ValueError, TypeError):
        return None


def prepara_asset(html, cartella_pagina):

    hash_svg, mancanti, trovati_svg = hash_immagini_svg(
        html,
        cartella_pagina,
    )

    mancanti_set = set(mancanti)
    trovati_set = set(trovati_svg)
    rimossi = []

    html_layer_rimossi = 0
    html_layer_non_abbinati = []

    # Conserva le immagini SVG con clipPath e rimuove
    # esclusivamente le copie HTML aventi gli stessi byte.

    def processa_resource_layer(match):

        nonlocal html_layer_rimossi

        tag = match.group(0)

        attrs = {
            k.lower(): v
            for k, _, v in ATTR_RE.findall(tag)
        }

        classi = attrs.get("class", "").lower().split()

        if "resource-layer" not in classi:
            return tag

        dati = decodifica_data_uri(attrs.get("src", ""))

        if dati is None:

            html_layer_non_abbinati.append(
                "resource-layer con sorgente non base64"
            )

            return tag

        digest = hashlib.sha256(dati).hexdigest()

        if digest in hash_svg:

            html_layer_rimossi += 1
            return ""

        html_layer_non_abbinati.append(
            attrs.get("style", "resource-layer senza posizione")[:160]
        )

        return tag

    html = IMG_TAG_RE.sub(processa_resource_layer, html)

    def processa_image(match):

        tag = match.group(0)

        attrs = {
            k.lower(): v
            for k, _, v in ATTR_RE.findall(tag)
        }

        href = attrs.get("xlink:href") or attrs.get("href")

        if not href or not href.startswith(("img/", "shade/")):
            return tag

        asset, riscrivere = risolvi_asset(
            href,
            cartella_pagina,
        )

        if asset is None:

            mancanti_set.add(href)

            rimossi.append(
                f"{href} (riferimento SVG locale assente)"
            )

            return ""

        trovati_set.add(str(asset))

        if riscrivere:

            nuovo = quote(asset.name, safe="-._~")

            tag = re.sub(
                r"((?:xlink:href|href)\s*=\s*)([\"'])"
                + re.escape(href)
                + r"\2",

                lambda m:
                    m.group(1) + m.group(2)
                    + nuovo + m.group(2),

                tag,
                count=1,
                flags=re.I,
            )

        return tag

    html = IMAGE_TAG_RE.sub(processa_image, html)

    def correggi_attributo(match):

        href = match.group("path")

        asset, riscrivere = risolvi_asset(
            href,
            cartella_pagina,
        )

        if asset is None:
            mancanti_set.add(href)
            return match.group(0)

        trovati_set.add(str(asset))

        if riscrivere:

            nuovo = quote(asset.name, safe="-._~")

            return (
                match.group("prefix")
                + match.group("quote")
                + nuovo
                + match.group("quote")
            )

        return match.group(0)

    html = LOCAL_ATTR_RE.sub(correggi_attributo, html)

    if html_layer_rimossi:

        rimossi.append(
            f"{html_layer_rimossi} copie HTML resource-layer rimosse; "
            "conservati i corrispondenti livelli SVG con clipPath"
        )

    if html_layer_non_abbinati:

        rimossi.append(
            f"ATTENZIONE: {len(html_layer_non_abbinati)} "
            "resource-layer HTML non abbinati conservati"
        )

    return (
        html,
        sorted(mancanti_set),
        sorted(trovati_set),
        sorted(rimossi),
    )


# ============================================================
# HTML PER LA STAMPA
# ============================================================

def html_per_stampa(html, w, h, cartella_pagina):

    html, mancanti, asset_trovati, rimossi = prepara_asset(
        html,
        cartella_pagina,
    )

    css = PRINT_CSS.format(w=w, h=h)

    base_href = (
        cartella_pagina.resolve().as_uri().rstrip("/") + "/"
    )

    base_tag = f'<base href="{base_href}">'

    if re.search(r"<base\b", html, re.I):

        html = re.sub(
            r"<base\b[^>]*>",
            base_tag,
            html,
            count=1,
            flags=re.I,
        )

    else:

        m = re.search(r"<head\b[^>]*>", html, re.I)

        if m:
            html = html[:m.end()] + base_tag + html[m.end():]
        else:
            html = "<head>" + base_tag + "</head>" + html

    if re.search(r"</head\s*>", html, re.I):

        html = re.sub(
            r"</head\s*>",
            css + "</head>",
            html,
            count=1,
            flags=re.I,
        )

    else:
        html = css + html

    return html, mancanti, asset_trovati, rimossi


# ============================================================
# VERIFICA PDF
# ============================================================

def conta_pagine_pdf(percorso):

    try:

        from pypdf import PdfReader

        return len(
            PdfReader(
                str(percorso),
                strict=False,
            ).pages
        )

    except ImportError:
        pass

    except Exception:
        return 0

    if shutil.which("pdfinfo"):

        r = subprocess.run(
            ["pdfinfo", str(percorso)],
            capture_output=True,
            text=True,
            check=False,
        )

        m = re.search(
            r"^Pages:\s+(\d+)",
            r.stdout,
            re.M,
        )

        if r.returncode == 0 and m:
            return int(m.group(1))

        return 0

    return None


# ============================================================
# STAMPA CON CHROMIUM
# ============================================================

def stampa_pdf(browser, html_path, pdf_path, profilo):

    parziale = pdf_path.with_name(
        pdf_path.stem + ".part.pdf"
    )

    parziale.unlink(missing_ok=True)

    cmd = list(browser) + [

        "--headless",
        "--disable-gpu",
        "--hide-scrollbars",
        "--disable-background-networking",
        "--disable-extensions",
        "--no-first-run",
        "--no-default-browser-check",
        "--allow-file-access-from-files",
        "--no-pdf-header-footer",
        "--print-to-pdf-no-header",
        "--virtual-time-budget=10000",

        f"--user-data-dir={profilo}",
        f"--print-to-pdf={parziale}",
    ]

    if hasattr(os, "geteuid") and os.geteuid() == 0:
        cmd.append("--no-sandbox")

    cmd.append(html_path.resolve().as_uri())

    try:

        r = subprocess.run(
            cmd,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE,
            text=True,
            timeout=180,
            check=False,
        )

    except subprocess.TimeoutExpired:

        parziale.unlink(missing_ok=True)

        return False, "Chromium ha superato il timeout di 180 secondi."

    except OSError as errore:

        parziale.unlink(missing_ok=True)

        return False, (
            "Impossibile avviare il browser: "
            f"{errore}. Verifica il percorso di chrome.exe e i permessi."
        )

    if not parziale.is_file() or parziale.stat().st_size == 0:

        parziale.unlink(missing_ok=True)

        return False, (
            r.stderr
            or "Chromium non ha prodotto il PDF."
        )[-1200:]

    pagine = conta_pagine_pdf(parziale)

    if pagine not in (None, 1):

        parziale.unlink(missing_ok=True)

        return False, (
            f"La singola pagina HTML ha generato {pagine} "
            "pagine PDF (attesa: 1)."
        )

    parziale.replace(pdf_path)

    return True, ""


# ============================================================
# UNIONE PDF + NUMERAZIONE COPERTINE
# ============================================================


def unisci(pdfs, uscita, copertine=0, sezioni_letterate=None):

    sezioni_letterate = sezioni_letterate or []

    try:

        from pypdf import PdfWriter

        from pypdf.generic import (
            ArrayObject,
            DictionaryObject,
            NameObject,
            NumberObject,
            TextStringObject,
        )

        if copertine < 0 or copertine > len(pdfs):

            raise ValueError(
                f"Numero copertine non valido: {copertine}; "
                f"pagine disponibili: {len(pdfs)}."
            )

        writer = PdfWriter()

        for p in pdfs:
            writer.append(str(p))

        # Costruzione delle etichette PDF.

        if copertine or sezioni_letterate:

            etichette = []

            # Copertine.

            if copertine:

                cover_label = DictionaryObject()

                cover_label[NameObject("/P")] = TextStringObject(
                    "Copertina "
                )

                cover_label[NameObject("/S")] = NameObject("/D")
                cover_label[NameObject("/St")] = NumberObject(1)

                etichette.append((0, cover_label))

                # Il contenuto riparte da pagina 1.

                if copertine < len(pdfs):

                    content_label = DictionaryObject()

                    content_label[NameObject("/S")] = NameObject("/D")
                    content_label[NameObject("/St")] = NumberObject(1)

                    etichette.append((copertine, content_label))

            # Sezioni con numerazione alfabetica.

            for sezione in sezioni_letterate:

                indice = sezione["pagina"] - 1

                label = DictionaryObject()

                label[NameObject("/P")] = TextStringObject(
                    sezione["lettera"]
                )

                label[NameObject("/S")] = NameObject("/D")

                label[NameObject("/St")] = NumberObject(
                    sezione["numero"]
                )

                etichette.append((indice, label))

            # Le etichette devono essere ordinate per pagina.

            etichette.sort(key=lambda x: x[0])

            nums = ArrayObject()

            for indice, label in etichette:

                nums.append(NumberObject(indice))
                nums.append(label)

            page_labels = DictionaryObject()

            page_labels[NameObject("/Nums")] = nums

            writer._root_object[
                NameObject("/PageLabels")
            ] = writer._add_object(page_labels)

        writer.add_metadata({

            "/Producer": f"crea_pdf.py {VERSIONE_SCRIPT}",

            "/Creator": BUILD_ID,

            "/Subject": (
                "PDF generato da pagine HTML locali; "
                "livelli SVG con clipPath conservati"
                + (
                    f"; copertine escluse dalla numerazione: {copertine}"
                    if copertine else ""
                )
                + (
                    f"; sezioni con numerazione alfabetica: "
                    f"{len(sezioni_letterate)}"
                    if sezioni_letterate else ""
                )
            ),

        })

        with open(uscita, "wb") as f:
            writer.write(f)

        return True

    except ImportError:

        print(
            "Per le etichette PDF personalizzate serve pypdf."
        )

        print(
            "Installa con: sudo apt install python3-pypdf"
        )

        return False

    except Exception as e:

        print(f"Errore pypdf durante l'unione: {e}")
        return False

    # Fallback originale se non sono richieste etichette personalizzate.

    if shutil.which("pdfunite"):

        return subprocess.run(
            ["pdfunite", *map(str, pdfs), str(uscita)],
            check=False,
        ).returncode == 0

    if shutil.which("qpdf"):

        return subprocess.run(
            [
                "qpdf",
                "--empty",
                "--pages",
                *map(str, pdfs),
                "--",
                str(uscita),
            ],
            check=False,
        ).returncode == 0

    print(
        "Nessuno strumento per unire i PDF. "
        "Installa pypdf oppure: sudo apt install poppler-utils"
    )

    return False



# ============================================================
# OCR FACOLTATIVO
# ============================================================

def aggiungi_ocr(pdf, lingua="eng+ita"):

    programma = shutil.which("ocrmypdf")

    if not programma:

        print(
            "OCRmyPDF non trovato. "
            "Installa OCRmyPDF e Tesseract per usare --ocr."
        )

        return False

    temporaneo = pdf.with_name(
        pdf.stem + "_ocr_temporaneo.pdf"
    )

    temporaneo.unlink(missing_ok=True)

    cmd = [

        programma,
        "--skip-text",
        "--optimize", "0",
        "--output-type", "pdf",
        "--language", lingua,

        str(pdf),
        str(temporaneo),
    ]

    print(f"Avvio OCR: lingue {lingua} ...")

    try:

        risultato = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=7200,
            check=False,
        )

        if (
            risultato.returncode != 0
            or not temporaneo.is_file()
            or temporaneo.stat().st_size == 0
        ):

            print(
                "OCR non riuscito; il PDF originale senza OCR "
                "è stato conservato."
            )

            if risultato.stderr:
                print(risultato.stderr[-3000:])

            temporaneo.unlink(missing_ok=True)

            return False

        temporaneo.replace(pdf)

        print(
            "OCR completato: aggiunto il livello di testo selezionabile."
        )

        return True

    except Exception as e:

        print(f"Errore durante OCR: {e}")

        temporaneo.unlink(missing_ok=True)

        return False


# ============================================================
# CACHE
# ============================================================

def firma_pagina(contenuto_html, asset):

    h = hashlib.sha256(
        contenuto_html.encode(
            "utf-8",
            errors="replace",
        )
    )

    for nome in asset:

        p = Path(nome)

        h.update(
            str(p).encode(
                "utf-8",
                errors="replace",
            )
        )

        try:

            with p.open("rb") as f:

                for blocco in iter(
                    lambda: f.read(1024 * 1024),
                    b"",
                ):

                    h.update(blocco)

        except OSError:

            h.update(b"<asset-non-legibile>")

    return h.hexdigest()


def identita_script():

    percorso = Path(__file__).resolve()

    try:

        digest = hashlib.sha256(
            percorso.read_bytes()
        ).hexdigest()

    except OSError:

        digest = "non-disponibile"

    return str(percorso), digest


# ============================================================
# PAGINE VUOTE
# ============================================================

def pagina_sorgente_vuota(html):

    if re.search(
        r'<img\b[^>]*class=["\'][^"\']*resource-layer',
        html,
        re.I,
    ):
        return False

    if re.search(
        r"<(?:canvas|video|iframe)\b",
        html,
        re.I,
    ):
        return False

    svgs = re.findall(
        r"<svg\b[^>]*>([\s\S]*?)</svg\s*>",
        html,
        re.I,
    )

    for svg in svgs:

        grafica = re.sub(
            r"<defs\b[\s\S]*?</defs\s*>",
            "",
            svg,
            flags=re.I,
        )

        grafica = re.sub(
            r"<!--[\s\S]*?-->",
            "",
            grafica,
        )

        if re.search(
            r"<(?:image|path|rect|text|polygon|use|"
            r"circle|ellipse|line|polyline|g)\b",
            grafica,
            re.I,
        ):
            return False

    if svgs:
        return True

    corpo = re.search(
        r"<body\b[^>]*>(.*?)</body\s*>",
        html,
        re.I | re.S,
    )

    if not corpo:
        return True

    contenuto = re.sub(
        r"<script\b[\s\S]*?</script\s*>",
        "",
        corpo.group(1),
        flags=re.I,
    )

    contenuto = re.sub(
        r"<style\b[\s\S]*?</style\s*>",
        "",
        contenuto,
        flags=re.I,
    )

    contenuto = re.sub(
        r"<[^>]+>",
        "",
        contenuto,
    )

    return not contenuto.strip()


# ============================================================
# NUMERAZIONE CON LETTERE
# ============================================================

def chiedi_sezioni_letterate(numero_pagine, copertine=0):

    sezioni = []

    print()
    print("=" * 65)
    print("NUMERAZIONE DELLE PAGINE CON LETTERE")
    print("=" * 65)

    print(
        "Il libro contiene pagine numerate con una lettera, "
        "ad esempio C213, A98, B125?"
    )

    while True:

        risposta = input("Sono presenti? [s/N]: ").strip().lower()

        if risposta in ("s", "si", "sì"):
            break

        if risposta in ("", "n", "no"):
            return sezioni

        print("Rispondi S oppure N.")

    precedente = copertine

    while True:

        print()
        print("Inserimento di una nuova sezione.")

        print(
            f"Il PDF contiene {numero_pagine} pagine."
        )

        print(
            f"Le prime {copertine} sono copertine."
        )

        while True:

            try:

                pagina = int(input(
                    "Da quale pagina del PDF inizia questa sezione? "
                ).strip())

                if pagina <= copertine:
                    print(
                        "La sezione deve iniziare dopo le copertine."
                    )
                    continue

                if pagina < 1 or pagina > numero_pagine:
                    print(
                        f"Inserisci un numero da 1 a {numero_pagine}."
                    )
                    continue

                if pagina <= precedente:
                    print(
                        "La nuova sezione deve iniziare dopo "
                        "quella precedente."
                    )
                    continue

                break

            except ValueError:
                print("Inserisci un numero intero valido.")

        while True:

            lettera = input(
                "Qual è la lettera della numerazione? (es. C): "
            ).strip()

            if re.fullmatch(r"[A-Za-z]+", lettera):
                lettera = lettera.upper()
                break

            print("Inserisci una o più lettere, senza numeri.")

        while True:

            try:

                numero = int(input(
                    "Da quale numero inizia? (es. 213): "
                ).strip())

                if numero < 1:
                    print("Il numero deve essere maggiore di zero.")
                    continue

                break

            except ValueError:
                print("Inserisci un numero intero valido.")

        sezioni.append({
            "pagina": pagina,
            "lettera": lettera,
            "numero": numero,
        })

        precedente = pagina

        print(
            f"Sezione aggiunta: pagina PDF {pagina} "
            f"→ {lettera}{numero}"
        )

        while True:

            altra = input(
                "Vuoi aggiungere un'altra sezione? [s/N]: "
            ).strip().lower()

            if altra in ("s", "si", "sì"):
                break

            if altra in ("", "n", "no"):
                print()
                print("Numerazione personalizzata configurata:")
                for s in sezioni:
                    print(
                        f"  Pagina PDF {s['pagina']} "
                        f"→ {s['lettera']}{s['numero']}"
                    )
                return sezioni

            print("Rispondi S oppure N.")

# ============================================================
# PROGRAMMA PRINCIPALE
# ============================================================

def main():

    percorso_script, hash_script = identita_script()

    ap = argparse.ArgumentParser(
        description="Converte le pagine HTML locali in PDF.",
        formatter_class=argparse.RawTextHelpFormatter,
    )

    ap.add_argument(
        "--version",
        action="version",
        version=(
            f"crea_pdf.py {VERSIONE_SCRIPT}\n"
            f"BUILD {BUILD_ID}\n"
            f"FILE {percorso_script}\n"
            f"SHA256 {hash_script}"
        ),
    )

    ap.add_argument(
        "cartella",
        nargs="?",
        default="downloaded_pages",
        help="cartella con le pagine N/composite.html",
    )

    ap.add_argument(
        "-o", "--output",
        default="libro.pdf",
        help="PDF di uscita",
    )

    ap.add_argument(
        "-j", "--jobs",
        type=int,
        default=2,
        help="pagine convertite in parallelo",
    )

    ap.add_argument(
        "--browser",
        help="percorso/comando di Chromium o Chrome",
    )

    ap.add_argument(
        "--da",
        type=int,
        help="prima pagina da convertire",
    )

    ap.add_argument(
        "--a",
        type=int,
        help="ultima pagina da convertire",
    )

    ap.add_argument(
        "--tieni-temp",
        action="store_true",
        help="non cancellare i file temporanei",
    )

    # NUOVE OPZIONI

    ap.add_argument(
        "--copertine",
        type=int,
        default=None,
        help="numero di pagine iniziali da etichettare come copertine",
    )

    ap.add_argument(
        "--ocr",
        action="store_true",
        help="aggiunge un livello OCR per selezionare e cercare il testo",
    )

    ap.add_argument(
        "--lingua-ocr",
        default="eng+ita",
        help="lingue OCR: eng, ita oppure eng+ita",
    )

    args = ap.parse_args()

    # Se non viene indicato --copertine, chiede il numero all'utente.

    if args.copertine is None:

        try:

            risposta = input(
                "\nQuante pagine iniziali sono copertine "
                "da escludere dalla numerazione? [0]: "
            ).strip()

            args.copertine = int(risposta) if risposta else 0

        except (ValueError, EOFError):

            ap.error("Numero di copertine non valido.")

    if args.copertine < 0:
        ap.error("--copertine non può essere negativo")

    if args.jobs < 1:
        ap.error("-j/--jobs deve essere almeno 1")

    if (
        args.da is not None
        and args.a is not None
        and args.da > args.a
    ):
        ap.error("--da non può essere maggiore di --a")

    # --------------------------------------------------------
    # IDENTIFICAZIONE
    # --------------------------------------------------------

    print()
    print("=" * 65)

    print(
        f"CREA_PDF VERSIONE {VERSIONE_SCRIPT}"
    )

    print(
        f"BUILD {BUILD_ID}"
    )

    print(
        f"Script eseguito: {percorso_script}"
    )

    print(
        f"Impronta SHA256: {hash_script}"
    )

    print("=" * 65)

    # --------------------------------------------------------
    # CARTELLA E BROWSER
    # --------------------------------------------------------

    radice = Path(args.cartella).resolve()

    if not radice.is_dir():
        sys.exit(f"Cartella non trovata: {radice}")

    try:
        browser = trova_browser(args.browser)
        verifica_browser(browser)
    except (FileNotFoundError, PermissionError, ValueError) as errore:
        sys.exit(
            f"Errore configurazione browser: {errore}\n"
            'Esempio: --browser "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe"'
        )

    # --------------------------------------------------------
    # PAGINE
    # --------------------------------------------------------

    pagine = elenco_pagine(
        radice,
        args.da,
        args.a,
    )

    if not pagine:
        sys.exit(f"Nessuna pagina N/composite.html trovata in {radice}")

    numeri = [n for n, _ in pagine]

    inizio = args.da if args.da is not None else numeri[0]
    fine = args.a if args.a is not None else numeri[-1]

    mancanti_pagine = sorted(
        set(range(inizio, fine + 1)) - set(numeri)
    )

    if mancanti_pagine:
        print(f"Attenzione: pagine HTML mancanti: {mancanti_pagine}")

    if args.copertine > len(pagine):

        sys.exit(
            f"Hai indicato {args.copertine} copertine, "
            f"ma le pagine disponibili sono {len(pagine)}."
        )
        
        
    # --------------------------------------------------------
    # NUMERAZIONE CON LETTERE
    # --------------------------------------------------------

    sezioni_letterate = chiedi_sezioni_letterate(
        len(pagine),
        args.copertine,
    )
    
    # --------------------------------------------------------
    # CACHE
    # --------------------------------------------------------

    temp = radice / "_pdf_tmp"

    marker = temp / ".crea_pdf_version"

    identita_cache = (
        f"{SCHEMA_CACHE}\n"
        f"{BUILD_ID}\n"
        f"{hash_script}\n"
    )

    if temp.exists() and (
        not marker.is_file()
        or marker.read_text(
            encoding="utf-8",
            errors="ignore",
        ) != identita_cache
    ):

        print(
            "Cache temporanea di un'altra versione/build: "
            "la ricreo da zero."
        )

        shutil.rmtree(
            temp,
            ignore_errors=True,
        )

    temp.mkdir(exist_ok=True)

    marker.write_text(
        identita_cache,
        encoding="utf-8",
    )

    browser = con_permessi(browser, radice)

    # --------------------------------------------------------
    # PROFILI BROWSER
    # --------------------------------------------------------

    profili = queue.Queue()

    for i in range(args.jobs):

        profilo = temp / f"profilo_{i}"

        profilo.mkdir(exist_ok=True)

        profili.put(profilo)

    print(f"Browser: {' '.join(browser)}")

    print(
        f"Pagine HTML da convertire: "
        f"{len(pagine)} ({numeri[0]}–{numeri[-1]})"
    )

    print(
        "Correzione attiva: priorità ai livelli SVG con clipPath."
    )

    print(
        "Copie HTML duplicate rimosse tramite SHA256."
    )

    print(
        "Dipendenze: nessuna Pillow richiesta."
    )

    print(
        f"Copertine da non numerare nel contenuto: {args.copertine}"
    )

    print(
        f"OCR richiesto: {'sì' if args.ocr else 'no'}"
    )

    # --------------------------------------------------------
    # PAGINE VUOTE
    # --------------------------------------------------------

    pagine_vuote = []

    for n, sorgente in pagine:

        try:

            contenuto = sorgente.read_text(
                encoding="utf-8",
                errors="replace",
            )

            if pagina_sorgente_vuota(contenuto):
                pagine_vuote.append(n)

        except OSError:
            pass

    if pagine_vuote:

        print(
            "Attenzione: pagine HTML sorgente vuote "
            f"(saranno mantenute): {pagine_vuote}"
        )

    # --------------------------------------------------------
    # CONVERSIONE SINGOLA PAGINA
    # --------------------------------------------------------

    falliti = []
    asset_mancanti = {}
    asset_rimossi = {}

    fatti = 0

    def lavora(n, sorgente):

        pdf = temp / f"{n:05d}.pdf"

        firma_file = temp / f"{n:05d}.sha256"

        html = sorgente.read_text(
            encoding="utf-8",
            errors="replace",
        )

        w, h = dimensioni(html)

        (
            html,
            mancanti_asset,
            asset,
            rimossi_asset,
        ) = html_per_stampa(
            html,
            w,
            h,
            sorgente.parent,
        )

        firma = firma_pagina(
            html,
            asset,
        )

        # Riutilizza soltanto PDF prodotti con gli stessi contenuti.

        if (
            pdf.is_file()
            and firma_file.is_file()
            and firma_file.read_text(
                encoding="ascii",
                errors="ignore",
            ).strip() == firma
        ):

            if conta_pagine_pdf(pdf) in (None, 1):

                return (
                    n,
                    True,
                    "",
                    mancanti_asset,
                    rimossi_asset,
                )

        stampa_html = temp / f"{n:05d}.html"

        stampa_html.write_text(
            html,
            encoding="utf-8",
        )

        profilo = profili.get()

        try:

            ok, errore = stampa_pdf(
                browser,
                stampa_html,
                pdf,
                profilo,
            )

            if not ok and not errore.startswith("Impossibile avviare il browser:"):

                ok, errore = stampa_pdf(
                    browser,
                    stampa_html,
                    pdf,
                    profilo,
                )

            if ok:

                firma_file.write_text(
                    firma,
                    encoding="ascii",
                )

        finally:

            profili.put(profilo)

        if ok:
            stampa_html.unlink(missing_ok=True)

        return (
            n,
            ok,
            errore,
            mancanti_asset,
            rimossi_asset,
        )

    # --------------------------------------------------------
    # CONVERSIONE PARALLELA
    # --------------------------------------------------------

    with ThreadPoolExecutor(
        max_workers=args.jobs
    ) as ex:

        futuri = [
            ex.submit(lavora, n, s)
            for n, s in pagine
        ]

        for f in as_completed(futuri):

            try:

                (
                    n,
                    ok,
                    errore,
                    missing,
                    removed,
                ) = f.result()

            except Exception as e:

                falliti.append((-1, str(e)))

                fatti += 1

                print(
                    f"\r  {fatti}/{len(pagine)}",
                    end="",
                    flush=True,
                )

                continue

            fatti += 1

            if not ok:
                falliti.append((n, errore))

            if missing:
                asset_mancanti[n] = missing

            if removed:
                asset_rimossi[n] = removed

            print(
                f"\r  {fatti}/{len(pagine)}",
                end="",
                flush=True,
            )

    print()

    # --------------------------------------------------------
    # RIEPILOGO ASSET MANCANTI
    # --------------------------------------------------------

    if asset_mancanti:

        print(
            "Attenzione: alcuni riferimenti immagine "
            "non hanno il file corrispondente:"
        )

        for n, refs in sorted(asset_mancanti.items()):

            print(
                f"  pagina {n}: "
                + ", ".join(refs[:8])
                + (" ..." if len(refs) > 8 else "")
            )

    # --------------------------------------------------------
    # RIEPILOGO COPIE DUPLICATE
    # --------------------------------------------------------

    if asset_rimossi:

        copie_html = 0

        for refs in asset_rimossi.values():

            for voce in refs:

                m = re.search(
                    r"(\d+) copie HTML",
                    voce,
                )

                if m:
                    copie_html += int(m.group(1))

        print(
            f"Livelli duplicati rimossi dal solo HTML: {copie_html}"
        )

        print(
            "Le versioni SVG con clipPath sono state conservate."
        )

        for n, refs in sorted(asset_rimossi.items()):

            descrizioni = [
                x for x in refs
                if (
                    "riferimento SVG locale assente" in x
                    or "ATTENZIONE" in x
                )
            ]

            if descrizioni:

                print(
                    f"  pagina {n}: "
                    + "; ".join(descrizioni[:6])
                )

    # --------------------------------------------------------
    # ERRORI
    # --------------------------------------------------------

    if falliti:

        print("Pagine non convertite:")

        for n, errore in sorted(
            falliti,
            key=lambda x: x[0],
        ):

            prefisso = (
                f"pagina {n}"
                if n > 0
                else "errore"
            )

            print(f"  {prefisso}: {errore}")

        print(
            "I temporanei sono stati conservati. "
            "Correggi l'errore e rilancia."
        )

        sys.exit(1)

    # --------------------------------------------------------
    # UNIONE
    # --------------------------------------------------------

    pdfs = [
        temp / f"{n:05d}.pdf"
        for n, _ in pagine
    ]

    uscita = Path(args.output).resolve()

    uscita.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    print(
        f"Unisco {len(pdfs)} pagine in {uscita} ..."
    )

    if not unisci(
        pdfs,
        uscita,
        args.copertine,
        sezioni_letterate,
    ):
        sys.exit(
            "Unione non riuscita. "
            f"Le pagine singole sono in {temp}"
        )
    # --------------------------------------------------------
    # OCR FACOLTATIVO
    # --------------------------------------------------------

    # La creazione del PDF tramite Chromium è già terminata.
    # L'OCR è una fase successiva e non modifica la pipeline originale.

    if args.ocr:

        if not aggiungi_ocr(
            uscita,
            args.lingua_ocr,
        ):

            sys.exit(
                "OCR non completato. "
                "Il PDF originale senza OCR è stato conservato."
            )

    # --------------------------------------------------------
    # VERIFICA FINALE
    # --------------------------------------------------------

    numero_finale = conta_pagine_pdf(uscita)

    if (
        numero_finale is not None
        and numero_finale != len(pagine)
    ):

        sys.exit(
            f"Verifica finale non superata: "
            f"il PDF contiene {numero_finale} pagine, "
            f"ma erano attese {len(pagine)}. "
            f"I temporanei sono in {temp}."
        )

    # --------------------------------------------------------
    # PULIZIA
    # --------------------------------------------------------

    if not args.tieni_temp:

        shutil.rmtree(
            temp,
            ignore_errors=True,
        )

    # --------------------------------------------------------
    # RISULTATO
    # --------------------------------------------------------

    print()
    print("=" * 65)

    print("CONVERSIONE COMPLETATA")

    print(f"File: {uscita}")

    print(
        f"Dimensione: "
        f"{uscita.stat().st_size / 1_048_576:.1f} MB"
    )

    print(
        f"Pagine: {numero_finale or len(pagine)}"
    )

    print(
        f"Copertine escluse dalla numerazione: {args.copertine}"
    )

    print(
        f"Sezioni con lettere: {len(sezioni_letterate)}"
    )

    for s in sezioni_letterate:

        print(
            f"  Pagina PDF {s['pagina']} "
            f"→ {s['lettera']}{s['numero']}"
        )

    print(
        f"OCR: {'attivo' if args.ocr else 'non richiesto'}"
    )

    print(
        f"Versione: {VERSIONE_SCRIPT}"
    )

    print(
        f"Build: {BUILD_ID}"
    )

    print(
        f"SHA256: {hash_script}"
    )

    print("=" * 65)


if __name__ == "__main__":
    main()