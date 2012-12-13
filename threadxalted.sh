#!/bin/sh

while true; do
   ./glennbot.py irc.freenode.net '#threadxalted'
   echo "Killed.  Restarting in 10 seconds..."
   sleep 10
done
