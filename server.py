#!/usr/bin/env python3
"""
TCP Chat Server
A simple multi-client chat server using only Python standard library.

Features:
- Multi-client support (thread-per-client)
- Login with unique username
- Message broadcasting
- Private messages (DM)
- User listing (WHO)
- Heartbeat (PING/PONG)
- Idle timeout (60 seconds)

Usage:
    python server.py [--port PORT]
    
Environment Variables:
    PORT - Server port (default: 4000)
"""

import socket
import threading
import argparse
import os
import time
from typing import Dict, Optional


class ChatServer:
    """Multi-client TCP chat server."""
    
    def __init__(self, host: str = '0.0.0.0', port: int = 4000, idle_timeout: int = 60):
        self.host = host
        self.port = port
        self.idle_timeout = idle_timeout
        self.server_socket: Optional[socket.socket] = None
        
        # Thread-safe client management
        # Maps socket -> username
        self.clients: Dict[socket.socket, str] = {}
        # Maps username -> socket (for DM lookup)
        self.usernames: Dict[str, socket.socket] = {}
        # Lock for thread-safe access to client dictionaries
        self.lock = threading.Lock()
        
        # Track last activity time for idle timeout
        self.last_activity: Dict[socket.socket, float] = {}
        
        self.running = False
    
    def start(self):
        """Start the chat server."""
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        
        try:
            self.server_socket.bind((self.host, self.port))
            self.server_socket.listen(10)
            self.running = True
            
            print(f"[SERVER] Chat server started on {self.host}:{self.port}")
            print(f"[SERVER] Idle timeout: {self.idle_timeout} seconds")
            print("[SERVER] Waiting for connections...")
            
            # Start idle checker thread
            idle_thread = threading.Thread(target=self._check_idle_clients, daemon=True)
            idle_thread.start()
            
            while self.running:
                try:
                    conn, addr = self.server_socket.accept()
                    print(f"[SERVER] New connection from {addr}")
                    
                    # Start a new thread to handle this client
                    client_thread = threading.Thread(
                        target=self._handle_client,
                        args=(conn, addr),
                        daemon=True
                    )
                    client_thread.start()
                    
                except socket.error as e:
                    if self.running:
                        print(f"[SERVER] Socket error: {e}")
                        
        except KeyboardInterrupt:
            print("\n[SERVER] Shutting down...")
        finally:
            self.stop()
    
    def stop(self):
        """Stop the chat server."""
        self.running = False
        
        # Close all client connections
        with self.lock:
            for conn in list(self.clients.keys()):
                try:
                    conn.close()
                except:
                    pass
            self.clients.clear()
            self.usernames.clear()
        
        if self.server_socket:
            try:
                self.server_socket.close()
            except:
                pass
        
        print("[SERVER] Server stopped.")
    
    def _handle_client(self, conn: socket.socket, addr):
        """Handle a single client connection."""
        username = None
        
        try:
            # Set socket timeout for idle detection
            conn.settimeout(5.0)  # Check every 5 seconds
            
            # Update activity timestamp
            with self.lock:
                self.last_activity[conn] = time.time()
            
            # Wait for LOGIN
            username = self._handle_login(conn, addr)
            
            if not username:
                conn.close()
                return
            
            print(f"[SERVER] User '{username}' logged in from {addr}")
            
            # Main message loop
            buffer = ""
            while self.running:
                try:
                    data = conn.recv(1024)
                    
                    if not data:
                        # Client disconnected
                        break
                    
                    # Update activity timestamp
                    with self.lock:
                        self.last_activity[conn] = time.time()
                    
                    # Decode and buffer the data
                    buffer += data.decode('utf-8', errors='ignore')
                    
                    # Process complete lines
                    while '\n' in buffer:
                        line, buffer = buffer.split('\n', 1)
                        line = line.strip()
                        
                        if line:
                            self._process_command(conn, username, line)
                            
                except socket.timeout:
                    # Timeout is normal, just continue
                    continue
                except ConnectionResetError:
                    break
                except Exception as e:
                    print(f"[SERVER] Error receiving from {username}: {e}")
                    break
                    
        except Exception as e:
            print(f"[SERVER] Error handling client {addr}: {e}")
        finally:
            # Clean up
            self._remove_client(conn, username)
    
    def _handle_login(self, conn: socket.socket, addr) -> Optional[str]:
        """Handle the login process. Returns username if successful, None otherwise."""
        buffer = ""
        
        while self.running:
            try:
                data = conn.recv(1024)
                
                if not data:
                    return None
                
                # Update activity
                with self.lock:
                    self.last_activity[conn] = time.time()
                
                buffer += data.decode('utf-8', errors='ignore')
                
                # Look for complete line
                while '\n' in buffer:
                    line, buffer = buffer.split('\n', 1)
                    line = line.strip()
                    
                    if not line:
                        continue
                    
                    # Parse LOGIN command
                    if line.startswith('LOGIN '):
                        username = line[6:].strip()
                        
                        if not username:
                            self._send(conn, "ERR invalid-username")
                            continue
                        
                        # Check if username is taken
                        with self.lock:
                            if username in self.usernames:
                                self._send(conn, "ERR username-taken")
                                continue
                            
                            # Register the user
                            self.clients[conn] = username
                            self.usernames[username] = conn
                        
                        self._send(conn, "OK")
                        return username
                    else:
                        self._send(conn, "ERR must-login-first")
                        
            except socket.timeout:
                continue
            except Exception as e:
                print(f"[SERVER] Login error from {addr}: {e}")
                return None
        
        return None
    
    def _process_command(self, conn: socket.socket, username: str, line: str):
        """Process a command from a logged-in user."""
        
        # MSG <text> - broadcast message
        if line.startswith('MSG '):
            text = line[4:].strip()
            if text:
                self._broadcast(f"MSG {username} {text}", exclude=conn)
        
        # WHO - list active users
        elif line == 'WHO':
            with self.lock:
                for user in self.usernames.keys():
                    self._send(conn, f"USER {user}")
        
        # DM <username> <text> - private message
        elif line.startswith('DM '):
            parts = line[3:].strip().split(' ', 1)
            if len(parts) >= 2:
                target_user, text = parts[0], parts[1]
                self._send_private(conn, username, target_user, text)
            else:
                self._send(conn, "ERR invalid-dm-format")
        
        # PING - heartbeat
        elif line == 'PING':
            self._send(conn, "PONG")
        
        # Unknown command - treat as message content (be lenient)
        else:
            # Silently ignore unknown commands
            pass
    
    def _send(self, conn: socket.socket, message: str):
        """Send a message to a single client."""
        try:
            conn.sendall((message + '\n').encode('utf-8'))
        except Exception as e:
            print(f"[SERVER] Error sending message: {e}")
    
    def _broadcast(self, message: str, exclude: Optional[socket.socket] = None):
        """Broadcast a message to all connected clients."""
        with self.lock:
            for conn in list(self.clients.keys()):
                if conn != exclude:
                    try:
                        conn.sendall((message + '\n').encode('utf-8'))
                    except Exception as e:
                        print(f"[SERVER] Error broadcasting to client: {e}")
    
    def _send_private(self, sender_conn: socket.socket, from_user: str, to_user: str, text: str):
        """Send a private message to a specific user."""
        with self.lock:
            if to_user not in self.usernames:
                self._send(sender_conn, f"ERR user-not-found {to_user}")
                return
            
            target_conn = self.usernames[to_user]
        
        self._send(target_conn, f"DM {from_user} {text}")
    
    def _remove_client(self, conn: socket.socket, username: Optional[str]):
        """Remove a client and notify others."""
        with self.lock:
            # Remove from tracking
            if conn in self.clients:
                del self.clients[conn]
            if username and username in self.usernames:
                del self.usernames[username]
            if conn in self.last_activity:
                del self.last_activity[conn]
        
        # Close connection
        try:
            conn.close()
        except:
            pass
        
        # Notify others if user was logged in
        if username:
            print(f"[SERVER] User '{username}' disconnected")
            self._broadcast(f"INFO {username} disconnected")
    
    def _check_idle_clients(self):
        """Background thread to check for idle clients."""
        while self.running:
            time.sleep(10)  # Check every 10 seconds
            
            current_time = time.time()
            clients_to_remove = []
            
            with self.lock:
                for conn, last_time in list(self.last_activity.items()):
                    if current_time - last_time > self.idle_timeout:
                        username = self.clients.get(conn)
                        clients_to_remove.append((conn, username))
            
            # Remove idle clients (outside the lock to avoid deadlock)
            for conn, username in clients_to_remove:
                if username:
                    print(f"[SERVER] User '{username}' timed out (idle)")
                    try:
                        self._send(conn, "ERR idle-timeout")
                    except:
                        pass
                self._remove_client(conn, username)


def main():
    """Main entry point."""
    # Parse command line arguments
    parser = argparse.ArgumentParser(description='TCP Chat Server')
    parser.add_argument(
        '--port', '-p',
        type=int,
        default=int(os.environ.get('PORT', 4000)),
        help='Port to listen on (default: 4000, or PORT env var)'
    )
    parser.add_argument(
        '--idle-timeout', '-t',
        type=int,
        default=60,
        help='Idle timeout in seconds (default: 60)'
    )
    
    args = parser.parse_args()
    
    # Create and start server
    server = ChatServer(port=args.port, idle_timeout=args.idle_timeout)
    
    try:
        server.start()
    except KeyboardInterrupt:
        print("\n[SERVER] Received interrupt signal")
    finally:
        server.stop()


if __name__ == '__main__':
    main()
