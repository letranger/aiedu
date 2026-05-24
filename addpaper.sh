#!/usr/bin/env bash
# Detect new PDFs in papers/, analyze each with Claude in letranger's voice,
# generate papers_src/<slug>.org, then rebuild HTML. Does NOT commit or push.
#
# Usage:  ./addpaper.sh
#
# Workflow:
#   1. scan papers/*.pdf
#   2. for any PDF without a matching papers_src/<slug>.org, treat as new
#   3. call `claude -p` headlessly with STYLE.md + first paper as few-shot
#   4. claude writes the org file
#   5. run build.py to regenerate HTML
#   6. you review p/<slug>.html, then run ./publish.sh manually
set -euo pipefail
cd "$(dirname "$0")"

# Force `claude -p` to use OAuth (Pro/Max session) instead of any stale
# API key sitting in env vars. Local-scope unset only — doesn't leak.
unset ANTHROPIC_API_KEY CLAUDE_API_KEY ANTHROPIC_AUTH_TOKEN 2>/dev/null || true

# ---- slug helper: lowercase filename, replace spaces/hyphens with _, drop other chars
slugify() {
  echo "$1" \
    | tr '[:upper:]' '[:lower:]' \
    | tr ' -' '__' \
    | sed 's/[^a-z0-9_]//g'
}

# ---- find new PDFs
shopt -s nullglob
declare -a new_entries=()
for pdf in papers/*.pdf; do
  base=$(basename "$pdf" .pdf)
  slug=$(slugify "$base")
  if [[ -z "$slug" ]]; then
    echo "[addpaper] ! skipping (empty slug): $pdf" >&2
    continue
  fi
  if [[ ! -f "papers_src/${slug}.org" ]]; then
    new_entries+=("${pdf}|${slug}")
  fi
done

if [[ ${#new_entries[@]} -eq 0 ]]; then
  echo "[addpaper] no new PDFs found in papers/."
  exit 0
fi

echo "[addpaper] found ${#new_entries[@]} new paper(s):"
for entry in "${new_entries[@]}"; do
  echo "  • ${entry%|*}  →  papers_src/${entry#*|}.org"
done
echo ""

today=$(date +%Y-%m-%d)

# ---- analyze each new paper via Claude headless
for entry in "${new_entries[@]}"; do
  pdf="${entry%|*}"
  slug="${entry#*|}"
  out="papers_src/${slug}.org"

  echo "[addpaper] ─── analyzing: $pdf"

  prompt=$(cat <<EOF
你的任務是分析一篇學術論文，產出一份 **letranger 風格** 的中文 org 筆記。

步驟：
1. 讀 ./STYLE.md（letranger 的寫作風格指南，必須嚴格遵守）
2. 讀 ./papers_src/pros_cons_ai_edu.org（第一篇範本，照這個結構與口吻寫）
3. 讀這份新論文：$pdf
4. 把分析結果寫到：$out

硬性要求：
- 嚴格遵守 STYLE.md 的「七個風格特徵」與「避免事項」，特別是：
  · 聊天口吻、不要學術腔
  · 大量使用「換句話說」「也就是說」「其實」「但現實是」等口語轉折
  · 對讀者有時用「你」第二人稱
  · 重點概念用「」標示，不要用粗體
  · 中文先、英文術語放括號補
  · 段落採「論點 → 換句話說 → 補一句個人判斷」三拍結構
  · 第三拍（個人判斷／實務反思）不可省略，這是這個系列最有價值的部分
- metadata 區參照範本格式：#+TITLE / #+ORIGINAL_TITLE / #+AUTHORS / #+JOURNAL / #+JOURNAL_URL / #+YEAR / #+DATE / #+LINK / #+ABSTRACT
- #+DATE 用 $today
- #+ABSTRACT 是一段有溫度的 hook，避免「本研究探討…」起手式
- **絕對不要編造 URL**：#+LINK 與 #+JOURNAL_URL 的處理順序如下：
  1. 先看 PDF 內文／封面／參考文獻區是否有明確網址，有就直接用
  2. 沒有的話，**用 WebSearch 工具搜尋論文標題 + 第一作者**，從搜尋結果裡找實際存在的頁面（academia.edu / researchgate / 期刊頁 / DOI / 作者學校 repository 都可以）。找到後 WebFetch 驗證連結確實是這篇論文再寫入
  3. 若搜尋仍找不到對應頁面，整行省略，**不要猜、不要填看起來合理的 ID、不要填網站首頁敷衍**
  寧可缺欄位，不要錯資料
- 條列前要有總結句帶出、條列後常有「也就是說：…」收尾解讀；不要做只有名詞的條列
- 標題本身要是完整的句子或論點，不只放名詞

完成後不要做其他任何動作（不要 git、不要 build、不要 publish），只要把 org 寫好即可。
EOF
)

  claude -p "$prompt" --permission-mode acceptEdits || {
    echo "[addpaper] ! claude failed for $pdf" >&2
    continue
  }

  if [[ -f "$out" ]]; then
    echo "[addpaper] ✓ wrote $out"
  else
    echo "[addpaper] ! $out was not created — check Claude output above" >&2
  fi
  echo ""
done

# ---- regenerate HTML
echo "[addpaper] ─── rebuilding HTML"
python3 build.py

echo ""
echo "[addpaper] ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "[addpaper]  done. next steps:"
echo "[addpaper]   1. review the generated org file(s) in papers_src/"
echo "[addpaper]   2. open p/<slug>.html locally to preview"
echo "[addpaper]   3. edit / refine in your editor"
echo "[addpaper]   4. when happy, run ./publish.sh"
echo "[addpaper] ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
