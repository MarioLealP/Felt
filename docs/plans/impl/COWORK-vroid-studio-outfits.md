# Cowork brief: make Felt outfits in VRoid Studio (pilot)

Paste everything below the line into a **Cowork** session in the Claude
desktop app, with **computer use** enabled. It drives VRoid Studio on
Mario's desktop. Context: WP-27, the wardrobe; see
`WP-25-31-life-features.md`.

---

**Goal:** make a new outfit for Felt (Mario's desktop companion) in
**VRoid Studio** and export it as a VRM that her overlay can wear. This is a
**pilot**: make **one** outfit end to end, note every step and anything
awkward, then stop and report.

**Files:**
- Base model: `E:\Felt\VRoid\model.vroid`. **Never overwrite it.** Open it
  and immediately *Save As* `E:\Felt\VRoid\outfits\felt_neon.vroid`
  (create the folder if needed), and work only in that copy.
- Clothing items (`.vroidcustomitem`) are under
  `E:\Felt\felt-character-assets\felt-godot-overlay\characters\Outfits\`.
  For the pilot, use the **Neon Outfit** folder's `Tops.vroidcustomitem`
  and `Skirt.vroidcustomitem`.
- Existing finished outfits, for reference on how they look:
  `E:\Felt\felt-character-assets\felt-godot-overlay\characters\Felt_*.vrm`.

**Rules:**
1. Change **only clothing** (tops, bottoms, one-piece, shoes, socks) and
   clothing accessories. **Never** touch her body, face, hair, eyes,
   proportions or skin. Her animations and expressions depend on those
   staying identical.
2. Import the items through VRoid Studio's own *custom item* import in the
   clothing tabs. Don't download anything new from the internet.
3. **Export as VRM 1.0 with the same export settings Mario used for the
   existing `Felt_*.vrm` outfits.** VRoid Studio remembers the last export
   settings, so keep them. In particular, keep the same polygon-reduction
   and material-merge options. Those outfits have meshes named
   `Face (merged)`, `Body (merged)` and `Hair001 (merged)`, so mesh merging
   was on. Don't change the bone or spring-bone options. If a setting looks
   like it would change the skeleton, leave it as it is and mention it.
4. Save the export as
   `E:\Felt\felt-character-assets\felt-godot-overlay\characters\Felt_Neon.vrm`.
   Don't overwrite any existing file.
5. If VRoid Studio asks about anything account-related (a VRoid Hub login,
   uploading, licence prompts), stop and ask Mario. Don't sign in or
   upload anything.
6. Close VRoid Studio when done. Don't touch any other app. Felt's overlay,
   a transparent always-on-top window, and a tray icon are running; leave
   them alone.

**Report back:**
- Did it work? The path of the exported VRM and the time taken.
- The exact clicks and menus used: clothing tabs, the item import, the
  export dialog and its settings, preferably with a screenshot of the
  export settings.
- Anything that needed guessing, and anything to avoid next time.
- Whether VRoid Studio's per-item **colour controls** would make recolour
  variants easy. For example: could you make a second export
  `Felt_Neon__pink.vrm` by recolouring the top and skirt in a few steps?
  Describe it only; don't do it in the pilot.

**After the report:** Claude Code (the terminal session) imports the VRM
into the Godot overlay, adds it to `outfits.json`, and Mario tries it on
with `POST /outfit {"id": "neon"}`. If the pilot works, later sessions
batch the remaining item combinations and recolours.
