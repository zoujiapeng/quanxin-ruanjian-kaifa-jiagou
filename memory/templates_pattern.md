---
name: Templates system architecture
description: Preset templates are defined in two places — store for script data, TopBar for UI registration
type: project
originSessionId: c9f6b2b2-d2ac-408e-a014-55a56c637c40
---
**Two-layer template system:**
- `src/renderer/store/index.ts` `PRESET_TEMPLATES` array — contains `createScript()` factory functions that generate the full `FlowScript` with nodes/edges
- `src/renderer/components/common/TopBar.tsx` `PRESET_LIST` array — contains UI entries (id, name, desc) for the dropdown menu

**Why separate:** The store owns template data generation; TopBar owns the UI presentation. Both must be updated when adding new templates.

**How to apply:** When adding a preset template, add the `ScriptTemplate` entry to `PRESET_TEMPLATES` in the store AND add a corresponding `{ id, name, desc }` entry to `PRESET_LIST` in TopBar. Missing either one means the template won't appear or won't load.
