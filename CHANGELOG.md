# Hugo och Hermans pruttmaskin

## 4.5.2 - Bromance-refrängen

- Replaced the Bromance piano opening motif with the instrumental main-lead/drop
  (chorus) melody from Bromance (Arena), using the same wet recorded fart instrument.
- Kept the same five song buttons and the other four recordings unchanged.
- Updated the offline cache to Version 4.5.2 so the revised clip replaces the
  previous version.

## 4.5.1 - Fem låtar och Bromance

- Removed Lover, Paw Patrol and The Puerto Rico Song, and replaced Ghosts ’n’ Stuff
  with Bromance by Avicii.
- The five songs are Greta Gris, Björnen sover, Baby Shark,
  En livstid i krig and Bromance, in that order.
- Kept the four retained recordings unchanged and preserved one-song playback,
  Stoppa allt, volume and Fisorkester for the nine original sound pads.
- Updated the offline cache to Version 4.5.1 with all five current songs.

## 4.5.0 - Åtta låtar med fisar

- Replaced Blinka lilla stjärna, Bä bä vita lamm, Broder Jakob and Imse vimse
  spindel with Paw Patrol, Lover, The Puerto Rico Song (the AI hit by
  Bill Stiteler / saxboybilly18) and Greta Gris.
- Added En livstid i krig and Ghosts ’n’ Stuff, for eight song buttons in total.
- Kept Björnen sover and Baby Shark exactly as approved, with the same wet
  recorded fart instrument used for the new arrangements.
- Songs still replace the previous song even with Fisorkester enabled.
- Updated the offline cache to include the eight current recordings.

## 4.4.2 - En sång i taget och Baby Shark

- Starting a new song stops the previous song, including a pending start, even
  with Fisorkester enabled. Tapping the active song again still stops it.
- Replaced London Bridge with Baby Shark using the approved wet fart instrument.
- Updated the offline cache so the replacement and playback rules work offline.

## 4.4.1 - Barnsånger med blötare fisar

- Added six song buttons: Blinka lilla stjärna, Bä bä vita lamm, Broder Jakob,
  Imse vimse spindel, Björnen sover and London Bridge.
- The melodies use pitched versions of the existing CC0 Trumpeten recording,
  with wet recorded attacks and textures from Blöta, and play
  as bundled MP3 files through the native audio player.
- Tap a playing song again to stop it. Songs share volume, Fisorkester and
  Stoppa allt with the nine original sounds.
- Added the songs to the Version 4.4.1 offline cache and included arrangement
  metadata, source credits and the audio rendering tool.

## 3.0 - Recorded audio

- Replaced the synthetic sound generator with nine different recorded MP3 clips.
- Bundled all nine clips in audio/; playback makes no requests to external sound services.
- CC0 sources, authors, SHA-256 checksums and file metadata: audio/sources.json and audio/CREDITS.md. Credits are also visible in the app.
- Preserved the app title, colourful nine-pad layout, volume, orchestra mode and Stop all.
- Added a visible Version 3.0 footer and offline-readiness indicator. Offline readiness requires all app resources and all nine clips to be cached.
- Installation is atomic: missing files do not replace the previous working offline version.
- Stops cancel pending playback as well as currently playing clips; simultaneous playback is limited to 12 voices.

Validation: all nine downloaded files passed MPEG Layer III structural checks and have distinct SHA-256 hashes. UI layout and player controls passed Chromium tests using local MP3 fixtures. Service-worker lifecycle and offline cache behavior passed in-memory unit tests. No physical iPhone/iPad audition or end-to-end Safari test has been performed.
