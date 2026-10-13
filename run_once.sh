#!/usr/bin/env bash
export TZ=America/Havana
H=$((10#$(date +%H))); D=$(date +%F); W=$(date +%u); NOW=$(date +%s)

LAST=$(cat .m_engage 2>/dev/null || echo 0)
if [ $((NOW - LAST)) -ge 18000 ]; then
  python engage.py || true; date +%s > .m_engage
fi
LASTG=$(cat .m_growth 2>/dev/null || echo 0)
if [ $((NOW - LASTG)) -ge 28800 ]; then
  python growth.py || true; date +%s > .m_growth
fi
if [ "$H" -ge 15 ]; then
  if [ "$(cat .m_post 2>/dev/null)" != "$D" ]; then
    python post.py || true; echo "$D" > .m_post
  fi
  if [ "$(cat .m_post10 2>/dev/null)" != "$D" ]; then
    python post10.py || true; echo "$D" > .m_post10
  fi
  if [ "$W" = 2 ] || [ "$W" = 6 ]; then
    if [ "$(cat .m_camp 2>/dev/null)" != "$D" ]; then
      python campaign.py post || true; echo "$D" > .m_camp
    fi
  fi
fi

# --- valor.py ---
if [ "$H" -ge 19 ] && [ "$(cat .m_nota 2>/dev/null)" != "$D" ]; then
  python valor.py nota || true; echo "$D" > .m_nota
fi
LASTZ=$(cat .m_zaps 2>/dev/null || echo 0)
if [ $((NOW - LASTZ)) -ge 7200 ]; then
  python valor.py zaps || true; date +%s > .m_zaps
fi
if [ "$H" -ge 11 ] && { [ "$W" = 1 ] || [ "$W" = 3 ] || [ "$W" = 5 ]; } && [ "$(cat .m_news 2>/dev/null)" != "$D" ]; then
  python valor.py noticias || true; echo "$D" > .m_news
fi
