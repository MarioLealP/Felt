# Wardrobe Tier C: Mario's VRoid outfit checklist

These are the outfits that need a **different garment shape**, which
scripts can't fake. Everything else (a new shirt every day, recolours,
prints, seasonal palettes, hats, scarves, glasses, props) is automated in
WP-32, WP-33 and WP-27.

Make them whenever you feel like it, in any order. The priority column is my
suggestion, based on how often she'd wear each one.

## How to make each one (the same every time)

1. Open `E:\Felt\VRoid\model.vroid` in VRoid Studio. **Save As** →
   `E:\Felt\VRoid\outfits\<id>.vroid` (create the folder), so the original
   stays untouched.
2. Change **only clothing (tops, bottoms, one-piece, socks, shoes) and
   clothing accessories.** **Don't touch the body, face, or hair**. Every
   animation, expression and the lip-sync depend on them staying identical.
   Keep her buns and braids.
3. Hoods and hats: keep hoods **down**, since a hood up clips through the
   buns. Headwear comes as automated accessories instead.
4. Export as VRM with the **same settings you used for the current
   `felt.vrm`** (VRM 1.0, no texture atlas, no polygon reduction changes).
   Save it as `E:\Felt\VRoid\Output\felt_<id>.vrm`.
5. Tell me (or the implementing session) the `id`. The automated side takes
   it from there: recolours, prints, accessories, triggers.

Tip: put a plain/white top on anything that has a top. The daily-print
system can then decorate it too.

## The list

| Priority | `id` | Outfit | When she wears it | VRoid pieces to pick |
|---|---|---|---|---|
| 1 | `pajamas` | Button-up pajama set, long sleeves and long pants, soft fabric | Late night (~1 am+), sleepy mood, AFK nap hobby | Top: long-sleeve shirt/blouse (pajama style). Bottoms: loose long pants. Shoes: slippers or barefoot socks. |
| 2 | `hoodie` | Oversized hoodie (hood down) + shorts or leggings | Chilly days, evenings, cozy mood. A second "default" | Top: hoodie / oversized sweatshirt. Bottoms: shorts or leggings. Shoes: sneakers. |
| 3 | `rain` | Rain jacket (hood down), boots | Rain or storm at home (from the weather skill) | Top: rain jacket / parka. Bottoms: jeans or leggings. Shoes: rain boots. The umbrella comes as an automated prop. |
| 4 | `winter` | Warm coat (duffle or puffer) + boots | Cold weather (below ~8 °C) and December–February | Top: coat. Bottoms: pants or a skirt with tights. Shoes: winter boots. The scarf and beanie come as automated accessories. |
| 5 | `halloween` | Witch dress (or another costume you like) | Oct 24 – Nov 1. **Make it by mid-October to use it this year** | One-piece: a dark dress. Shoes: boots or heels. The witch hat comes as an automated accessory. |
| 6 | `summer` | Sundress, or a tank top + denim shorts | Hot days (above ~26 °C), June–August | One-piece: sundress, *or* top: tank top + bottoms: shorts. Shoes: sandals. |
| 7 | `christmas` | Knit sweater (Christmas-sweater style) + skirt | December | Top: knit sweater. Bottoms: skirt + tights. Shoes: boots. The pattern and Santa hat come automated. |
| 8 | `endfield` | An Arknights-Endfield-inspired techwear outfit (jacket, straps, clean industrial look) | Special days and random rare picks. Her "signature" look | Top: a structured jacket. Bottoms: cargo or tech pants. Shoes: boots. Colours: Endfield's palette. |
| 9 | `going_out` (optional) | A cute casual dress / going-out look | Weekends, occasionally | One-piece: casual dress. Shoes: flats or sneakers. |
| 10 | `sporty` (optional) | Track jacket + joggers | Occasionally while you're gaming hard | Top: track jacket. Bottoms: joggers. Shoes: sneakers. |

## Where to get extra clothing

- VRoid Studio's built-in items and colour/texture editing cover most of
  these.
- Booth.pm has lots of VRoid clothing texture packs, many free (needs your
  pixiv login). WP-32 produces a shortlist with links (`E:\Felt\Assets\booth-shortlist.md`).
- `E:\Felt\VRoid\Textures\` already has shoe, sock and hair textures you
  downloaded earlier.
