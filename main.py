from fastapi import FastAPI, Form, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import paramiko

app = FastAPI()

# Mount static directory for CSS
app.mount("/static", StaticFiles(directory="static"), name="static")

# Configure templates
templates = Jinja2Templates(directory="templates")

class RouterConnection:
    def __init__(self, ip, username, password):
        self.ip = ip
        self.username = username
        self.password = password
        self.ssh_client = paramiko.SSHClient()
        self.ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

    def connect(self):
        try:
            self.ssh_client.connect(hostname=self.ip, username=self.username, password=self.password, port=8222)
            return True
        except Exception as e:
            return False

    def execute_command(self, command):
        try:
            stdin, stdout, stderr = self.ssh_client.exec_command(command)
            output = stdout.read().decode()
            error = stderr.read().decode()
            return output.strip() if not error else error.strip()
        except Exception:
            return None

    def disconnect(self):
        self.ssh_client.close()

# Diagnostic and troubleshooting functions
def ping_test(router):
    return {"description": "Ping test to Google DNS", "output": router.execute_command("ping 8.8.8.8 count=10")}

def check_interface_status(router):
    return {"description": "Checking router interface status", "output": router.execute_command("interface print")}

def troubleshoot(router):
    results = {}
    if not router.connect():
        results["connection"] = {"description": "Failed to connect to router"}
        return results

    results["ping_test"] = ping_test(router)
    results["interface_status"] = check_interface_status(router)
    
    # Clear ARP cache if CPU load is high
    cpu_load = router.execute_command("system resource print")
    if "high" in cpu_load.lower():
        router.execute_command("ip arp remove [find]")
        results["arp_cache"] = {"description": "ARP cache cleared due to high CPU load"}

    # Restart interface if down
    interface_status = check_interface_status(router)
    if "down" in interface_status["output"]:
        router.execute_command("interface disable ether1; interface enable ether1")
        results["interface_fix"] = {"description": "Restarted interface 'ether1' due to status issue"}

    router.disconnect()
    return results

@app.get("/", response_class=HTMLResponse)
async def get_form(request: Request):
    return templates.TemplateResponse("form.html", {"request": request})

@app.post("/troubleshoot", response_class=HTMLResponse)
async def troubleshoot_device(request: Request, ip_address: str = Form(...)):
    username = "admin"
    password = "y26oKUWD"

    router = RouterConnection(ip_address, username, password)
    results = troubleshoot(router)

    # Render the results template with context
    return templates.TemplateResponse("results.html", {"request": request, "results": results})
