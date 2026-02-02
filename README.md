# TCP Chat Server

A simple multi-client TCP chat server built using only Python's standard library. No HTTP, no database, no external dependencies.

## Features

| Command | Description |
|---------|-------------|
| `LOGIN <username>` | Log in with a unique username |
| `MSG <text>` | Broadcast a message to all users |
| `WHO` | List all connected users |
| `DM <username> <text>` | Send a private message |
| `PING` | Heartbeat (responds with `PONG`) |

**Additional Features:**
- Multi-client support (10+ concurrent users)
- Automatic disconnect notifications
- 60-second idle timeout
- Configurable port

---

## Quick Start

### 1. Start the Server

```bash
python server.py
```

With custom port:
```bash
python server.py --port 5000
# or
set PORT=5000 && python server.py
```

### 2. Connect Clients

Using **netcat** (Linux/Mac) or **ncat** (Windows via Nmap):

```bash
nc localhost 4000
```

Or using **telnet**:
```bash
telnet localhost 4000
```

> **Windows Users:** Install [Nmap](https://nmap.org/download.html) for `ncat`, or use WSL.

---

## Example Session

### Terminal 1 (Client 1)
```
$ nc localhost 4000
LOGIN Naman
OK
MSG hi everyone!
MSG how are you?
MSG Yudi hello Naman!
INFO Yudi disconnected
```

### Terminal 2 (Client 2)
```
$ nc localhost 4000
LOGIN Yudi
OK
MSG Naman hi everyone!
MSG Naman how are you?
MSG hello Naman!
WHO
USER Naman
USER Yudi
DM Naman secret message
PING
PONG
```

### What Naman Sees (Client 1)
```
MSG Yudi hello Naman!
DM Yudi secret message
INFO Yudi disconnected
```

### Duplicate Username Attempt
```
$ nc localhost 4000
LOGIN Naman
ERR username-taken
```

---

## Commands Reference

| Client Sends | Server Responds | Notes |
|--------------|-----------------|-------|
| `LOGIN <username>` | `OK` or `ERR username-taken` | Must be first command |
| `MSG <text>` | Broadcasts `MSG <username> <text>` to all others | Requires login |
| `WHO` | `USER <username>` for each user | Lists all connected users |
| `DM <user> <text>` | Sends `DM <from> <text>` to target | Private message |
| `PING` | `PONG` | Heartbeat check |

### Server Notifications
| Message | Meaning |
|---------|---------|
| `INFO <username> disconnected` | User left the chat |
| `ERR idle-timeout` | Disconnected due to inactivity |

---

## Command Line Options

```
python server.py [-h] [--port PORT] [--idle-timeout SECONDS]

Options:
  -p, --port          Port to listen on (default: 4000)
  -t, --idle-timeout  Idle timeout in seconds (default: 60)
```

---

## Documentation

| Document | Description |
|----------|-------------|
| [HLD.md](./HLD.md) | High Level Design - Architecture, components, data flow |
| [LLD.md](./LLD.md) | Low Level Design - Class structure, algorithms, protocol spec |

---

## Project Structure

```
algokart/
├── server.py    # Main chat server implementation (371 lines)
├── README.md    # This file
├── HLD.md       # High Level Design document
└── LLD.md       # Low Level Design document
```

---

## Screen Recording

**Demo Video:**  [View Demo](https://www.loom.com/share/abbff6a0f4fb4b938afdfbab4f7ca283)


---

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

## Connect with me

If you’d like to connect, feel free to reach out — [Click here](https://minianonlink.vercel.app/tusharbhardwaj)
