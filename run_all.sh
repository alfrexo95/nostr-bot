#!/data/data/com.termux/files/usr/bin/bash
cd ~/nostr
while true; do
  H=$(date +%H); D=$(date +%F); W=$(date +%u); NOW=$(date +%s)

  LAST=$(cat .m_engage 2>/dev/null || echo 0)
  if [ $((NOW - LAST)) -ge 18000 ]; then
    python engage.py >> logeng.txt 2>&1; date +%s > .m_engage
  fi

  LASTG=$(cat .m_growth 2>/dev/null || echo 0)
  if [ $((NOW - LASTG)) -ge 28800 ]; then
    python growth.py >> logg.txt 2>&1; date +%s > .m_growth
  fi

  if [ "$H" -ge 15 ]; then
    if [ "$(cat .m_post 2>/dev/null)" != "$D" ]; then
      python post.py >> log.txt 2>&1; echo "$D" > .m_post; sleep 60
    fi
    if [ "$(cat .m_post10 2>/dev/null)" != "$D" ]; then
      python post10.py >> log10.txt 2>&1; echo "$D" > .m_post10; sleep 60
    fi
    if [ "$W" = 2 ] || [ "$W" = 6 ]; then
      if [ "$(cat .m_camp 2>/dev/null)" != "$D" ]; then
        python campaign.py post >> logc.txt 2>&1; echo "$D" > .m_camp
      fi
    fi
  fi
  sleep 600
done
