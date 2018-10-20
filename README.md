# KrokBot_TS3
A Teamspeak 3 bot created in python 3.6 to control game servers.

Currently only supports Ark servers installed via [LGSM](https://linuxgsm.com/)
It uses [Paramiko](http://www.paramiko.org/) to connect via SSH and execute commands.

*The bot is created to fit my own needs, but feel free to request features/games you want to see and I will gladly implement them.*

## Features

 - Gathers status of Ark server and amount of online players (visible
   from !ark status command).
 - Shuts down the server if nobody has been online for 30 minutes.
 - Ark server can be started by anyone using the !ark start command.


## Install Instructions
*Tested on Debian 9*

**Requirements**
- Ark server installed via [LGSM](https://linuxgsm.com/)
- Ark server reachable via SSH
- Python3.6 installed

Clone the repository

    git clone https://github.com/LickABrick/KrokBot_TS3.git

Install the required python packages

    pip3 install ts3 python-valve configparser paramiko

Rename the config.ini.example to config.ini

    cp config.ini.example config.ini
Edit the config.ini to with your own settings.
Start the bot (I use nohup to keep it running in the background)

    nohup python3 main.py &
