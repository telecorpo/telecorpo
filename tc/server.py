
import socket
import socketserver
import time
import threading


PRODUCERS = {}
PRODUCERS_LOCK = threading.Lock()


class ServerHandler(socketserver.BaseRequestHandler):

    def handle(self):
        data = self.request.recv(1024).decode()
        with PRODUCERS_LOCK:
            if data == "*":
                resp = "\n".join(" ".join([p] + m) for p, m in PRODUCERS)
            else:
                ipaddr = self.request.getsockname()[0]
                mounts = data.split()
                if ipaddr in PRODUCERS:
                    resp = "Producer already connected"
                else:
                    PRODUCERS[ipaddr] = mounts
                    resp = "OK"
        self.request.send(resp.encode())



def janitor():
    while True:
        for producer in PRODUCERS.copy():
            time.sleep(0.2)
            try:
                with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                    address = (producer, 13371)
                    sock.connect(address)
                    sock.send(b"OPTIONS * RTSP/1.0\r\n")
                    data = sock.recv(4096).decode().split("\r\n")[0]
                    assert data == "RTSP/1.0 200 OK"
            except Exception as err:
                print(str(err))
                with PRODUCERS_LOCK:
                    del PRODUCERS[producer]
                    break


if __name__ == '__main__':
    janitor_thread = threading.Thread(target=janitor)
    janitor_thread.start()

    address = ('0.0.0.0', 13370)
    server = socketserver.TCPServer(address, ServerHandler)
    server.serve_forever()

#
# if __name__ == '__main__':
#     app.run(host='0.0.0.0', port=13370, debug=True)
