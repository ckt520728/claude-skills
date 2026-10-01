#!/usr/bin/env bash
# Deploy vault-src/ into the live vault. One-way, idempotent, and it never loses a user edit.
#
# Usage:
#   bash scripts/deploy.sh            # deploy
#   bash scripts/deploy.sh --dry-run  # show what would change, touch nothing
#
# Three kinds of file, three rules:
#
#   code   vault-src/**            -> Life OS/**      overwritten on every deploy
#          vault-src/Templates/*   -> vault Templates/
#          Dashboards, views, prompts, guide, scripts. Never hand-edit the deployed copy.
#
#   seed   vault-src/_seed/**      -> Life OS/**      created once; then it is YOURS
#          Compass Config, Life Theme, Core Values, Ideal Week, the task list, boards.
#          Upgraded only while the vault copy is byte-identical to something this
#          script shipped (scripts/deploy-ledger.tsv proves that). Edit it once and
#          the deploy leaves it alone and says so.
#
#   retired  anything in the ledger that vault-src no longer ships is removed -- but
#          only when its hash proves nobody touched it. Otherwise it is kept and named.
#
# There is no reverse sync, on purpose.

set -euo pipefail

SRC_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SRC="$SRC_ROOT/vault-src"
LEDGER="$SRC_ROOT/scripts/deploy-ledger.tsv"
VAULT="${LIFEOS_VAULT:-G:/我的雲端硬碟/Second Brain}"
DEST="$VAULT/Life OS"
TPL_DEST="$VAULT/Templates"

DRY=0
[ "${1:-}" = "--dry-run" ] && DRY=1

# Folders holding the user's own writing. The deploy never writes inside these.
PROTECTED=("每日筆記" "Clippings" "知識庫" "創作庫" "影片筆記" "教學素材" "內容草稿"
           "01 Journal" "02 Retreats" "05 People")

say() { printf '%s\n' "$*"; }
act() { if [ "$DRY" = 1 ]; then say "  would $*"; else say "  $*"; fi; }
sha() { sha256sum "$1" | cut -d' ' -f1; }

say "deploy: $SRC"
say "    ->  $DEST"
[ "$DRY" = 1 ] && say "    (dry run — nothing will be written)"
say ""

# --- preflight -----------------------------------------------------------------
[ -d "$SRC" ]   || { say "FAIL: vault-src not found at $SRC"; exit 1; }
[ -d "$VAULT" ] || { say "FAIL: vault not found at $VAULT"; exit 1; }
[ -f "$VAULT/CLAUDE.md" ] || { say "FAIL: $VAULT does not look like the vault (no CLAUDE.md). Refusing."; exit 1; }
touch "$LEDGER"

changed=0; skipped=0; kept=0; retired=0
declare -A SHIPPED_NOW=()

shipped_before() {  # $1 = hash, $2 = vault-relative path
  grep -qF "$1	$2" "$LEDGER"
}

record() {  # $1 = file just written, $2 = vault-relative path
  [ "$DRY" = 1 ] && return 0
  local h; h="$(sha "$1")"
  shipped_before "$h" "$2" || printf '%s\t%s\n' "$h" "$2" >> "$LEDGER"
}

guard() {  # refuse any destination outside Life OS/ or Templates/, or inside user data
  case "$1" in
    "$DEST"/*|"$TPL_DEST"/*) ;;
    *) say "FAIL: refusing to write outside Life OS/ or Templates/: $1"; exit 1 ;;
  esac
  for p in "${PROTECTED[@]}"; do
    case "$1" in */"$p"/*) say "FAIL: refusing to write inside protected folder $p: $1"; exit 1 ;; esac
  done
}

put() {  # $1 src, $2 dst, $3 mode (code|seed)
  local src="$1" dst="$2" mode="$3" rel="${2#"$VAULT"/}"
  guard "$dst"
  SHIPPED_NOW["$rel"]=1
  if [ -f "$dst" ] && cmp -s "$src" "$dst"; then
    skipped=$((skipped + 1)); return 0
  fi
  if [ "$mode" = seed ] && [ -f "$dst" ]; then
    if ! shipped_before "$(sha "$dst")" "$rel"; then
      say "  kept    $rel  (you edited it; the new version is in vault-src/_seed — merge by hand if wanted)"
      kept=$((kept + 1)); return 0
    fi
  fi
  local verb="create"; [ -f "$dst" ] && verb="update"
  if [ "$DRY" = 0 ]; then mkdir -p "$(dirname "$dst")"; cp -- "$src" "$dst"; fi
  act "$verb  $rel"
  record "$src" "$rel"
  changed=$((changed + 1))
}

# --- templates -> the vault's own Templates/ -------------------------------------
while IFS= read -r -d '' f; do
  put "$f" "$TPL_DEST/$(basename "$f")" code
done < <(find "$SRC/Templates" -maxdepth 1 -type f -print0 2>/dev/null)

# --- seeds -------------------------------------------------------------------------
while IFS= read -r -d '' f; do
  put "$f" "$DEST/${f#$SRC/_seed/}" seed
done < <(find "$SRC/_seed" -type f \( -name '*.md' -o -name '*.js' \) -print0 2>/dev/null)

# --- code --------------------------------------------------------------------------
while IFS= read -r -d '' f; do
  rel="${f#$SRC/}"
  case "$rel" in Templates/*|_seed/*) continue ;; esac
  put "$f" "$DEST/$rel" code
done < <(find "$SRC" -type f \( -name '*.md' -o -name '*.js' \) -print0)

# --- retire what vault-src no longer ships, only when provably untouched ------------
while IFS=$'\t' read -r h rel; do
  [ -n "${rel:-}" ] || continue
  [ -n "${SHIPPED_NOW[$rel]:-}" ] && continue
  dst="$VAULT/$rel"
  [ -f "$dst" ] || continue
  guard "$dst"
  if [ "$(sha "$dst")" = "$h" ]; then
    [ "$DRY" = 0 ] && rm -- "$dst"
    act "retire  $rel"
    retired=$((retired + 1))
    [ "$DRY" = 0 ] && rmdir --ignore-fail-on-non-empty "$(dirname "$dst")" 2>/dev/null || true
  fi
done < <(sort -u -t$'\t' -k2,2 -k1,1 "$LEDGER" | awk -F'\t' '!seen[$2 FS $1]++')

# A retired path whose content is NOT in the ledger was edited by the user: name it.
while IFS=$'\t' read -r _h rel; do
  [ -n "${rel:-}" ] || continue
  [ -n "${SHIPPED_NOW[$rel]:-}" ] && continue
  dst="$VAULT/$rel"
  [ -f "$dst" ] || continue
  shipped_before "$(sha "$dst")" "$rel" && continue
  say "  kept    $rel  (no longer shipped, but you edited it — move or delete it yourself)"
  kept=$((kept + 1))
done < <(awk -F'\t' '!seen[$2]++' "$LEDGER")

say ""
say "changed: $changed    unchanged: $skipped    kept (yours): $kept    retired: $retired"
say "verified: every write targeted Life OS/ or Templates/ only"
