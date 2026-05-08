#!/bin/sh
set -e
# Substitute only ${BACKEND_URL} — leave all nginx variables ($host, $uri, etc.) untouched
envsubst '${BACKEND_URL}' < /etc/nginx/nginx.conf.template > /etc/nginx/conf.d/default.conf
exec "$@"
