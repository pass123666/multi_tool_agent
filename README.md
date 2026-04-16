# 🤖 multi_tool_agent

A multi-agent AI system that lets you control a **Debian Linux VM** (running in VirtualBox on Windows) using natural language commands — powered by **Google ADK** and **Gemini 2.5 Flash**.

---

## 📌 What It Does

You type commands in plain English. The agent figures out what to do, delegates to the right specialist, runs the actual command on your Debian VM over SSH, and explains the result — all automatically.

**Examples:**
```
"Install nginx and start it"
"How much disk space is left?"
"List all PostgreSQL databases"
"Back up the /var/www folder"
"Is the VM online?"
```

---

## 🏗️ Architecture

```
You (terminal)
     │
     ▼
root_agent  ← main brain, routes requests
     │
     ├── ssh_agent          → raw bash commands, connectivity
     ├── services_agent     → install packages, manage services
     ├── postgresql_agent   → PostgreSQL database operations
     ├── mongodb_agent      → MongoDB operations
     ├── storage_agent      → backups, file listing, archives
     ├── system_info_agent  → disk, memory, CPU, uptime
     └── docker_agent       → Docker containers & images
```

All agents use **Gemini 2.5 Flash** and communicate with the Debian VM via **SSH (Paramiko)**.

---

## 📁 Project Structure

```
multi_tool_agent/
├── .adk/                  # Google ADK configuration
├── agent.py               # Main agent definition (all tools + agents)
├── agent1.py              # Alternate/experimental agent
├── check_models.py        # Utility to verify available Gemini models
├── __init__.py
├── __init_1.py
├── .env                   # Your secrets (not committed)
├── .env.example.txt       # Template for environment variables
├── .gitignore
└── .gitattributes
```

---

## ⚙️ Setup

### 1. Prerequisites

- Python 3.10+
- A Debian Linux VM running in VirtualBox (with SSH enabled)
- A Google AI API key with access to Gemini models

### 2. Clone the repo

```bash
git clone https://github.com/pass123666/multi_tool_agent.git
cd multi_tool_agent
```

### 3. Install dependencies

```bash
pip install google-adk paramiko python-dotenv
```

### 4. Configure environment variables

Copy the example file and fill in your values:

```bash
cp .env.example.txt .env
```

Edit `.env`:

```env
DEBIAN_IP=192.168.x.x        # IP address of your Debian VM
DEBIAN_USER=your_username     # SSH username
DEBIAN_PASSWORD=your_password # SSH password
DEBIAN_PORT=22                # SSH port (default: 22)
GOOGLE_API_KEY=your_key_here  # Gemini API key
```

### 5. Enable SSH on Debian VM

```bash
sudo apt install openssh-server -y
sudo systemctl enable ssh
sudo systemctl start ssh
```

Make sure the VM's network adapter is set to **Bridged** or **Host-only** in VirtualBox so it's reachable from Windows.

---

## ▶️ Running the Agent

```bash
python agent.py
```

You'll see:
```
Agent ready! Type your commands (Ctrl+C to quit)

You: 
```

Type any command and the agent responds.

---

## 🛠️ What Each Agent Can Do

| Agent | Capabilities |
|---|---|
| `ssh_agent` | Run any bash command, ping the VM |
| `services_agent` | `apt install`, `systemctl start/stop/restart/status` |
| `postgresql_agent` | List/create databases, run SQL queries, manage users |
| `mongodb_agent` | Install, start/stop mongod, list databases, run shell commands |
| `storage_agent` | Create tar.gz backups, list files, check disk usage, make directories |
| `system_info_agent` | Disk space, RAM, CPU, processes, network interfaces, uptime |
| `docker_agent` | List containers/images, pull images, start/stop, view logs |

---

## 🔒 Safety

The agent blocks a hardcoded list of destructive commands and will never run them:

```python
HARD_BLOCK = [
    "rm -rf /",
    "mkfs",
    "dd if=/dev/zero of=/dev/sd",
    ":(){:|:&};:",
    "chmod -R 777 /",
]
```

Any command matching these patterns returns an error instead of executing.

---

## 🗺️ Routing Logic

The root agent automatically routes your request to the right specialist:

| Your request includes... | Goes to |
|---|---|
| "install", "setup", "service" | `services_agent` |
| "postgres", "sql", "database" | `postgresql_agent` |
| "mongo", "mongodb" | `mongodb_agent` |
| "docker", "container", "image" | `docker_agent` |
| "backup", "archive", "tar", "list files" | `storage_agent` |
| "disk", "memory", "ram", "cpu", "uptime" | `system_info_agent` |
| "ping", "is debian up" | direct ping tool |
| "windows", "local", "my pc" | local Windows command runner |
| anything else | `ssh_agent` |

---

## 🧪 Example Session

```
You: is the vm online?
Agent: [ssh_agent] Pinged 192.168.1.50 — VM is online and reachable.

You: check disk space
Agent: [system_info_agent] Filesystem is 34% used (18GB of 54GB free). Looks healthy.

You: install redis-server
Agent: [services_agent] Installed redis-server via apt-get. Service is active and running.

You: backup /home/user
Agent: [storage_agent] Created /backup/backup_20250415_1045.tar.gz (2.3MB). Backup successful.
```

---

## 🤝 Contributing

Pull requests are welcome! For major changes, open an issue first to discuss what you'd like to change.

---

## 📄 License

This project is currently unlicensed. Add a `LICENSE` file if you plan to share it publicly.
