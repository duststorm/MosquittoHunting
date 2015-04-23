#!/usr/bin/python
# -*- coding: utf-8 -*-

import signal
import sys
import argparse
import curses
import mosquitto

OLD_MOSQUITTO = True

parser = argparse.ArgumentParser(description='Monitors a mosquitto MQTT broker.')
parser.add_argument("--host", default='localhost',
                   help="mqtt host to connect to. Defaults to localhost.")
parser.add_argument("-p", "--port", type=int, default=1883,
                   help="network port to connect to. Defaults to 1883.")
parser.add_argument("-k", "--keepalive", type=int, default=60,
                   help="keep alive in seconds for this client. Defaults to 60.")
parser.add_argument("-n", "--newmosquitto", type=bool, default=False,
                   help="Monitor new mosquitto (v>=1.0).")

args = parser.parse_args()

OLD_MOSQUITTO = not args.newmosquitto

# Totals
SYS_BYTES_RECEIVED = "$SYS/broker/bytes/received"
SYS_BYTES_SENT = "$SYS/broker/bytes/sent"
SYS_MESSAGES_DROPPED = "$SYS/broker/messages/dropped"
SYS_MESSAGES_RECEIVED = "$SYS/broker/messages/received"
SYS_MESSAGES_SENT = "$SYS/broker/messages/sent"

# Average
SYS_LOAD_BYTES_RECEIVED = "$SYS/broker/load/bytes/received/1min"
SYS_LOAD_BYTES_SENT = "$SYS/broker/load/bytes/sent/1min"
SYS_LOAD_PUBLISHED_RECEIVED = "$SYS/broker/load/publish/received/1min"
SYS_LOAD_PUBLISHED_SENT = "$SYS/broker/load/publish/sent/1min"
SYS_LOAD_SOCKETS = "$SYS/broker/load/sockets/1min"
SYS_LOAD_CONNECTIONS = "$SYS/broker/load/connections/+"

# Clients
if OLD_MOSQUITTO:
    SYS_CLIENTS_CONNECTED = "$SYS/broker/clients/active"
    SYS_CLIENTS_DISCONNECTED = "$SYS/broker/clients/inactive"
else:
    SYS_CLIENTS_CONNECTED = "$SYS/broker/clients/connected"
    SYS_CLIENTS_DISCONNECTED = "$SYS/broker/clients/disconnected"
SYS_CLIENTS_EXPIRED = "$SYS/broker/clients/expired"
SYS_CLIENTS_MAXIMUM = "$SYS/broker/clients/maximum"
SYS_CLIENTS_TOTAL = "$SYS/broker/clients/total"

# Message storage
SYS_MESSAGES_STORED = "$SYS/broker/messages/stored"
SYS_MESSAGES_RETAINED = "$SYS/broker/retained messages/count"
SYS_SUBSCRIPTIONS_COUNT = "$SYS/broker/subscriptions/count"
SYS_MESSAGES_INFLIGHT = "$SYS/broker/messages/inflight"

# Broker info
SYS_BROKER_UPTIME = "$SYS/broker/uptime"
SYS_BROKER_VERSION = "$SYS/broker/version"

topics = [
  SYS_BYTES_RECEIVED,
  SYS_BYTES_SENT,
  SYS_MESSAGES_DROPPED,
  SYS_MESSAGES_RECEIVED,
  SYS_MESSAGES_RETAINED,
  SYS_MESSAGES_STORED,
  SYS_MESSAGES_SENT,
  SYS_LOAD_BYTES_RECEIVED,
  SYS_LOAD_BYTES_SENT,
  SYS_LOAD_PUBLISHED_RECEIVED,
  SYS_LOAD_PUBLISHED_SENT,
  SYS_LOAD_CONNECTIONS,
  SYS_LOAD_SOCKETS,
  SYS_MESSAGES_INFLIGHT,
  SYS_SUBSCRIPTIONS_COUNT,
  SYS_CLIENTS_CONNECTED,
  SYS_CLIENTS_DISCONNECTED,
  SYS_CLIENTS_EXPIRED,
  SYS_CLIENTS_TOTAL,
  SYS_CLIENTS_MAXIMUM,
  SYS_BROKER_UPTIME,
  SYS_BROKER_VERSION
]

stats = {}

flags = {
  "connected": False
}

screen = curses.initscr()
curses.noecho()
curses.curs_set(0) 
screen.keypad(1)
screen.timeout(10)

i = 1

def draw():
  global i  
  receivedMb = float(stats.get(SYS_BYTES_RECEIVED, 0.0)) / 1024.0 / 1024.0
  sentMb = float(stats.get(SYS_BYTES_SENT, 0.0)) / 1024.0 / 1024.0
  
  receivedKbps = float(stats.get(SYS_LOAD_BYTES_RECEIVED, 0.0)) / 1024.0 / 60.0
  sentKbps = float(stats.get(SYS_LOAD_BYTES_SENT, 0.0)) / 1024.0 / 60.0

  i = 1
  def _clear_screen():
    global i
    screen.clear()
    i = 1
  
  def _to_screen(text):
    global i
    screen.addstr(i,2, text)
    i += 1

  _clear_screen()
  _to_screen("Mosquitto Stats")
  _to_screen("%s  uptime: %s" % (stats.get(SYS_BROKER_VERSION), stats.get(SYS_BROKER_UPTIME)))
  _to_screen("Connected: %s (%s:%d, %d)" % ( ("Yes" if flags["connected"] else "No"), args.host, args.port, args.keepalive ))
  i += 1
  _to_screen("         |  Received\t\tSent\t\tReceived/min\t\tSent/min")
  _to_screen("-------------------------------------------------------------------------------")
  _to_screen("Bytes    |  %.2f Mb\t\t%.2f Mb\t\t%.2f kbps\t\t%.2f kbps" % (receivedMb, sentMb, receivedKbps, sentKbps ))    
  _to_screen("Messages |  %s\t\t%s\t\t%s\t\t\t%s" % (stats.get(SYS_MESSAGES_RECEIVED), stats.get(SYS_MESSAGES_SENT), stats.get(SYS_LOAD_PUBLISHED_RECEIVED), stats.get(SYS_LOAD_PUBLISHED_SENT) ))
  i += 1
  _to_screen("Messages dropped: %s" % stats.get(SYS_MESSAGES_DROPPED))
  i += 2
  _to_screen("         |  Stored\t\tRetained\tIn-flight")
  _to_screen("-------------------------------------------------------------------------------")
  _to_screen("Messages |  %s\t\t%s\t\t%s" % (stats.get(SYS_MESSAGES_STORED), stats.get(SYS_MESSAGES_RETAINED), stats.get(SYS_MESSAGES_INFLIGHT)))
  i += 1
  _to_screen("Subscriptions: %s" % stats.get(SYS_SUBSCRIPTIONS_COUNT))
  i += 2
  _to_screen("         |  Connected\t\tDisconnected (persist)\tTotal\tExpired (persist)")
  _to_screen("-------------------------------------------------------------------------------")
  _to_screen("Clients  |  %s\t\t\t%s\t\t\t%s\t%s" % (stats.get(SYS_CLIENTS_CONNECTED), stats.get(SYS_CLIENTS_DISCONNECTED), stats.get(SYS_CLIENTS_TOTAL), stats.get(SYS_CLIENTS_EXPIRED) ))
  i += 1
  _to_screen("Clients connected all-time maximum: %s" % stats.get(SYS_CLIENTS_MAXIMUM))
  i += 2
  _to_screen("         |  Sockets\t\tConnections")
  _to_screen("-------------------------------------------------------------------------------")
  _to_screen("Load/min |  %s\t\t%s" % (stats.get(SYS_LOAD_SOCKETS), stats.get(SYS_LOAD_CONNECTIONS)))
  i += 2
  _to_screen("Press 'q' to quit")

def signal_handler(signal, frame):
  curses.endwin()
  sys.exit(0)

signal.signal(signal.SIGINT, signal_handler)

def on_connect(mosq, obj, rc):
  flags["connected"] = True
  draw()
  for topic in topics:
    mosq.subscribe(topic, 0)
    
def on_disconnect(mosq, obj, rc):
  flags["connected"] = False
  draw()

def on_message(mosq, obj, msg):
  stats[msg.topic] = str(msg.payload)
  draw()

def on_log(mosq, obj, level, string):
  print(string)

mqttc = mosquitto.Mosquitto()

# Register callbacks
mqttc.on_message = on_message
mqttc.on_connect = on_connect
mqttc.on_disconnect = on_disconnect
#mqttc.on_log = on_log

# Connect on start
mqttc.connect(args.host, args.port, args.keepalive)

draw()

while True:
  rc = mqttc.loop()
  if rc != 0: break
  
  event = screen.getch()
  
  if event == ord("q"): break
  elif event == ord("c"): 
    mqttc.connect(args.host)
  elif event == ord("d"):
    mqttc.disconnect()
  
  draw()

curses.endwin()
