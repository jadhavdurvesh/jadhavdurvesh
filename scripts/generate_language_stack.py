#!/usr/bin/env python3
"""Generate a GitSkins-inspired two-column language card with first-class DMJScript and Rudra."""
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
LIMIT = 20
COLUMN_SIZE = 11

# Count real source programs from each language's own repository.
# Compiler implementation files (C/Python), generated output and conformance
# fixtures are intentionally excluded.
LANGUAGE_PROJECTS = [
    ("DMJScript", "jadhavdurvesh/dmjscript", ".dmj", ("", "examples/")),
    ("Rudra", "jadhavdurvesh/Rudra-dedicated-programming-language", ".rudra", ("examples/",)),
]


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


def fetch_language_project_bytes(repository, extension, allowed_roots):
    repo = get_json(f"{API}/repos/{repository}")
    branch = repo["default_branch"]
    tree = get_json(f"{API}/repos/{repository}/git/trees/{branch}?recursive=1")
    if tree.get("truncated"):
        raise RuntimeError(f"Git tree for {repository} was truncated; refusing partial language stats.")

    total = 0
    matched_files = []
    for item in tree.get("tree", []):
        path = item.get("path", "")
        if item.get("type") != "blob" or not path.endswith(extension):
            continue
        if not any(path.startswith(root) for root in allowed_roots):
            continue
        size = int(item.get("size", 0))
        total += size
        matched_files.append(path)

    if not matched_files:
        raise RuntimeError(f"No {extension} source programs found in {repository}.")
    print(f"{repository}: {len(matched_files)} {extension} programs, {total} bytes")
    return total


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

    standard_ranked = sorted(totals.items(), key=lambda item: item[1], reverse=True)[:LIMIT]

    original_language_sizes = {}
    for language, repository, extension, allowed_roots in LANGUAGE_PROJECTS:
        original_language_sizes[language] = fetch_language_project_bytes(
            repository, extension, allowed_roots
        )

    # Add first-class language totals to the common denominator.
    all_totals = dict(totals)
    all_totals.update(original_language_sizes)
    total_bytes = sum(all_totals.values())
    if not standard_ranked or total_bytes <= 0:
        raise SystemExit("No repository language data returned; SVG not generated.")

    # Preserve the existing top-20 order: ten detected languages per column,
    # then one original language at the bottom of its respective column.
    display_entries = (
        standard_ranked[:10]
        + [("DMJScript", original_language_sizes["DMJScript"])]
        + standard_ranked[10:20]
        + [("Rudra", original_language_sizes["Rudra"])]
    )

    colors = [
        "#58a6ff", "#f05b3e", "#e3a184", "#8bd450", "#f1df4f",
        "#3178c6", "#b084f5", "#00b8a9", "#e34c26", "#6e7681",
        "#f97583", "#79c0ff", "#d2a8ff", "#ffa657", "#a5d6ff",
        "#ff7b72", "#a5d6ff", "#d2a8ff", "#7ee787", "#ffa657",
        "#58a6ff", "#a371f7",
    ]

    width = 1200
    top = 174
    row_h = 43
    bar_w = 300
    bar_offset = 220
    col_origins = [62, 620]
    rows = []

    for index, (name, size) in enumerate(display_entries):
        column = index // COLUMN_SIZE
        row = index % COLUMN_SIZE
        origin = col_origins[column]
        y = top + row * row_h
        pct = size / total_bytes * 100
        bar_length = max(3, bar_w * pct / 100)
        color = colors[index % len(colors)]
        delay = index * 0.045
        bar_x = origin + bar_offset

        rows.append(f"""
  <g class="language" style="animation-delay:{delay:.3f}s">
    <circle cx="{origin + 5}" cy="{y + 5}" r="6" fill="{color}"/>
    <text x="{origin + 22}" y="{y + 11}" class="name">{escape(name)}</text>
    <text x="{origin + 205}" y="{y + 11}" class="percentage" text-anchor="end">{pct:.2f}%</text>
    <rect x="{bar_x}" y="{y - 3}" width="{bar_w}" height="15" rx="7.5" fill="#30363d"/>
    <rect x="{bar_x}" y="{y - 3}" width="{bar_length:.1f}" height="15" rx="7.5" fill="{color}">
      <animate attributeName="width" from="0" to="{bar_length:.1f}" dur=".9s" begin="{delay:.2f}s" fill="freeze"/>
    </rect>
  </g>""")

    height = top + COLUMN_SIZE * row_h + 48

    svg = f'''<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}" role="img" aria-labelledby="title desc">
  <title id="title">{USER}'s Language Stack</title>
  <desc id="desc">Top 20 repository languages plus DMJScript and Rudra, measured by source bytes and displayed in two columns.</desc>
  <defs>
    <linearGradient id="outer" x1="0" y1="0" x2="1" y2="1">
      <stop offset="0" stop-color="#58a6ff" stop-opacity=".35"/>
      <stop offset=".52" stop-color="#238636" stop-opacity=".22"/>
      <stop offset="1" stop-color="#a371f7" stop-opacity=".35"/>
    </linearGradient>
    <linearGradient id="panel" x1="0" y1="0" x2="1" y2="1">
      <stop offset="0" stop-color="#101722"/>
      <stop offset=".55" stop-color="#0d1715"/>
      <stop offset="1" stop-color="#171322"/>
    </linearGradient>
    <radialGradient id="glow" cx="18%" cy="0%" r="80%">
      <stop offset="0" stop-color="#388bfd" stop-opacity=".23"/>
      <stop offset=".55" stop-color="#238636" stop-opacity=".09"/>
      <stop offset="1" stop-color="#0d1117" stop-opacity="0"/>
    </radialGradient>
    <style>
      text{{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif}}
      .heading{{fill:#f0f6fc;font-size:38px;font-weight:800;letter-spacing:-1px}}
      .subtitle{{fill:#8b949e;font-size:16px;font-weight:700;letter-spacing:1.2px}}
      .scan{{fill:#58a6ff;font-size:15px;font-weight:700}}
      .name{{fill:#e6edf3;font-size:16px;font-weight:700}}
      .percentage{{fill:#c9d1d9;font-size:15px;font-weight:700;font-variant-numeric:tabular-nums}}
      .language{{opacity:0;animation:fade .45s ease-out forwards}}
      @keyframes fade{{to{{opacity:1}}}}
    </style>
  </defs>
  <rect x="10" y="10" width="1180" height="{height - 20}" rx="30" fill="url(#outer)" stroke="#388bfd" stroke-opacity=".75"/>
  <rect x="28" y="28" width="1144" height="{height - 56}" rx="24" fill="url(#panel)" stroke="#388bfd" stroke-opacity=".42"/>
  <rect x="28" y="28" width="1144" height="{height - 56}" rx="24" fill="url(#glow)"/>
  <circle cx="1115" cy="86" r="4" fill="#58a6ff" opacity=".85"/>
  <circle cx="1115" cy="86" r="28" fill="none" stroke="#58a6ff" stroke-opacity=".07"/>
  <text x="62" y="91" class="heading">Language Stack</text>
  <text x="64" y="123" class="subtitle">Repository-weighted technologies · 22 LANGUAGES</text>
  <text x="1120" y="91" class="scan" text-anchor="end">&gt; stack.scan</text>
  <line x1="62" y1="145" x2="1138" y2="145" stroke="#30363d" stroke-opacity=".75"/>
  <line x1="600" y1="164" x2="600" y2="{height - 58}" stroke="#30363d" stroke-opacity=".65"/>
  {''.join(rows)}
  <text x="1125" y="{height - 42}" text-anchor="end" fill="#6e7681" font-size="12">github.com/{USER}</text>
</svg>
'''
    output = Path("assets/language-stack-custom.svg")
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(svg, encoding="utf-8")
    print(f"Generated {output} with 22 language entries from {len(repos)} repositories.")


if __name__ == "__main__":
    main()
