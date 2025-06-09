# Subtitle Extractor GUI with SRT/ASS + VTT dual export, smart naming, progress bar and explorer

import os
import re
import subprocess
import tkinter as tk
from tkinter import filedialog, messagebox, ttk, scrolledtext
from tkinterdnd2 import DND_FILES, TkinterDnD
import webbrowser


class SubtitleExtractorApp:
    def __init__(self, root):
        self.root = root
        self.root.title("MKV Subtitle Extractor")
        self.root.geometry("800x700")

        self.mkv_file = None
        self.mkv_dir = None
        self.subtitle_info = []

        self.orig_vars = []
        self.vtt_vars = []
        self.check_buttons = []

        self.label = tk.Label(root, text="⬇️ Drag and drop an MKV file here", font=("Segoe UI", 14))
        self.label.pack(pady=10)

        self.button_frame = tk.Frame(root)
        self.button_frame.pack()

        self.select_all_btn = tk.Button(self.button_frame, text="Select All Subtitles", command=self.select_all)
        self.select_all_btn.pack(side=tk.LEFT, padx=5)

        self.open_folder_btn = tk.Button(self.button_frame, text="Open MKV Folder", command=self.open_mkv_folder)
        self.open_folder_btn.pack(side=tk.LEFT, padx=5)

        self.frame = tk.Frame(root)
        self.frame.pack(fill='both', expand=True)

        self.overwrite_var = tk.BooleanVar(value=True)
        self.overwrite_check = tk.Checkbutton(root, text="Force overwrite existing files", variable=self.overwrite_var)
        self.overwrite_check.pack(pady=5)

        self.progress = ttk.Progressbar(root, mode='determinate')
        self.progress.pack(fill='x', padx=10, pady=5)

        self.export_button = tk.Button(root, text="Export Selected Subtitles", command=self.export_subtitles, state=tk.DISABLED)
        self.export_button.pack(pady=5)

        self.log_box = scrolledtext.ScrolledText(root, wrap=tk.WORD, height=10, state='disabled', font=("Consolas", 10))
        self.log_box.pack(fill='x', padx=10, pady=10)

        self.root.drop_target_register(DND_FILES)
        self.root.dnd_bind('<<Drop>>', self.on_drop)

    def log(self, message):
        self.log_box.configure(state='normal')
        self.log_box.insert(tk.END, message + "\n")
        self.log_box.yview(tk.END)
        self.log_box.configure(state='disabled')
        print(message)

    def on_drop(self, event):
        files = self.root.tk.splitlist(event.data)
        if not files:
            return
        file = files[0]
        if not file.lower().endswith('.mkv'):
            messagebox.showerror("Error", "Only MKV files are supported.")
            return
        self.mkv_file = file
        self.mkv_dir = os.path.dirname(file)
        self.label.config(text=f"📄 Loaded: {os.path.basename(file)}")
        self.log(f"[INFO] MKV file loaded: {self.mkv_file}")
        self.list_subtitles()

    def list_subtitles(self):
        self.clear_checkboxes()
        self.log("[INFO] Analyzing subtitle streams...")

        cmd = ['ffmpeg', '-i', self.mkv_file]
        proc = subprocess.run(cmd, stderr=subprocess.PIPE, stdout=subprocess.PIPE, text=True)
        raw_output = proc.stderr
        self.log("[DEBUG] Raw ffmpeg output:\n" + raw_output)

        lines = raw_output.replace('\r\n', '\n').split('\n')
        self.subtitle_info.clear()

        i = 0
        while i < len(lines):
            line = lines[i].strip()
            match = re.match(
                r'Stream #(?P<id>0:\d+)(\((?P<lang>[a-z]{3})\))?: Subtitle: (?P<codec>\w+)(?P<desc>.*?)$', line
            )
            if match:
                stream_id = match.group("id")
                lang = match.group("lang") or "und"
                codec = match.group("codec")
                desc_raw = match.group("desc").strip()
                title = ""

                j = i + 1
                while j < len(lines) and lines[j].startswith("    "):
                    title_match = re.search(r'title\s*:\s*(.*)', lines[j])
                    if title_match:
                        title = title_match.group(1).strip()
                        break
                    j += 1

                full_label = f"{desc_raw} - {title}" if title else desc_raw or "Subtitle"
                safe_label = re.sub(r'[^\w\-]', '_', full_label)

                self.subtitle_info.append({
                    "stream_id": stream_id,
                    "lang": lang,
                    "codec": codec,
                    "desc": full_label,
                    "safe_desc": safe_label
                })
            i += 1

        if not self.subtitle_info:
            self.log("[WARN] No subtitle streams detected.")
            messagebox.showinfo("No subtitles", "No subtitle streams found in the file.")
            return

        self.log(f"[INFO] Found {len(self.subtitle_info)} subtitle stream(s):")

        for sub in self.subtitle_info:
            self.log(f"  - stream {sub['stream_id']}: lang={sub['lang']} codec={sub['codec']} desc={sub['desc']}")

            orig_var = tk.BooleanVar()
            vtt_var = tk.BooleanVar()
            label = f"[{sub['lang']}] ({sub['codec']}) {sub['desc']}"
            row = tk.Frame(self.frame)
            row.pack(fill='x', padx=10)

            cb1 = tk.Checkbutton(row, text=label, variable=orig_var, anchor='w', justify='left')
            cb1.pack(side=tk.LEFT, fill='x', expand=True)

            cb2 = tk.Checkbutton(row, text="VTT", variable=vtt_var)
            cb2.pack(side=tk.RIGHT)

            self.orig_vars.append(orig_var)
            self.vtt_vars.append(vtt_var)
            self.check_buttons.append((cb1, cb2))

        self.export_button.config(state=tk.NORMAL)

    def clear_checkboxes(self):
        for cb1, cb2 in self.check_buttons:
            cb1.destroy()
            cb2.destroy()
        self.orig_vars.clear()
        self.vtt_vars.clear()
        self.check_buttons.clear()

    def select_all(self):
        for var in self.orig_vars:
            var.set(True)

    def open_mkv_folder(self):
        if self.mkv_dir:
            os.startfile(self.mkv_dir)

    def export_subtitles(self):
        export_dir = filedialog.askdirectory(title="Choose export folder", initialdir=self.mkv_dir)
        if not export_dir:
            self.log("[WARN] Export canceled - no folder selected.")
            return

        basename = os.path.splitext(os.path.basename(self.mkv_file))[0]
        overwrite = self.overwrite_var.get()

        # Count duplicates per language
        lang_count = {}
        for i, sub in enumerate(self.subtitle_info):
            if self.orig_vars[i].get():
                lang = sub['lang']
                lang_count[lang] = lang_count.get(lang, 0) + 1

        vtt_outputs = []
        orig_outputs = []

        total_tasks = sum(var.get() for var in self.orig_vars + self.vtt_vars)
        if total_tasks == 0:
            messagebox.showwarning("No subtitles selected", "Please select at least one subtitle to export.")
            return

        self.progress['value'] = 0
        step = 100 / total_tasks

        vtt_count = 0
        for i, sub in enumerate(self.subtitle_info):
            lang = sub['lang']
            codec = sub['codec']
            ext = "srt" if codec.lower() == "subrip" else "ass"

            if self.orig_vars[i].get():
                # filename formatting
                if lang_count[lang] > 1:
                    filename = f"{basename}.{lang}.{sub['safe_desc']}.{ext}"
                else:
                    filename = f"{basename}.{lang}.{ext}"
                output_path = os.path.join(export_dir, filename)

                cmd = [
                    'ffmpeg',
                    '-y' if overwrite else '-n',
                    '-i', self.mkv_file,
                    '-map', sub["stream_id"],
                    output_path
                ]
                self.log(f"[EXPORT] Original: {' '.join(cmd)}")
                result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
                self.log(result.stdout)
                orig_outputs.append(output_path)
                self.progress['value'] += step
                self.root.update_idletasks()

            if self.vtt_vars[i].get():
                vtt_count += 1
                vtt_outputs.append(i)

        vtt_filenames = []
        if vtt_outputs:
            for idx, i in enumerate(vtt_outputs):
                sub = self.subtitle_info[i]
                is_ass = sub["codec"].lower() == "ass"
                temp_ext = "srt" if sub["codec"].lower() == "subrip" else "ass"
                temp_file = os.path.join(export_dir, f"__temp__{i}.{temp_ext}")
                temp_srt_file = os.path.join(export_dir, f"__temp__{i}.srt") if is_ass else temp_file
        
                vtt_name = f"{basename}.vtt" if len(vtt_outputs) == 1 else f"subtitle{idx + 1}.vtt"
                vtt_path = os.path.join(export_dir, vtt_name)
        
                # Step 1: Extract and convert to SRT directly from MKV stream
                extract_to_srt_cmd = [
                    'ffmpeg', '-y',
                    '-i', f'"{self.mkv_file}"',
                    '-map', sub["stream_id"],
                    '-c:s', 'srt',
                    f'"{temp_srt_file}"'
                ]
                self.log(f"[EXPORT] Extracting and converting to SRT: {' '.join(extract_to_srt_cmd)}")
                subprocess.run(' '.join(extract_to_srt_cmd), shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
                
                # Step 2: Convert SRT to VTT
                convert_to_vtt_cmd = ['ffmpeg', '-y', '-i', f'"{temp_srt_file}"', f'"{vtt_path}"']
                self.log(f"[EXPORT] Converting to VTT: {' '.join(convert_to_vtt_cmd)}")
                subprocess.run(' '.join(convert_to_vtt_cmd), shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)

                
                # Cleanup
                #if os.path.exists(temp_file):
                    #os.remove(temp_file)
                #if is_ass and os.path.exists(temp_srt_file):
                #    os.remove(temp_srt_file)
        
                self.progress['value'] += step
                self.root.update_idletasks()
     
        self.log("[DONE] Export complete.")
        messagebox.showinfo("Export Complete", f"{len(orig_outputs)} original + {len(vtt_outputs)} VTT subtitles exported to:\n{export_dir}")
        self.progress['value'] = 100


if __name__ == "__main__":
    root = TkinterDnD.Tk()
    app = SubtitleExtractorApp(root)
    root.mainloop()
