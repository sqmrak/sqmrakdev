#!/usr/bin/env python3
"""Guard the one repository mistake that forces users to re-add the source.

A package manager caches the Packages index for as long as its own TTL says,
and it trusts the hash it read there. Two things break that trust and neither
heals on its own:

  * the bytes behind a Filename change while the Version stays the same. The
    client downloads the new file, compares it against the cached hash and
    reports "Hash Sum mismatch" forever.
  * a .deb named by a still-cached index is deleted. The client reports
    "Unable to fetch some archives".

Both leave a repository that looks permanently broken, and the only cure the
user knows is deleting the source and adding it again. So this refuses to build
an index that would cause either: a version is published exactly once, with one
set of bytes, and the file behind it is never taken away while it is listed.

The ledger is the record of what has already gone out. It is committed with the
source, so the check works from a fresh clone.
"""
import hashlib
import json
import os
import subprocess
import sys

LEDGER = "published.json"


def deb_version(path):
    try:
        out = subprocess.check_output(["dpkg-deb", "-f", path, "Version"],
                                      stderr=subprocess.DEVNULL)
    except (OSError, subprocess.CalledProcessError):
        raise SystemExit("check_builds: %s is not a readable .deb" % path)
    return out.decode("utf-8", "replace").strip()


def sha256(path):
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def load(path):
    if not os.path.exists(path):
        return {}
    with open(path) as handle:
        try:
            return json.load(handle)
        except ValueError:
            return {}


def main():
    if len(sys.argv) < 4:
        raise SystemExit("usage: check_builds.py <ledger> <channel> <debs-dir>")
    ledger_path, channel, debs = sys.argv[1], sys.argv[2], sys.argv[3]

    ledger = load(ledger_path)
    known = ledger.setdefault(channel, {})

    found = {}
    for name in sorted(os.listdir(debs)):
        if not name.endswith(".deb"):
            continue
        path = os.path.join(debs, name)
        version = deb_version(path)
        if not version:
            raise SystemExit("check_builds: %s has no Version field" % path)
        if version in found:
            raise SystemExit(
                "check_builds: %s and %s both claim version %s in the %s channel.\n"
                "  one version is one build; give this one its own version."
                % (found[version]["file"], name, version, channel))
        found[version] = {"file": name, "sha256": sha256(path)}

    problems = []
    for version, entry in sorted(found.items()):
        was = known.get(version)
        if was and was.get("sha256") != entry["sha256"]:
            problems.append(
                "  %s was published as %s\n"
                "    then: %s\n"
                "    now:  %s\n"
                "  republishing different bytes under one version is what makes a\n"
                "  package manager report a hash mismatch until the source is deleted\n"
                "  and added again. bump the version instead."
                % (version, was.get("file", entry["file"]),
                   was.get("sha256", "?"), entry["sha256"]))

    for version, was in sorted(known.items()):
        if version not in found:
            problems.append(
                "  %s (%s) was published and is now missing from %s.\n"
                "  a manager still holding the old index would fail to fetch it.\n"
                "  keep the file, or drop the entry from the ledger on purpose."
                % (version, was.get("file", "?"), debs))

    if problems:
        sys.stderr.write("check_builds: refusing to index the %s channel\n%s\n"
                         % (channel, "\n".join(problems)))
        return 1

    for version, entry in found.items():
        if version not in known:
            known[version] = entry

    with open(ledger_path, "w") as handle:
        json.dump(ledger, handle, indent=2, sort_keys=True)
        handle.write("\n")

    print("   %d build(s) in %s, all immutable" % (len(found), channel))
    return 0


if __name__ == "__main__":
    sys.exit(main())
