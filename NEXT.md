# Next step: paint test, not a compressor

The pose cut is in `art/batman_poses.tar.gz` (100 transparent PNGs plus `contact.png` and `frames.json`). Idle stance is `f000_62x89.png`.

UMK3 fighter tiles are not stored raw in the ROM. That was checked: 19 of 1,069 VRAM tiles match the ROM, and half-tiles do no better. Do not spend the next session finding the compressor. The tiles are already decoded in video RAM during a fight. Write Batman there.

Run:

```
python3 tools/batman_vram_test.py "Ultimate Mortal Kombat 3 (USA).sfc" /tmp/paint
```

It boots Rain (roster cell 0,0, fighter id 0x18) into a fight, prints WRAM addresses that look like the 544-byte sprite table, then paints those sprites' tiles white at four possible VRAM bases. Open the `paint_*.png` files. The one where Rain's body turns white is the live tile store.

That PNG is the gate. After it exists, slice `f000_62x89.png` into 4bpp tiles and poke them at that base every frame. If the shape is shredded, the pieces are the game's old layout: then rewrite x/y of the left-side sprites (x under 140) to a grid of the Batman pose. Damage stays Rain's until that screenshot is real.
