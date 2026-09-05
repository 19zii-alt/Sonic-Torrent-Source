import sys
import os
import time
import string
import ctypes
import winreg
import shutil
from tkinter import Tk
from tkinter.filedialog import askopenfilename
import libtorrent as lt
from colorama import init, Fore, Style

# Initialize Colorama
init(autoreset=True)

# Set CMD / Terminal Window Always On Top
def set_window_always_on_top():
    if os.name == "nt":
        hwnd = ctypes.windll.kernel32.GetConsoleWindow()
        if hwnd:
            # HWND_TOPMOST = -1, SWP_NOMOVE = 0x0002, SWP_NOSIZE = 0x0001
            ctypes.windll.user32.SetWindowPos(hwnd, -1, 0, 0, 0, 0, 0x0001 | 0x0002)

def center_text(text):
    """
    Centers each line of text dynamically based on the CMD terminal width.
    """
    terminal_width = shutil.get_terminal_size((80, 24)).columns
    centered_lines = []
    for line in text.split('\n'):
        line_clean = line.replace('\xa0', ' ')
        stripped_line = line_clean.rstrip()
        if not stripped_line:
            centered_lines.append("")
        else:
            padding = max(0, (terminal_width - len(stripped_line)) // 2)
            centered_lines.append(" " * padding + stripped_line)
    return "\n".join(centered_lines)

# Raw Exact ASCII Logo Banner
ASCII_LOGO = r""" 
 _____             _        _____                         _   
/  ___|           (_)      |_   _|                       | |  
\ `--.  ___  _ __  _  ___    | | ___  _ __ _ __ ___ _ __ | |_ 
 `--. \/ _ \| '_ \| |/ __|   | |/ _ \| '__| '__/ _ \ '_ \| __|
/\__/ / (_) | | | | | (__    | | (_) | |  | | |  __/ | | | |_ 
\____/ \___/|_| |_|_|\___|   \_/\___/|_|  |_|  \___|_| |_|\__|
                                                                                      """

SUB_HEADER = r"""------------------------------------------------------"""

def print_header():
    """
    Clears console and prints centered ASCII banner in RED ONCE.
    """
    os.system("cls" if os.name == "nt" else "clear")
    centered_logo = center_text(ASCII_LOGO)
    print(Fore.LIGHTRED_EX + centered_logo + Style.RESET_ALL)
    
    centered_header = center_text(SUB_HEADER)
    print(Fore.LIGHTRED_EX + centered_header + Style.RESET_ALL)

# ==============================================================================
# System & Registry Operations
# ==============================================================================

def is_admin():
    try:
        return ctypes.windll.shell32.IsUserAnAdmin()
    except Exception:
        return False

def register_magnet_handler():
    if not is_admin():
        return
    try:
        script_path = os.path.abspath(sys.argv[0])
        python_exe = sys.executable

        if script_path.endswith('.py'):
            command = f'"{python_exe}" "{script_path}" "%1"'
        else:
            command = f'"{script_path}" "%1"'

        key = winreg.CreateKey(winreg.HKEY_CLASSES_ROOT, "magnet")
        winreg.SetValue(key, "", winreg.REG_SZ, "URL:Torrent Magnet URL")
        winreg.SetValueEx(key, "URL Protocol", 0, winreg.REG_SZ, "")

        open_key = winreg.CreateKey(key, r"shell\open\command")
        winreg.SetValue(open_key, "", winreg.REG_SZ, command)

        winreg.CloseKey(key)
        winreg.CloseKey(open_key)
    except Exception:
        pass

def get_available_drives():
    drives = []
    bitmask = ctypes.windll.kernel32.GetLogicalDrives()
    for letter in string.ascii_uppercase:
        if bitmask & 1:
            drives.append(f"{letter}:")
        bitmask >>= 1
    return drives

def select_download_path():
    drives = get_available_drives()
    print(Fore.LIGHTRED_EX + center_text("\nSelect Download Drive:"))
    
    drives_str = " | ".join([f"[ {idx} ] {drive}" for idx, drive in enumerate(drives, 1)])
    print(Fore.LIGHTRED_EX + center_text(drives_str))

    while True:
        try:
            choice = int(input(Fore.LIGHTRED_EX + center_text("\nChoose Drive > ")))
            if 1 <= choice <= len(drives):
                selected_drive = drives[choice - 1]
                break
        except ValueError:
            pass
        print(center_text(Fore.LIGHTRED_EX + "Invalid choice, please try again."))

    target_dir = os.path.join(f"{selected_drive}\\", "Games")
    if not os.path.exists(target_dir):
        os.makedirs(target_dir, exist_ok=True)

    return target_dir

# ==============================================================================
# Formatting Tools
# ==============================================================================

def format_bytes(size):
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if size < 1024.0:
            return f"{size:.2f}{unit}"
        size /= 1024.0
    return f"{size:.2f}PB"

def format_time(seconds):
    if seconds <= 0 or seconds > 864000:
        return "--:--"
    m, s = divmod(int(seconds), 60)
    h, m = divmod(m, 60)
    if h > 0:
        return f"{h}:{m:02d}:{s:02d}"
    return f"{m:02d}:{s:02d}"

def select_file_dialog():
    root = Tk()
    root.withdraw()
    root.attributes('-topmost', True)
    file_path = askopenfilename(filetypes=[("Torrent Files", "*.torrent")])
    root.destroy()
    return file_path

# ==============================================================================
# Download Engine
# ==============================================================================

def download_torrent(source, save_dir):
    ses = lt.session({'listen_interfaces': '0.0.0.0:6881'})

    if source.startswith('magnet:'):
        params = lt.parse_magnet_uri(source)
        params.save_path = save_dir
        handle = ses.add_torrent(params)
        print(Fore.LIGHTRED_EX + center_text("\nFetching Magnet Metadata... Please wait."))
        while not handle.has_metadata():
            time.sleep(1)
    else:
        info = lt.torrent_info(source)
        handle = ses.add_torrent({'ti': info, 'save_path': save_dir})

    print(Fore.LIGHTRED_EX + center_text(f"\nDownload started in: {save_dir}\n"))

    while not handle.status().is_seeding:
        s = handle.status()
        progress = s.progress * 100

        total_blocks = 30
        filled_blocks = int(round(total_blocks * s.progress))
        empty_blocks = total_blocks - filled_blocks

        bar = (Fore.LIGHTRED_EX + "-" * filled_blocks) + (Fore.RED + "-" * empty_blocks) + Style.RESET_ALL
        eta = (s.total_wanted - s.total_wanted_done) / s.download_rate if s.download_rate > 0 else 0

        total_size_str = format_bytes(s.total_wanted)
        eta_str = format_time(eta)

        status_line = f"{total_size_str} | {bar} | {eta_str} ({progress:.1f}%)"
        
        terminal_width = shutil.get_terminal_size((80, 24)).columns
        padding = max(0, (terminal_width - 45) // 2)
        
        sys.stdout.write(f"\r{' ' * padding}{Fore.LIGHTRED_EX}{status_line}{Style.RESET_ALL}")
        sys.stdout.flush()
        time.sleep(1)

    print("\n")
    full_bar = Fore.LIGHTRED_EX + "-" * 30 + Style.RESET_ALL
    final_line = f"{format_bytes(handle.status().total_wanted)} | {full_bar} | 00:00 (100%)"
    print(center_text(Fore.LIGHTRED_EX + final_line))

    torrent_info = handle.torrent_file()
    setup_file_path = None

    for f in torrent_info.files():
        if f.path.endswith("setup.exe"):
            setup_file_path = os.path.join(save_dir, f.path)
            break

    if setup_file_path and os.path.exists(setup_file_path):
        os.startfile(setup_file_path)
        print(Fore.LIGHTRED_EX + center_text("\nDone , Setup Is Running"))
    else:
        print(Fore.LIGHTRED_EX + center_text("\nDone , Can't Run Setup"))

    input(Fore.LIGHTRED_EX + center_text("\nPress Any Key to Return ..."))

# ==============================================================================
# Main Program Entry Point
# ==============================================================================

def main():
    set_window_always_on_top()
    register_magnet_handler()
    print_header()

    if len(sys.argv) > 1:
        input_data = sys.argv[1]
        save_dir = select_download_path()
        download_torrent(input_data, save_dir)
        return

    options_text = "[ 1 ] .torrent | [ 2 ] magnet"
    print(Fore.LIGHTRED_EX + center_text(options_text))
    print()

    choice = input(Fore.LIGHTRED_EX + center_text("choose number > "))

    if choice == '1':
        print(Fore.LIGHTRED_EX + center_text("\nChoose Torrent File..."))
        file_path = select_file_dialog()
        if file_path:
            save_dir = select_download_path()
            download_torrent(file_path, save_dir)
        else:
            print(center_text(Fore.LIGHTRED_EX + "No file selected."))
            input(Fore.LIGHTRED_EX + center_text("Press Any Key to Return ..."))

    elif choice == '2':
        magnet_link = input(Fore.LIGHTRED_EX + center_text("\nEnter Link > "))
        if magnet_link.strip():
            save_dir = select_download_path()
            download_torrent(magnet_link.strip(), save_dir)
        else:
            print(center_text(Fore.LIGHTRED_EX + "Invalid link."))
            input(Fore.LIGHTRED_EX + center_text("Press Any Key to Return ..."))

if __name__ == "__main__":
    main()