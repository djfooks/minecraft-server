#!/usr/bin/python

# > list
# [21:33:54] [Server thread/INFO] [minecraft/DedicatedServer]: There are 1/20 players online:
# [21:33:54] [Server thread/INFO] [minecraft/DedicatedServer]: username

import json
from BaseHTTPServer import BaseHTTPRequestHandler,HTTPServer
import subprocess
import threading
from time import sleep
import sys
import pty
import os

PORT_NUMBER = 8252

mount_drive = False
minecraft_cmd = ['python', 'fake-minecraft.py']
minecraft_dir = '.'

# mount_drive = True
# minecraft_cmd = ['sudo', '-u', 'ubuntu', './ServerStart.sh']
# minecraft_dir = '/data/skyfactory4/'

class MinecraftOutputJob(threading.Thread):

    def __init__(self, process, stdout, output_lines):
        threading.Thread.__init__(self)
        self.process = process
        self.stdout = stdout
        self.output_lines = output_lines

    def run(self):
        print('MinecraftOutputJob Thread #%s started' % self.ident)

        try:
            while True:
                # data = self.stdout.read(1).decode("utf-8")
                # if not data:
                #     break
                # sys.stdout.write(data)
                # sys.stdout.flush()
                output = self.stdout.readline()
                if output:
                    self.output_lines.append(output)
                    if len(self.output_lines) > 100:
                        self.output_lines.pop(0)
        except IOError:
            pass

        print('MinecraftOutputJob Thread #%s stopped' % self.ident)

class MinecraftJob(threading.Thread):

    def __init__(self, output_lines):
        threading.Thread.__init__(self)
        self.output_lines = output_lines
        self.shutdown_flag = threading.Event()

    def run(self):
        print('MinecraftJob Thread #%s started' % self.ident)

        master, slave = pty.openpty()

        minecraft_server_process = subprocess.Popen(minecraft_cmd,
                cwd=minecraft_dir,
                stdout=slave,
                stderr=slave,
                close_fds=True,
                stdin=subprocess.PIPE)
        print('Starting minecraft server...')

        stdout = os.fdopen(master)
        os.close(slave)

        minecraft_output_thread = MinecraftOutputJob(minecraft_server_process, stdout, self.output_lines)
        minecraft_output_thread.start()

        while not self.shutdown_flag.is_set():
            sleep(1)

        print 'Stopping minecraft server'
        minecraft_server_process.stdin.write('stop\n')
        minecraft_server_process.wait()
        minecraft_output_thread.join()
        print 'Minecraft server stopped'

        print('MinecraftJob Thread #%s stopped' % self.ident)

def main():
    if mount_drive:
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

    output_lines = []
    minecraft_server_thread = MinecraftJob(output_lines)

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
            elif self.path == '/output':
                for l in output_lines:
                    self.wfile.write(l)
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
