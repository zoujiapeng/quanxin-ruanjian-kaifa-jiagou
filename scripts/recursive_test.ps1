$projectDir = "C:\Users\zou\Desktop\claude1"
Set-Location $projectDir

$prompt = @"
You must use lobster_* MCP tools to complete this GUI automation test.

Step 1: lobster_detect_process name="notepad.exe"
Step 2: IF not running -> lobster_launch_program target="notepad.exe"
Step 3: lobster_focus_window title="Notepad"
Step 4: lobster_type_text text="Recursive test: Lobster self-boot verified"
Step 5: Let 1.5 seconds pass (you can use lobster_run_dsl_sync with dsl="WAIT 1.5")
Step 6: lobster_screenshot
Step 7: lobster_ocr_find_text text="Lobster self-boot verified"
Step 8: IF OCR found -> report "RECURSIVE TEST PASSED - Lobster self-boot verification successful"
Step 9: lobster_hotkey keys="alt+f4"
Step 10: lobster_click_target target="Don't Save"

Execute each step and report results. This is a test that verifies Lobster can do what other CLI-only tools cannot: process management + window control + keyboard input + screenshot + OCR in one workflow.
"@

$prompt | claude -p 2>&1
