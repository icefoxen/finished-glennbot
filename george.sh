#!/bin/sh

while true; do
   ./glennbot.py irc.hwcommunity.com '#outsider'
   echo "Killed.  Restarting in 10 seconds..."
   sleep 10
done
