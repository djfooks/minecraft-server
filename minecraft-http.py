#!/usr/bin/python

# > list
# [21:33:54] [Server thread/INFO] [minecraft/DedicatedServer]: There are 1/20 players online:
# [21:33:54] [Server thread/INFO] [minecraft/DedicatedServer]: username

import json
from BaseHTTPServer import BaseHTTPRequestHandler,HTTPServer
import subprocess
import threading
from time import sleep, time
import sys
import pty
import os
import re
import httplib

PORT_NUMBER = 8252
API_KEY = sys.argv[1]

#mount_drive = False
# minecraft_cmd = ['python', 'fake-minecraft.py']
# minecraft_dir = '.'

mount_drive = True
minecraft_cmd = ['sudo', '-u', 'ubuntu', 'java', '-jar', 'server.jar', 'nogui']
minecraft_dir = '/data/minecraft/'

class MinecraftOutputJob(threading.Thread):

    def __init__(self, process, stdout, minecraft_info):
        threading.Thread.__init__(self)
        self.process = process
        self.stdout = stdout
        self.minecraft_info = minecraft_info

    def run(self):
        print('MinecraftOutputJob Thread #%s started' % self.ident)

        output_lines = self.minecraft_info['output_lines']

        self.minecraft_info['server_empty_time'] = time()

        any_players_joined = False
        num_players_regex = re.compile('There are ([0-9]+)/[0-9]+ players online:')
        num_players = 0

        try:
            while True:
                self.minecraft_info['last_output'] = time()
                output = self.stdout.readline().strip()
                self.minecraft_info['lines_output'] += 1
                if output:
                    match = num_players_regex.search(output)
                    if match:
                        prev_num_players = num_players
                        num_players = int(match.group(1))
                        self.minecraft_info['num_players'] = num_players
                        if num_players > 0:
                            any_players_joined = True
                        elif prev_num_players > 0:
                            self.minecraft_info['server_empty_time'] = time()
                        self.minecraft_info['status'] = 'RUNNING'
                        self.minecraft_info['any_players_joined'] = any_players_joined
                    output_lines.append(output)
                    if len(output_lines) > 300:
                        output_lines.pop(0)
        except IOError:
            pass

        print('MinecraftOutputJob Thread #%s stopped' % self.ident)

class MinecraftJob(threading.Thread):

    def __init__(self, minecraft_info):
        threading.Thread.__init__(self)
        self.minecraft_info = minecraft_info
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

        minecraft_output_thread = MinecraftOutputJob(minecraft_server_process, stdout, self.minecraft_info)
        minecraft_output_thread.start()

        last_player_check = time()
        start_time = time()

        while not self.shutdown_flag.is_set():
            sleep(1)
            if last_player_check + 5 < time() and self.minecraft_info['last_output'] + 5 < time():
                last_player_check = time()
                minecraft_server_process.stdin.write('list\n')
                minecraft_server_process.stdin.flush()
                if self.minecraft_info['any_players_joined'] or start_time + 60 * 20 < time():
                    if self.minecraft_info['num_players'] == 0 and self.minecraft_info['server_empty_time'] + 60 * 5 < time():
                        break

        self.minecraft_info['status'] = 'STOPPING'
        print 'Stopping minecraft server'
        minecraft_server_process.stdin.write('stop\n')
        minecraft_server_process.wait()
        minecraft_output_thread.join()
        print 'Minecraft server stopped'

        # shutdown the server if we are stopping due to no players on minecraft or we were told to
        if not self.shutdown_flag.is_set() or self.minecraft_info['stop_server']:
            shutdown_server()

        print('MinecraftJob Thread #%s stopped' % self.ident)

def shutdown_server():
    if mount_drive:
        print("Unmounting volume")
        subprocess.Popen(['umount', '/data']).wait()

    print("Shutting down")
    for i in xrange(99):
        sleep(5)
        con = httplib.HTTPSConnection('if39zuadqc.execute-api.eu-west-2.amazonaws.com')
        con.set_debuglevel(1)
        con.request('GET', '/default/stop-server', None, { 'api-key': API_KEY })
        print(con.getresponse())

def main():
    if mount_drive:
        print "Starting up..."
        already_mounted = False
        found = None
        while not found:
            for device in ['/dev/xvdf', '/dev/nvme1n1']:
                lsblk = subprocess.Popen(['lsblk', device, '-l', '-n'], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                out, outerr = lsblk.communicate()
                if '/data' in out or '/data' in outerr:
                    found = device
                    print "Already mounted!"
                    already_mounted = True
                    break
                if lsblk.wait() == 0:
                    found = device
                    break
            print "Waiting for drive to mount..."
            sleep(1)

        if not already_mounted:
            mount_result = subprocess.Popen(['mount', found, '/data']).wait()
            if mount_result != 0:
                print "Mount failed!"
                return
            print "Drive mounted"

    minecraft_info = {
        'last_output': 0,
        'lines_output': 0,
        'num_players': 0,
        'status': 'LOADING',
        'server_empty_time': 0,
        'any_players_joined': False,
        'output_lines': [],
        'stop_server': False
    }
    minecraft_server_thread = MinecraftJob(minecraft_info)

    class myHandler(BaseHTTPRequestHandler):
        def do_GET(self):
            self.send_response(200)
            self.send_header('Content-type','text/plain')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            if self.path == '/stop-minecraft':
                minecraft_server_thread.shutdown_flag.set()
                if minecraft_server_thread.is_alive():
                    self.wfile.write(json.dumps({'status': 'STOPPING'}))
                else:
                    self.wfile.write(json.dumps({'status': 'STOPPED'}))

            elif self.path == '/stop-server':
                stopping_server = minecraft_info['stop_server']
                minecraft_info['stop_server'] = True
                if minecraft_server_thread.is_alive():
                    minecraft_server_thread.shutdown_flag.set()
                    self.wfile.write(json.dumps({'status': 'STOPPING'}))
                else:
                    self.wfile.write(json.dumps({'status': 'STOPPED'}))
                    if not stopping_server:
                        shutdown_server()

            elif self.path == '/status':
                if minecraft_server_thread.is_alive():
                    self.wfile.write(json.dumps({'minecraft': {
                        'status': minecraft_info['status'],
                        'lines_output': minecraft_info['lines_output'],
                        'last_output': minecraft_info['last_output'],
                        'num_players': minecraft_info['num_players'],
                        'server_empty_time': minecraft_info['server_empty_time'],
                        'any_players_joined': minecraft_info['any_players_joined']
                    }}))
                else:
                    self.wfile.write(json.dumps({'status': 'STOPPED'}))

            elif self.path == '/output':
                self.wfile.write(str(minecraft_info['last_output']) + '\n')
                for l in minecraft_info['output_lines']:
                    self.wfile.write(l + '\n')

            else:
                self.wfile.write('Hello world\n')
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
