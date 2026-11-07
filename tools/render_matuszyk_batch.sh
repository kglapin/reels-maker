#!/bin/bash
# Batch worker for the Matuszyk&Radajak realization reels.
# One slug per invocation: studio-qa (+fail-closed fallbacks) -> studio-render
# -> A/V probe -> storyboard -> locked report append.
#
# Guards:
#   * never writes to the report without an exclusive flock on REPORT.lock,
#     so concurrent/duplicate fleet runs cannot interleave lines;
#   * idempotent: skips work when the MP4 + board already exist and are
#     newer than the manifest (safe to re-run the whole batch);
#   * fail-closed copy: any '…' anywhere in scenes rejects the manifest
#     instead of rendering truncated text.
#
# Usage: render_matuszyk_batch.sh <slug>
# Env overrides: REELS_ROOT (repo root), REELS_HOME (asset/icon cache HOME),
#   REELS_REPORT (report jsonl path).
set -u
SLUG="$1"
ROOT="${REELS_ROOT:-/Users/kamilglapinski_mbp14/Documents/CODING/PROJECTS/reels-maker}"
MAN="$ROOT/brands/matuszyk-radajak/projects/auto/$SLUG.json"
OUT="$ROOT/renders/matuszyk-radajak/$SLUG.mp4"
QA_OUT="$ROOT/renders/matuszyk-radajak/qa/auto/$SLUG.png"
REPORT="${REELS_REPORT:-/tmp/batch-report.jsonl}"
export HOME="${REELS_HOME:-/tmp/rm-home}"
export PYTHONPATH="$ROOT/src:$ROOT/tests"
cd "$ROOT" || exit 1

report() {
  # $1 = status, $2 = extra json fragment or empty. Locked append.
  local status="$1" extra="${2:-}" line
  if [ -n "$extra" ]; then line="{\"slug\":\"$SLUG\",\"status\":\"$status\",$extra}";
  else line="{\"slug\":\"$SLUG\",\"status\":\"$status\"}"; fi
  LOCK="$REPORT.lock" LINE="$line" .venv/bin/python - <<'EOF'
import fcntl, os
with open(os.environ["LOCK"], "a") as lock:
    fcntl.flock(lock, fcntl.LOCK_EX)
    with open(os.environ.get("REELS_REPORT", "/tmp/batch-report.jsonl"), "a") as f:
        f.write(os.environ["LINE"] + "\n")
    fcntl.flock(lock, fcntl.LOCK_UN)
EOF
}

newer_than() { # $1 = file, $2 = reference: true when $1 exists and is newer
  [ -f "$1" ] && [ ! "$1" -ot "$2" ]
}

if newer_than "$OUT" "$MAN" && newer_than "$QA_OUT" "$MAN"; then
  SIZE="$(stat -f%z "$OUT" 2>/dev/null || stat -c%s "$OUT")"
  report "ok_cached" "\"bytes\":$SIZE"
  exit 0
fi

qa_errors() {
  .venv/bin/reels-maker studio-qa "$MAN" --root . --json 2>/dev/null | python3 -c "
import json,sys
raw=sys.stdin.read(); d=json.loads(raw[raw.index('{'):])
if not d.get('ok'): print('FATAL:'+str(d.get('error'))); raise SystemExit
errs=[(s['scene'],i['code']) for s in d['qa']['scenes'] for i in s['issues'] if i['severity']=='error']
print('ERRORS:'+json.dumps(errs))
"
}

strip_kickers() {
  # $1 = which scenes: mid | hook
  .venv/bin/python - "$MAN" "$1" <<'EOF'
import json,sys
man, which = sys.argv[1], sys.argv[2]
d=json.load(open(man,encoding='utf-8'))
for s in d['scenes']:
    if which=='mid' and s.get('composition')=='spotlight' and s.get('id')!='hook':
        s.pop('kicker',None)
    if which=='hook' and s.get('id')=='hook':
        s.pop('kicker',None)
json.dump(d,open(man,'w',encoding='utf-8'),ensure_ascii=False,indent=1)
print('stripped',which)
EOF
}

if .venv/bin/python - "$MAN" <<'EOF' | grep -q ELLIPSIS; then
import json,sys
d=json.load(open(sys.argv[1],encoding='utf-8'))
blob=json.dumps(d.get('scenes',[]),ensure_ascii=False)
print('ELLIPSIS' if '…' in blob else 'CLEAN')
EOF
  report "copy_rejected"
  exit 6
fi
RES="$(qa_errors)"
if [[ "$RES" == ERRORS* ]]; then
  if [[ "$RES" == *contrast_low* ]]; then
    strip_kickers mid >/dev/null
    RES="$(qa_errors)"
  fi
fi
if [[ "$RES" == ERRORS* && "$RES" != "ERRORS:[]" ]]; then
  if [[ "$RES" == *contrast_low* ]]; then
    strip_kickers hook >/dev/null
    RES="$(qa_errors)"
  fi
fi
if [[ "$RES" == *reels_content_safe_zone* ]]; then
  .venv/bin/python - "$MAN" <<'EOF2'
import json,sys
d=json.load(open(sys.argv[1],encoding='utf-8'))
for s in d['scenes']:
    if s.get('id')=='hook': s.pop('subtitle',None)
json.dump(d,open(sys.argv[1],'w',encoding='utf-8'),ensure_ascii=False,indent=1)
print('dropped hook subtitle on safe-zone violation')
EOF2
  RES="$(qa_errors)"
fi
if [[ "$RES" != "ERRORS:[]" ]]; then
  DETAIL="$(echo "$RES" | python3 -c "import json,sys; print(json.dumps(sys.stdin.read()))")"
  report "qa_failed" "\"detail\":$DETAIL"
  exit 2
fi

mkdir -p "$ROOT/renders/matuszyk-radajak/qa/auto"
if ! .venv/bin/reels-maker studio-render "$MAN" --root . --jobs 2 --output "$OUT" --json >/tmp/render-"$SLUG".log 2>&1; then
  report "render_failed"
  exit 3
fi
PROBE="$(ffprobe -v error -show_streams -of json "$OUT" 2>/dev/null | python3 -c "
import json,sys
m=json.load(sys.stdin); kinds=sorted(s['codec_type'] for s in m['streams'])
print(','.join(kinds))")"
if [[ "$PROBE" != "audio,video" ]]; then
  report "probe_failed" "\"detail\":\"$PROBE\""
  exit 4
fi
if ! .venv/bin/reels-maker storyboard "$MAN" --video "$OUT" --output "$QA_OUT" --json >/dev/null 2>&1; then
  report "storyboard_failed"
  exit 5
fi
SIZE="$(stat -f%z "$OUT" 2>/dev/null || stat -c%s "$OUT")"
report "ok" "\"bytes\":$SIZE"
