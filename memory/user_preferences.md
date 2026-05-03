---
name: User preferences
description: UI preferences, language, and workflow style
type: user
originSessionId: e06d26ba-2f33-4d5f-a526-e6c68b6f2b3b
---
Prefers a minimal, clean UI — panels should appear on mouse proximity but stay visible (no auto-hide). Manual hide only via the status bar "收起所有面板" button. The canvas should always be the primary visible area.

**Language:** Full Chinese UI (native menu bar, all labels, buttons, tooltips). The native Electron menu (文件/编辑/视图/窗口/帮助) was manually built in Chinese.

**Workflow:** Wants changes committed to git frequently. Uses GitHub with SOCKS5 proxy (127.0.0.1:7897) for git operations.

**Git config:** Has `url.https://github.com/.insteadof=git@github.com:` set globally, so SSH-style remotes get rewritten to HTTPS.
