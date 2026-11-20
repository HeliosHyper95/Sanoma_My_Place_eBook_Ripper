#!/usr/bin/env bash
# Avvio su Linux/Ubuntu: sostituisce XAMPP con il server integrato di PHP.
# Uso: copia questo file nella cartella del progetto (dove c'è index.php) ed eseguilo.
#   chmod +x avvia.sh && ./avvia.sh
set -euo pipefail

cd "$(dirname "$(readlink -f "$0")")"

PORTA="${1:-8000}"

# Dipendenze: php-cli e l'estensione curl
if ! command -v php >/dev/null 2>&1 || ! php -m | grep -qi '^curl$'; then
    echo "Installo php-cli e php-curl (serve sudo)..."
    sudo apt update
    sudo apt install -y php-cli php-curl
fi

# La cartella deve essere scrivibile: lo script crea "downloaded_pages"
if [ ! -w . ]; then
    echo "Errore: la cartella $(pwd) non è scrivibile." >&2
    exit 1
fi

echo "PHP $(php -r 'echo PHP_VERSION;')"
echo "Apri nel browser: http://localhost:${PORTA}/"
echo "Ctrl+C per fermare il server."

# Con PHP >= 8.2 utf8_decode() è deprecata: nascondo gli avvisi per non sporcare l'output
exec php -d error_reporting='E_ALL & ~E_DEPRECATED' -d display_errors=1 \
    -S "localhost:${PORTA}" -t .
