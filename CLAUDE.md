# CLAUDE.md — aiedu 論文閱讀分析系統

這是 letranger 自製的「AI 教育論文閱讀分析系統」。把論文 PDF 交給 Claude 依個人
寫作風格分析成中文 org 筆記，再產出靜態網站發布到 GitHub Pages。

網站標題「AI in Education — 教育領域相關AI論文研究」，
上線位置 https://letranger.github.io/aiedu/ （repo: github.com/letranger/aiedu）。

## 流水線

```
papers/*.pdf ──addpaper.sh──> papers_src/<slug>.org ──build.py──> p/<slug>.html + index.html ──publish.sh──> 上線
```

- **`addpaper.sh`** — 掃 `papers/*.pdf`，對還沒有對應 `papers_src/<slug>.org` 的 PDF
  視為新論文，用 `claude -p` 無頭模式依 `STYLE.md` 分析成 org，再自動跑 `build.py`。
  **不會** commit/push。slug = 檔名轉小寫、空白與 `-` 轉 `_`、去掉其他字元。
- **`build.py`** — 用 `emacs --batch` 把 org 匯出 HTML fragment，套 `templates/` 產生
  `p/<slug>.html`，卡片依 `#+DATE` 降冪注入 `index.html`。需要 emacs。
- **`publish.sh ["訊息"]`** — 再跑一次 build，若有變更就 `git add -A && commit && push`。

## 日常操作

```bash
cd ~/Dropbox/notes/aiedu
# 新論文 PDF 放進 papers/（papers_queues/ 是待處理暫存區，處理時先 mv 到 papers/）
./addpaper.sh                 # 分析 + build（不上線）
open p/<slug>.html            # 檢視、必要時手改 papers_src/<slug>.org
./publish.sh "commit 訊息"    # build + push 上線
```

## 已知限制與慣例

- **無頭 `claude -p` 沒有 web 權限**：`addpaper.sh` 跑分析時 WebSearch/WebFetch 會被擋，
  所以 `#+LINK`（論文原文連結）常因無法驗證而被省略（STYLE 規則：寧缺勿錯、不猜 URL）。
  **正確做法**：事後在互動式 session 裡逐篇 WebSearch → WebFetch 驗證確為該論文，
  再把 `#+LINK` 補進 org、重跑 `build.py`。只有印在 PDF 上的 DOI / 頁尾網址可直接採用。
- **PDF 不進版控**：`.gitignore` 排除 `papers/*.pdf`、`papers_queues/*.pdf`、根目錄 PDF
  （著作權）。
- **org metadata 必填鍵**：`#+TITLE #+ORIGINAL_TITLE #+AUTHORS #+JOURNAL #+YEAR #+DATE
  #+ABSTRACT`；選填：`#+JOURNAL_URL #+LINK #+PDF`。`#+DATE` 是寫筆記的日期。
- **寫作風格**由 `STYLE.md` 定義（七個風格特徵）：聊天口吻、「換句話說／也就是說」等
  口語轉折、對讀者用「你」、重點概念用「」不用粗體、中文先英文術語括號補、段落走
  「論點→換句話說→個人判斷」三拍且第三拍不可省。範本：`papers_src/pros_cons_ai_edu.org`。
