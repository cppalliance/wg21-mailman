#!/usr/bin/env bash
# Create Mailman lists and bulk HyperKitty archive data for local UI work.
set -euo pipefail

cd "$(dirname "$0")"

DOMAIN="${MAILMAN_DOMAIN:-lists.example.com}"
LIST_PARTS="${SEED_LISTS:-delegates,paper-reviews,general,dev,announce,cpp,boost,test}"
THREADS="${SEED_THREADS:-12}"
REPLIES="${SEED_REPLIES:-5}"

echo "==> Creating mailing lists in Mailman core"
# `mailman create` registers the list's domain by default (-d/--domain); no
# separate domain step is needed. (mailman shell has no -c; use -r for scripts.)
IFS=',' read -ra PARTS <<< "${LIST_PARTS}"
for part in "${PARTS[@]}"; do
  part="$(echo "$part" | xargs)"
  fqdn="${part}@${DOMAIN}"
  # Capture combined output so we can distinguish "already exists" (benign,
  # idempotent re-run) from real failures (broken domain, permissions, etc).
  if create_output="$(docker compose exec -T mailman-core mailman --run-as-root create -q "${fqdn}" 2>&1)"; then
    echo "  created ${fqdn}"
  elif [[ "${create_output}" == *"already exists"* ]]; then
    echo "  exists  ${fqdn}"
  else
    echo "  FAILED  ${fqdn}:" >&2
    echo "${create_output}" >&2
    exit 1
  fi
done

echo "==> Seeding HyperKitty archives (${THREADS} threads x ${REPLIES} msgs per list)"
docker compose exec -T mailman-web sh -c "cd /opt/mailman-web && PYTHONPATH=/opt/mailman-web python /opt/wg21-scripts/seed_dev_data.py \
  --domain '${DOMAIN}' \
  --lists '${LIST_PARTS}' \
  --threads '${THREADS}' \
  --replies '${REPLIES}'"

echo "==> Syncing list metadata from Mailman"
docker compose exec -T mailman-web python manage.py mailman_sync

echo "==> Updating search index"
docker compose exec -T mailman-web python manage.py update_index --remove -v 0

echo ""
echo "Ready:"
echo "  Postorius:  http://localhost:8300/mailman3/lists/"
echo "  HyperKitty: http://localhost:8300/archives/"
