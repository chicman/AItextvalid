# AITextValid (中文標點驗證)

A Python GUI application for comparing text files with intelligent Chinese text normalization.

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

```bash
pip install tkinterdnd2
```

## Usage

```bash
python main.py
```

1. Load source and target files (drag & drop or click buttons)
2. Click "Compare" or press `Cmd+Enter`
3. Review differences in the side-by-side view
4. Click any log entry to highlight the corresponding difference

## Keyboard Shortcuts

- `Cmd+Enter` / `Ctrl+Enter` - Compare files
- `Cmd+` / `Cmd=` - Increase font size
- `Cmd-` - Decrease font size

## License

MIT
