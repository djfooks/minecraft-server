#!/usr/bin/python
import json
from BaseHTTPServer import BaseHTTPRequestHandler,HTTPServer
import subprocess
import threading
from time import sleep

PORT_NUMBER = 8251

# minecraft_cmd = ['python', 'fake-minecraft.py']
# minecraft_dir = 'C:\\dev\\minecraft-server'

minecraft_cmd = ['sudo', '-u', 'ubuntu', './ServerStart.sh']
minecraft_dir = '/data/skyfactory4/'

class MinecraftJob(threading.Thread):

    def __init__(self):
        threading.Thread.__init__(self)
        self.shutdown_flag = threading.Event()

    def run(self):
        print('Thread #%s started' % self.ident)

        minecraft_server_process = subprocess.Popen(minecraft_cmd,
                cwd=minecraft_dir,
                stdin=subprocess.PIPE)
        print('Starting minecraft server...')

        while not self.shutdown_flag.is_set():
            sleep(1)

        print 'Stopping minecraft server'
        minecraft_server_process.communicate('stop\n')
        minecraft_server_process.wait()
        print 'Minecraft server stopped'

        print('Thread #%s stopped' % self.ident)

def main():
    print "Starting up..."
    already_mounted = False
    while True:
        lsblk = subprocess.Popen(['lsblk', '/dev/xvdf', '-l', '-n'], stdout=subprocess.PIPE)
        out, outerr = lsblk.communicate()
        if lsblk.wait() != 0:
            break
        if '/data' in out:
            print "Already mounted!"
            already_mounted = True
            break
        print "Waiting for drive to mount..."
        sleep(1)

    if not already_mounted:
        mount_result = subprocess.Popen(['mount', '/dev/xvdf', '/data']).wait()
        if mount_result != 0:
            print "Mount failed!"
            return
        print "Drive mounted"

    minecraft_server_thread = MinecraftJob()

    class myHandler(BaseHTTPRequestHandler):
        def do_GET(self):
            self.send_response(200)
            self.send_header('Content-type','text/json')
            self.end_headers()
            if self.path == '/stop-server':
                minecraft_server_thread.shutdown_flag.set()
                if minecraft_server_thread.is_alive():
                    self.wfile.write(json.dumps({'status': 200, 'result': 'STOPPING', 'body': 'Stopping server...'}))
                else:
                    self.wfile.write(json.dumps({'status': 200, 'result': 'STOPPED', 'body': 'Stopped server'}))
            else:
                self.wfile.write(json.dumps({'status': 200, 'body': 'ok'}))
            return

    minecraft_server_thread.start()

    try:
        server = HTTPServer(('', PORT_NUMBER), myHandler)
        print 'Started httpserver on port ' , PORT_NUMBER
        server.serve_forever()

    except KeyboardInterrupt:
        print '^C received, shutting down the web server'
        minecraft_server_thread.shutdown_flag.set()
        minecraft_server_thread.join()
        server.socket.close()

main()
