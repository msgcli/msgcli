#!/bin/bash
set -e

# install.sh — Quick installer for msgcli
# Usage: curl -fsSL https://msgcli.org/install.sh | bash

REPO="${MSGCLI_REPO:-https://github.com/msgcli/msgcli}"
PYTHON_MIN="3.9"

RED='\033[31m'
GREEN='\033[32m'
RESET='\033[0m'

check_python() {
    if ! command -v python3 &>/dev/null; then
        echo -e "${RED}Error: python3 is not installed${RESET}" >&2
        exit 1
    fi

    if ! python3 -c "import sys; assert sys.version_info >= (3, 9)" 2>/dev/null; then
        pyver=$(python3 -c 'import sys; print(".".join(map(str, sys.version_info[:2])))')
        echo -e "${RED}Error: Python >= ${PYTHON_MIN} is required (found ${pyver})${RESET}" >&2
        exit 1
    fi
}

check_pip() {
    if ! command -v pip3 &>/dev/null; then
        echo -e "${RED}Error: pip3 is not installed${RESET}" >&2
        exit 1
    fi
}

install() {
    check_python
    check_pip

    echo "Installing msgcli..."
    pip3 install --upgrade --user "git+${REPO}.git"
    pip3 install --upgrade --user cryptography

    echo ""
    echo -e "${GREEN}msgcli installed successfully!${RESET}"
    echo ""
    echo "Quick start:"
    echo "  msg <username>    # Hybrid mode (server + client)"
    echo "  msg user@host     # Client connect and chat"
    echo "  msg --server      # Server mode"
    echo "For more details, visit https://msgcli.org"
}

install
