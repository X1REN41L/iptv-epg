# iptv-epg

Custom EPG (guide) for the `p.nvisionbd.com` Xtream playlist, one fixed channel list, one script.

## Setup
- App: Lineup (`~/workspace/lineup-iptv-player`); its nvision playlist (`main`) takes the guide from the release link under Refresh as `guideUrl` (the user sets this in Lineup) and maps `nvfav.<xtream_id>` itself.
- Credentials live in Lineup's `data/settings.json`; the guide build doesn't need them. Never print them.
- Don't keep a `backup/` folder (user preference).

## Guide build
- `scripts/fetch_epg.py` downloads the sources named in `work/channels.tsv` and builds the guide. Map columns: `xtream_id`, title, candidates `FILE:channel_id` (comma-separated; empty = no guide on purpose). The candidate with the most upcoming programmes in the window wins, first on a tie; the output lists each choice. The channel list is fixed: the matcher was removed (in git history at `3f2d8a5`), so new provider channels get a guide only by adding a row and pushing (approval needed).
- Sources: `https://epgshare01.online/epgshare01/epg_ripper_<FILE>.xml.gz` (listing at `/epgshare01/`). There is no US1; FS1/FS2 are in US2, Fubo Sports Network in PLEX1. `US_LOCALS1` and call-sign matching were dropped on purpose (user's choice): US/CA local stations have no guide.
- epg.pw is no longer used: its times are UTC+8 labelled `+0000` and the build applies no time corrections. NO1 channel ids contain commas; candidates split only at `,FILE:`.
- Map keys `IPTVX` (`https://iptvx.one/EPG_LITE`, ~15 MB) and `IT999` (`http://epg.it999.ru/edem.xml.gz`, 42 MB) are the sources for RU Match!, Ziggo and AR beIN 1/3/5/6 and candidates for RU and some Asian channels; ids like `match-football1` / numeric.
- epgshare BEIN1 doesn't match the AR beIN streams at any offset.
- AR beIN 2/4/7/8/9 FHD and English 1–2 have no guide: streams run old replays no source lists. AR beIN HD variants carry other content than FHD and have no guide.
- Output `out/premium_nvision_epg.xml.gz` (~3,340 channels, ~278k programmes, 14.5 MB), channel ids `nvfav.<xtream_id>`, loaded by Lineup as the playlist's custom guide. Programmes keep only title, sub-title, desc and one category.
- Window: today 00:00 to the end of the day after tomorrow, local time (UTC+6). No past days and no carry-over: Lineup drops programmes that ended over 2h before import anyway. The build applies no time corrections or shifts.
- Never translate the guide (user's standing rule): keep the original language.
- Guide must match the stream; prefer another source. TNT Sport 2 and TR1 match their raw times.
- TR beIN Sports Max 1–2 have no guide: TR1 lists them with 0 programmes; BEIN1 "MAX" channels are MENA beIN, not Turkish.
- Also no guide: PT DAZN 6, NO TV 2 Sport Premium 2, AR Almagd TV (listing is another channel), EG Sada Elbalad 2, TR Kanal D (listings didn't match), CA Disney Channel 348866 (stream carries ADTV). CZ1 lists Nova Sport with 0 programmes.
- BG Max Sport 1–4 auto-match BG1, recorded as 1–2.5h off, with only a few programmes ahead (user chose to leave them). RO1's odd `-0500` stamps are correct UTC.
- IN Sony Ten 1–5 use IN1 (Sony Ten 4 is the only Sony Sports channel without a 4K stream; 167595 in CRICKET). Star Sports Select 1–2 have no guide: IN1 lists them with 0 programmes, IN4 is stale, epg.pw has none. Sony Ten 2 (4K)'s provider epg id wrongly says Ten 1.
- RU Match Premier 353391 is a dead duplicate; 353351 is the working one.
- If a stream carries a different feed than its name, use the guide of the feed shown: Sky Sports Arena = Sky Sports F1 UK (IE1). Sky Sports Premier League auto-matches the UK listing though its stream last carried Sky Sport PL DE (user chose to leave it). Feeds can change.

## Refresh
- GitHub Actions (`.github/workflows/refresh-guide.yml`, public repo `X1REN41L/iptv-epg`) rebuilds daily at 04:13 UTC and publishes to the `guide` release: `https://github.com/X1REN41L/iptv-epg/releases/latest/download/premium_nvision_epg.xml.gz`. A push to `work/` or the script also triggers it. Local run (no publish): `python3 -I scripts/fetch_epg.py` (~3 min).
- Lineup re-reads the guide after its `epg.refreshHours` setting (currently 6h) or via its guide refresh (`POST /api/epg/refresh`).
