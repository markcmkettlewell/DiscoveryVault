import sys
import os
import subprocess
import platform
from pathlib import Path

def get_base_path():
    """Returns the folder where the executable or script is running."""
    if getattr(sys, 'frozen', False):
        return Path(sys.executable).parent
    return Path(__file__).parent

def install_windows():
    """Windows-specific logic using certutil and ctypes."""
    import ctypes
    
    def is_admin():
        try: return ctypes.windll.shell32.IsUserAnAdmin()
        except: return False

    def message_box(title, text, style=0):
        # Styles: 0=OK, 16=Critical, 48=Warning, 64=Info
        ctypes.windll.user32.MessageBoxW(0, text, title, style)

    cert_path = get_base_path() / "server.crt"

    if not cert_path.exists():
        message_box("Error", f"Could not find 'server.crt' in:\n{get_base_path()}", 16)
        return

    # 1. Elevation Check
    if not is_admin():
        # Re-launch self with Admin privileges
        try:
            ctypes.windll.shell32.ShellExecuteW(
                None, "runas", sys.executable, " ".join(sys.argv), None, 1
            )
        except Exception:
            message_box("Error", "Could not request Administrator privileges.", 16)
        return

    # 2. Install
    try:
        # certutil -addstore "ROOT" <cert>
        cmd = f'certutil -addstore -f "ROOT" "{cert_path}"'
        
        # 0x08000000 hides the console window
        result = subprocess.run(
            cmd, capture_output=True, text=True, creationflags=0x08000000
        )
        
        if result.returncode == 0:
            message_box("Success", "Certificate installed successfully!\n\nPlease restart your browser.", 64)
        else:
            message_box("Failed", f"Windows Error:\n{result.stderr}", 16)

    except Exception as e:
        message_box("Critical Error", str(e), 16)

def install_mac():
    """macOS-specific logic using security and osascript."""
    
    def mac_alert(title, message):
        """Displays a native macOS dialog box."""
        # Escape quotes for AppleScript
        safe_msg = message.replace('"', '\\"')
        safe_title = title.replace('"', '\\"')
        script = f'display dialog "{safe_msg}" with title "{safe_title}" buttons {{"OK"}} default button "OK"'
        subprocess.run(['osascript', '-e', script])

    cert_path = get_base_path() / "server.crt"

    if not cert_path.exists():
        mac_alert("Error", f"Could not find server.crt in: {get_base_path()}")
        return

    # 3. Construct the Security Command
    # security add-trusted-cert -d (admin) -r trustRoot (root CA) -k (keychain)
    cmd = f'security add-trusted-cert -d -r trustRoot -k "/Library/Keychains/System.keychain" "{cert_path}"'
    
    # 4. Wrap in AppleScript to trigger the graphical Admin/Password prompt
    apple_script_wrapper = f'''
    do shell script "{cmd}" with administrator privileges
    '''
    
    try:
        result = subprocess.run(
            ['osascript', '-e', apple_script_wrapper], 
            capture_output=True, 
            text=True
        )

        if result.returncode == 0:
            mac_alert("Success", "Certificate installed! Please restart your browser.")
        else:
            # If user clicked Cancel, ignore. Otherwise show error.
            if "UserCanceled" not in result.stderr:
                mac_alert("Installation Failed", f"Error details:\n{result.stderr}")
                
    except Exception as e:
        mac_alert("Script Error", str(e))

if __name__ == '__main__':
    os_type = platform.system()
    
    if os_type == "Windows":
        install_windows()
    elif os_type == "Darwin": # Darwin is the technical name for macOS
        install_mac()
    else:
        print(f"Unsupported Operating System: {os_type}")
