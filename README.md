# 特教課表產生器（timetable-skill）

給特教老師用的手機課表查詢網頁產生器。三個分頁：**查教室／查各師／查學生**，
目前上課的那一節會發光，點組別可看學生名單。

課表、組別、學生有異動時，**只改一份 `data.json`**，重新產生網頁即可，不用手改 HTML。

## 內容

| 檔案 | 說明 |
|---|---|
| `SKILL.md` | 給 AI（Claude Code 等）讀的操作說明 |
| `template.html` | 網頁範本（不含任何學校資料） |
| `build.py` | `data.json` → 單檔 HTML，並檢查衝堂 |
| `example.json` | 匿名的資料格式範例 |

## 直接使用（不需要 AI）

需要 Python 3。

```bash
python build.py example.json 課表.html
```

用瀏覽器開 `課表.html` 就能看。把 `example.json` 複製一份，改成自己學校的老師、教室、組別，再重新執行即可。
若有警告（衝堂、找不到老師或教室），終端機會列出來。

## 搭配 AI 使用

把整個資料夾放進 AI 工具的 skills 資料夾（例如 Claude Code 的 `.claude/skills/timetable-skill/`），
然後直接說：「幫我把陸老師週二午休改上學策C」、「新增一組數學抽離」，AI 會依 `SKILL.md` 修改 `data.json` 並重新產生網頁。

## data.json 格式

詳見 `SKILL.md` 與 `example.json`。重點：只需要列出老師、教室、**組別（含學生與上課時段）**，
學生清單、每人課表、人數、顏色都會自動推出來。

## 注意

- 網頁會包含學生姓名，請勿放在公開可被搜尋的網址；分享範例請用匿名資料。
- 「目前這一節」依 `period_times` 判斷，請改成貴校的鐘聲時間。
