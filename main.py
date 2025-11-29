import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from tkinterdnd2 import DND_FILES, TkinterDnD
import difflib
import os
import re
import unicodedata
import platform
import traceback
import logging

# Configure logging
logging.basicConfig(filename='debug.log', level=logging.DEBUG, 
                    format='%(asctime)s - %(levelname)s - %(message)s')

# Determine OS and Key Bindings
IS_MAC = platform.system() == 'Darwin'
CMD_KEY = "Command" if IS_MAC else "Control"
CMD_KEY_NAME = "Cmd" if IS_MAC else "Ctrl"

# File size limits (in bytes)
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB hard limit
WARN_FILE_SIZE = 5 * 1024 * 1024  # 5MB warning threshold
SUMMARY_MODE_SIZE = 5 * 1024 * 1024  # 5MB - use summary mode instead of full diff
CHUNK_SIZE = 50000  # Compare in 50KB chunks to prevent freezing



class TextValidApp:
    def __init__(self, root):
        self.root = root
        self.root.title("中文標點驗證")
        self.root.geometry("1200x850")
        # Mapping from log entry tags to text indices for highlighting
        self.log_mappings = {}
        # Track currently highlighted range
        self.current_highlight_tag = None
        # Font size tracking
        self.text_font_size = 16
        self.log_font_size = 15
        # Log counter for tracking entries
        self.log_counter = 0

        self.file_a_path = None
        self.file_b_path = None
        self._scrolling = False

        self._setup_styles()
        self._setup_ui()
        self._bind_hotkeys()
        # Bind click on log entries
        self.log_text.bind("<Button-1>", self._on_log_click)

    def _setup_styles(self):
        self.style = ttk.Style()
        self.style.theme_use('clam') # 'clam' often looks cleaner than default on some systems, but let's try to adapt
        
        # Check if 'aqua' is available (macOS native)
        if 'aqua' in self.style.theme_names():
            self.style.theme_use('aqua')
        
        # General Frame bg
        # self.root.configure(bg="#f5f5f7") # macOS-ish light gray

        # Configure common fonts
        default_font = ("Helvetica Neue", 16)
        header_font = ("Helvetica Neue", 17, "bold")
        
        self.style.configure(".", font=default_font)
        self.style.configure("TButton", padding=6)
        self.style.configure("TLabel", padding=2)
        
        # Custom style for the large Compare button
        self.style.configure("Large.TButton", font=("Helvetica Neue", 20, "bold"), padding=15)

    def _setup_ui(self):
        # Top Control Panel
        control_frame = ttk.Frame(self.root, padding="15 15 15 15")
        control_frame.pack(fill=tk.X)

        # Source Controls (File A)
        self.btn_load_a = ttk.Button(control_frame, text="Load Source", command=self.load_file_a)
        self.btn_load_a.grid(row=0, column=0, padx=5, pady=5, sticky="ew")
        self.lbl_file_a = ttk.Label(control_frame, text="No file selected", foreground="gray")
        self.lbl_file_a.grid(row=0, column=1, padx=5, pady=5, sticky="w")

        # Target Controls (File B)
        self.btn_load_b = ttk.Button(control_frame, text="Load Target file", command=self.load_file_b)
        self.btn_load_b.grid(row=1, column=0, padx=5, pady=5, sticky="ew")
        self.lbl_file_b = ttk.Label(control_frame, text="No file selected", foreground="gray")
        self.lbl_file_b.grid(row=1, column=1, padx=5, pady=5, sticky="w")

        # Compare Button (Large)
        self.btn_compare = ttk.Button(control_frame, text=f"Compare ({CMD_KEY_NAME}+Enter)", command=self.compare_files, state=tk.DISABLED, style="Large.TButton")
        self.btn_compare.grid(row=0, column=2, rowspan=2, padx=30, sticky="ns")

        # Main Content Area (Split View)
        self.paned_window = tk.PanedWindow(self.root, orient=tk.HORIZONTAL, sashrelief=tk.FLAT, sashwidth=4, bg="#d0d0d0")
        self.paned_window.pack(fill=tk.BOTH, expand=True, padx=15, pady=10)

        # Text Area A (Source)
        self.frame_a = ttk.Frame(self.paned_window)
        self.lbl_header_a = ttk.Label(self.frame_a, text="Source (Original) - Drop File Here", font=("Helvetica Neue", 17, "bold"))
        self.lbl_header_a.pack(side=tk.TOP, anchor="w", pady=(0, 5))
        
        self.text_a = tk.Text(self.frame_a, wrap=tk.NONE, undo=False, font=("Menlo", 16), relief=tk.FLAT, highlightthickness=1, highlightbackground="#cccccc")
        self.scroll_a_y = ttk.Scrollbar(self.frame_a, orient=tk.VERTICAL, command=self.text_a.yview)
        self.scroll_a_x = ttk.Scrollbar(self.frame_a, orient=tk.HORIZONTAL, command=self.text_a.xview)
        self.text_a.configure(yscrollcommand=self._sync_scroll_y, xscrollcommand=self.scroll_a_x.set)
        
        self.scroll_a_y.pack(side=tk.RIGHT, fill=tk.Y)
        self.scroll_a_x.pack(side=tk.BOTTOM, fill=tk.X)
        self.text_a.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        # Drag and Drop for A
        self.text_a.drop_target_register(DND_FILES)
        self.text_a.dnd_bind('<<Drop>>', self.drop_a)
        
        self.paned_window.add(self.frame_a, stretch="always")

        # Text Area B (Target)
        self.frame_b = ttk.Frame(self.paned_window)
        self.lbl_header_b = ttk.Label(self.frame_b, text="Target file (AI Generated) - Drop File Here", font=("Helvetica Neue", 17, "bold"))
        self.lbl_header_b.pack(side=tk.TOP, anchor="w", pady=(0, 5))

        self.text_b = tk.Text(self.frame_b, wrap=tk.NONE, undo=False, font=("Menlo", 16), relief=tk.FLAT, highlightthickness=1, highlightbackground="#cccccc")
        self.scroll_b_y = ttk.Scrollbar(self.frame_b, orient=tk.VERTICAL, command=self.text_b.yview)
        self.scroll_b_x = ttk.Scrollbar(self.frame_b, orient=tk.HORIZONTAL, command=self.text_b.xview)
        self.text_b.configure(yscrollcommand=self._sync_scroll_y, xscrollcommand=self.scroll_b_x.set)

        self.scroll_b_y.pack(side=tk.RIGHT, fill=tk.Y)
        self.scroll_b_x.pack(side=tk.BOTTOM, fill=tk.X)
        self.text_b.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        # Drag and Drop for B
        self.text_b.drop_target_register(DND_FILES)
        self.text_b.dnd_bind('<<Drop>>', self.drop_b)

        self.paned_window.add(self.frame_b, stretch="always")
        

        # Configure Tags for Highlighting
        self._configure_tags(self.text_a)
        self._configure_tags(self.text_b)

        # Log Frame (Bottom)
        self.log_frame = ttk.LabelFrame(self.root, text="Comparison Log", padding=10)
        self.log_frame.pack(fill=tk.BOTH, expand=False, padx=15, pady=15)
        
        self.log_text = tk.Text(self.log_frame, height=18, font=("Menlo", 15), relief=tk.FLAT, bg="#1e1e1e", fg="#d4d4d4", wrap=tk.WORD)
        self.log_scroll = ttk.Scrollbar(self.log_frame, orient=tk.VERTICAL, command=self.log_text.yview)
        self.log_text.configure(yscrollcommand=self.log_scroll.set)
        # Make read-only by preventing insertions/deletions
        self.log_text.bind("<Key>", lambda e: "break" if e.keysym not in ('Left', 'Right', 'Up', 'Down', 'Home', 'End', 'Prior', 'Next') else None)
        
        self.log_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        self.log_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

    def _bind_hotkeys(self):
        # Bind Command+Enter (macOS) and Control+Enter (Windows/Linux)
        self.root.bind(f"<{CMD_KEY}-Return>", lambda event: self.compare_files())
        
        # Bind font size controls
        # Increase: Cmd/Ctrl + Plus/Equal
        self.root.bind(f"<{CMD_KEY}-plus>", lambda event: self._increase_font_size())
        self.root.bind(f"<{CMD_KEY}-equal>", lambda event: self._increase_font_size())
        
        # Decrease: Cmd/Ctrl + Minus/Underscore
        self.root.bind(f"<{CMD_KEY}-minus>", lambda event: self._decrease_font_size())
        self.root.bind(f"<{CMD_KEY}-underscore>", lambda event: self._decrease_font_size())
        
        # Keypad support if needed
        self.root.bind(f"<{CMD_KEY}-KP_Subtract>", lambda event: self._decrease_font_size())
        self.root.bind(f"<{CMD_KEY}-KP_Add>", lambda event: self._increase_font_size())

    def _configure_tags(self, text_widget):
        text_widget.tag_config("added", background="#e6ffec", foreground="#006600") # Light green (Extra in Target)
        text_widget.tag_config("removed", background="#ffebe9", foreground="#cc0000") # Light red (Missing in Target)
        # Tag for active highlight when a log entry is selected - bright orange for visibility
        text_widget.tag_config("active_highlight", background="#ff9800", foreground="#ffffff")
        text_widget.tag_config("changed", background="#fff8c4", foreground="#996600") # Light yellow
        text_widget.tag_config("header", background="#f0f0f0", foreground="#888888") # Gray for context

    def _sync_scroll_y(self, *args):
        # Sync scrolling for both text widgets
        if self._scrolling: return
        self._scrolling = True
        try:
            self.text_a.yview_moveto(args[0])
            self.text_b.yview_moveto(args[0])
            self.scroll_a_y.set(*args)
            self.scroll_b_y.set(*args)
        finally:
            self._scrolling = False


    def drop_a(self, event):
        path = event.data
        # Handle curly braces if path contains spaces (tkinterdnd quirk)
        if path.startswith('{') and path.endswith('}'):
            path = path[1:-1]
        self.load_file_from_path(path, is_source=True)

    def drop_b(self, event):
        path = event.data
        if path.startswith('{') and path.endswith('}'):
            path = path[1:-1]
        self.load_file_from_path(path, is_source=False)

    def load_file_a(self):
        path = filedialog.askopenfilename()
        if path:
            self.load_file_from_path(path, is_source=True)

    def load_file_b(self):
        path = filedialog.askopenfilename()
        if path:
            self.load_file_from_path(path, is_source=False)

    def load_file_from_path(self, path, is_source):
        if is_source:
            self.file_a_path = path
            self.lbl_file_a.config(text=os.path.basename(path), foreground="black")
            self._load_content(path, self.text_a)
        else:
            self.file_b_path = path
            self.lbl_file_b.config(text=os.path.basename(path), foreground="black")
            self._load_content(path, self.text_b)
        self._check_ready()

    def _load_content(self, path, text_widget):
        try:
            # Check file size first
            file_size = os.path.getsize(path)
            logging.info(f"Loading file: {path}, size: {file_size} bytes")
            
            if file_size > MAX_FILE_SIZE:
                messagebox.showerror("File Too Large", 
                                   f"File size is {file_size / (1024*1024):.1f}MB.\n\n"
                                   f"Maximum supported size is {MAX_FILE_SIZE / (1024*1024):.0f}MB.\n\n"
                                   "Please use a smaller file.")
                return
            
            if file_size > WARN_FILE_SIZE:
                result = messagebox.askyesno("Large File Warning",
                                            f"File size is {file_size / (1024*1024):.2f}MB.\n\n"
                                            "Processing large files may take time and could freeze the app.\n\n"
                                            "Continue?")
                if not result:
                    return
            
            with open(path, 'r', encoding='utf-8') as f:
                content = f.read()
                text_widget.config(state=tk.NORMAL)
                text_widget.delete(1.0, tk.END)
                text_widget.insert(tk.END, content)
                text_widget.config(state=tk.DISABLED)
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load file: {e}")
            logging.error(f"Failed to load file {path}: {e}")

    def _check_ready(self):
        if self.file_a_path and self.file_b_path:
            self.btn_compare.config(state=tk.NORMAL)

    def normalize_text(self, text):
        # Remove all punctuation (half-width and full-width) and whitespace
        # Unicode categories: P* (Punctuation), Z* (Separator/Space), C* (Control)
        # Return tuple: (normalized_string, index_mapping)
        # index_mapping[i] is the index in 'text' corresponding to normalized_string[i]
        
        normalized = []
        mapping = []
        for i, char in enumerate(text):
            cat = unicodedata.category(char)
            # P* = Punctuation, Z* = Separator, C* = Control
            if not (cat.startswith('P') or cat.startswith('Z') or cat.startswith('C')):
                normalized.append(char)
                mapping.append(i)
        return "".join(normalized), mapping

    def compare_files(self):
        if not self.file_a_path or not self.file_b_path:
            return

        try:
            # Disable compare button during processing
            self.btn_compare.config(state=tk.DISABLED)
            self.btn_compare.config(text="Processing...")
            self.root.update_idletasks()  # Force UI update
            
            # Check combined file sizes
            size_a = os.path.getsize(self.file_a_path)
            size_b = os.path.getsize(self.file_b_path)
            total_size = size_a + size_b
            
            logging.info(f"Comparing files: {size_a} + {size_b} = {total_size} bytes")
            
            with open(self.file_a_path, 'r', encoding='utf-8') as f1, \
                 open(self.file_b_path, 'r', encoding='utf-8') as f2:
                text_a = f1.read()
                text_b = f2.read()

            # Use summary mode for large files
            if total_size > SUMMARY_MODE_SIZE:
                self._compare_summary_mode(text_a, text_b)
            else:
                self._display_diff(text_a, text_b)

        except Exception as e:
            messagebox.showerror("Error", f"Comparison failed: {e}")
            logging.error(f"Comparison failed: {e}")
        finally:
            # Re-enable compare button
            self.btn_compare.config(state=tk.NORMAL)
            self.btn_compare.config(text=f"Compare ({CMD_KEY_NAME}+Enter)")

    def _display_diff(self, text_a, text_b):
        # Clear existing content
        self.text_a.config(state=tk.NORMAL)
        self.text_b.config(state=tk.NORMAL)
        self.text_a.delete(1.0, tk.END)
        self.text_b.delete(1.0, tk.END)
        
        self._clear_log()
        self._log("Starting comparison...")

        # Normalize content
        norm_a, map_a = self.normalize_text(text_a)
        norm_b, map_b = self.normalize_text(text_b)
        
        # Use chunked comparison for better performance on large files
        if len(norm_a) > CHUNK_SIZE or len(norm_b) > CHUNK_SIZE:
            self._log(f"Using optimized chunked comparison for large content ({len(norm_a) + len(norm_b)} chars)...")
            self._display_diff_chunked(text_a, text_b, norm_a, norm_b, map_a, map_b)
        else:
            self._display_diff_full(text_a, text_b, norm_a, norm_b, map_a, map_b)

    def _display_diff_full(self, text_a, text_b, norm_a, norm_b, map_a, map_b):
        """Original full diff algorithm for smaller files."""
        matcher = difflib.SequenceMatcher(None, norm_a, norm_b)
        
        curr_a = 0
        curr_b = 0
        
        differences_found = False
        
        for tag, i1, i2, j1, j2 in matcher.get_opcodes():
            # Determine start/end in original text
            # Start
            start_a = map_a[i1] if i1 < len(map_a) else len(text_a)
            start_b = map_b[j1] if j1 < len(map_b) else len(text_b)
            
            # End
            end_a = map_a[i2 - 1] + 1 if i2 > i1 else start_a
            end_b = map_b[j2 - 1] + 1 if j2 > j1 else start_b
            
            # 1. Handle "Ignored" content (punctuation/newlines) BEFORE this chunk
            ignored_a = text_a[curr_a:start_a]
            ignored_b = text_b[curr_b:start_b]
            
            self._insert_and_sync(ignored_a, ignored_b, "header")
            
            # 2. Handle the "Meaningful" chunk
            chunk_a = text_a[start_a:end_a]
            chunk_b = text_b[start_b:end_b]

            # Calculate line numbers
            line_a = text_a.count('\n', 0, start_a) + 1
            line_b = text_b.count('\n', 0, start_b) + 1
            
            if tag == 'equal':
                self._insert_and_sync(chunk_a, chunk_b, None)
            elif tag == 'replace':
                # Get widget positions BEFORE inserting
                widget_start_a = self.text_a.index("end-1c")
                widget_start_b = self.text_b.index("end-1c")
                
                self._insert_and_sync(chunk_a, chunk_b, "removed", "added")
                
                # Get widget positions AFTER inserting
                widget_end_a = self.text_a.index("end-1c")
                widget_end_b = self.text_b.index("end-1c")
                
                self._log_difference(f"[Line A:{line_a} / B:{line_b}] [DIFFERENCE] Replaced: '{chunk_a}' with '{chunk_b}'", 
                                   widget_start_a, widget_end_a, widget_start_b, widget_end_b)
                differences_found = True
            elif tag == 'delete':
                # Get widget positions BEFORE inserting
                widget_start_a = self.text_a.index("end-1c")
                widget_start_b = self.text_b.index("end-1c")
                
                self._insert_and_sync(chunk_a, "", "removed", None)
                
                # Get widget positions AFTER inserting
                widget_end_a = self.text_a.index("end-1c")
                widget_end_b = self.text_b.index("end-1c")
                
                self._log_difference(f"[Line A:{line_a} / B:{line_b}] [DIFFERENCE] Deleted: '{chunk_a}'", 
                                   widget_start_a, widget_end_a, widget_start_b, widget_end_b)
                differences_found = True
            elif tag == 'insert':
                # Get widget positions BEFORE inserting
                widget_start_a = self.text_a.index("end-1c")
                widget_start_b = self.text_b.index("end-1c")
                
                self._insert_and_sync("", chunk_b, None, "added")
                
                # Get widget positions AFTER inserting
                widget_end_a = self.text_a.index("end-1c")
                widget_end_b = self.text_b.index("end-1c")
                
                self._log_difference(f"[Line A:{line_a} / B:{line_b}] [DIFFERENCE] Inserted: '{chunk_b}'", 
                                   widget_start_a, widget_end_a, widget_start_b, widget_end_b)
                differences_found = True
                
            curr_a = end_a
            curr_b = end_b
            
        # Handle remaining content
        remaining_a = text_a[curr_a:]
        remaining_b = text_b[curr_b:]
        self._insert_and_sync(remaining_a, remaining_b, "header")

        self.text_a.config(state=tk.DISABLED)
        self.text_b.config(state=tk.DISABLED)
        
        if not differences_found:
            self._log("SUCCESS: Files are identical (ignoring punctuation/whitespace).")
        else:
            self._log("Comparison complete. Differences found.")

    def _display_diff_chunked(self, text_a, text_b, norm_a, norm_b, map_a, map_b):
        """Optimized chunked comparison for large files to prevent freezing."""
        differences_found = False
        
        # Quick check if files are identical
        if norm_a == norm_b:
            self.text_a.insert(tk.END, text_a, None)
            self.text_b.insert(tk.END, text_b, None)
            self.text_a.config(state=tk.DISABLED)
            self.text_b.config(state=tk.DISABLED)
            self._log("SUCCESS: Files are identical (ignoring punctuation/whitespace).")
            return
        
        # Split into chunks for comparison
        chunk_size = CHUNK_SIZE
        num_chunks = max(len(norm_a), len(norm_b)) // chunk_size + 1
        
        self._log(f"Comparing in {num_chunks} chunks...")
        
        curr_a_norm = 0
        curr_b_norm = 0
        curr_a = 0
        curr_b = 0
        
        for chunk_idx in range(num_chunks):
            # Get chunk bounds in normalized text
            chunk_start_a = chunk_idx * chunk_size
            chunk_end_a = min((chunk_idx + 1) * chunk_size, len(norm_a))
            chunk_start_b = chunk_idx * chunk_size
            chunk_end_b = min((chunk_idx + 1) * chunk_size, len(norm_b))
            
            if chunk_start_a >= len(norm_a) and chunk_start_b >= len(norm_b):
                break
            
            # Get chunks
            chunk_norm_a = norm_a[chunk_start_a:chunk_end_a]
            chunk_norm_b = norm_b[chunk_start_b:chunk_end_b]
            
            # Quick check if chunks are identical
            if chunk_norm_a == chunk_norm_b:
                # Map back to original text
                orig_start_a = map_a[chunk_start_a] if chunk_start_a < len(map_a) else len(text_a)
                orig_end_a = map_a[chunk_end_a - 1] + 1 if chunk_end_a > chunk_start_a and chunk_end_a - 1 < len(map_a) else orig_start_a
                orig_start_b = map_b[chunk_start_b] if chunk_start_b < len(map_b) else len(text_b)
                orig_end_b = map_b[chunk_end_b - 1] + 1 if chunk_end_b > chunk_start_b and chunk_end_b - 1 < len(map_b) else orig_start_b
                
                # Insert matching content
                content_a = text_a[curr_a:orig_end_a]
                content_b = text_b[curr_b:orig_end_b]
                self._insert_and_sync(content_a, content_b, None)
                
                curr_a = orig_end_a
                curr_b = orig_end_b
            else:
                # Chunks differ - do detailed comparison of this chunk
                differences_found = True
                self._log(f"Analyzing differences in chunk {chunk_idx + 1}/{num_chunks}...")
                
                # Run detailed diff on this chunk only
                chunk_map_a = [map_a[i] - (map_a[chunk_start_a] if chunk_start_a < len(map_a) else 0) 
                              for i in range(chunk_start_a, chunk_end_a) if i < len(map_a)]
                chunk_map_b = [map_b[i] - (map_b[chunk_start_b] if chunk_start_b < len(map_b) else 0) 
                              for i in range(chunk_start_b, chunk_end_b) if i < len(map_b)]
                
                # Get original text for this chunk
                orig_start_a = map_a[chunk_start_a] if chunk_start_a < len(map_a) else len(text_a)
                orig_end_a = map_a[chunk_end_a - 1] + 1 if chunk_end_a > 0 and chunk_end_a - 1 < len(map_a) else len(text_a)
                orig_start_b = map_b[chunk_start_b] if chunk_start_b < len(map_b) else len(text_b)
                orig_end_b = map_b[chunk_end_b - 1] + 1 if chunk_end_b > 0 and chunk_end_b - 1 < len(map_b) else len(text_b)
                
                chunk_text_a = text_a[orig_start_a:orig_end_a]
                chunk_text_b = text_b[orig_start_b:orig_end_b]
                
                # Detailed diff of the chunk
                matcher = difflib.SequenceMatcher(None, chunk_norm_a, chunk_norm_b)
                
                for tag, i1, i2, j1, j2 in matcher.get_opcodes():
                    # Map indices back to chunk text
                    if i1 < len(chunk_map_a):
                        start_a_chunk = chunk_map_a[i1]
                    else:
                        start_a_chunk = len(chunk_text_a)
                    
                    if i2 > 0 and i2 - 1 < len(chunk_map_a):
                        end_a_chunk = chunk_map_a[i2 - 1] + 1
                    else:
                        end_a_chunk = start_a_chunk
                    
                    if j1 < len(chunk_map_b):
                        start_b_chunk = chunk_map_b[j1]
                    else:
                        start_b_chunk = len(chunk_text_b)
                    
                    if j2 > 0 and j2 - 1 < len(chunk_map_b):
                        end_b_chunk = chunk_map_b[j2 - 1] + 1
                    else:
                        end_b_chunk = start_b_chunk
                    
                    # Handle ignored content before this operation
                    ignored_a = chunk_text_a[curr_a - orig_start_a:start_a_chunk] if curr_a >= orig_start_a else ""
                    ignored_b = chunk_text_b[curr_b - orig_start_b:start_b_chunk] if curr_b >= orig_start_b else ""
                    if ignored_a or ignored_b:
                        self._insert_and_sync(ignored_a, ignored_b, "header")
                    
                    # Handle the meaningful content
                    content_a_chunk = chunk_text_a[start_a_chunk:end_a_chunk]
                    content_b_chunk = chunk_text_b[start_b_chunk:end_b_chunk]
                    
                    if tag == 'equal':
                        self._insert_and_sync(content_a_chunk, content_b_chunk, None)
                    elif tag == 'replace':
                        widget_start_a = self.text_a.index("end-1c")
                        widget_start_b = self.text_b.index("end-1c")
                        self._insert_and_sync(content_a_chunk, content_b_chunk, "removed", "added")
                        widget_end_a = self.text_a.index("end-1c")
                        widget_end_b = self.text_b.index("end-1c")
                        self._log_difference(f"[Chunk {chunk_idx+1}] Replaced: '{content_a_chunk[:50]}...' with '{content_b_chunk[:50]}...'",
                                           widget_start_a, widget_end_a, widget_start_b, widget_end_b)
                    elif tag == 'delete':
                        widget_start_a = self.text_a.index("end-1c")
                        widget_start_b = self.text_b.index("end-1c")
                        self._insert_and_sync(content_a_chunk, "", "removed", None)
                        widget_end_a = self.text_a.index("end-1c")
                        widget_end_b = self.text_b.index("end-1c")
                        self._log_difference(f"[Chunk {chunk_idx+1}] Deleted: '{content_a_chunk[:50]}...'",
                                           widget_start_a, widget_end_a, widget_start_b, widget_end_b)
                    elif tag == 'insert':
                        widget_start_a = self.text_a.index("end-1c")
                        widget_start_b = self.text_b.index("end-1c")
                        self._insert_and_sync("", content_b_chunk, None, "added")
                        widget_end_a = self.text_a.index("end-1c")
                        widget_end_b = self.text_b.index("end-1c")
                        self._log_difference(f"[Chunk {chunk_idx+1}] Inserted: '{content_b_chunk[:50]}...'",
                                           widget_start_a, widget_end_a, widget_start_b, widget_end_b)
                    
                    curr_a = orig_start_a + end_a_chunk
                    curr_b = orig_start_b + end_b_chunk
                
                # Move to end of chunk
                curr_a = orig_end_a
                curr_b = orig_end_b

            
            curr_a_norm = chunk_end_a
            curr_b_norm = chunk_end_b
        
        # Handle any remaining content
        if curr_a < len(text_a) or curr_b < len(text_b):
            self._insert_and_sync(text_a[curr_a:], text_b[curr_b:], None)
        
        self.text_a.config(state=tk.DISABLED)
        self.text_b.config(state=tk.DISABLED)
        
        if not differences_found:
            self._log("SUCCESS: Files are identical (ignoring punctuation/whitespace).")
        else:
            self._log(f"Comparison complete. Differences found (chunks processed: {num_chunks}).")

    def _compare_summary_mode(self, text_a, text_b):
        """Lightweight comparison mode for large files - shows summary instead of full diff."""
        self._clear_log()
        self._log(f"Processing large files ({len(text_a) + len(text_b)} bytes total)...")
        self._log("Summary mode: Results only, no full text display.")
        
        # Clear text widgets
        self.text_a.config(state=tk.NORMAL)
        self.text_b.config(state=tk.NORMAL)
        self.text_a.delete(1.0, tk.END)
        self.text_b.delete(1.0, tk.END)
        
        # Normalize
        norm_a, _ = self.normalize_text(text_a)
        norm_b, _ = self.normalize_text(text_b)
        
        # Quick comparison
        if norm_a == norm_b:
            self.text_a.insert(tk.END, "✓ Files are IDENTICAL\n\n(ignoring punctuation/whitespace)\n\nOriginal text is not displayed in summary mode for large files.", "header")
            self.text_b.insert(tk.END, "✓ Files are IDENTICAL\n\n(ignoring punctuation/whitespace)\n\nOriginal text is not displayed in summary mode for large files.", "header")
            self._log("SUCCESS: Files are identical (ignoring punctuation/whitespace).")
        else:
            # Show statistics
            diff_count = sum(1 for a, b in zip(norm_a, norm_b) if a != b)
            self.text_a.insert(tk.END, f"✗ Files are DIFFERENT\n\n", "header")
            self.text_a.insert(tk.END, f"Differences detected: ~{diff_count} characters differ\n", "header")
            self.text_a.insert(tk.END, f"\nSource length: {len(norm_a)} chars (normalized)\n", "header")
            self.text_a.insert(tk.END, f"\nOriginal text is not displayed in summary mode for large files.", "header")
            
            self.text_b.insert(tk.END, f"✗ Files are DIFFERENT\n\n", "header")
            self.text_b.insert(tk.END, f"Differences detected: ~{diff_count} characters differ\n", "header")
            self.text_b.insert(tk.END, f"\nTarget length: {len(norm_b)} chars (normalized)\n", "header")
            self.text_b.insert(tk.END, f"\nOriginal text is not displayed in summary mode for large files.", "header")
            
            self._log(f"Files are DIFFERENT: approximately {diff_count} characters differ.")
        
        self.text_a.config(state=tk.DISABLED)
        self.text_b.config(state=tk.DISABLED)


    def _insert_and_sync(self, content_a, content_b, tag_a, tag_b=None):
        # If tag_b is not provided, use tag_a (for symmetric tags like 'header')
        # Actually for replace/delete/insert we pass specific tags.
        if tag_b is None and tag_a == "header":
            tag_b = "header"
            
        # Insert content
        if content_a:
            self.text_a.insert(tk.END, content_a, tag_a)
        if content_b:
            self.text_b.insert(tk.END, content_b, tag_b)
            
        # Sync newlines
        newlines_a = content_a.count('\n')
        newlines_b = content_b.count('\n')
        
        if newlines_a > newlines_b:
            self.text_b.insert(tk.END, '\n' * (newlines_a - newlines_b))
        elif newlines_b > newlines_a:
            self.text_a.insert(tk.END, '\n' * (newlines_b - newlines_a))

    def _log(self, message):
        """Log a generic message without mapping (e.g., start/completion)."""
        self.log_text.insert(tk.END, f"[{self.log_counter}] {message}\n")
        self.log_counter += 1
        self.log_text.see(tk.END)

    def _log_difference(self, message, widget_start_a, widget_end_a, widget_start_b, widget_end_b):
        """Log a difference entry and store its mapping for interactive highlighting.
        Each entry gets a unique tag based on the current log line number.
        """
        # Get the position where we'll insert (before insertion)
        line_start = self.log_text.index("end-1c")
        tag_name = f"diff_{len(self.log_mappings)}"
        # Store WIDGET positions, not original text positions
        self.log_mappings[tag_name] = (widget_start_a, widget_end_a, widget_start_b, widget_end_b)
        
        # Insert the message with log ID
        self.log_text.insert(tk.END, f"[{self.log_counter}] {message}\n")
        self.log_counter += 1
        
        # Get the position after insertion (should be start of next line)
        line_end = self.log_text.index("end-1c")
        
        # Apply tag to the inserted line
        self.log_text.tag_add(tag_name, line_start, line_end)
        
        # Make it look clickable with better styling
        self.log_text.tag_config(tag_name, foreground="#4fc3f7", underline=True)
        
        # Add hover effect (cursor change)
        self.log_text.tag_bind(tag_name, "<Enter>", lambda e: self.log_text.config(cursor="hand2"))
        self.log_text.tag_bind(tag_name, "<Leave>", lambda e: self.log_text.config(cursor=""))
        
        self.log_text.see(tk.END)
        
        print(f"Tagged {tag_name} from {line_start} to {line_end}, widget positions: A[{widget_start_a}:{widget_end_a}] B[{widget_start_b}:{widget_end_b}]")  # Debug

    def _on_log_click(self, event):
        """Handle click on a log entry: highlight corresponding text in both panes."""
        print(f"Click detected at {event.x}, {event.y}")  # Debug
        
        index = self.log_text.index(f"@{event.x},{event.y}")
        print(f"Index: {index}")  # Debug
        
        # Find tags at this index (ignore default tags)
        tags = self.log_text.tag_names(index)
        print(f"Tags at index: {tags}")  # Debug
        
        diff_tag = None
        for t in tags:
            if t.startswith("diff_"):
                diff_tag = t
                break
        
        if not diff_tag:
            print("No diff tag found")  # Debug
            return
        
        print(f"Found diff tag: {diff_tag}")  # Debug
        
        # Retrieve mapping
        mapping = self.log_mappings.get(diff_tag, (None, None, None, None))
        start_a, end_a, start_b, end_b = mapping
        
        print(f"Mapping: {mapping}")  # Debug
        
        if start_a is None:
            print("No mapping found")  # Debug
            return
        
        # Enable text widgets to modify tags
        self.text_a.config(state=tk.NORMAL)
        self.text_b.config(state=tk.NORMAL)
        
        # Clear previous highlights
        if self.current_highlight_tag:
            self.text_a.tag_remove(self.current_highlight_tag, "1.0", tk.END)
            self.text_b.tag_remove(self.current_highlight_tag, "1.0", tk.END)
        
        # Apply new highlight
        self.current_highlight_tag = "active_highlight"
        
        print(f"Adding highlight A: {start_a} to {end_a}")  # Debug
        print(f"Adding highlight B: {start_b} to {end_b}")  # Debug
        
        self.text_a.tag_add(self.current_highlight_tag, start_a, end_a)
        self.text_b.tag_add(self.current_highlight_tag, start_b, end_b)
        
        # Raise the highlight tag priority so it shows on top of other tags
        self.text_a.tag_raise(self.current_highlight_tag)
        self.text_b.tag_raise(self.current_highlight_tag)
        
        # Disable text widgets again
        self.text_a.config(state=tk.DISABLED)
        self.text_b.config(state=tk.DISABLED)
        
        # Ensure visibility - scroll to show the highlighted text
        self.text_a.see(start_a)
        self.text_b.see(start_b)
        
        print("Highlight applied successfully")  # Debug

    def _clear_log(self):
        self.log_text.delete(1.0, tk.END)
        self.log_mappings = {}  # Clear mappings when clearing log
        self.log_counter = 0  # Reset log counter

    def _increase_font_size(self):
        """Increase font size for all text widgets."""
        self.text_font_size = min(self.text_font_size + 1, 32)  # Max 32
        self.log_font_size = min(self.log_font_size + 1, 32)
        self._update_fonts()

    def _decrease_font_size(self):
        """Decrease font size for all text widgets."""
        self.text_font_size = max(self.text_font_size - 1, 8)  # Min 8
        self.log_font_size = max(self.log_font_size - 1, 8)
        self._update_fonts()

    def _update_fonts(self):
        """Apply current font sizes to all text widgets."""
        self.text_a.config(font=("Menlo", self.text_font_size))
        self.text_b.config(font=("Menlo", self.text_font_size))
        self.log_text.config(font=("Menlo", self.log_font_size))


if __name__ == "__main__":
    try:
        logging.info("Starting application...")
        root = TkinterDnD.Tk()
        app = TextValidApp(root)
        root.mainloop()
    except Exception as e:
        error_msg = f"An error occurred:\n{str(e)}\n\nTraceback:\n{traceback.format_exc()}"
        logging.critical(error_msg)
        try:
            # Try to show error in GUI if possible
            import tkinter.messagebox
            # If root exists but mainloop failed, we might need a new root for the messagebox
            # or just use the existing one if it's not destroyed.
            # For safety, we'll try to use the existing root if available, or create a minimal one.
            if 'root' in locals():
                root.withdraw() # Hide main window if it exists
            
            err_root = tk.Tk()
            err_root.withdraw()
            tkinter.messagebox.showerror("Critical Error", error_msg)
            err_root.destroy()
        except:
            # If GUI fails entirely, just print to stderr
            print(error_msg)
