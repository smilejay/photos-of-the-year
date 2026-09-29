#!/usr/bin/env bash
# Restore only the `photos_of_the_year` database from a mysqldump backup file.
# Skips the `mysql` system database so local privileges/timezone tables stay intact.
#
# Usage:
#   ./restore_db.sh                                      # picks the newest mysql-backup-*.sql in project root
#   ./restore_db.sh path/to/mysql-backup-YYYYMMDD.sql    # restore a specific file
#
# Env overrides:
#   MYSQL_USER (default: from backend/.env DB_USER, else root)
#   MYSQL_PASSWORD (default: from backend/.env DB_PASSWORD)
#   MYSQL_HOST (default: from backend/.env DB_HOST, else 127.0.0.1)
#   TARGET_DB  (default: from backend/.env DB_NAME, else photos_of_the_year)

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

# 从 backend/.env 读取数据库凭据（该文件不提交到仓库）
ENV_FILE="$PROJECT_ROOT/backend/.env"
if [[ -f "$ENV_FILE" ]]; then
    set -a
    # shellcheck disable=SC1090
    source "$ENV_FILE"
    set +a
fi

MYSQL_USER="${MYSQL_USER:-${DB_USER:-root}}"
MYSQL_PASSWORD="${MYSQL_PASSWORD:-${DB_PASSWORD:-}}"
MYSQL_HOST="${MYSQL_HOST:-${DB_HOST:-127.0.0.1}}"
TARGET_DB="${TARGET_DB:-${DB_NAME:-photos_of_the_year}}"

if [[ $# -ge 1 ]]; then
    BACKUP_FILE="$1"
else
    # Filenames follow mysql-backup-YYYYMMDD-HHMMSS.sql, so lexical sort == chronological.
    BACKUP_FILE="$(find "$PROJECT_ROOT" -maxdepth 1 -type f -name 'mysql-backup-*.sql' | sort -r | head -n 1)"
fi

if [[ -z "${BACKUP_FILE:-}" || ! -f "$BACKUP_FILE" ]]; then
    echo "Error: backup file not found." >&2
    echo "Usage: $0 [path/to/mysql-backup-YYYYMMDD-HHMMSS.sql]" >&2
    exit 1
fi

if ! command -v mysql >/dev/null 2>&1; then
    echo "Error: 'mysql' client not found in PATH." >&2
    exit 1
fi

echo "Backup file : $BACKUP_FILE"
echo "Target DB   : $TARGET_DB @ $MYSQL_HOST (user=$MYSQL_USER)"

TMP_SQL="$(mktemp -t restore_db.XXXXXX.sql)"
trap 'rm -f "$TMP_SQL"' EXIT

# mysqldump's tail restores session vars via SET x=@OLD_x. Since we sliced away
# the header that defines those @OLD_* variables, seed them from current session
# values so the tail is a no-op instead of erroring on NULL.
cat > "$TMP_SQL" <<'PREAMBLE'
SET @OLD_CHARACTER_SET_CLIENT=@@CHARACTER_SET_CLIENT;
SET @OLD_CHARACTER_SET_RESULTS=@@CHARACTER_SET_RESULTS;
SET @OLD_COLLATION_CONNECTION=@@COLLATION_CONNECTION;
SET @OLD_TIME_ZONE=@@TIME_ZONE;
SET @OLD_UNIQUE_CHECKS=@@UNIQUE_CHECKS, UNIQUE_CHECKS=0;
SET @OLD_FOREIGN_KEY_CHECKS=@@FOREIGN_KEY_CHECKS, FOREIGN_KEY_CHECKS=0;
SET @OLD_SQL_MODE=@@SQL_MODE, SQL_MODE='NO_AUTO_VALUE_ON_ZERO';
SET @OLD_SQL_NOTES=@@SQL_NOTES;
SET NAMES utf8mb4;
PREAMBLE

# Extract only the section for TARGET_DB. mysqldump marks each database with:
#   -- Current Database: `<name>`
# so we slice from that marker up to the next such marker.
awk -v target="$TARGET_DB" '
    /^-- Current Database: `.+`$/ {
        match($0, /`[^`]+`/)
        current = substr($0, RSTART + 1, RLENGTH - 2)
        in_target = (current == target) ? 1 : 0
    }
    in_target { print }
' "$BACKUP_FILE" >> "$TMP_SQL"

if [[ ! -s "$TMP_SQL" ]]; then
    echo "Error: no data for database '$TARGET_DB' found in backup." >&2
    exit 1
fi

LINE_COUNT=$(wc -l < "$TMP_SQL")
echo "Extracted $LINE_COUNT lines for '$TARGET_DB'."

echo "Ensuring database '$TARGET_DB' exists..."
MYSQL_PWD="$MYSQL_PASSWORD" mysql \
    -h "$MYSQL_HOST" \
    -u "$MYSQL_USER" \
    -e "CREATE DATABASE IF NOT EXISTS \`$TARGET_DB\` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;"

echo "Restoring data..."
MYSQL_PWD="$MYSQL_PASSWORD" mysql \
    -h "$MYSQL_HOST" \
    -u "$MYSQL_USER" \
    "$TARGET_DB" < "$TMP_SQL"

echo "Done. Verifying row counts:"
MYSQL_PWD="$MYSQL_PASSWORD" mysql \
    -h "$MYSQL_HOST" \
    -u "$MYSQL_USER" \
    "$TARGET_DB" \
    -e "SELECT 'user' AS tbl, COUNT(*) AS row_count FROM user UNION ALL SELECT 'photo', COUNT(*) FROM photo;"
