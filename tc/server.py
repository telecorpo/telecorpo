
import socket
import socketserver
import time
import threading


PRODUCERS = {}
PRODUCERS_LOCK = threading.Lock()


class ServerHandler(socketserver.BaseRequestHandler):

    def handle(self):
        data = self.request.recv(1024).decode().strip()
        with PRODUCERS_LOCK:
            if data == "*":
                resp = "\n".join(" ".join([p] + m) for p, m in PRODUCERS.items())
            else:
                ipaddr = self.request.getpeername()[0]
                mounts = data.split()
                if ipaddr in PRODUCERS:
                    resp = "Producer already connected"
                    print("== cannot registrate {} again".format(ipaddr))
                else:
                    PRODUCERS[ipaddr] = mounts
                    resp = "OK"
                    print("-> registrated {}: {}".format(ipaddr, ', '.join(mounts)))
        self.request.send(resp.encode())



def janitor():
    while True:
        for producer in PRODUCERS.copy():
            time.sleep(0.2)
            try:
                with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                    address = (producer, 13371)
                    sock.connect(address)
                    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                    sock.send(b"OPTIONS * RTSP/1.0\r\n")
                    data = sock.recv(4096).decode().split("\r\n")[0]
                    assert data == "RTSP/1.0 200 OK"
            except Exception as err:
                with PRODUCERS_LOCK:
                    print("<- removed {}".format(producer))
                    del PRODUCERS[producer]
                    break

def main():
    janitor_thread = threading.Thread(target=janitor, daemon=True)
    janitor_thread.start()

    try:
        address = ('0.0.0.0', 13370)
        server = socketserver.TCPServer(address, ServerHandler)
        print('Running...')
        server.serve_forever()
    except KeyboardInterrupt:
        pass

