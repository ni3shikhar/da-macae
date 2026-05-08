#!/bin/sh
set -e
# Read the container's DNS resolver so nginx can resolve upstream hosts at request time
DNS_RESOLVER=$(grep -m1 '^nameserver' /etc/resolv.conf | awk '{print $2}')
export DNS_RESOLVER="${DNS_RESOLVER:-127.0.0.11}"
# Substitute only our two variables — leave nginx variables ($host, $uri, etc.) untouched
envsubst '${BACKEND_URL} ${DNS_RESOLVER}' < /etc/nginx/nginx.conf.template > /etc/nginx/conf.d/default.conf
exec "$@"
