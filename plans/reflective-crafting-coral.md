# 語音設定調整計畫：暫用大陸語音替代台灣腔調

## Context

用戶希望將 `/Users/OwenYeh/Claude Code/voice_profiles.json` 中的 abogen 語音設定改為台灣腔調。經研究確認：
- Kokoro-82M 沒有台灣腔調語音（所有 8 個中文語音皆為大陸普通話口音）
- Supertonic TTS 完全不支援中文
- edge-tts 有台灣語音但無法直接整合到 abogen
- 用戶決定**先用現有大陸語音暫代**，選擇聽起來較柔和的組合

## 修改內容

### 檔案：`/Users/OwenYeh/Claude Code/voice_profiles.json`

將現有的 `zf_xiaoxiao` + `zm_yunyang` 組合替換為多組候選 profile，方便用戶測試比較：

```json
{
  "abogen_voice_profiles": {
    "zf_xiaoni_zm_yunxi": {
      "voices": [
        ["zf_xiaoni", 0.5],
        ["zm_yunxi", 0.5]
      ],
      "language": "z"
    }
  }
}
```

### 語音特性參考

| Voice ID | 性別 | 備註 |
|----------|------|------|
| `zf_xiaobei` | 女 | 可測試 |
| `zf_xiaoni` | 女 | 可測試 |
| `zf_xiaoxiao` | 女 | 原設定 |
| `zf_xiaoyi` | 女 | 可測試 |
| `zm_yunjian` | 男 | 可測試 |
| `zm_yunxi` | 男 | 可測試 |
| `zm_yunxia` | 男 | 可測試 |
| `zm_yunyang` | 男 | 原設定 |

### 建議做法

1. 先換一組不同的語音組合（如 `zf_xiaoni` + `zm_yunxi`），取代原本的 `zf_xiaoxiao` + `zm_yunyang`
2. 用 abogen 產生測試音檔，聽看看效果
3. 不滿意的話，可以再嘗試其他組合或調整權重比例

> **注意**：這只是更換不同的大陸語音組合，無法真正產生台灣腔調。未來若 abogen 支援 edge-tts 或 Kokoro 新增 zh-TW 語音，可再更新。

## 驗證方式

1. 修改 `voice_profiles.json`
2. 使用 abogen 產生一段測試音檔
3. 比較新舊語音組合的效果
4. 根據聽感決定是否調整組合或權重
