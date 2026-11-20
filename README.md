# Sanoma My Place eBook Ripper – PDF Edition

Questa repository deriva dal progetto originale [Sanoma_My_Place_eBook_Ripper](https://github.com/Tecnologica-Mente/Sanoma_My_Place_eBook_Ripper), sviluppato da Tecnologica-Mente, premetto che è stato creato con AI.

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