# Plan: 修正 ~/.claude/ 配置讓 Claude Code 自動發現所有元件

## Context

Owen 已建置完 `~/.claude/` 設定架構（8 agents、9 skills、10 commands、6 hooks），但需確認 Claude Code 是否能自動發現這些元件。經查證，存在 3 個問題需修正。

## 診斷結果

| 元件 | 自動發現？ | 當前狀態 | 需修正？ |
|------|-----------|---------|---------|
| `skills/` | ✅ 自動掃描 `SKILL.md` | 9/10 OK（`learned/` 缺 SKILL.md） | 是 |
| `agents/` | ✅ 自動掃描 `.md` + frontmatter | 8/8 OK | 否 |
| `commands/` | ⚠️ **已棄用**，被 skills 取代 | 10 個 `.md` 仍可用但非正式機制 | 建議遷移 |
| `hooks/` | ❌ **不自動發現**，必須在 `settings.json` 註冊 | 已在 settings.json 註冊，路徑已修正 | 否 |

## 問題清單

### 問題 1：`skills/learned/` 目錄缺少 `SKILL.md`（空目錄）
- 位置：`~/.claude/skills/learned/`
- 影響：Claude Code 掃描到此目錄但無法載入
- 修正：刪除空目錄，或建立 `SKILL.md`

### 問題 2：`commands/` 目錄是舊版機制，已被 `skills/` 取代
- 位置：`~/.claude/commands/*.md`（10 個檔案）
- 影響：目前仍可用（向下相容），但 skills 優先
- 建議：**保持不動**——向下相容正常運作中，遷移是可選的
- 若要遷移：每個 command 改為 `skills/<name>/SKILL.md` 格式

### 問題 3：`settings.json` 可能需要確認 `statusLine` 腳本路徑是否攜帶到新電腦後仍有效
- 位置：`~/.claude/settings.json` 裡 `"command": "bash /Users/OwenYeh/.claude/statusline-command.sh"` 是硬編碼絕對路徑
- 影響：攜帶到新電腦如果 username 不同，statusline 會失效
- 修正：改為 `bash "$HOME/.claude/statusline-command.sh"`

## 執行步驟

1. **刪除空目錄** `~/.claude/skills/learned/`
2. **修正 statusline 路徑**：`settings.json` 中 `/Users/OwenYeh/.claude/statusline-command.sh` → `$HOME/.claude/statusline-command.sh`
3. **驗證**：
   - 確認 skills 列表中無 `learned`
   - 確認 statusline 使用 `$HOME` 而非硬編碼路徑
   - 重建壓縮包 `claude-config-20260324.tar.gz`（可選）

## 修改檔案
- `~/.claude/settings.json` — statusline 路徑改為可攜帶格式
- `~/.claude/skills/learned/` — 刪除空目錄

## 驗證
- `ls ~/.claude/skills/` 確認 `learned` 已消失
- `grep 'OwenYeh' ~/.claude/settings.json` 確認無硬編碼 username
- 啟動新 Claude session 確認 skills/agents 正常載入
