#!/usr/bin/env bash
# One-time: bash regress-bootstrap.sh dev|prod — asks for the root login and sets up the regression stand.
set -euo pipefail
env="${1:?dev or prod}"
read -r -p "Root email ($env): " LUCKY_ROOT_EMAIL
read -r -s -p "Root password ($env): " LUCKY_ROOT_PASSWORD; echo
export LUCKY_ROOT_EMAIL LUCKY_ROOT_PASSWORD
node "$(dirname "$0")/regress-bootstrap.mjs" "$env"
