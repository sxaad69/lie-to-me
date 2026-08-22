#!/usr/bin/env python3
"""Build assets.json: base64 data-URI manifest for the LIE TO ME v2 single-file bundle.
Reads converted assets from /root/ltm-build, writes /root/lie-to-me/tools/assets.v2.json."""
import base64, json, os

BUILD = "/root/ltm-build"
OUT = "/root/lie-to-me/tools/assets.v2.json"

def uri(fname, mime):
    with open(os.path.join(BUILD, fname), "rb") as f:
        return f"data:{mime};base64," + base64.b64encode(f.read()).decode()

manifest = {"portraits": {}, "sfx": {}, "dressing": {}, "music": {}}
for who in ("marlowe", "vega", "ash"):
    for st in ("composed", "fraying", "broken"):
        manifest["portraits"][f"{who}-{st}"] = uri(f"{who}-{st}.jpg", "image/jpeg")
for n in ("stamp-thunk-1", "stamp-thunk-2", "stamp-thunk-3", "string-twang",
          "lamp-flicker-buzz", "bass-drop", "gavel-slam", "typewriter-clatter",
          "release-stamp"):
    manifest["sfx"][n] = uri(f"{n}.wav", "audio/wav")
for n in ("ledger-page", "polaroid-frame", "elevator-log-strip"):
    manifest["dressing"][n] = uri(f"{n}.png", "image/png")
manifest["music"]["rain"] = uri("amb-rain.mp3", "audio/mpeg")
manifest["music"]["bass"] = uri("stem-bass-walk.mp3", "audio/mpeg")
manifest["music"]["drums"] = uri("stem-brushed-drums.mp3", "audio/mpeg")

with open(OUT, "w") as f:
    json.dump(manifest, f, separators=(",", ":"))
print("wrote", OUT, round(os.path.getsize(OUT) / 1024), "KB,",
      sum(len(v) for v in manifest.values()), "entries")
