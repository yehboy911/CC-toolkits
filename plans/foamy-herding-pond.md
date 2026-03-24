# Add SBOM Validation Checkpoints (CP16 + CP17)

## Context

osc-evidence 目前用 SBOM 資料作為**輸入**來強化 GPL/LGPL 風險偵測（CP02/05/06/10），
但不驗證 SBOM 本身是否正確。姊妹工具 SBOM-Checker 做的是**檔名級**比對（CMake output filename ↔ SBOM target filename），
無法做到**語意級**分析（link dependencies、FetchContent、ExternalProject）。

本次延伸利用 osc-evidence 已有的 CMake 語意解析能力，新增兩個 checkpoint：

| ID | Name | 驗證什麼 |
|----|------|---------|
| CP16 | Dependency Completeness | CMake 中 `target_link_libraries` / `FetchContent` / `ExternalProject` 引用的相依，是否都列在 SBOM |
| CP17 | License Accuracy | SBOM 宣告的 license 與 LICENSE 檔掃描 / name pattern 比對是否一致 |

歸入新的 **Tier 4: SBOM Validation**。

---

## Files to Modify/Create (8 files)

### 1. `src/osc_evidence/gpl_scanner.py` — 新增 `SbomEntry` + `build_sbom_entries()`

在 `GplComponent` dataclass 下方新增：

```python
@dataclass
class SbomEntry:
    name: str       # normalized
    version: str
    license: str    # raw license string from SBOM
    raw_name: str   # original name for display
```

新增 `build_sbom_entries(sbom_paths)` → `List[SbomEntry]`，
複用現有 CSV parsing 邏輯（UTF-8 BOM、skip metadata rows、header detection），
但保留所有 license（不只 GPL/LGPL）的完整資料。跳過 `_SKIP_LICENSES` 中的行。

### 2. `src/osc_evidence/cmake_helpers.py` — 新檔，抽取共用函式

從 CP06 的 `_extract_linked_names()` 提取為共用模組：

```python
def extract_linked_names(args_text: str) -> List[str]:
    """Tokenize target_link_libraries args, skip CMake keywords."""

def extract_project_name(args_text: str) -> str:
    """Extract first token from FetchContent_Declare / ExternalProject_Add."""
```

### 3. `src/osc_evidence/checkpoints/cp06_static_gpl_risk.py` — 改用共用 import

```python
# Before: def _extract_linked_names(args_text)  (local function, lines 53-59)
# After:  from ..cmake_helpers import extract_linked_names
```

刪除 local function，call site `_extract_linked_names` → `extract_linked_names`。

### 4. `src/osc_evidence/checkpoints/cp16_dependency_completeness.py` — 新檔

**邏輯：**
1. 收集所有外部相依名稱：
   - `target_link_libraries` findings → 跳過第一個 token（target 本身）+ CMake keywords + 系統 libs（`pthread`, `dl`, `rt`, `m`）+ `${VAR}` / `$<>` / `-lfoo` / `Foo::Bar`
   - `FetchContent_Declare` findings → 專案名
   - `ExternalProject_Add` findings → 專案名
2. 過濾掉 project 內部 target（`pr.targets` 中的 name）
3. 對 `sbom_all_names` 做 membership check
4. 不在 SBOM + GPL/LGPL → **FAIL**；不在 SBOM + 其他 → **MANUAL**；全部在 → **PASS**
5. 無 SBOM → **N/A**；無外部相依 → **N/A**

**Injectable attributes:** `sbom_all_names: Set[str]`, `gpl_components: List[GplComponent]`

### 5. `src/osc_evidence/checkpoints/cp17_license_accuracy.py` — 新檔

**邏輯：**
1. 建立 `sbom_by_name: Dict[str, SbomEntry]`
2. **Check A**（LICENSE 檔 vs SBOM）：`gpl_components` 中 `confirmed_by == "license_file"` 的元件，若 SBOM 宣告非 GPL → **FAIL**
3. **Check B**（name pattern vs SBOM）：SBOM 中宣告非 GPL 的元件，若 `classify_name()` 匹配 GPL/LGPL → **MANUAL**
4. 全部一致 → **PASS**
5. 無 `sbom_entries` → **N/A**

**Injectable attributes:** `gpl_components: List[GplComponent]`, `sbom_entries: List[SbomEntry]`

### 6. `src/osc_evidence/checkpoint_engine.py` — 註冊 + 注入

- Import `CP16DependencyCompleteness`, `CP17LicenseAccuracy`, `SbomEntry`
- 加入 `_ALL_CHECKPOINTS` 末尾
- `run_all()` 新增 `sbom_entries: Optional[List[SbomEntry]] = None` 參數
- 注入邏輯：`if sbom_entries is not None and hasattr(cp, "sbom_entries"): cp.sbom_entries = sbom_entries`
- 更新 docstring：「Runs all 17 checkpoints」

### 7. `src/osc_evidence/cli.py` — 建構 + 傳遞 `sbom_entries`

```python
from .gpl_scanner import build_gpl_set, build_sbom_name_set, build_sbom_entries

# Line ~187, after sbom_all_names:
sbom_entries = build_sbom_entries(sbom_paths or None)

# Line ~196, engine.run_all() 新增:
sbom_entries=sbom_entries,
```

### 8. `src/osc_evidence/report_generator.py` — 新增 Tier 4

```python
_TIERS = [
    ("Tier 1: GPL/LGPL Direct Risk Detection", ["CP01", "CP02", "CP04", "CP05", "CP06"]),
    ("Tier 2: Build System Hygiene", ["CP03", "CP07", "CP08", "CP09", "CP10", "CP11", "CP12"]),
    ("Tier 3: External Source Tracking", ["CP13", "CP14", "CP15"]),
    ("Tier 4: SBOM Validation", ["CP16", "CP17"]),  # NEW
]
```

---

## Design Decisions

1. **新 Tier 而非塞入現有 Tier** — CP16/CP17 驗證的是 SBOM 文件正確性，語意上與 GPL 風險偵測（T1）、建置衛生（T2）、外部追蹤（T3）不同
2. **CP16 過濾 `Foo::Bar` namespaced targets** — 這些是 `find_package` 匯入的 CMake target，名稱與 SBOM 元件名幾乎不會一致，會造成大量 false positive
3. **CP17 分兩層**：LICENSE 檔掃描是強證據（FAIL），name pattern 是弱啟發式（MANUAL）
4. **N/A when no `--sbom`** — 與 CP06/CP10 相同模式，無 SBOM 就無法驗證
5. **共用 `cmake_helpers.py`** — CP06 和 CP16 都需要 `extract_linked_names()`，避免重複

---

## Verification

```bash
# 1. Install
pip3 install -e "/Users/OwenYeh/Claude Code/osc-evidence-master" --force-reinstall

# 2. Smoke test — 無 SBOM（CP16/CP17 應為 N/A）
osc-evidence audit /path/to/cmake/project --no-interactive -o /tmp/test_no_sbom.md
grep -E "CP1[67]" /tmp/test_no_sbom.md   # 應顯示 N/A

# 3. Smoke test — 有 SBOM
osc-evidence audit /path/to/cmake/project --sbom /path/to/sbom.csv --no-interactive -o /tmp/test_sbom.md
grep -E "CP1[67]" /tmp/test_sbom.md       # 應顯示 PASS/FAIL/MANUAL

# 4. 確認 Tier 4 出現在報告
grep "Tier 4" /tmp/test_sbom.md

# 5. 確認 CP06 仍正常（refactor 後）
grep "CP06" /tmp/test_sbom.md
```
