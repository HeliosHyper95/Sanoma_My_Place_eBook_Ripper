# Sanoma My Place eBook Ripper – PDF Edition

Questa repository deriva dal progetto originale [Sanoma_My_Place_eBook_Ripper](https://github.com/Tecnologica-Mente/Sanoma_My_Place_eBook_Ripper), sviluppato da Tecnologica-Mente, premetto che è stata creata con AI.

La variante documentata in questa repository mantiene il sistema originale di download delle pagine HTML e introduce modifiche al downloader, uno script Python per la conversione in PDF e funzionalità aggiuntive per la gestione delle pagine, della numerazione e del riconoscimento del testo.

## Indice

- [Descrizione](#descrizione)
- [Differenze rispetto al progetto originale](#differenze-rispetto-al-progetto-originale)
- [Struttura dei file](#struttura-dei-file)
- [Requisiti](#requisiti)
- [Fase 1 – Download delle pagine HTML](#fase-1--download-delle-pagine-html)
- [Fase 2 – Conversione in PDF](#fase-2--conversione-in-pdf)
- [Numerazione personalizzata](#numerazione-personalizzata)
- [OCR e testo selezionabile](#ocr-e-testo-selezionabile)
- [Opzioni disponibili](#opzioni-disponibili)
- [Risoluzione dei problemi](#risoluzione-dei-problemi)
- [Note e responsabilità](#note-e-responsabilità)
- [Crediti e licenza](#crediti-e-licenza)

---

## Descrizione

Il progetto consente di scaricare localmente le pagine di un libro disponibile sulla piattaforma Sanoma My Place e di visualizzarle successivamente senza dover utilizzare il Book Viewer online.

Il procedimento è diviso in due fasi indipendenti:

1. **Download:** il programma PHP scarica le pagine del libro e le relative risorse, generando pagine HTML consultabili localmente.
2. **Conversione:** lo script Python `crea_pdf.py` elabora le pagine HTML scaricate e genera un documento PDF.

La conversione in PDF è facoltativa: è possibile continuare a utilizzare il downloader originale e consultare le pagine tramite il file `index.html`.

## Differenze rispetto al progetto originale

Questa variante mantiene la struttura e il funzionamento generale del progetto originale, introducendo le seguenti modifiche.

### Modifiche al downloader PHP

Il file `download.php` è stato modificato per:

- Mostrare progressivamente l'avanzamento del download nel browser.
- Evitare di scaricare nuovamente le pagine già presenti sul disco.
- Effettuare fino a tre tentativi aggiuntivi quando il contenuto SVG di una pagina risulta vuoto.
- Aggiornare correttamente il numero totale di pagine nell'indice HTML generato.

### Nuovo convertitore PDF

È stato aggiunto `crea_pdf.py`, uno script Python autonomo che:

- Converte le pagine HTML tramite Chrome o Chromium.
- Mantiene i livelli SVG e gestisce gli elementi `clipPath`.
- Rimuove duplicazioni tra risorse HTML e SVG attraverso il confronto SHA256, preservando le versioni SVG necessarie.
- Conserva le pagine sorgente vuote.
- Permette di convertire più pagine contemporaneamente.
- Utilizza una cache temporanea per evitare di ripetere conversioni già completate.
- Permette di escludere le copertine dalla numerazione del documento.
- Supporta etichette PDF personalizzate e numerazioni suddivise in sezioni.
- Offre una fase OCR facoltativa per rendere ricercabile e selezionabile il testo contenuto nelle pagine.

## Struttura dei file

| File | Descrizione |
|---|---|
| `index.php` | Interfaccia web per configurare il download |
| `download.php` | Downloader delle pagine e delle risorse |
| `crea_pdf.py` | Convertitore HTML-PDF |
| `avvia.sh` | Avvio del server PHP integrato su Linux |
| `jquery/` oppure `jquery.zip` | Libreria jQuery |
| `imgs/` oppure `imgs.zip` | Immagini utilizzate dall'interfaccia |

La cartella `downloaded_pages` viene creata durante il download e contiene le pagine del libro.

## Requisiti

### Per il download

- PHP con estensione cURL.
- Un browser moderno.
- Un account Sanoma My Place con accesso al prodotto interessato.
- I dati di connessione e la sessione necessari per effettuare le richieste autorizzate.

Su Windows è possibile utilizzare XAMPP Lite, come indicato nella documentazione del progetto originale.

Su Linux è disponibile `avvia.sh`, che avvia il server PHP integrato e verifica la presenza di PHP CLI e dell'estensione cURL. Su distribuzioni Debian/Ubuntu può installare automaticamente le dipendenze mancanti, richiedendo sudo.

### Per la conversione PDF

- Python 3.
- Google Chrome oppure Chromium.
- OCRmyPDF e Tesseract OCR, soltanto se si desidera utilizzare la funzione OCR.

L'OCR è facoltativo: senza `--ocr` è possibile generare il PDF senza installare questi due componenti.

## Fase 1 – Download delle pagine HTML

La procedura di download rimane sostanzialmente quella del progetto originale.

1. Scaricare o clonare la repository ed estrarla in una cartella.
2. Avviare il server PHP.
3. Aprire nel browser l'indirizzo locale del progetto.
4. Accedere a Sanoma My Place e caricare il libro desiderato nel Book Viewer.
5. Aprire gli strumenti per sviluppatori del browser con F12.
6. Individuare nella scheda Network/Rete una richiesta relativa a una risorsa del libro.
7. Recuperare il `Request URL` e le informazioni di sessione necessarie.
8. Inserire nell'interfaccia i dati richiesti:
   - Base URL;
   - Product path;
   - Username;
   - Password;
   - Session Cookie;
   - Pagina iniziale;
   - Pagina finale.
9. Premere **Procedi** e attendere il completamento.

Al termine sarà disponibile la cartella `downloaded_pages`, contenente le pagine HTML e le risorse scaricate.

Per consultare il libro senza conversione è sufficiente aprire `downloaded_pages/index.html`.

## Fase 2 – Conversione in PDF

Lo script Python deve essere eseguito dalla cartella principale della repository.

Il comando più semplice è:

```bash
python3 crea_pdf.py
```

Se non vengono specificate altre opzioni, lo script utilizza la cartella `downloaded_pages` e genera `libro.pdf`.

Per specificare il nome del PDF:

```bash
python3 crea_pdf.py -o libro.pdf
```

Per convertire un intervallo di pagine:

```bash
python3 crea_pdf.py --da 1 --a 100 -o prova.pdf
```

Per utilizzare due processi paralleli:

```bash
python3 crea_pdf.py -j 2 -o libro.pdf
```

La conversione produce un PDF composto dalle pagine HTML selezionate, mantenendo per quanto possibile la struttura grafica originale.

## Numerazione personalizzata

È possibile indicare quante pagine iniziali devono essere considerate copertine.

Per esempio:

```bash
python3 crea_pdf.py -o libro.pdf --copertine 17
```

In questo esempio le prime 17 pagine vengono conservate nel PDF, ma escluse dalla numerazione del contenuto.

Lo script supporta anche sezioni con numerazione letterata. Durante l'esecuzione è possibile indicare:

- La pagina PDF in cui inizia la sezione.
- La lettera da utilizzare.
- Il numero iniziale della numerazione.

Esempio:

```text
Pagina PDF 18 → A210
Pagina PDF 132 → C150
Pagina PDF 258 → B272
Pagina PDF 352 → D150
```

Le etichette vengono applicate attraverso i Page Labels del PDF, in modo da distinguere la numerazione editoriale da quella fisica delle pagine.

## OCR e testo selezionabile

La funzione OCR permette di aggiungere un livello di testo riconosciuto alle pagine del PDF.

Per utilizzarla occorre installare OCRmyPDF:

```bash
python -m pip install OCRmyPDF
```

È inoltre necessario installare separatamente Tesseract OCR.

Su Windows è possibile utilizzare Winget:

```cmd
winget install -e --id tesseract-ocr.tesseract
```

Dopo l'installazione bisogna verificare che entrambi i programmi siano raggiungibili dal PATH:

```cmd
ocrmypdf --version
tesseract --version
tesseract --list-langs
```

Per il riconoscimento in italiano deve essere disponibile la lingua `ita`.

Esempio di conversione con OCR:

```bash
python3 crea_pdf.py -o libro.pdf --copertine 17 --ocr --lingua-ocr ita
```

Per il riconoscimento combinato italiano e inglese:

```bash
python3 crea_pdf.py -o libro.pdf --ocr --lingua-ocr eng+ita
```

**Nota Windows:** installare OCRmyPDF con pip non significa necessariamente che il comando `ocrmypdf` sia già presente nel PATH. La cartella `Scripts` dell'installazione Python deve essere raggiungibile da Windows. Anche la cartella di installazione di Tesseract deve essere presente nel PATH.

Se OCRmyPDF o Tesseract non sono disponibili, la fase OCR non viene completata. Il PDF originale senza OCR viene conservato.

## Opzioni disponibili

| Opzione | Funzione |
|---|---|
| `--version` | Mostra versione, build e impronta SHA256 |
| `-o`, `--output` | Specifica il PDF di uscita |
| `-j`, `--jobs` | Numero di conversioni parallele |
| `--browser` | Specifica il percorso o comando del browser |
| `--da` | Prima pagina da convertire |
| `--a` | Ultima pagina da convertire |
| `--copertine` | Numero di copertine iniziali da escludere dalla numerazione |
| `--ocr` | Attiva il riconoscimento OCR |
| `--lingua-ocr` | Specifica le lingue OCR |
| `--tieni-temp` | Conserva i file temporanei e la cache |

Per visualizzare tutte le opzioni:

```bash
python3 crea_pdf.py --help
```

Per verificare la versione installata:

```bash
python3 crea_pdf.py --version
```

## Risoluzione dei problemi

### Chrome o Chromium non trovato

Su Windows lo script cerca automaticamente Chrome nei percorsi di installazione standard.

Se necessario, è possibile indicare manualmente il percorso:

```cmd
python3 crea_pdf.py --browser "C:\Program Files\Google\Chrome\Application\chrome.exe"
```

### OCRmyPDF non trovato

Verificare che il comando sia disponibile:

```cmd
where ocrmypdf
```

Se non viene trovato, controllare la cartella `Scripts` dell'installazione Python e aggiungerla al PATH.

### Tesseract non trovato

Verificare:

```cmd
where tesseract
```

Se necessario, aggiungere al PATH la cartella di installazione, normalmente:

```text
C:\Program Files\Tesseract-OCR
```

### Conservare i file temporanei

Per mantenere i file intermedi in caso di problemi:

```bash
python3 crea_pdf.py -o libro.pdf --tieni-temp
```

La cartella `_pdf_tmp` contiene i PDF delle singole pagine e i dati della cache.

## Note e responsabilità

Il progetto è destinato esclusivamente a scopi di studio e ricerca tecnica.

L'utente è responsabile del rispetto delle condizioni d'uso della piattaforma, dei diritti d'autore e delle leggi applicabili nel proprio Paese.

Le credenziali e i cookie di sessione sono informazioni riservate: non devono essere condivisi, pubblicati o inseriti nei file della repository.

Il progetto non è affiliato, approvato o supportato da Sanoma.

## Crediti e licenza

Il downloader originale è stato sviluppato da [Tecnologica-Mente](https://github.com/Tecnologica-Mente/Sanoma_My_Place_eBook_Ripper).

Questa variante ne mantiene la struttura di base e introduce modifiche al downloader e il convertitore PDF Python.

Il progetto originale è distribuito con licenza MIT. Consultare il file `LICENSE` per i termini e le condizioni di utilizzo e mantenere le attribuzioni previste dalla licenza.

---

ENGLISH 

# Sanoma My Place eBook Ripper – PDF Edition

This repository is a derivative of the original [Sanoma_My_Place_eBook_Ripper](https://github.com/Tecnologica-Mente/Sanoma_My_Place_eBook_Ripper), developed by [Tecnologica-Mente](https://github.com/Tecnologica-Mente). This version was created with AI assistance.

It retains the original HTML page downloader and introduces improvements to the downloader, a Python-based PDF converter, and additional features for page handling, custom page numbering, and text recognition.

## Table of contents

- [Overview](#overview)
- [Differences from the original project](#differences-from-the-original-project)
- [Repository structure](#repository-structure)
- [Requirements](#requirements)
- [Step 1 – Downloading the HTML pages](#step-1--downloading-the-html-pages)
- [Step 2 – Converting the pages to PDF](#step-2--converting-the-pages-to-pdf)
- [Custom page numbering](#custom-page-numbering)
- [OCR and selectable text](#ocr-and-selectable-text)
- [Available options](#available-options)
- [Troubleshooting](#troubleshooting)
- [Notes and disclaimer](#notes-and-disclaimer)
- [Credits and license](#credits-and-license)

---

## Overview

This project allows you to download locally the pages of a book available on the Sanoma My Place platform and view them later without using the online Book Viewer.

The workflow consists of two independent steps:

1. **Download:** the PHP application downloads the book pages and their related resources, saving them as local HTML pages.
2. **Conversion:** the Python script `crea_pdf.py` processes the downloaded HTML pages and creates a PDF document.

PDF conversion is optional. You can still use the original downloader and browse the downloaded pages through the generated `index.html` file.

## Differences from the original project

This version retains the general structure and workflow of the original project, with the following additions and changes.

### PHP downloader improvements

The `download.php` file has been modified to:

- Display download progress progressively in the browser.
- Skip pages that have already been downloaded.
- Retry up to three times when a page's SVG content is empty or unavailable.
- Use the requested final page number when generating the HTML index.

### New PDF converter

The new `crea_pdf.py` script:

- Converts HTML pages using Google Chrome or Chromium.
- Preserves SVG layers and handles SVG `clipPath` elements.
- Removes duplicate content between HTML and SVG resources using SHA256 comparisons, while preserving the SVG versions required for rendering.
- Keeps blank source pages in the output.
- Supports parallel page conversion.
- Uses a temporary cache to avoid repeating completed conversions.
- Allows the initial cover pages to be excluded from the document's page numbering.
- Supports custom PDF page labels and section-based numbering.
- Offers optional OCR to make text in the pages searchable and selectable.

## Repository structure

| File or directory | Description |
|---|---|
| `index.php` | Web interface used to configure the download |
| `download.php` | Downloads book pages and their resources |
| `crea_pdf.py` | Converts the downloaded HTML pages into a PDF |
| `avvia.sh` | Starts PHP's built-in web server on Linux |
| `jquery/` or `jquery.zip` | jQuery library |
| `imgs/` or `imgs.zip` | Images used by the web interface |
| `downloaded_pages/` | Created during download; stores the downloaded pages |

## Requirements

### For downloading

- PHP with the cURL extension enabled.
- A modern web browser.
- A Sanoma My Place account with access to the relevant book.
- The connection and session information required to make authorized requests.

On Windows, you can use XAMPP Lite, as described in the original project's documentation.

On Linux, the included `avvia.sh` script starts PHP's built-in web server and checks for PHP CLI and the cURL extension. On Debian/Ubuntu-based distributions, it can install missing dependencies automatically (sudo access is required).

### For PDF conversion

- Python 3.
- Google Chrome or Chromium.
- OCRmyPDF and Tesseract OCR, only if you want to use the OCR feature.

OCR is optional. You can create PDFs without installing OCRmyPDF or Tesseract by running the converter without the `--ocr` option.

## Step 1 – Downloading the HTML pages

The download procedure is largely the same as in the original project.

1. Clone or download this repository and extract it into a folder.
2. Start the PHP server.
3. Open the project's local address in your browser.
4. Sign in to Sanoma My Place and open the desired book in the Book Viewer.
5. Open the browser developer tools by pressing F12.
6. In the **Network** tab, find a request related to one of the book's resources.
7. Retrieve the required `Request URL` and session information.
8. Enter the requested information in the web interface:
   - Base URL;
   - Product path;
   - Username;
   - Password;
   - Session Cookie;
   - First page;
   - Last page.
9. Click **Proceed** and wait for the download to finish.

When the process is complete, the `downloaded_pages` folder will contain the downloaded HTML pages and their resources.

To browse the downloaded book without converting it, open:

```text
downloaded_pages/index.html
```

### Starting the PHP server on Linux

From the repository directory, make the script executable and run it:

```bash
chmod +x avvia.sh
./avvia.sh
```

By default, the server uses port 8000. You can specify another port:

```bash
./avvia.sh 8080
```

Then open `http://localhost:8000/` (or the port you selected) in your browser. Press Ctrl+C in the terminal to stop the server.

## Step 2 – Converting the pages to PDF

Run the Python script from the repository's main directory.

The simplest command is:

```bash
python3 crea_pdf.py
```

On Windows, you can use `python` instead of `python3`, depending on your Python installation:

```cmd
python crea_pdf.py
```

If no other options are specified, the script uses the `downloaded_pages` folder and creates `libro.pdf`.

To specify the output filename:

```bash
python3 crea_pdf.py -o libro.pdf
```

To convert a range of pages:

```bash
python3 crea_pdf.py --da 1 --a 100 -o sample.pdf
```

To use two parallel conversion workers:

```bash
python3 crea_pdf.py -j 2 -o libro.pdf
```

The resulting PDF contains the selected HTML pages, preserving the original page layout as closely as possible.

## Custom page numbering

You can specify how many initial pages should be treated as covers.

For example:

```bash
python3 crea_pdf.py -o libro.pdf --copertine 17
```

In this example, the first 17 pages are kept in the PDF but excluded from the content page numbering.

The script also supports sections with letter-based numbering. During execution, you can enter:

- The PDF page where the section starts.
- The letter to use.
- The starting number for that section.

Example:

```text
PDF page 18  → A210
PDF page 132 → C150
PDF page 258 → B272
PDF page 352 → D150
```

These labels are stored using the PDF Page Labels feature, keeping editorial page numbering separate from the PDF's physical page positions.

## OCR and selectable text

The optional OCR stage adds a recognized text layer to the PDF pages. This makes scanned or image-based text searchable and selectable.

Install OCRmyPDF with pip:

```bash
python -m pip install ocrmypdf
```

Tesseract OCR must also be installed separately.

On Windows, you can install Tesseract using WinGet:

```cmd
winget install -e --id tesseract-ocr.tesseract
```

After installation, check that both commands are available:

```cmd
ocrmypdf --version
tesseract --version
tesseract --list-langs
```

The Italian language data must be installed if you want to recognize Italian text. Tesseract should list `ita` among the available languages.

Example: convert a book, exclude the first 17 pages from the content numbering, and run OCR in Italian:

```bash
python3 crea_pdf.py -o libro.pdf --copertine 17 --ocr --lingua-ocr ita
```

For combined Italian and English recognition:

```bash
python3 crea_pdf.py -o libro.pdf --ocr --lingua-ocr eng+ita
```

**Windows note:** installing OCRmyPDF with pip does not necessarily make the `ocrmypdf` command available in the Windows PATH. The Python installation's `Scripts` directory must be included in PATH. The Tesseract installation directory must also be included in PATH.

If OCRmyPDF or Tesseract cannot be found, the OCR stage cannot be completed. The PDF created before OCR is retained.

## Available options

| Option | Description |
|---|---|
| `--version` | Displays the script version, build ID, and SHA256 fingerprint |
| `-o`, `--output` | Sets the output PDF filename |
| `-j`, `--jobs` | Sets the number of parallel conversion workers |
| `--browser` | Specifies the browser command or executable path |
| `--da` | First page to convert |
| `--a` | Last page to convert |
| `--copertine` | Number of initial cover pages to exclude from content numbering |
| `--ocr` | Enables OCR |
| `--lingua-ocr` | Sets the OCR language or language combination |
| `--tieni-temp` | Keeps temporary files and the conversion cache |

To display all available options:

```bash
python3 crea_pdf.py --help
```

To check the installed script version:

```bash
python3 crea_pdf.py --version
```

## Troubleshooting

### Chrome or Chromium not found

On Windows, the script automatically checks standard installation locations for Chrome, Chromium, and Microsoft Edge.

If necessary, specify the browser executable manually:

```cmd
python crea_pdf.py --browser "C:\Program Files\Google\Chrome\Application\chrome.exe"
```

### OCRmyPDF not found

Check whether Windows can locate the command:

```cmd
where ocrmypdf
```

If it cannot, check the `Scripts` directory of your Python installation and add it to PATH.

### Tesseract not found

Check:

```cmd
where tesseract
```

If necessary, add the installation directory to PATH. The default location is usually:

```text
C:\Program Files\Tesseract-OCR
```

### Keeping temporary files

To preserve intermediate files for troubleshooting, run:

```bash
python3 crea_pdf.py -o libro.pdf --tieni-temp
```

The `_pdf_tmp` directory contains the individual page PDFs and cache data.

## Notes and disclaimer

This project is intended for personal study and technical research purposes only.

Users are responsible for complying with the platform's terms of use, copyright rules, and all laws applicable in their country.

Usernames, passwords, and session cookies are confidential information. Do not share them, publish them, or commit them to this repository.

This project is not affiliated with, endorsed by, or supported by Sanoma.

## Credits and license

The original downloader was developed by [Tecnologica-Mente](https://github.com/Tecnologica-Mente/Sanoma_My_Place_eBook_Ripper).

This repository retains the original project's basic structure and includes downloader modifications and the Python PDF converter.

The original project is distributed under the MIT License. See the `LICENSE` file for the terms and conditions. Keep the copyright notice and required attributions when redistributing the software.

---
