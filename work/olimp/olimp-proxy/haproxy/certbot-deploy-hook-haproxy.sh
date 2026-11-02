#!/bin/sh
# certbot deploy-hook: склеить fullchain+privkey в cert.cer для haproxy и перечитать конфиг
set -e
cat "$RENEWED_LINEAGE/fullchain.pem" "$RENEWED_LINEAGE/privkey.pem" > /etc/haproxy/ssl/cert.cer.new
chmod 600 /etc/haproxy/ssl/cert.cer.new
mv /etc/haproxy/ssl/cert.cer.new /etc/haproxy/ssl/cert.cer
systemctl reload haproxy
