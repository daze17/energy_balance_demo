#!/bin/sh
# n8n-д credential болон 4 AI агентын workflow-г автоматаар оруулж, идэвхжүүлнэ.
# docker compose up бүрт ажиллана — repo доторх workflow JSON-ийг n8n-тэй синк хийнэ.
# LLM_PROVIDER=gemini|claude (.env) — аль загварын хувилбарыг оруулахыг сонгоно.
set -e

PROVIDER=${LLM_PROVIDER:-gemini}
SRC=/bootstrap/workflows/$PROVIDER
[ -d "$SRC" ] || { echo "✗ LLM_PROVIDER='$PROVIDER' буруу — gemini эсвэл claude байна"; exit 1; }

OUT=/tmp/eb-render
rm -rf "$OUT" && mkdir -p "$OUT/workflows"

render() {
  sed -e "s|__ANTHROPIC_API_KEY__|${ANTHROPIC_API_KEY}|g" \
      -e "s|__CLAUDE_MODEL__|${CLAUDE_MODEL:-claude-sonnet-5-5}|g" \
      -e "s|__GEMINI_API_KEY__|${GEMINI_API_KEY}|g" \
      -e "s|__GEMINI_MODEL__|${GEMINI_MODEL:-gemini-3.5-flash-lite}|g" \
      -e "s|__DB_PASSWORD__|${DB_PASSWORD}|g" \
      -e "s|__INTERNAL_TOKEN__|${INTERNAL_TOKEN}|g" \
      -e "s|__MAIL_FROM__|${MAIL_FROM}|g" \
      -e "s|__STAFF_EMAIL__|${STAFF_EMAIL}|g" \
      "$1" > "$2"
}

echo "→ AI загвар: $PROVIDER"
if [ "$PROVIDER" = "gemini" ] && [ -z "$GEMINI_API_KEY" ]; then
  echo "⚠️  GEMINI_API_KEY хоосон — aistudio.google.com-оос авч .env-д нэмээд 'docker compose up -d' дахин ажиллуулна уу."
fi
if [ "$PROVIDER" = "claude" ] && [ -z "$ANTHROPIC_API_KEY" ]; then
  echo "⚠️  ANTHROPIC_API_KEY хоосон — .env-д нэмээд 'docker compose up -d' дахин ажиллуулна уу."
fi

render /bootstrap/credentials.json.tpl "$OUT/credentials.json"
for f in "$SRC"/*.json; do
  render "$f" "$OUT/workflows/$(basename "$f")"
done

echo "→ Credential оруулж байна"
n8n import:credentials --input="$OUT/credentials.json"

echo "→ Workflow оруулж байна"
n8n import:workflow --separate --input="$OUT/workflows"

echo "→ Workflow-уудыг нийтэлж (publish) байна"
for f in "$OUT"/workflows/*.json; do
  id=$(sed -n 's/^  "id": "\([^"]*\)".*/\1/p' "$f" | head -1)
  [ -n "$id" ] && (n8n publish:workflow --id="$id" || echo "  ($id publish алгассан)")
done

rm -rf "$OUT"
echo "✓ n8n бэлэн ($PROVIDER)"
