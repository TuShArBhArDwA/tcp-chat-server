# High Level Design (HLD) - TCP Chat Server

## 1. Overview

A real-time multi-user TCP chat server built using Python's standard library. The server enables multiple clients to connect, authenticate, and exchange messages in real-time.

## 2. Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                      TCP Chat Server                        │
│                     (Port 4000)                             │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐   │
│  │   Client 1   │    │   Client 2   │    │   Client N   │   │
│  │   (Thread)   │    │   (Thread)   │    │   (Thread)   │   │
│  └──────┬───────┘    └──────┬───────┘    └──────┬───────┘   │
│         │                   │                   │           │
│         └───────────────────┼───────────────────┘           │
│                             │                               │
│                    ┌────────▼────────┐                      │
│                    │  Shared State   │                      │
│                    │  (Thread-Safe)  │                      │
│                    │  - clients{}    │                      │
│                    │  - usernames{}  │                      │
│                    └─────────────────┘                      │
│                                                             │
│         ┌─────────────────────────────────────┐             │
│         │      Background Idle Checker        │             │
│         │      (Daemon Thread)                │             │
│         └─────────────────────────────────────┘             │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

## 3. Components

| Component | Responsibility |
|-----------|----------------|
| **Main Server Loop** | Accept incoming TCP connections |
| **Client Handler Thread** | Handle login, commands, and disconnection per client |
| **Shared State Manager** | Thread-safe storage for connected clients |
| **Message Broadcaster** | Distribute messages to all/specific clients |
| **Idle Checker Thread** | Monitor and disconnect inactive clients |

## 4. Communication Flow

```
Client                          Server
  │                               │
  │──── TCP Connect ─────────────►│
  │                               │ (spawn new thread)
  │◄─── (waiting for login) ──────│
  │                               │
  │──── LOGIN Naman ─────────────►│
  │                               │ (validate username)
  │◄─── OK ───────────────────────│
  │                               │
  │──── MSG hello ───────────────►│
  │                               │ (broadcast to others)
  │                               │
  │◄─── MSG OtherUser hi ─────────│ (receive from others)
  │                               │
  │──── (disconnect) ────────────►│
  │                               │ (notify others)
                                  │──► INFO Naman disconnected
```

## 5. Design Decisions

| Decision | Rationale |
|----------|-----------|
| **Thread-per-client** | Simple model, adequate for 10-20 concurrent users |
| **Threading.Lock** | Ensures thread-safe access to shared client data |
| **Daemon threads** | Auto-cleanup when main server shuts down |
| **Buffered line parsing** | Handles fragmented TCP messages gracefully |
| **60s idle timeout** | Prevents zombie connections, configurable |

## 6. Scalability Considerations

- Current design supports ~50-100 concurrent users
- For higher scale, consider: asyncio, select/epoll, or message queues
- No persistence layer (by design - assignment requirement)
