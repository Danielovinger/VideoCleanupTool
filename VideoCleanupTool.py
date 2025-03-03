import os
import subprocess
import shlex
import json
import tkinter as tk
from tkinter import ttk, filedialog, messagebox

from send2trash import send2trash

ASPECT_RATIOS = {
    "All":   (None, None),  
    "16:9":  (16, 9),
    "4:3":   (4, 3),
    "1:1":   (1, 1),
    "21:9":  (21, 9),
    "9:16":  (9, 16)
}

def safe_send_to_trash(path):
    """
    Converts 'path' to an absolute, normalized Windows path
    and then calls send2trash. This helps avoid the '\\\\?\\' path issue.
    """
    normalized_path = os.path.normpath(os.path.abspath(path))
    send2trash(normalized_path)

def get_video_metadata(file_path):
    """
    Uses ffprobe to return a dict with video metadata:
      - duration (float)
      - width (int)
      - height (int)
    Returns None if file isn't readable as video or ffprobe fails.
    """
    cmd = f'ffprobe -v quiet -print_format json -show_streams "{file_path}"'
    try:
        result = subprocess.run(
            shlex.split(cmd),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            universal_newlines=True
        )
        if result.returncode != 0:
            return None

        data = json.loads(result.stdout)
        for stream in data.get('streams', []):
            if stream.get('codec_type') == 'video':
                duration_str = stream.get('duration', '0')
                duration = float(duration_str) if duration_str else 0.0
                width = stream.get('width', 0)
                height = stream.get('height', 0)
                return {
                    'duration': duration,
                    'width': width,
                    'height': height
                }
        return None
    except Exception as e:
        print(f"Error reading metadata for {file_path}: {e}")
        return None

def cleanup_videos(folder_path, min_duration, ratio_tuple, progress_var, root):
    """
    Scans ONLY the top-level folder (no subfolders),
    checks each video’s duration and aspect ratio,
    and sends matching videos to Recycle Bin.

    - If min_duration > 0, we delete videos below that duration.
    - If min_duration == 0, ignore duration entirely.
    - If ratio_tuple == (None, None), ignore aspect ratio checks.
    - Otherwise, delete only if aspect ratio matches (within tolerance).

    folder_path   : the folder selected by the user
    min_duration  : float, 0 means ignore time
    ratio_tuple   : (None, None) => "All" ratio
    progress_var  : tkinter variable to update the progress bar
    root          : reference to main Tk window (for .update())
    """
    all_files = []
    # Will only walk the top-level folder by clearing subdirs, remove dirs.clear() if you want to include subfolders
    for root_dir, dirs, files in os.walk(folder_path):
        dirs.clear()  # <- prevents descending into subfolders REMOVE JUST THIS LINE TO INCLUDE SUBFOLDERS
        for f in files:
            if f.lower().endswith(('.mp4', '.mov', '.avi', '.mkv', '.flv', '.wmv')):
                file_path = os.path.join(root_dir, f)
                all_files.append(file_path)

    total_files = len(all_files)
    if total_files == 0:
        messagebox.showinfo("No Videos Found", "No video files found in the selected folder.")
        return

    check_aspect_ratio = (ratio_tuple != (None, None))
    if check_aspect_ratio:
        target_aspect_float = ratio_tuple[0] / ratio_tuple[1] if ratio_tuple[1] != 0 else 0
        ratio_tolerance = 0.01  

    deleted_count = 0

    for i, file_path in enumerate(all_files):
        metadata = get_video_metadata(file_path)
        if not metadata:
            pass  
        else:
            duration = metadata['duration']
            width = metadata['width']
            height = metadata['height']

            
            if min_duration > 0:
                if duration < min_duration:  
                    if check_aspect_ratio:
                        if height > 0:
                            file_aspect = width / height
                            if abs(file_aspect - target_aspect_float) < ratio_tolerance:
                                safe_send_to_trash(file_path)
                                deleted_count += 1
                    else:
                        
                        safe_send_to_trash(file_path)
                        deleted_count += 1
            else:
                
                if check_aspect_ratio:
                    if height > 0:
                        file_aspect = width / height
                        if abs(file_aspect - target_aspect_float) < ratio_tolerance:
                            safe_send_to_trash(file_path)
                            deleted_count += 1
                else:
                    
                    safe_send_to_trash(file_path)
                    deleted_count += 1

        
        progress_var.set((i + 1) / total_files * 100)
        root.update_idletasks()

    messagebox.showinfo("Finished",
                        f"Scan complete. Sent {deleted_count} file(s) to Recycle Bin.\nFolder: {folder_path}")

def run_cleanup():
    """ Triggered by the 'Run' button """
    folder_path = folder_path_var.get()
    if not folder_path or not os.path.isdir(folder_path):
        messagebox.showerror("Error", "Please select a valid folder first.")
        return

    try:
        seconds_str = time_entry.get().strip()
        min_duration = float(seconds_str)
        if min_duration < 0:
            raise ValueError
    except ValueError:
        messagebox.showerror("Error", "Please enter a valid non-negative number for seconds.")
        return

    ratio_label = aspect_ratio_var.get()
    if ratio_label not in ASPECT_RATIOS:
        messagebox.showerror("Error", "Please select a valid aspect ratio.")
        return
    ratio_tuple = ASPECT_RATIOS[ratio_label]

    cleanup_videos(folder_path, min_duration, ratio_tuple, progress_var, root)

def select_folder():
    """ Prompts user to choose a folder via Explorer dialog. """
    chosen_path = filedialog.askdirectory(title="Select Folder with Videos")
    if chosen_path:
        folder_path_var.set(chosen_path)

def show_time_tooltip():
    """
    Show a small popup explaining the '0' behavior and caution.
    """
    messagebox.showinfo(
        "Time Threshold Help",
        "Enter '0' to ignore the time variable entirely.\n\n"
        "Warning: If you combine '0' with aspect ratio 'All', the tool "
        "will remove *all* video files in the folder!"
    )

def main():
    global root, folder_path_var, time_entry, aspect_ratio_var, progress_var

    root = tk.Tk()
    root.title("Video Cleanup Tool")

    folder_frame = ttk.Frame(root, padding="10 10 10 10")
    folder_frame.pack(fill='x', expand=True)

    select_button = ttk.Button(folder_frame, text="Select Folder", command=select_folder)
    select_button.pack(side='left', padx=(0, 10))

    folder_path_var = tk.StringVar(value="")
    folder_label = ttk.Label(folder_frame, textvariable=folder_path_var, width=60, anchor="w")
    folder_label.pack(side='left', fill='x', expand=True)

    input_frame = ttk.Frame(root, padding="10 10 10 10")
    input_frame.pack(fill='x', expand=True)

    ttk.Label(input_frame, text="Delete if shorter than (sec):").pack(side='left', padx=5)
    time_entry = ttk.Entry(input_frame, width=5)
    time_entry.insert(0, "10")  
    time_entry.pack(side='left', padx=5)

    question_button = ttk.Button(input_frame, text="?", width=2, command=show_time_tooltip)
    question_button.pack(side='left', padx=5)

    aspect_ratio_var = tk.StringVar()
    aspect_ratio_box = ttk.Combobox(input_frame, textvariable=aspect_ratio_var, width=5, state="readonly")
    aspect_ratio_box['values'] = list(ASPECT_RATIOS.keys())  
    aspect_ratio_box.current(1)  
    aspect_ratio_box.pack(side='left', padx=5)

    run_button = ttk.Button(input_frame, text="Run", command=run_cleanup)
    run_button.pack(side='left', padx=(10, 0))

    progress_frame = ttk.Frame(root, padding="10 10 10 10")
    progress_frame.pack(fill='x', expand=True)

    progress_var = tk.DoubleVar(value=0.0)
    progress_bar = ttk.Progressbar(progress_frame, variable=progress_var, maximum=100)
    progress_bar.pack(fill='x', expand=True)

    root.mainloop()

if __name__ == "__main__":
    main()
