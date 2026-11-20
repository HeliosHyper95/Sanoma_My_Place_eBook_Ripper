# Changelog

All notable changes to this project are documented in this file.

This repository is derived from [Sanoma_My_Place_eBook_Ripper](https://github.com/Tecnologica-Mente/Sanoma_My_Place_eBook_Ripper). Changes specific to this edition are listed separately from the original project's release history.

## [4.2.1] - 2026-11-18

### Added
- Automatic detection of Google Chrome and Chromium in standard Windows installation locations.
- Support for Microsoft Edge as a Chromium-based browser.
- Explicit browser selection through the `--browser` option, including executable paths containing spaces.
- A version/build identification command through `--version`.

### Improved
- Browser availability is checked before starting the PDF conversion.
- Browser startup errors are handled more clearly.
- Windows browser detection is supported while retaining Linux and Flatpak compatibility.
- PDF conversion supports parallel processing and temporary caching.
- PDF page labels support cover-page exclusion and custom section numbering.
- Optional OCR can add a searchable and selectable text layer to the generated PDF.

### Fixed
- Improved handling of browser executable paths and command aliases on Windows.
- Improved validation when the selected browser cannot be found or started.

## [4.2.0] - 2026-11-18

### Added
- Python-based conversion of downloaded HTML pages into a PDF document.
- SVG rendering support, including SVG `clipPath` elements.
- SHA256-based duplicate detection between HTML and SVG resources.
- Preservation of blank source pages.
- Optional OCR integration through OCRmyPDF and Tesseract.
- Configurable OCR languages through `--lingua-ocr`.
- Custom PDF page labels, including exclusion of initial cover pages from content numbering.
- Section-based page numbering with letter prefixes.
- Temporary conversion cache and the `--tieni-temp` option.

### Improved
- Parallel conversion of HTML pages.
- PDF output handling and page layout preservation.
- Conversion workflow for downloaded books.

## Fork-specific downloader changes

The following improvements were made to `download.php` in this repository:

- Stream download progress to the browser instead of waiting for the entire process to finish.
- Skip pages that have already been downloaded.
- Retry SVG downloads up to three times when the response is empty or unavailable.
- Flush progress output after each completed page.
- Generate the HTML index using the requested final page number.

## [1.0.0] - 2025-07-30

Initial release of the original project.

### Added
- Download HTML files for eBook pages.
- Bottom navigation menu for moving between pages.
- Page zoom controls.
- Italian-language interface.
