import ts3
import valve.source.a2s
import paramiko
from threading import Thread
import time
from datetime import datetime, timedelta
import configparser

config = configparser.ConfigParser()
config.read('config.ini')


def ark_ssh_exec(command):
    ssh_client = paramiko.SSHClient()
    ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh_client.connect(hostname=config['Ark Server']['hostname'], username=config['Ark Server']['username'], password=config['Ark Server']['password'])
    ssh_client.exec_command(command)


def ark_get_serverinfo():
    global ark_playercount
    global ark_server_status
    ark_server_status = "unknown"
    server_address = (config['Ark Server']['hostname'], int(config['Ark Server']['query_port']))
    while True:
        try:
            with valve.source.a2s.ServerQuerier(server_address) as server:
                ark_playercount = server.info()['player_count']
                ark_server_status = "online"
        except valve.source.NoResponseError:
            if ark_server_status == "starting":
                pass
            else:
                ark_server_status = "offline"
            ark_playercount = 0
        print(ark_server_status)
        print("Players online: {}".format(ark_playercount))
        time.sleep(10)


def ark_start_server():
    global ark_server_status
    ark_server_status = "starting"
    command = "timeout -k 360 300 ./arkserver start"
    ark_ssh_exec(command)
    print("Ark Server has been started!")


def ark_stop_server():
    command = "./arkserver stop"
    ark_ssh_exec(command)
    print("Ark Server has been stopped!")


def ark_get_serveridletime():
    global idle_time
    time_active = datetime.now()
    while True:
        global ark_server_status
        if ark_server_status == "starting":
            time_active = datetime.now()
        elif ark_server_status == "online":
            if ark_playercount > 0:
                time_active = datetime.now()
            idle_time = datetime.now() - time_active
            if idle_time > timedelta(minutes=30):
                print("Server has been idle for over 30 minutes, stopping server")
                ark_server_status = "offline"
                Thread(target=ark_stop_server).start()
            time.sleep(30)
        else:
            idle_time = "none"


thread1 = Thread(target=ark_get_serverinfo, daemon=True)
thread2 = Thread(target=ark_get_serveridletime, daemon=True)
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
            # Once every 100 seconds a new keepalive message will be sent.
            event = ts3conn.wait_for_event(timeout=100)

        except ts3.query.TS3TimeoutError as e:
            print(e)
        else:
            # Print event to terminal (for testing purposes)
            # print(event[0])

            if "msg" in event[0]:
                if event[0]["msg"].lower() == "!ark status":
                    msg = "The ark server is status is: {} and there are currently {} player(s) online! Server has been idle for {}".format(ark_server_status, ark_playercount, idle_time)
                    ts3conn.sendtextmessage(targetmode="2", target=1, msg=msg)

                elif event[0]["msg"].lower() == "!ark start":
                    if ark_server_status == "starting":
                        msg = "The ark server is already being started, this can take upto 2 minutes."
                    elif ark_server_status == "online":
                        msg = "The ark server is already started."
                    elif ark_server_status == "unknown":
                        msg = "Waiting for status, please try again in a bit!"
                    elif ark_server_status == "offline":
                        msg = "The Ark server will be started shortly, this can take upto 2 minutes."
                        start_server = Thread(target=ark_start_server)
                        start_server.start()
                    else:
                        msg = "Error, please contact an administrator"
                    ts3conn.sendtextmessage(targetmode="2", target=1, msg=msg)
                elif event[0]["msg"].lower() == "!help":
                    msg = "List of commands: \n " \
                          "!help \n" \
                          "!ark status \n" \
                          "!ark start"
                    ts3conn.sendtextmessage(targetmode="2", target=1, msg=msg)
