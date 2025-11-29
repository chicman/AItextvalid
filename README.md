# AITextValid (中文標點驗證)

A Python GUI application for comparing text files with intelligent Chinese text normalization.

## Example Use Case: Validating AI-Modernized Buddhist Texts

AITextValid is perfect for verifying AI-generated content, especially when modernizing traditional Chinese texts:

**Scenario**: You have a traditional Chinese Buddhist text with old-style punctuation and want to modernize it using AI.

1.  **Source File** (traditional_sutra.txt):
    ```
    觀自在菩薩行深般若波羅蜜多時照見五蘊皆空度一切苦厄舍利子色不異空空不異色
    ```

2.  **Ask AI to modernize the punctuation**:
    -   Prompt: "Please add modern punctuation marks to this Buddhist text"

3.  **AI Output** (ai_modernized.txt):
    ```
    觀自在菩薩，行深般若波羅蜜多時，照見五蘊皆空，度一切苦厄。舍利子，色不異空，空不異色。
    ```

4.  **Use AITextValid to verify**:
    -   Load both files into AITextValid
    -   Click "Compare" (Cmd+Enter)
    -   **Result**: SUCCESS! The log shows "Files are identical (ignoring punctuation/whitespace)"
    -   This confirms the AI only added punctuation without modifying, deleting, or adding any Chinese characters

**Why this matters**: When working with sacred or historical texts, it's critical to ensure AI hasn't altered the actual content—only the formatting. AITextValid gives you confidence that the original text remains intact.

## Features

- **Smart Text Normalization**: Ignores punctuation and whitespace when comparing Chinese text
- **Side-by-Side Comparison**: Dual pane view with synchronized scrolling
- **Interactive Log**: Click any difference to highlight and jump to it in both panes
- **Drag & Drop Support**: Easy file loading
- **Modern macOS UI**: Native styling with `ttk` widgets
- **Font Size Control**: Adjustable with `Cmd+`/`Cmd-` hotkeys
- **Keyboard Shortcuts**: `Cmd+Enter` to compare files

## Requirements

- Python 3.x
- tkinterdnd2

## Installation

### macOS

```bash
# Install Python 3 (if not already installed)
brew install python3

# Install tkinterdnd2
pip3 install tkinterdnd2
```

> **Note for macOS users**: You may see a harmless warning on first click: `error messaging the mach port for IMKCFRunLoopWakeUpReliable`. This is a normal macOS system message related to input methods and can be safely ignored.

## Usage

```bash
python3 main.py
```

1. Load source and target files (drag & drop or click buttons)
2. Click "Compare" or press `Cmd+Enter`
3. Review differences in the side-by-side view
4. Click any log entry to highlight the corresponding difference

## Keyboard Shortcuts

### macOS
- `Cmd+Enter` - Compare files
- `Cmd+` / `Cmd=` - Increase font size
- `Cmd-` - Decrease font size

### Windows/Linux
- `Ctrl+Enter` - Compare files
- `Ctrl+` / `Ctrl=` - Increase font size
- `Ctrl-` - Decrease font size

## Features in Detail

### Smart Normalization
The app intelligently ignores:
- Chinese and English punctuation (，。！？、；：" " 「」『』, . ! ? ; : " " etc.)
- Whitespace and line breaks
- Control characters

This makes it perfect for validating AI-generated Chinese text against source material.

### Interactive Highlighting
- Click any difference in the log panel
- Both text panes automatically scroll to show the difference
- Bright orange highlight makes it easy to spot the exact location

### Synchronized Scrolling
- Both text panes scroll together
- 50/50 split maintained when resizing window

## License

MIT
