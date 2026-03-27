#!/usr/bin/env bash
# deploy.sh — create the D1 database if it doesn't exist, then deploy the Worker.
set -euo pipefail

cd "$(dirname "$0")"

# ── 1. Resolve database ID ────────────────────────────────────────────────────
if [ -n "${D1_DATABASE_ID:-}" ]; then
  DB_ID="$D1_DATABASE_ID"
  echo "Using D1_DATABASE_ID from environment: $DB_ID"
else
  echo "D1_DATABASE_ID not set — looking up or creating 'kalaos-db' …"

  # Try to find an existing database by name.
  LIST_STDERR=$(mktemp)
  LIST_JSON=$(npx wrangler d1 list --json 2>"$LIST_STDERR" || true)
  if [ -s "$LIST_STDERR" ]; then
    echo "Warning: wrangler d1 list produced errors:" >&2
    cat "$LIST_STDERR" >&2
  fi
  rm -f "$LIST_STDERR"

  DB_ID=$(node -e "
    try {
      const dbs = JSON.parse(process.argv[1]);
      const db = dbs.find(d => d.name === 'kalaos-db');
      process.stdout.write(db ? (db.uuid || db.id || '') : '');
    } catch (e) {
      process.stderr.write('Warning: could not parse d1 list output: ' + e.message + '\n');
      process.stdout.write('');
    }
  " "$LIST_JSON")

  if [ -z "$DB_ID" ]; then
    echo "Database not found — creating …"
    CREATE_STDERR=$(mktemp)
    CREATE_JSON=$(npx wrangler d1 create kalaos-db --json 2>"$CREATE_STDERR" || true)
    if [ -s "$CREATE_STDERR" ]; then
      echo "Warning: wrangler d1 create produced errors:" >&2
      cat "$CREATE_STDERR" >&2
    fi
    rm -f "$CREATE_STDERR"

    DB_ID=$(node -e "
      try {
        const d = JSON.parse(process.argv[1]);
        process.stdout.write(d.uuid || d.id || '');
      } catch (e) {
        process.stderr.write('Warning: could not parse d1 create output: ' + e.message + '\n');
        process.stdout.write('');
      }
    " "$CREATE_JSON")
  fi

  if [ -z "$DB_ID" ]; then
    echo "ERROR: Could not find or create the D1 database 'kalaos-db'." >&2
    echo "Set the D1_DATABASE_ID environment variable and retry." >&2
    exit 1
  fi
fi

# ── 2. Export so Wrangler picks it up via \${D1_DATABASE_ID} substitution ─────
export D1_DATABASE_ID="$DB_ID"
echo "Deploying with database_id: $DB_ID"

# ── 3. Deploy ─────────────────────────────────────────────────────────────────
npx wrangler deploy
