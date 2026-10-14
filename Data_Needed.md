Data needed from external sites
================================

Goal: add Batman (sprites and moves from Batman Returns) as a new playable
fighter in Ultimate Mortal Kombat 3 (USA), with a move list entry for him.

Sites I could not read (Cloudflare bot check or error), with the data I need.

1. romhacking.net, UMK3 Deluxe v2.3 page
   URL: https://www.romhacking.net/hacks/5025/
   Need: description, credits, patch notes or documentation, and any
         technical notes on how Sheeva was made playable (which fighter
         ID or slot, which tables were edited, which graphics were reused).
   Why: the Deluxe ROM is the only known working roster change on this
        exact ROM. Its notes would tell me which tables to edit.
   Status: blocked (Cloudflare). Local Chromium also blocked.

2. romhacking.net, UMK3 Redux page
   URL: https://www.romhacking.net/hacks/3618/
   Need: same as above, if it has any technical notes.
   Status: never fetched.

3. romhacking.net forums (UMK3 SNES character or data threads)
   Need: any thread documenting the fighter data table, roster index,
         move list screen, or sprite compression for UMK3 SNES.
   Status: not found. Search results were all Genesis or cheat pages.

4. Data Crystal, UMK3 SNES ROM map
   URL: https://datacrystal.tcrf.net/wiki/Ultimate_Mortal_Kombat_3_(SNES)/ROM_map
   Need: fighter data table addresses, graphics pointer tables, move list
         data addresses, roster count.
   Status: 404 when fetched.

5. Data Crystal, UMK3 SNES RAM map
   URL: https://datacrystal.tcrf.net/wiki/Ultimate_Mortal_Kombat_3_(SNES)/RAM_map
   Got: screen codes (0D Character Select, 0B Versus) and options. No
        fighter ID or roster RAM. Some entries look wrong (unverified).
   Status: readable. Still need fighter ID and slot RAM addresses.

6. The Cutting Room Floor, UMK3 SNES page
   URL: https://tcrf.net/Ultimate_Mortal_Kombat_3_(SNES)
   Need: notes on the unused Sheeva data (sprite locations, ROM offsets)
         and any other unused fighter data.
   Why: the Deluxe readme says Sheeva was enabled, which points to unused
        data already in the original ROM.
   Status: blocked (Cloudflare 403).

7. RHDN decompression document (SNES graphics formats)
   URL: https://otakon273.duckdns.org/Consoles/RomHacking.net/rhdn_20240801/documents/[116]Decomp.doc
   Need: the SNES graphics decompression algorithms (LZ or RLE variants).
   Why: Batman Returns sprite data is compressed, and I have not identified
        the format.
   Status: 503 when fetched.

8. Batman Returns SNES ROM map or graphics documentation
   Need: sprite data locations, compression format, Batman's frame data.
   Status: none found. Data Crystal page returned 404.

What I can do without these
- Analyse the uploaded ROMs directly (name table, Deluxe diff).
- Use the Deluxe ROM as a reference, since its changes already show the
  roster edit works on this ROM.

How to get the data to me
- Open each URL in your own browser and save the page as text or PDF, or
  paste the relevant text into the chat.
- Upload the Deluxe patch notes or any documentation files.
