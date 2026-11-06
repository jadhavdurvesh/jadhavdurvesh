#!/usr/bin/env python3
"""Generate a GitSkins-inspired top-15 language card for the profile README."""
import json
import os
import time
import urllib.request
import urllib.error
from pathlib import Path
from xml.sax.saxutils import escape

USER = os.getenv("GITHUB_USERNAME", "jadhavdurvesh")
TOKEN = os.getenv("GITHUB_TOKEN")
API = "https://api.github.com"
LIMIT = 15

def get_json(url):
    headers = {"Accept": "application/vnd.github+json", "User-Agent": "profile-language-stack"}
    if TOKEN:
        headers["Authorization"] = f"Bearer {TOKEN}"
    request = urllib.request.Request(url, headers=headers)
    for attempt in range(4):
        try:
            with urllib.request.urlopen(request, timeout=30) as response:
                return json.load(response)
        except urllib.error.HTTPError as exc:
            if exc.code not in (403, 429) or attempt == 3:
                raise
            time.sleep(2 ** (attempt + 1))

def main():
    repos = []
    page = 1
    while True:
        batch = get_json(f"{API}/users/{USER}/repos?type=owner&per_page=100&page={page}")
        repos.extend(r for r in batch if not r.get("fork") and not r.get("archived"))
        if len(batch) < 100:
            break
        page += 1

    totals = {}
    for repo in repos:
        for language, size in get_json(repo["languages_url"]).items():
            totals[language] = totals.get(language, 0) + size

    ranked = sorted(totals.items(), key=lambda item: item[1], reverse=True)[:LIMIT]
    if not ranked:
        raise SystemExit("No repository language data returned; SVG not generated.")
    total = sum(totals.values())
    colors = ["#58a6ff", "#f05b3e", "#e3a184", "#8bd450", "#f1df4f",
              "#3178c6", "#b084f5", "#00b8a9", "#e34c26", "#6e7681",
              "#f97583", "#79c0ff", "#d2a8ff", "#ffa657", "#a5d6ff"]
    width, top, row_h, bar_x, bar_w = 1200, 174, 43, 390, 735
    height = top + len(ranked) * row_h + 48
    rows = []
    for i, (name, size) in enumerate(ranked):
        y = top + i * row_h
        pct = size / total * 100
        length = max(3, bar_w * pct / 100)
        color = colors[i % len(colors)]
        delay = i * 0.05
        rows.append(f"""
  <g class="language" style="animation-delay:{delay:.2f}s">
    <circle cx="78" cy="{y+5}" r="6" fill="{color}"/>
    <text x="98" y="{y+11}" class="name">{escape(name)}</text>
    <text x="350" y="{y+11}" class="percentage" text-anchor="end">{pct:.1f}%</text>
    <rect x="{bar_x}" y="{y-3}" width="{bar_w}" height="15" rx="7.5" fill="#30363d"/>
    <rect x="{bar_x}" y="{y-3}" width="{length:.1f}" height="15" rx="7.5" fill="{color}">
      <animate attributeName="width" from="0" to="{length:.1f}" dur=".9s" begin="{delay:.2f}s" fill="freeze"/>
    </rect>
  </g>""")

    svg = f'''<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}" role="img" aria-labelledby="title desc">
  <title id="title">{USER}'s Language Stack</title>
  <desc id="desc">Top {len(ranked)} languages by source-code bytes across owned, non-fork, non-archived repositories.</desc>
  <defs>
    <linearGradient id="outer" x1="0" y1="0" x2="1" y2="1">
      <stop offset="0" stop-color="#58a6ff" stop-opacity=".35"/>
      <stop offset=".52" stop-color="#238636" stop-opacity=".22"/>
      <stop offset="1" stop-color="#a371f7" stop-opacity=".35"/>
    </linearGradient>
    <linearGradient id="panel" x1="0" y1="0" x2="1" y2="1">
      <stop offset="0" stop-color="#101722"/><stop offset=".55" stop-color="#0d1715"/><stop offset="1" stop-color="#171322"/>
    </linearGradient>
    <radialGradient id="glow" cx="18%" cy="0%" r="80%">
      <stop offset="0" stop-color="#388bfd" stop-opacity=".23"/><stop offset=".55" stop-color="#238636" stop-opacity=".09"/><stop offset="1" stop-color="#0d1117" stop-opacity="0"/>
    </radialGradient>
    <style>
      text{{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif}}
      .heading{{fill:#f0f6fc;font-size:38px;font-weight:800;letter-spacing:-1px}}
      .subtitle{{fill:#8b949e;font-size:16px;font-weight:700;letter-spacing:1.2px}}
      .scan{{fill:#58a6ff;font-size:15px;font-weight:700}}
      .name{{fill:#e6edf3;font-size:18px;font-weight:700}}
      .percentage{{fill:#c9d1d9;font-size:17px;font-weight:700;font-variant-numeric:tabular-nums}}
      .language{{opacity:0;animation:fade .45s ease-out forwards}}
      @keyframes fade{{to{{opacity:1}}}}
    </style>
  </defs>
  <rect x="10" y="10" width="1180" height="{height-20}" rx="30" fill="url(#outer)" stroke="#388bfd" stroke-opacity=".75"/>
  <rect x="28" y="28" width="1144" height="{height-56}" rx="24" fill="url(#panel)" stroke="#388bfd" stroke-opacity=".42"/>
  <rect x="28" y="28" width="1144" height="{height-56}" rx="24" fill="url(#glow)"/>
  <circle cx="1115" cy="86" r="4" fill="#58a6ff" opacity=".85"/>
  <circle cx="1115" cy="86" r="28" fill="none" stroke="#58a6ff" stroke-opacity=".07"/>
  <text x="62" y="91" class="heading">Language Stack</text>
  <text x="64" y="123" class="subtitle">Repository-weighted technologies</text>
  <text x="1120" y="91" class="scan" text-anchor="end">&gt; stack.scan</text>
  <line x1="62" y1="145" x2="1138" y2="145" stroke="#30363d" stroke-opacity=".75"/>
  {''.join(rows)}
  <text x="1125" y="{height-42}" text-anchor="end" fill="#6e7681" font-size="12">github.com/{USER}</text>
</svg>
'''
    output = Path("assets/language-stack.svg")
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(svg, encoding="utf-8")
    print(f"Generated {output} with {len(ranked)} languages from {len(repos)} repositories.")

if __name__ == "__main__":
    main()
