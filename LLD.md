# Low Level Design (LLD) - TCP Chat Server

## 1. Class Structure

```
┌─────────────────────────────────────────────────────────────┐
│                       ChatServer                            │
├─────────────────────────────────────────────────────────────┤
│ Attributes:                                                 │
│   - host: str                  # Bind address (0.0.0.0)    │
│   - port: int                  # Listen port (4000)        │
│   - idle_timeout: int          # Timeout in seconds (60)   │
│   - server_socket: socket      # Main listening socket      │
│   - clients: Dict[socket, str] # socket → username mapping │
│   - usernames: Dict[str, socket] # username → socket mapping│
│   - last_activity: Dict[socket, float] # Activity timestamps│
│   - lock: threading.Lock       # Thread synchronization     │
│   - running: bool              # Server state flag          │
├─────────────────────────────────────────────────────────────┤
│ Methods:                                                    │
│   + start()                    # Start server main loop     │
│   + stop()                     # Graceful shutdown          │
│   - _handle_client(conn, addr) # Per-client thread entry    │
│   - _handle_login(conn, addr)  # Login flow handler         │
│   - _process_command(...)      # Command dispatcher         │
│   - _send(conn, msg)           # Send to single client      │
│   - _broadcast(msg, exclude)   # Send to all clients        │
│   - _send_private(...)         # DM handler                 │
│   - _remove_client(conn, user) # Cleanup on disconnect      │
│   - _check_idle_clients()      # Background idle monitor    │
└─────────────────────────────────────────────────────────────┘
```

## 2. Data Structures

### Client Tracking (Thread-Safe)
```python
# Protected by self.lock
clients: Dict[socket, str] = {
    <socket_obj>: "Naman",
    <socket_obj>: "Yudi"
}

usernames: Dict[str, socket] = {
    "Naman": <socket_obj>,
    "Yudi": <socket_obj>
}

last_activity: Dict[socket, float] = {
    <socket_obj>: 1706900000.123  # Unix timestamp
}
```

## 3. Protocol Specification

### Client → Server Commands

| Command | Format | Response |
|---------|--------|----------|
| Login | `LOGIN <username>\n` | `OK\n` or `ERR username-taken\n` |
| Message | `MSG <text>\n` | (broadcasts to others) |
| List Users | `WHO\n` | `USER <name>\n` per user |
| Private Message | `DM <user> <text>\n` | `ERR user-not-found\n` if invalid |
| Heartbeat | `PING\n` | `PONG\n` |

### Server → Client Messages

| Message | Format | Trigger |
|---------|--------|---------|
| Broadcast | `MSG <sender> <text>\n` | Another user sent MSG |
| Private | `DM <sender> <text>\n` | Received DM |
| User Info | `USER <username>\n` | Response to WHO |
| Disconnect Notice | `INFO <user> disconnected\n` | User left |
| Timeout | `ERR idle-timeout\n` | 60s inactivity |

## 4. Thread Model

```
Main Thread                    Client Threads              Daemon Thread
     │                              │                           │
     │  accept()                    │                           │
     ├──────────────────►┌──────────┴───────────┐               │
     │                   │ _handle_client(conn) │               │
     │                   │   └─► _handle_login  │               │
     │                   │   └─► message loop   │               │
     │                   └──────────────────────┘               │
     │                                                          │
     │                                          ┌───────────────┴──┐
     │                                          │_check_idle_clients│
     │                                          │  (every 10 sec)   │
     │                                          └──────────────────┘
```

## 5. Key Algorithms

### Login Flow
```python
def _handle_login(conn, addr):
    while running:
        data = conn.recv(1024)
        line = parse_line(data)
        
        if line.startswith("LOGIN "):
            username = line[6:].strip()
            
            with lock:
                if username in usernames:
                    send(conn, "ERR username-taken")
                else:
                    clients[conn] = username
                    usernames[username] = conn
                    send(conn, "OK")
                    return username
```

### Message Broadcasting
```python
def _broadcast(message, exclude=None):
    with lock:
        for conn in clients.keys():
            if conn != exclude:
                conn.sendall((message + '\n').encode())
```

### Idle Detection
```python
def _check_idle_clients():
    while running:
        sleep(10)
        current = time.time()
        
        with lock:
            for conn, last_time in last_activity.items():
                if current - last_time > 60:
                    remove_client(conn)
```

## 6. Error Handling

| Scenario | Handling |
|----------|----------|
| Connection reset | Catch `ConnectionResetError`, cleanup client |
| Socket timeout | Continue loop (expected for idle check) |
| Invalid command | Silently ignore (lenient parsing) |
| Send failure | Log error, continue (don't crash server) |
| Keyboard interrupt | Graceful shutdown, close all sockets |

## 7. Configuration

| Parameter | Default | Source |
|-----------|---------|--------|
| Port | 4000 | `--port` CLI or `PORT` env var |
| Idle Timeout | 60s | `--idle-timeout` CLI |
| Listen Backlog | 10 | Hardcoded in `listen(10)` |
| Recv Buffer | 1024 bytes | Hardcoded |
| Socket Timeout | 5s | Per-client for idle detection |
