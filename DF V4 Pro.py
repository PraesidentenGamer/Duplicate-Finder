import os
import hashlib
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import zipfile
import csv
from collections import Counter
import datetime
import glob
import tkinter as tk
from tkinter import messagebox
import sys
import tkinter as tk
from tkinter import simpledialog, messagebox
import sys
# --- Lizenzprüfung ---
def check_license():
    root = tk.Tk()
    root.withdraw()

    # Dein festgelegter Lizenzschlüssel
    richtiger_key = "PRO-GO1JK-W12YS-4CPZZ-MGWNE-YJACK"

    # Nutzerabfrage
    user_key = simpledialog.askstring("Lizenzschlüssel", "Bitte gib deinen Lizenzschlüssel ein:")

    if user_key != richtiger_key:
        messagebox.showerror("Lizenzfehler", "Ungültiger Lizenzschlüssel! Das Programm wird beendet.")
        root.destroy()
        sys.exit(1)

    root.destroy()

check_license()

# --- Einstellungen Backup ---
BACKUP_FOLDER = "backups"

class DuplicateFinderApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("🧐 Duplicate Finder Pro")
        self.geometry("900x600")
        self.resizable(True, True)
        self.configure(bg="#1e1e2f")
        
        self.folder_path = tk.StringVar()
        self.min_size = tk.IntVar(value=1)
        self.file_types = tk.StringVar(value="*.*")
        self.error_log = []
        self.duplicates = {}
        self.backup_zip_path = None
        self.stop_event = threading.Event()
        
        self.create_widgets()
        
    def create_widgets(self):
        style = ttk.Style(self)
        style.theme_use('clam')
        style.configure("TLabel", background="#1e1e2f", foreground="#ddd", font=("Segoe UI", 10))
        style.configure("TButton", font=("Segoe UI Semibold", 10))
        style.configure("Treeview", font=("Segoe UI", 9), background="#2d2d44", foreground="#ddd",
                        fieldbackground="#2d2d44")
        style.map('TButton', foreground=[('pressed', 'white'), ('active', 'white')],
                  background=[('pressed', '#0052cc'), ('active', '#0066ff')])
        style.configure("TProgressbar", troughcolor="#252535", background="#4caf50")
        
        # Ordnerauswahl
        frm_top = tk.Frame(self, bg="#1e1e2f")
        frm_top.pack(fill=tk.X, padx=15, pady=10)
        
        ttk.Label(frm_top, text="Ordner zum Durchsuchen:").pack(side=tk.LEFT)
        ttk.Entry(frm_top, textvariable=self.folder_path, width=55).pack(side=tk.LEFT, padx=8)
        ttk.Button(frm_top, text="...", command=self.browse_folder, width=3).pack(side=tk.LEFT)
        
        # Optionen
        frm_opts = tk.Frame(self, bg="#1e1e2f")
        frm_opts.pack(fill=tk.X, padx=15)
        
        ttk.Label(frm_opts, text="Dateitypen (z.B. *.jpg;*.png):").grid(row=0, column=0, sticky=tk.W)
        ttk.Entry(frm_opts, textvariable=self.file_types, width=30).grid(row=0, column=1, sticky=tk.W, padx=8)
        
        ttk.Label(frm_opts, text="Min. Dateigröße (KB):").grid(row=0, column=2, sticky=tk.W)
        ttk.Spinbox(frm_opts, from_=0, to=100000, textvariable=self.min_size, width=8).grid(row=0, column=3, sticky=tk.W, padx=8)
        
        # Buttons Scan/Stop/Delete/Export
        frm_btn = tk.Frame(self, bg="#1e1e2f")
        frm_btn.pack(fill=tk.X, padx=15, pady=10)
        
        self.btn_scan = ttk.Button(frm_btn, text="Scan starten", command=self.start_scan)
        self.btn_scan.pack(side=tk.LEFT, padx=6)
        
        self.btn_stop = ttk.Button(frm_btn, text="Scan abbrechen", command=self.stop_scan, state=tk.DISABLED)
        self.btn_stop.pack(side=tk.LEFT, padx=6)
        
        self.btn_delete = ttk.Button(frm_btn, text="Ausgewählte löschen", command=self.delete_selected, state=tk.DISABLED)
        self.btn_delete.pack(side=tk.LEFT, padx=6)
        
        self.btn_export = ttk.Button(frm_btn, text="Ergebnisse exportieren (CSV)", command=self.export_csv, state=tk.DISABLED)
        self.btn_export.pack(side=tk.LEFT, padx=6)
        
        self.btn_show_errors = ttk.Button(frm_btn, text="Fehler anzeigen", command=self.show_errors, state=tk.DISABLED)
        self.btn_show_errors.pack(side=tk.RIGHT, padx=6)
        
        # Fortschritt und Statistiken
        self.label_progress = ttk.Label(self, text="Bereit", anchor=tk.CENTER, font=("Segoe UI Semibold", 11), background="#1e1e2f")
        self.label_progress.pack(fill=tk.X, padx=15)
        
        self.progress = ttk.Progressbar(self, orient=tk.HORIZONTAL, length=800, mode='determinate')
        self.progress.pack(padx=15, pady=5)
        
        # Treeview für Ergebnisse
        columns = ("Gruppe", "Dateipfad", "Dateigröße (KB)", "Dateityp")
        self.tree = ttk.Treeview(self, columns=columns, show='headings', selectmode="extended")
        for col in columns:
            self.tree.heading(col, text=col, command=lambda c=col: self.treeview_sort_column(self.tree, c, False))
            self.tree.column(col, anchor=tk.W, width=280 if col=="Dateipfad" else 120)
        self.tree.pack(expand=True, fill=tk.BOTH, padx=15, pady=10)
        
        # Scrollbar Treeview
        scrollbar = ttk.Scrollbar(self, orient=tk.VERTICAL, command=self.tree.yview)
        scrollbar.place(relx=0.98, rely=0.25, relheight=0.6)
        self.tree.configure(yscroll=scrollbar.set)
        
        # Statistik-Label
        self.label_stats = ttk.Label(self, text="", background="#1e1e2f", font=("Segoe UI", 10))
        self.label_stats.pack(fill=tk.X, padx=15, pady=(0,10))
    
    def browse_folder(self):
        path = filedialog.askdirectory()
        if path:
            self.folder_path.set(path)
    
    def start_scan(self):
        folder = self.folder_path.get()
        if not os.path.isdir(folder):
            messagebox.showwarning("Ungültiger Ordner", "Bitte wähle einen gültigen Ordner aus.")
            return
        self.btn_scan.config(state=tk.DISABLED)
        self.btn_stop.config(state=tk.NORMAL)
        self.btn_delete.config(state=tk.DISABLED)
        self.btn_export.config(state=tk.DISABLED)
        self.error_log.clear()
        self.duplicates.clear()
        self.tree.delete(*self.tree.get_children())
        self.label_stats.config(text="")
        self.progress.config(value=0)
        self.label_progress.config(text="Starte Scan...")
        self.stop_event.clear()
        
        threading.Thread(target=self.scan_duplicates, daemon=True).start()
    
    def stop_scan(self):
        self.stop_event.set()
    
    def scan_duplicates(self):
        try:
            folder = self.folder_path.get()
            min_size_bytes = self.min_size.get() * 1024
            patterns = [p.strip() for p in self.file_types.get().split(';') if p.strip()]
            max_workers = 8
            
            # Backup aufräumen (ältere Backups löschen)
            self.cleanup_backups()
            
            # Phase 1: Alle Dateien sammeln
            all_files = []
            for pattern in patterns:
                all_files.extend(glob.glob(os.path.join(folder, '**', pattern), recursive=True))
            
            all_files = [f for f in all_files if os.path.isfile(f) and os.path.getsize(f) >= min_size_bytes]
            total_files = len(all_files)
            if total_files == 0:
                self.after(0, lambda: self.label_progress.config(text="Keine Dateien gefunden mit den Filterkriterien."))
                self.scan_finished()
                return
            
            # Phase 2: Gruppieren nach Dateigröße
            size_map = {}
            for i, file in enumerate(all_files, 1):
                if self.stop_event.is_set():
                    self.scan_finished(aborted=True)
                    return
                size_map.setdefault(os.path.getsize(file), []).append(file)
                self.update_progress(i, total_files, "Dateien gruppieren")
            
            # Nur Größen mit mind. 2 Dateien behalten
            candidates = [files for files in size_map.values() if len(files) > 1]
            
            # Phase 3: Schnell-Hash (erste 4kB)
            def quick_hash(path):
                try:
                    with open(path, 'rb') as f:
                        data = f.read(4096)
                    return hashlib.md5(data).hexdigest()
                except Exception as e:
                    self.error_log.append(f"Fehler bei Schnellhash {path}: {e}")
                    return None
            
            quickhash_map = {}
            total_qh = sum(len(group) for group in candidates)
            count_qh = 0
            for group in candidates:
                for file in group:
                    if self.stop_event.is_set():
                        self.scan_finished(aborted=True)
                        return
                    qh = quick_hash(file)
                    if qh:
                        quickhash_map.setdefault(qh, []).append(file)
                    count_qh += 1
                    self.update_progress(count_qh, total_qh, "Schnellhash berechnen")
            
            # Phase 4: Vollhash (ganze Datei)
            def full_hash(path):
                try:
                    h = hashlib.sha256()
                    with open(path, 'rb') as f:
                        while True:
                            if self.stop_event.is_set():
                                return path, None
                            chunk = f.read(8192)
                            if not chunk:
                                break
                            h.update(chunk)
                    return path, h.hexdigest()
                except Exception as e:
                    self.error_log.append(f"Fehler bei Vollhash {path}: {e}")
                    return path, None
            
            files_for_fullhash = [f for fgroup in quickhash_map.values() if len(fgroup) > 1 for f in fgroup]
            total_fullhash = len(files_for_fullhash)
            fullhash_map = {}
            done_count = 0
            
            with ThreadPoolExecutor(max_workers=max_workers) as executor:
                futures = {executor.submit(full_hash, f): f for f in files_for_fullhash}
                for future in as_completed(futures):
                    if self.stop_event.is_set():
                        self.scan_finished(aborted=True)
                        return
                    fpath, fhash = future.result()
                    if fhash:
                        fullhash_map.setdefault(fhash, []).append(fpath)
                    done_count += 1
                    self.update_progress(done_count, total_fullhash, "Vollhash berechnen")
            
            # Duplikate filtern
            self.duplicates = {h: files for h, files in fullhash_map.items() if len(files) > 1}
            
            self.after(0, self.show_duplicates)
        except Exception as e:
            self.error_log.append(f"Unbekannter Fehler: {e}")
            self.scan_finished()
    
    def update_progress(self, current, total, text):
        percent = int(current / total * 100) if total else 0
        self.after(0, lambda: self.progress.config(value=percent))
        self.after(0, lambda: self.label_progress.config(text=f"{text} ({current}/{total}) - {percent}%"))
    
    def scan_finished(self, aborted=False):
        self.after(0, lambda: self.btn_scan.config(state=tk.NORMAL))
        self.after(0, lambda: self.btn_stop.config(state=tk.DISABLED))
        self.after(0, lambda: self.progress.config(value=0))
        if aborted:
            self.after(0, lambda: self.label_progress.config(text="Scan abgebrochen."))
            return
        self.after(0, lambda: self.label_progress.config(text="Scan abgeschlossen."))
        if self.duplicates:
            self.after(0, lambda: self.btn_delete.config(state=tk.NORMAL))
            self.after(0, lambda: self.btn_export.config(state=tk.NORMAL))
        if self.error_log:
            self.after(0, lambda: self.btn_show_errors.config(state=tk.NORMAL))
        self.update_stats()
    
    def show_duplicates(self):
        self.tree.delete(*self.tree.get_children())
        group_num = 1
        total_saved_bytes = 0
        filetype_counter = Counter()
        
        for hash_val, files in self.duplicates.items():
            for f in files:
                size = os.path.getsize(f)
                total_saved_bytes += size
                ext = os.path.splitext(f)[1].lower()
                filetype_counter[ext] += 1
                size_kb = size // 1024
                self.tree.insert("", tk.END, values=(group_num, f, size_kb, ext))
            group_num += 1
        
        gesparter_speicher_mb = total_saved_bytes / (1024*1024)
        self.label_progress.config(text=f"Gefundene Duplikate: {len(self.duplicates)} Gruppen. Gesparter Speicher ca. {gesparter_speicher_mb:.2f} MB")
        self.update_stats()
        self.scan_finished()
    
    def update_stats(self):
        if not self.duplicates:
            self.label_stats.config(text="Keine Duplikate gefunden.")
            return
        # Berechne gesparter Speicher und häufigste Dateitypen
        total_saved = 0
        ext_counter = Counter()
        for files in self.duplicates.values():
            # Speicher gespart = Summe aller Dateien - 1 Datei pro Gruppe behalten
            sizes = [os.path.getsize(f) for f in files]
            total_saved += sum(sizes) - max(sizes)
            ext_counter.update([os.path.splitext(f)[1].lower() for f in files])
        mb_saved = total_saved / (1024 * 1024)
        
        # Häufigste Dateitypen (top 3)
        common_types = ext_counter.most_common(3)
        common_str = ", ".join([f"{ext or '(kein)'}: {count}" for ext, count in common_types])
        
        self.label_stats.config(text=f"Gesparter Speicher: {mb_saved:.2f} MB | Häufigste Dateitypen: {common_str}")
    
    def delete_selected(self):
        selected = self.tree.selection()
        if not selected:
            messagebox.showinfo("Keine Auswahl", "Bitte wähle mindestens eine Datei zum Löschen aus.")
            return
        confirm = messagebox.askyesno("Löschen bestätigen", f"Sollen {len(selected)} Dateien wirklich gelöscht werden?")
        if not confirm:
            return
        errors = []
        for item in selected:
            path = self.tree.item(item, "values")[1]
            try:
                os.remove(path)
                self.tree.delete(item)
            except Exception as e:
                errors.append(f"Fehler beim Löschen {path}: {e}")
        if errors:
            messagebox.showerror("Fehler beim Löschen", "\n".join(errors))
        else:
            messagebox.showinfo("Erfolg", "Ausgewählte Dateien wurden gelöscht.")
        self.update_stats()
    
    def export_csv(self):
        if not self.duplicates:
            messagebox.showinfo("Keine Daten", "Keine Duplikate zum Exportieren vorhanden.")
            return
        path = filedialog.asksaveasfilename(defaultextension=".csv", filetypes=[("CSV Dateien", "*.csv")])
        if not path:
            return
        try:
            with open(path, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow(["Gruppe", "Dateipfad", "Dateigröße (KB)", "Dateityp"])
                group_num = 1
                for hash_val, files in self.duplicates.items():
                    for file in files:
                        size_kb = os.path.getsize(file) // 1024
                        ext = os.path.splitext(file)[1].lower()
                        writer.writerow([group_num, file, size_kb, ext])
                    group_num += 1
            messagebox.showinfo("Export erfolgreich", f"Duplikate wurden als CSV nach\n{path}\nexportiert.")
        except Exception as e:
            messagebox.showerror("Fehler", f"Fehler beim Exportieren: {e}")
    
    def show_errors(self):
        if not self.error_log:
            messagebox.showinfo("Keine Fehler", "Keine Fehler aufgetreten.")
            return
        error_window = tk.Toplevel(self)
        error_window.title("Fehlerprotokoll")
        error_window.geometry("700x400")
        error_window.configure(bg="#1e1e2f")
        
        txt = tk.Text(error_window, bg="#2d2d44", fg="#ddd", font=("Segoe UI", 10))
        txt.pack(expand=True, fill=tk.BOTH)
        txt.insert(tk.END, "\n".join(self.error_log))
        txt.config(state=tk.DISABLED)
    
    def treeview_sort_column(self, tv, col, reverse):
        l = [(tv.set(k, col), k) for k in tv.get_children('')]
        try:
            l.sort(key=lambda t: int(t[0]), reverse=reverse)
        except ValueError:
            l.sort(reverse=reverse)
        for index, (val, k) in enumerate(l):
            tv.move(k, '', index)
        tv.heading(col, command=lambda: self.treeview_sort_column(tv, col, not reverse))
    
    def cleanup_backups(self):
        if not os.path.exists(BACKUP_FOLDER):
            os.makedirs(BACKUP_FOLDER)
            return
        now = time.time()
        for f in os.listdir(BACKUP_FOLDER):
            path = os.path.join(BACKUP_FOLDER, f)
            if os.path.isfile(path):
                created = os.path.getctime(path)
                age_days = (now - created) / (60 * 60 * 24)
                if age_days > BACKUP_RETENTION_DAYS:
                    try:
                        os.remove(path)
                    except:
                        pass

if __name__ == "__main__":
    app = DuplicateFinderApp()
    app.mainloop()
