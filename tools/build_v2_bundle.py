#!/usr/bin/env python3
"""Assemble the LIE TO ME v2 single-file HTML: inject the base64 asset manifest
from tools/assets.v2.json into src/v2.template.html -> root index.html."""
import json, os

ROOT = "/root/lie-to-me"
tpl = open(os.path.join(ROOT, "src/v2.template.html"), encoding="utf-8").read()
manifest = open(os.path.join(ROOT, "tools/assets.v2.json"), encoding="utf-8").read()
json.loads(manifest)  # sanity: must be valid JSON
assert "__ASSET_MANIFEST__" in tpl, "template token missing"
out = tpl.replace("__ASSET_MANIFEST__", manifest)
with open(os.path.join(ROOT, "index.html"), "w", encoding="utf-8") as f:
    f.write(out)
print("index.html:", round(os.path.getsize(os.path.join(ROOT, "index.html")) / 1024), "KB")
