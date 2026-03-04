# Northwind TUI — Claude Code Context

## Environment
- Python 3.9 (not 3.10+) — avoid `X | Y` union type syntax; use `Optional[X]` or no annotation
- App runs as: `python3 app.py`
- Current branch: `fix/order-line-item-discount` (main branch is `master`)

## Before Reading Files
- Always read files via the Read tool before editing — the Edit tool has shown stale cache issues
  in this repo; verify line 1 content matches expectations before proceeding
- `pdf_export.py` uses English doc names (DN/INV/GR/CR/CP/CN) since v2.5 — not WZ/FV/PZ/KP/KW

## CSS Gotcha
- `.panel-container Vertical { height: 1fr }` is a blanket rule that overrides `.form-field { height: auto }`
  (specificity 0-1-1 beats 0-1-0). Override with `ParentWidget .section Vertical { height: auto }` (0-1-2)
- Business Details uses this pattern — see `BusinessDetailsPanel .settings-section Vertical` in northwind.tcss

## Per-Commit README Checklist
Every version bump must update ALL of these or the README drifts:
1. `app.py` TITLE string (`TITLE = "Northwind Traders vX.Y"`)
1a. `screens/login.py` login title label (`"Northwind Traders vX.Y"`) — **must match app.py**
2. README version table — new row
3. README `## Features (vX.Y)` block — new section at top
4. README Project Structure — stale version refs in file comments
5. README Key Bindings — any new keyboard shortcuts
6. README `tests/` entry — test count + new test files
7. README What I Learned — 1–3 rows per new technique used
8. README Dependencies — new packages; remove "planned" packages if still unimplemented
9. Screenshots — retake affected panel screenshots

## Architecture Notes
- `data/` is pure SQL, no UI imports — keep it that way
- `screens/` widgets import from `data/` only, never cross-import between screens
- Settings stored as key-value in AppSettings table via `data/settings.get_setting()` / `set_setting()`
- PDF export: all 7 docs share `_draw_header()` in `pdf_export.py`; QR added via `qr_data=` param
- `FileSelectModal(mode="open"|"save")` in `screens/modals.py` — reuse for any file pick
- Logo copied to `assets/logo<ext>` on browse; path saved to `co_logo_path` setting

## Known README Debt (fix when touching those areas)
- Installation says "Python 3.10+" → should be "Python 3.9+"
- `python-barcode` in dependencies listed as "planned" since v2.1 — never implemented
- v2.14 feature text says "6 document types" → actually 7 (CN also has QR)
- `pdf_export.py` tree comment says `(v2.1–v2.4)` → `(v2.1–v2.14)`
- Key Bindings missing: `U` (All Unpaid), `S` (Statement), `P` (Pay Invoice) — added v2.13
