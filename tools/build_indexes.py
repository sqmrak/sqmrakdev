#!/usr/bin/env python3
"""Turn the raw dpkg-scanpackages output into the files the storefronts read.

The Packages stanza is the single source of truth: the Sileo depiction and the
HTML depiction are generated from it, so a version bump cannot leave a
storefront page describing the previous build.
"""
import io
import json
import os
import re
import shutil
import subprocess
import sys
import tarfile

BASE = sys.argv[1].rstrip("/")
TINT = sys.argv[2] if len(sys.argv) > 2 and sys.argv[2] else "#2f6bff"

# each channel is generated with its own directory as the working directory, so
# the shared templates and the fallback icon are looked up where they live
TEMPLATES = os.environ.get("REPO_TEMPLATE_DIR", ".")

HTML_TEMPLATE = open(os.path.join(TEMPLATES, "depiction-template.html")).read()
INDEX_TEMPLATE = open(os.path.join(TEMPLATES, "index-template.html")).read()


def shade(color, factor):
    """Lighten (factor > 0) or darken (factor < 0) a #rrggbb accent, so the
    pages only ever need the one colour from repo.conf."""
    try:
        r, g, b = (int(color[i:i + 2], 16) for i in (1, 3, 5))
    except (ValueError, IndexError):
        return color
    if factor >= 0:
        r, g, b = (int(c + (255 - c) * factor) for c in (r, g, b))
    else:
        r, g, b = (int(c * (1.0 + factor)) for c in (r, g, b))
    return "#%02x%02x%02x" % (r, g, b)


TINT_SOFT = shade(TINT, 0.34)
TINT_DEEP = shade(TINT, -0.42)


def parse(stanza):
    """Keep the field order dpkg produced; a continuation line belongs to the
    field above it."""
    fields, order, key = {}, [], None
    for line in stanza.splitlines():
        if line[:1] in (" ", "\t") and key:
            fields[key] += "\n" + line
            continue
        if ":" not in line:
            continue
        key, _, value = line.partition(":")
        key = key.strip()
        fields[key] = value.strip()
        order.append(key)
    return fields, order


def esc(text):
    return (text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;"))


def tagline(fields):
    """The storefronts get a compact line instead of the control-file blurb.
    An explicit Tagline: in the control wins; otherwise the supported iOS range
    is what a jailbreaker actually looks for before installing."""
    explicit = fields.get("Tagline")
    if explicit:
        return explicit
    found = re.search(r"iOS\s*\d+(?:\.\d+)?\s*[-\u2013]\s*\d+(?:\.\d+)?",
                      fields.get("Description", ""), re.I)
    return found.group(0) if found else ""


def icon_rank(name):
    """Prefer the densest icon the bundle ships, so the storefront gets the
    same artwork the springboard shows rather than a blurry copy."""
    base = os.path.basename(name).lower()
    if not base.endswith(".png"):
        return -1
    if "icon" not in base:
        return -1
    if "@3x" in base:
        return 3
    if "@2x" in base:
        return 2
    return 1


def extract_icon(deb, target):
    """Pull the app icon straight out of the package. The icon a manager shows
    next to a package is then whatever the app itself carries, with no second
    copy to keep in step by hand."""
    if not deb or not os.path.exists(deb):
        return False
    try:
        payload = subprocess.check_output(["dpkg-deb", "--fsys-tarfile", deb])
    except (OSError, subprocess.CalledProcessError):
        return False

    best, best_key = None, (-1, -1)
    with tarfile.open(fileobj=io.BytesIO(payload)) as tar:
        for member in tar.getmembers():
            if not member.isfile() or ".app/" not in member.name:
                continue
            rank = icon_rank(member.name)
            if rank < 0:
                continue
            key = (rank, member.size)
            if key > best_key:
                best_key, best = key, member.name
        if best is None:
            return False
        handle = tar.extractfile(best)
        if handle is None:
            return False
        data = handle.read()

    with open(target, "wb") as out:
        out.write(data)
    return True


def write_depiction(fields):
    pkg = fields["Package"]
    out_dir = os.path.join("depictions", pkg)
    os.makedirs(out_dir, exist_ok=True)

    icon = os.path.join(out_dir, "icon.png")
    if not extract_icon(fields.get("Filename"), icon):
        fallback = os.path.join(TEMPLATES, "CydiaIcon.png")
        if not os.path.exists(icon) and os.path.exists(fallback):
            shutil.copyfile(fallback, icon)

    name = fields.get("Name", pkg)
    description = tagline(fields)
    version = fields.get("Version", "")
    author = fields.get("Author", fields.get("Maintainer", ""))
    try:
        size = "%.1f MB" % (int(fields.get("Size", "0")) / 1048576.0)
    except ValueError:
        size = ""

    rows = [
        ("Version", version),
        ("Size", size),
        ("Developer", author),
        ("Section", fields.get("Section", "")),
        ("Identifier", pkg),
        ("Compatibility", fields.get("Depends", "")),
    ]
    rows = [(t, v) for t, v in rows if v]

    views = [{"class": "DepictionHeaderView", "title": name}]
    if description:
        views.append({"class": "DepictionMarkdownView", "markdown": description})
    views.append({"class": "DepictionSeparatorView"})
    views += [{"class": "DepictionTableTextView", "title": t, "text": v}
              for t, v in rows]

    tabs = [{"class": "DepictionStackView", "tabname": "Details", "views": views}]

    with open(os.path.join(out_dir, "sileo.json"), "w") as handle:
        json.dump({"minVersion": "0.1", "class": "DepictionTabView",
                   "tintColor": TINT, "tabs": tabs},
                  handle, indent=2, ensure_ascii=False)
        handle.write("\n")

    table = "\n".join("  <tr><th>%s</th><td>%s</td></tr>" % (esc(t), esc(v))
                      for t, v in rows)
    with open(os.path.join(out_dir, "index.html"), "w") as handle:
        handle.write(HTML_TEMPLATE % {
            "name": esc(name),
            "desc": ("<p>%s</p>\n" % esc(description)) if description else "",
            "version": esc(version),
            "table": table,
            "tint": TINT,
            "tint_soft": TINT_SOFT,
            "tint_deep": TINT_DEEP,
        })


def write_index(packages):
    """The landing page exists so opening the repository URL in a browser gives
    the add-to-manager links instead of a directory listing."""
    items = []
    for fields in sorted(packages, key=lambda f: f.get("Name", f["Package"]).lower()):
        pkg = fields["Package"]
        short = tagline(fields)
        items.append(
            '    <li><a class="pkglink" href="depictions/%s/">'
            '<img class="pkgicon" src="depictions/%s/icon.png" alt="">'
            '<span><span class="pkg">%s</span>'
            '<span class="meta"><span class="ver">%s</span>%s</span>'
            '</span></a></li>'
            % (pkg, pkg, esc(fields.get("Name", pkg)),
               esc(fields.get("Version", "")),
               " &middot; " + esc(short) if short else ""))

    with open("index.html", "w") as handle:
        handle.write(INDEX_TEMPLATE % {
            "origin": esc(os.environ.get("REPO_ORIGIN", "repository")),
            "description": esc(os.environ.get("REPO_DESCRIPTION", "")),
            "base": esc(BASE),
            "tint": TINT,
            "tint_soft": TINT_SOFT,
            "tint_deep": TINT_DEEP,
            "channels": os.environ.get("REPO_CHANNELS_HTML", ""),
            "packages": "\n".join(items),
        })


def version_gt(a, b):
    """Debian version ordering, which is not string ordering: 09092026-patch1
    sorts above 09092026, and 2.0.10 above 2.0.9. dpkg owns the rules, so it is
    asked rather than reimplemented."""
    if a == b:
        return False
    try:
        return subprocess.call(["dpkg", "--compare-versions", a, "gt", b]) == 0
    except (OSError, subprocess.CalledProcessError):
        return a > b


def main():
    raw = open("Packages.raw").read()
    stanzas = [s for s in raw.split("\n\n") if s.strip()]
    rendered = []
    parsed = []
    count = 0

    for stanza in stanzas:
        fields, order = parse(stanza)
        pkg = fields.get("Package")
        if not pkg:
            continue
        # a depiction is what turns a bare list entry into a page with a
        # description in all three clients
        for key, value in (
            ("Depiction", "%s/depictions/%s/" % (BASE, pkg)),
            ("SileoDepiction", "%s/depictions/%s/sileo.json" % (BASE, pkg)),
            ("Icon", "%s/depictions/%s/icon.png" % (BASE, pkg)),
            ("Homepage", BASE + "/"),
        ):
            if key not in fields:
                fields[key] = value
                order.append(key)

        # the managers list a package by its Description, so the compact line
        # has to go into the stanza too, not only into the pages
        short = tagline(fields)
        if short:
            fields["Description"] = short

        rendered.append("\n".join("%s: %s" % (k, fields[k]) for k in order))
        parsed.append(fields)
        count += 1

    if not count:
        raise SystemExit("build_indexes: no package stanza found")

    # every build stays installable, so the stanza list keeps all of them and a
    # manager can still offer an older one when the newest turns out bad
    with open("Packages", "w") as handle:
        handle.write("\n\n".join(rendered) + "\n")

    # a depiction and a landing page row describe a package, not a build, so
    # both are written from the newest version of each. without this the page
    # would describe whichever stanza dpkg happened to emit last
    newest = {}
    for fields in parsed:
        pkg = fields["Package"]
        if pkg not in newest or version_gt(fields.get("Version", ""),
                                           newest[pkg].get("Version", "")):
            newest[pkg] = fields

    for fields in newest.values():
        write_depiction(fields)
    write_index(list(newest.values()))
    print("   %d package(s), %d build(s)" % (len(newest), count))


if __name__ == "__main__":
    main()
