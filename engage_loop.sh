#!/data/data/com.termux/files/usr/bin/bash
cd ~/nostr
while true; do
  python engage.py >> logeng.txt 2>&1
  sleep $(( (RANDOM % 7200) + 14400 ))
done
