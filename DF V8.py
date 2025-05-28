import os
import hashlib
import threading
import tkinter as tk
from tkinter import filedialog, ttk, messagebox
import time
import csv
from collections import defaultdict

class DuplicateFileFinderGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Duplicate File Finder")
        self.root.geometry("1000x650")
        self.root.configure(bg="#1e1e1e")

        self.setup_ui()
        self.reset()

    def setup_ui(self):
        style = ttk.Style()
        style.theme_use("default")
        style.configure("TFrame", background="#1e1e1e")
        style.configure("TLabel", background="#1e1e1e", foreground="white", font=("Arial", 10))
        style.configure("TButton", font=("Arial", 10), padding=6)
        style.configure("TProgressbar", thickness=20)

        frame = ttk.Frame(self.root)
        frame.pack(pady=20)

        self.dir_label = ttk.Label(frame, text="Directory:")
        self.dir_label.grid(row=0, column=0, padx=5, pady=5)

        self.dir_entry = ttk.Entry(frame, width=60)
        self.dir_entry.grid(row=0, column=1, padx=5, pady=5)

        self.browse_button = ttk.Button(frame, text="Durchsuchen", command=self.browse_directory)
        self.browse_button.grid(row=0, column=2, padx=5, pady=5)

        self.start_button = ttk.Button(frame, text="Start Scan", command=self.start_scan)
        self.start_button.grid(row=0, column=3, padx=5, pady=5)

        self.pause_button = ttk.Button(frame, text="Pause", command=self.pause_scan, state='disabled')
        self.pause_button.grid(row=0, column=4, padx=5, pady=5)

        self.resume_button = ttk.Button(frame, text="Scan fortsetzen", command=self.resume_scan, state='disabled')
        self.resume_button.grid(row=0, column=5, padx=5, pady=5)

        self.stop_button = ttk.Button(frame, text="Stop", command=self.stop_scan, state='disabled')
        self.stop_button.grid(row=0, column=6, padx=5, pady=5)

        self.progress_label = ttk.Label(self.root, text="Progress: 0%")
        self.progress_label.pack(pady=5)

        self.progress = ttk.Progressbar(self.root, orient="horizontal", length=600, mode="determinate")
        self.progress.pack(pady=10)

        self.tree = ttk.Treeview(self.root, columns=("#1", "#2"), show="headings")
        self.tree.heading("#1", text="File Path")
        self.tree.heading("#2", text="Hash")
        self.tree.column("#1", width=600)
        self.tree.column("#2", width=300)
        self.tree.pack(pady=10, expand=True, fill='both')

        self.export_button = ttk.Button(self.root, text="Export CSV", command=self.export_csv)
        self.export_button.pack(pady=5)

        self.stats_label = ttk.Label(self.root, text="")
        self.stats_label.pack(pady=5)

    def reset(self):
        self.duplicates = defaultdict(list)
        self.paused = threading.Event()
        self.paused.set()
        self.stop_flag = False
        self.total_files = 0
        self.scanned_files = 0

    def browse_directory(self):
        directory = filedialog.askdirectory()
        if directory:
            self.dir_entry.delete(0, tk.END)
            self.dir_entry.insert(0, directory)

    def start_scan(self):
        self.reset()
        directory = self.dir_entry.get()
        if not directory:
            messagebox.showwarning("Warnung", "bitte wähle ein Verzeichnis")
            return

        self.start_button.config(state='disabled')
        self.pause_button.config(state='normal')
        self.stop_button.config(state='normal')

        self.tree.delete(*self.tree.get_children())
        self.duplicates.clear()

        self.scan_thread = threading.Thread(target=self.scan_files, args=(directory,))
        self.scan_thread.start()

    def pause_scan(self):
        self.paused.clear()
        self.pause_button.config(state='disabled')
        self.resume_button.config(state='normal')

    def resume_scan(self):
        self.paused.set()
        self.pause_button.config(state='normal')
        self.resume_button.config(state='disabled')

    def stop_scan(self):
        self.stop_flag = True
        self.paused.set()
        self.start_button.config(state='normal')
        self.pause_button.config(state='disabled')
        self.resume_button.config(state='disabled')
        self.stop_button.config(state='disabled')

    def update_progress(self):
        if self.total_files > 0:
            percent = (self.scanned_files / self.total_files) * 100
            self.progress["value"] = percent
            self.progress_label.config(text=f"Fortschritt: {percent:.2f}%")

    def scan_files(self, directory):
        all_files = []
        for dirpath, _, filenames in os.walk(directory):
            for filename in filenames:
                filepath = os.path.join(dirpath, filename)
                all_files.append(filepath)

        self.total_files = len(all_files)

        hashes = {}
        for filepath in all_files:
            if self.stop_flag:
                break

            while not self.paused.is_set():
                time.sleep(0.1)

            try:
                with open(filepath, "rb") as f:
                    file_hash = hashlib.md5(f.read()).hexdigest()
                    if file_hash in hashes:
                        self.duplicates[file_hash].append(filepath)
                    else:
                        hashes[file_hash] = filepath
            except Exception as e:
                print(f"Error reading file {filepath}: {e}")

            self.scanned_files += 1
            self.update_progress()

        for hash_value, file_list in self.duplicates.items():
            file_list.insert(0, hashes[hash_value])
            for file_path in file_list:
                self.tree.insert("", "end", values=(file_path, hash_value))

        self.start_button.config(state='normal')
        self.pause_button.config(state='disabled')
        self.resume_button.config(state='disabled')
        self.stop_button.config(state='disabled')
        self.stats_label.config(text=f"Scanned: {self.scanned_files} | Duplicates: {sum(len(v) for v in self.duplicates.values())}")

    def export_csv(self):
        if not self.duplicates:
            messagebox.showinfo("Info", "Keine Duplikate zum exportieren")
            return

        file_path = filedialog.asksaveasfilename(defaultextension=".csv", filetypes=[("CSV files", "*.csv")])
        if not file_path:
            return

        with open(file_path, "w", newline="") as csvfile:
            writer = csv.writer(csvfile)
            writer.writerow(["Hash", "File Path"])
            for hash_value, file_list in self.duplicates.items():
                for file_path in file_list:
                    writer.writerow([hash_value, file_path])

        messagebox.showinfo("Success", "Duplikate erfolgreich exportiert")

if __name__ == "__main__":
    root = tk.Tk()
    app = DuplicateFileFinderGUI(root)
    root.mainloop()
