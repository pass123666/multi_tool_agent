"""
multi_tool_agent
================
A multi-agent AI system to control a Debian Linux VM via natural language.

Author  : Suchita Kunghatkar (pass123666)
GitHub  : https://github.com/pass123666/multi_tool_agent
Model   : Gemini 2.5 Flash (Google ADK)
Version : 1.0.0

Description:
    Type commands in plain English. The root agent routes your request
    to the right specialist sub-agent, which runs the actual SSH command
    on your Debian VM and explains the result.

Sub-agents:
    - ssh_agent          : raw bash commands, connectivity
    - services_agent     : install packages, manage services
    - postgresql_agent   : PostgreSQL database operations
    - mongodb_agent      : MongoDB operations
    - storage_agent      : backups, file listing, archives
    - system_info_agent  : disk, memory, CPU, uptime
    - docker_agent       : Docker containers and images
"""
import os
import subprocess
import paramiko
from dotenv import load_dotenv
from google.adk.agents import Agent

# Load .env from the same directory as this file
load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), ".env"))

# ── Debian VM config (read from .env) ────────────────────
DEBIAN_IP       = os.getenv("DEBIAN_IP")
DEBIAN_USER     = os.getenv("DEBIAN_USER")
DEBIAN_PASSWORD = os.getenv("DEBIAN_PASSWORD")
DEBIAN_PORT     = int(os.getenv("DEBIAN_PORT", "22"))

# ── Safety: commands that are too destructive to ever run ─
HARD_BLOCK = [
    "rm -rf /",
    "mkfs",
    "dd if=/dev/zero of=/dev/sd",
    ":(){:|:&};:",
    "chmod -R 777 /",
]

def _is_safe(cmd: str) -> bool:
    return not any(bad.lower() in cmd.lower() for bad in HARD_BLOCK)


# ── SSH helper: opens a connection, runs one command, closes ──
def _ssh_run(cmd: str) -> str:
    try:
        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        client.connect(
            hostname=DEBIAN_IP,
            port=DEBIAN_PORT,
            username=DEBIAN_USER,
            password=DEBIAN_PASSWORD,
            timeout=15
        )

        needs_sudo = any(cmd.startswith(x) for x in [
            "apt", "systemctl", "service", "ufw",
            "mkdir /", "chown", "chmod", "adduser", "useradd"
        ])
        if needs_sudo:
            cmd = f"echo '{DEBIAN_PASSWORD}' | sudo -S {cmd}"

        stdin, stdout, stderr = client.exec_command(cmd, timeout=60)
        out = stdout.read().decode().strip()
        err = stderr.read().decode().strip()
        client.close()

        if out:
            return out
        if err:
            clean = "\n".join(
                line for line in err.splitlines()
                if "[sudo]" not in line and "password" not in line.lower()
            )
            return clean if clean else "Done."
        return "Command executed successfully (no output)."

    except paramiko.AuthenticationException:
        return "SSH Error: Authentication failed. Check .env file."
    except paramiko.SSHException:
        return f"SSH Error: Cannot connect to {DEBIAN_IP}. Is VM running?"
    except Exception as e:
        return f"SSH Error: {str(e)}"

# ════════════════════════════════════════════════════════
# TOOLS — Python functions the agents can call
# ════════════════════════════════════════════════════════

def ping_debian(ip: str) -> dict:
    """
    Ping the Debian VM to check if it is online and reachable.
    Use this before attempting SSH operations to verify connectivity.

    Args:
        ip: The IP address to ping. Use the Debian VM's configured IP address.

    Returns:
        A dict with 'status' (success/error) and 'result' describing if the host is online.
    """
    result = subprocess.run(
        f"ping -n 2 {ip}",
        shell=True, capture_output=True, text=True
    )
    online = "TTL=" in result.stdout or "bytes=" in result.stdout
    return {
        "status": "success" if online else "error",
        "result": f"{ip} is {'online and reachable' if online else 'offline or unreachable'}",
        "raw_output": result.stdout[:300]
    }


def run_debian_command(command: str) -> dict:
    """
    Execute any Linux bash command on the Debian VM via SSH.
    Use this for general commands that don't fit other specialized tools.
    Examples: listing files, checking logs, creating users, configuring software,
    running scripts, network commands, downloading files with wget or curl.

    Args:
        command: The exact bash command to execute on Debian Linux.

    Returns:
        A dict with 'status', 'command_run', and 'result' containing the command output.
    """
    if not _is_safe(command):
        return {
            "status": "error",
            "result": f"BLOCKED: '{command}' is too destructive to run."
        }
    output = _ssh_run(command)
    return {
        "status": "success",
        "command_run": command,
        "result": output
    }


def install_package(package_name: str) -> dict:
    """
    Install any software package on Debian Linux using apt-get.
    Works for: nginx, mongodb, postgresql, docker.io, nodejs, redis-server,
    python3, git, curl, wget, htop, ufw, or any package in the Debian repository.

    Args:
        package_name: The exact apt package name to install (e.g. 'nginx', 'mongodb', 'redis-server').

    Returns:
        A dict with 'status', 'package', and 'result' showing installation output.
    """
    cmd = f"apt-get install -y {package_name}"
    output = _ssh_run(cmd)
    return {
        "status": "success",
        "package": package_name,
        "result": output
    }


def manage_service(service_name: str, action: str) -> dict:
    """
    Start, stop, restart, enable, disable, or check status of any Linux service.
    Works for: nginx, postgresql, mongod, redis, ssh, docker, apache2, mysql, and any systemd service.

    Args:
        service_name: Name of the service (e.g. 'nginx', 'postgresql', 'mongod', 'docker').
        action: What to do. Must be one of: start, stop, restart, status, enable, disable.

    Returns:
        A dict with 'status', 'service', 'action', and 'result'.
    """
    allowed_actions = ["start", "stop", "restart", "status", "enable", "disable"]
    if action not in allowed_actions:
        return {
            "status": "error",
            "result": f"Invalid action '{action}'. Must be one of: {allowed_actions}"
        }
    cmd = f"systemctl {action} {service_name}"
    output = _ssh_run(cmd)
    return {
        "status": "success",
        "service": service_name,
        "action": action,
        "result": output
    }


def check_system_info(info_type: str) -> dict:
    """
    Get system information and health metrics from the Debian VM.

    Args:
        info_type: What to check. Options:
            'disk'      - disk space usage (df -h)
            'memory'    - RAM usage (free -h)
            'cpu'       - CPU and top processes
            'processes' - all running processes sorted by memory
            'network'   - network interfaces and open ports
            'uptime'    - system uptime and kernel version
            'users'     - logged-in users and login history
            'all'       - disk + memory + uptime combined

    Returns:
        A dict with 'status', 'info_type', and 'result' with the system data.
    """
    command_map = {
        "disk":      "df -h",
        "memory":    "free -h",
        "cpu":       "top -bn1 | head -20",
        "processes": "ps aux --sort=-%mem | head -20",
        "network":   "ip addr show && echo '---' && ss -tulnp",
        "uptime":    "uptime && echo '---' && uname -a",
        "users":     "who && echo '---' && last | head -10",
        "all":       "echo '=== DISK ===' && df -h && echo '=== MEMORY ===' && free -h && echo '=== UPTIME ===' && uptime",
    }
    cmd = command_map.get(info_type.lower())
    if not cmd:
        return {
            "status": "error",
            "result": f"Unknown info_type '{info_type}'. Choose from: {list(command_map.keys())}"
        }
    output = _ssh_run(cmd)
    return {
        "status": "success",
        "info_type": info_type,
        "result": output
    }


def postgresql_task(task_description: str, sql_command: str = "") -> dict:
    """
    Perform PostgreSQL database operations on the Debian VM.
    Use for: listing databases, creating/dropping databases, running SQL queries,
    creating users, checking PostgreSQL status, managing tables.

    Args:
        task_description: Plain English description of what you want to do.
            Examples: 'list all databases', 'create database myapp', 'check status'
        sql_command: Optional raw SQL to execute directly.
            Examples: 'SELECT * FROM users;', 'CREATE TABLE orders (id SERIAL PRIMARY KEY);'

    Returns:
        A dict with 'status', 'task', and 'result' with database output.
    """
    if sql_command:
        cmd = f'sudo -u postgres psql -c "{sql_command}"'
    else:
        task_lower = task_description.lower()
        if "list" in task_lower and "database" in task_lower:
            cmd = "sudo -u postgres psql -l"
        elif "create database" in task_lower:
            db_name = task_description.strip().split()[-1]
            cmd = f"sudo -u postgres createdb {db_name}"
        elif "status" in task_lower:
            cmd = "systemctl status postgresql"
        elif "list table" in task_lower:
            cmd = "sudo -u postgres psql -c '\\dt'"
        elif "create user" in task_lower:
            username = task_description.strip().split()[-1]
            cmd = f"sudo -u postgres createuser --interactive {username}"
        else:
            cmd = "sudo -u postgres psql -l"

    output = _ssh_run(cmd)
    return {
        "status": "success",
        "task": task_description,
        "result": output
    }


def mongodb_task(task_description: str, mongo_command: str = "") -> dict:
    """
    Perform MongoDB operations on the Debian VM.
    Use for: installing MongoDB, starting/stopping mongod service, listing databases,
    creating collections, inserting documents, running MongoDB shell commands.

    Args:
        task_description: Plain English description of the MongoDB task.
            Examples: 'list all databases', 'check mongodb status', 'show collections'
        mongo_command: Optional raw MongoDB shell command to run via mongosh.
            Examples: 'show dbs', 'use mydb; show collections'

    Returns:
        A dict with 'status', 'task', and 'result' with MongoDB output.
    """
    if mongo_command:
        cmd = f'mongosh --eval "{mongo_command}"'
    else:
        task_lower = task_description.lower()
        if "status" in task_lower:
            cmd = "systemctl status mongod"
        elif "list" in task_lower and "database" in task_lower:
            cmd = 'mongosh --eval "show dbs"'
        elif "start" in task_lower:
            cmd = "systemctl start mongod"
        elif "stop" in task_lower:
            cmd = "systemctl stop mongod"
        elif "install" in task_lower:
            cmd = "apt-get install -y mongodb"
        elif "collection" in task_lower:
            cmd = 'mongosh --eval "show collections"'
        else:
            cmd = "systemctl status mongod"

    output = _ssh_run(cmd)
    return {
        "status": "success",
        "task": task_description,
        "result": output
    }


def storage_backup_task(action: str, source_path: str, dest_path: str = "/backup") -> dict:
    """
    Perform file storage and backup operations on the Debian VM.
    Use for: backing up folders, listing files, checking disk usage,
    creating directories, archiving files with tar.

    Args:
        action: What to do. Options:
            'backup'     - create a compressed tar.gz backup of source_path
            'list'       - list files at source_path (ls -lah)
            'disk_usage' - show size of source_path (du -sh)
            'create_dir' - create directory at source_path (mkdir -p)
            'delete'     - delete source_path (blocked for dangerous paths)
        source_path: The file or folder path to operate on (e.g. '/home/agent', '/var/log').
        dest_path: Destination for backup files. Defaults to '/backup'.

    Returns:
        A dict with 'status', 'action', 'path', and 'result'.
    """
    if action == "backup":
        cmd = f"mkdir -p {dest_path} && tar -czf {dest_path}/backup_$(date +%Y%m%d_%H%M%S).tar.gz {source_path} && ls -lah {dest_path}"
    elif action == "list":
        cmd = f"ls -lah {source_path}"
    elif action == "disk_usage":
        cmd = f"du -sh {source_path}"
    elif action == "create_dir":
        cmd = f"mkdir -p {source_path}"
    elif action == "delete":
        if not _is_safe(f"rm -rf {source_path}"):
            return {
                "status": "error",
                "result": f"BLOCKED: Deleting '{source_path}' is too dangerous."
            }
        cmd = f"rm -rf {source_path}"
    else:
        cmd = f"ls -lah {source_path}"

    output = _ssh_run(cmd)
    return {
        "status": "success",
        "action": action,
        "path": source_path,
        "result": output
    }


def docker_task(task_description: str, container_name: str = "") -> dict:
    """
    Perform Docker container operations on the Debian VM.
    Use for: listing containers, starting/stopping containers, pulling images,
    checking Docker status, viewing container logs.

    Args:
        task_description: Plain English description of the Docker task.
            Examples: 'list all containers', 'pull nginx image', 'show container logs'
        container_name: Optional container name for operations targeting a specific container.

    Returns:
        A dict with 'status', 'task', and 'result'.
    """
    task_lower = task_description.lower()
    if "list" in task_lower and "container" in task_lower:
        cmd = "docker ps -a"
    elif "list" in task_lower and "image" in task_lower:
        cmd = "docker images"
    elif "pull" in task_lower:
        image = task_description.strip().split()[-1]
        cmd = f"docker pull {image}"
    elif "start" in task_lower and container_name:
        cmd = f"docker start {container_name}"
    elif "stop" in task_lower and container_name:
        cmd = f"docker stop {container_name}"
    elif "log" in task_lower and container_name:
        cmd = f"docker logs {container_name} --tail 50"
    elif "status" in task_lower or "info" in task_lower:
        cmd = "docker info"
    elif "install" in task_lower:
        cmd = "apt-get install -y docker.io && systemctl enable docker && systemctl start docker"
    else:
        cmd = "docker ps -a"

    output = _ssh_run(cmd)
    return {
        "status": "success",
        "task": task_description,
        "result": output
    }


def run_local_windows_command(command: str) -> dict:
    """
    Run a command on the local Windows machine (NOT on Debian).
    Use when the user explicitly asks about their Windows PC:
    checking local IP, Windows processes, local disk space, Windows system info.

    Args:
        command: A Windows CMD command to run locally (e.g. 'ipconfig', 'tasklist', 'dir').

    Returns:
        A dict with 'status', 'command', and 'result' with the command output.
    """
    try:
        result = subprocess.run(
            command, shell=True, capture_output=True, text=True, timeout=30
        )
        output = result.stdout.strip() or result.stderr.strip() or "(no output)"
        return {"status": "success", "command": command, "result": output}
    except subprocess.TimeoutExpired:
        return {"status": "error", "result": "Command timed out after 30 seconds."}
    except Exception as e:
        return {"status": "error", "result": str(e)}


# ════════════════════════════════════════════════════════
# SUB-AGENTS
# ════════════════════════════════════════════════════════

ssh_agent = Agent(
    name="ssh_agent",
    model="gemini-2.5-flash",
    description=(
        "Handles direct SSH command execution and connectivity checks on the Debian VM. "
        "Use for raw bash commands, checking if the server is reachable, or any task "
        "that doesn't fit a more specialized agent."
    ),
    instruction=(
        "You are an SSH execution agent connected to a Debian Linux VM. "
        "Use ping_debian to check if the server is online when connectivity is uncertain. "
        "Use run_debian_command to execute any bash command on Debian. "
        "Always report the exact output you receive. "
        "If a command fails, explain what the error means and suggest a fix."
    ),
    tools=[ping_debian, run_debian_command],
)

services_agent = Agent(
    name="services_agent",
    model="gemini-2.5-flash",
    description=(
        "Installs software packages and manages Linux services on Debian. "
        "Use for: installing nginx, mongodb, docker, nodejs, redis, postgresql, "
        "and for starting/stopping/restarting/enabling any service."
    ),
    instruction=(
        "You are a Linux package and services manager for Debian. "
        "Use install_package to install any software via apt-get. "
        "Use manage_service to control systemd services (start/stop/restart/status/enable/disable). "
        "Always confirm what was installed or what action was taken. "
        "Report any errors clearly and suggest fixes."
    ),
    tools=[install_package, manage_service],
)

postgresql_agent = Agent(
    name="postgresql_agent",
    model="gemini-2.5-flash",
    description=(
        "Handles all PostgreSQL database operations on Debian. "
        "Use for: listing databases, creating/dropping databases, running SQL, "
        "managing database users, checking PostgreSQL service status."
    ),
    instruction=(
        "You are a PostgreSQL database specialist. "
        "Use postgresql_task for all database operations. "
        "You can list databases, create/drop databases, run SQL queries, and manage users. "
        "Always explain what the output means in plain English. "
        "If PostgreSQL is not installed or not running, say so clearly."
    ),
    tools=[postgresql_task],
)

mongodb_agent = Agent(
    name="mongodb_agent",
    model="gemini-2.5-flash",
    description=(
        "Handles all MongoDB operations on Debian. "
        "Use for: installing MongoDB, starting/stopping mongod, listing databases, "
        "showing collections, running MongoDB shell commands."
    ),
    instruction=(
        "You are a MongoDB specialist. "
        "Use mongodb_task for all MongoDB operations. "
        "You can install MongoDB, manage the mongod service, list databases, and run shell commands. "
        "Always explain results clearly. "
        "If MongoDB is not installed, offer to install it."
    ),
    tools=[mongodb_task],
)

storage_agent = Agent(
    name="storage_agent",
    model="gemini-2.5-flash",
    description=(
        "Handles file storage, backups, and disk operations on Debian. "
        "Use for: creating backups with tar, listing files, checking disk usage, "
        "creating directories, archiving folders."
    ),
    instruction=(
        "You are a storage and backup specialist. "
        "Use storage_backup_task for all file and storage operations. "
        "You can back up folders, list files, check sizes, and create directories. "
        "Always report file sizes and paths clearly. "
        "Confirm when backups are created successfully."
    ),
    tools=[storage_backup_task],
)

system_info_agent = Agent(
    name="system_info_agent",
    model="gemini-2.5-flash",
    description=(
        "Checks and reports system health information from the Debian VM. "
        "Use for: disk space, memory/RAM usage, CPU load, running processes, "
        "network interfaces, uptime, logged-in users."
    ),
    instruction=(
        "You are a system monitoring specialist. "
        "Use check_system_info to retrieve system metrics. "
        "Summarize results in plain English — tell the user if something looks normal or concerning. "
        "For disk: warn if usage is above 80%. "
        "For memory: warn if less than 10% is free."
    ),
    tools=[check_system_info],
)

docker_agent = Agent(
    name="docker_agent",
    model="gemini-2.5-flash",
    description=(
        "Handles Docker container and image operations on Debian. "
        "Use for: listing containers, pulling images, starting/stopping containers, "
        "viewing logs, installing Docker."
    ),
    instruction=(
        "You are a Docker specialist. "
        "Use docker_task for all Docker operations. "
        "You can list containers, pull images, start/stop containers, and view logs. "
        "If Docker is not installed, offer to install it. "
        "Always explain what containers are running and what they do."
    ),
    tools=[docker_task],
)


# ════════════════════════════════════════════════════════
# ROOT AGENT — the main brain (must be named root_agent)
# ════════════════════════════════════════════════════════

root_agent = Agent(
    name="main_agent",
    model="gemini-2.5-flash",
    description="Main AI brain controlling a Debian Linux VM via SSH from Windows VirtualBox.",
    instruction=(
        "You are the Main Agent Brain. You control a Debian Linux virtual machine "
        "running inside VirtualBox on Windows. You can execute ANYTHING the user asks.\n\n"

        "You have these specialist sub-agents — delegate to them:\n"
        "- ssh_agent: raw SSH commands, connectivity checks, anything general on Debian\n"
        "- services_agent: installing packages (apt), managing services (systemctl)\n"
        "- postgresql_agent: all PostgreSQL database tasks\n"
        "- mongodb_agent: all MongoDB tasks\n"
        "- storage_agent: backups, file listing, disk operations, tar archives\n"
        "- system_info_agent: disk space, memory, CPU, processes, network, uptime\n"
        "- docker_agent: Docker containers, images, logs, installation\n\n"

        "You also have direct tools:\n"
        "- run_debian_command: run any bash command on Debian directly\n"
        "- run_local_windows_command: run commands on the local Windows machine\n"
        "- ping_debian: check if the Debian VM is reachable\n\n"

        "ROUTING RULES (follow these):\n"
        "- 'install X', 'download X', 'setup X service' → services_agent\n"
        "- 'postgres', 'postgresql', 'sql', 'database' → postgresql_agent\n"
        "- 'mongo', 'mongodb' → mongodb_agent\n"
        "- 'docker', 'container', 'image' → docker_agent\n"
        "- 'backup', 'archive', 'tar', 'list files' → storage_agent\n"
        "- 'disk space', 'memory', 'ram', 'cpu', 'processes', 'uptime' → system_info_agent\n"
        "- 'ping', 'connect', 'is debian up' → use ping_debian tool directly\n"
        "- 'windows', 'local', 'my pc', 'this machine' → use run_local_windows_command\n"
        "- Everything else on Debian → ssh_agent or run_debian_command directly\n\n"

        "Always tell the user:\n"
        "1. Which agent or tool handled the request\n"
        "2. What command was run\n"
        "3. What the output means in plain English\n"
        "4. If something failed, what to do about it"
    ),
    tools=[run_debian_command, run_local_windows_command, ping_debian],
    sub_agents=[
        ssh_agent,
        services_agent,
        postgresql_agent,
        mongodb_agent,
        storage_agent,
        system_info_agent,
        docker_agent,
    ],
)
if __name__ == "__main__":
    import asyncio
    from google.adk.runners import Runner
    from google.adk.sessions import InMemorySessionService
    from google.genai import types

    session_service = InMemorySessionService()
    
    APP_NAME = "debian_agent"
    USER_ID = "user"
    SESSION_ID = "session1"

    async def main():
        # Create session first
        await session_service.create_session(
            app_name=APP_NAME,
            user_id=USER_ID,
            session_id=SESSION_ID
        )

        # Pass app_name correctly
        runner = Runner(
            agent=root_agent,
            app_name=APP_NAME,
            session_service=session_service
        )

        print("Agent ready! Type your commands (Ctrl+C to quit)\n")

        while True:
            user_input = input("You: ")
            if not user_input.strip():
                continue

            response_text = ""
            # लक्ष द्या: 'async for' आता 'while' च्या आत आहे
            async for event in runner.run_async(
                user_id=USER_ID,
                session_id=SESSION_ID,
                new_message=types.Content(
                    role="user",
                    parts=[types.Part(text=user_input)]
                )
            ):
                if event.is_final_response() and event.content:
                    for part in event.content.parts:
                        if hasattr(part, "text") and part.text:
                            response_text += part.text
                        elif hasattr(part, "function_call"):
                            # फंक्शन कॉलची माहिती प्रिंट होईल
                            print(f"\n[System] Agent is calling function: {part.function_call.name}")

            print(f"Agent: {response_text}\n")

if __name__ == "__main__":
    asyncio.run(main())
