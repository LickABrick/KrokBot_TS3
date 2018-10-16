import ts3
import requests
import json
import paramiko
from threading import Thread
import time
from datetime import datetime, timedelta
import re
import configparser

config = configparser.ConfigParser()
config.read('config.ini')

hostname = config['Ark Server']['hostname']
username = config['Ark Server']['username']
password = config['Ark Server']['password']


def ark_get_playercount():
    if ark_server_status == "online":
        url = "https://arkservers.net/api/query/{}:27015".format(config['Ark Server']['public_ip'])
        page = requests.get(url)
        json_data = json.loads(page.text)
        return json_data['info']['Players']
    else:
        return 0


def ark_get_serverstatus():
    global ark_server_status
    ark_server_status = 'unknown'
    while True:
        command = "timeout -k 30 20 ./arkserver monitor | tail -1"
        ssh_client = paramiko.SSHClient()
        ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh_client.connect(hostname=hostname, username=username, password=password)

        stdin, stdout, stderr = ssh_client.exec_command(command)
        result = stdout.readlines()
        result = str(result[0]).replace('\n', '')
        ansi_escape = re.compile(r'\x1b[^m]*m')
        result = ansi_escape.sub('', result)
        if "* To enable monitor run ./arkserver start" in result:
            if ark_server_status == "starting":
                pass
            else:
                ark_server_status = "offline"
        elif "  OK  ] Monitor arkserver: Querying port: gsquery: {}:27015 : 0/1: OK".format(config['Ark Server']['hostname']) in result:
            ark_server_status = "online"
        elif "Monitor arkserver: Querying port: gsquery: {}:27015 : 10/1: WAIT".format(config['Ark Server']['hostname']) in result:
            ark_server_status = "starting"
        else:
            ark_server_status = "error"
        print(ark_server_status)
        time.sleep(10)


def ark_start_server():
    command = "timeout -k 360 300 ./arkserver start"
    ssh_client = paramiko.SSHClient()
    ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh_client.connect(hostname=hostname, username=username, password=password)

    ssh_client.exec_command(command)


def ark_stop_server():
    command = "timeout -k 120 100 ./arkserver stop"
    ssh_client = paramiko.SSHClient()
    ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh_client.connect(hostname=hostname, username=username, password=password)

    ssh_client.exec_command(command)


def ark_get_serveridletime():
    global idle_time
    time_active = datetime.now()
    while True:
        global ark_server_status
        if ark_server_status == "starting":
            time_active = datetime.now()
        elif ark_server_status == "online":
            players_online = ark_get_playercount()
            if players_online > 0:
                time_active = datetime.now()
            idle_time = datetime.now() - time_active
            if idle_time > timedelta(hours=1, minutes=5):
                print("Server has been idle for over 1 minute now")
                ts3conn.sendtextmessage(targetmode="2", target=1, msg="Ark server has been idle for over 1 hour, stopping it! If you want to start it again use !ark start")
                ark_server_status = "offline"
                Thread(target=ark_stop_server).start()
            time.sleep(30)
        else:
            idle_time = "none"


thread1 = Thread(target=ark_get_serverstatus)
thread2 = Thread(target=ark_get_serveridletime)
thread1.start()
thread2.start()


with ts3.query.TS3Connection(config['TeamSpeak3']['hostname']) as ts3conn:
    # Note, that the client will wait for the response and raise a
    # **TS3QueryError** if the error id of the response is not 0.
    ts3conn.login(
        client_login_name=config['TeamSpeak3']['login_name'],
        client_login_password=config['TeamSpeak3']['login_password']
    )

    ts3conn.use(sid=config['TeamSpeak3']['sid'])

    # Set nickname of bot.
    ts3conn.clientupdate(client_nickname=config['TeamSpeak3']['nickname'])

    # Register for events
    ts3conn.servernotifyregister(event="server")
    ts3conn.servernotifyregister(event="textchannel")

    while True:
        # Send keepalive message to avoid being kicked after 10 minutes.
        ts3conn.send_keepalive()
        try:
            # Once every 550 seconds a new keepalive message will be sent.
            event = ts3conn.wait_for_event(timeout=100)

        except ts3.query.TS3TimeoutError as e:
            print(e)
        else:
            # Print event to terminal (for testing purposes)
            print(event[0])

            if "msg" in event[0]:
                global ark_server_status
                if event[0]["msg"].lower() == "!ark status":
                    playercount = ark_get_playercount()
                    msg = "The ark server is status is: {} and there are currently {} player(s) online! Server has been idle for {}".format(ark_server_status, playercount, idle_time)
                    ts3conn.sendtextmessage(targetmode="2", target=1, msg=msg)

                if event[0]["msg"].lower() == "!ark start":
                    if ark_server_status == "starting":
                        msg = "The ark server is already being started, this can take upto 2 minutes."
                    elif ark_server_status == "online":
                        msg = "The ark server is already started."
                    elif ark_server_status == "unknown":
                        msg = "Waiting for status, please try again in a bit!"
                    elif ark_server_status == "offline":
                        msg = "The Ark server will be started shortly, this can take upto 2 minutes."
                        ark_server_status = "starting"
                        start_server = Thread(target=ark_start_server)
                        start_server.start()
                    else:
                        msg = "Error, please contact an administrator"
                    ts3conn.sendtextmessage(targetmode="2", target=1, msg=msg)

                if event[0]["msg"].lower() == "!help":
                    msg = "List of commands: \n " \
                          "!help \n" \
                          "!ark status \n" \
                          "!ark start"
                    ts3conn.sendtextmessage(targetmode="2", target=1, msg=msg)
