#!/usr/bin/env bash
# Rebuild the indexes and replace the published branch with the current site.
#
# The branch is written as a single commit every time, so a 19 MB package never
# accumulates in history: what GitHub keeps reachable is one release, whatever
# the release number is. The sources stay on the branch this script is run from.
set -euo pipefail

here="$(cd "$(dirname "$0")" && pwd)"
cd "${here}"

BRANCH="${SQMRAKDEV_BRANCH:-gh-pages}"
REMOTE="${SQMRAKDEV_REMOTE:-}"
if [ -z "${REMOTE}" ]; then
    REMOTE="$(git config --get remote.origin.url || true)"
fi
if [ -z "${REMOTE}" ]; then
    echo "publish: no remote. add one with" >&2
    echo "  git remote add origin git@github.com:sqmrak/sqmrakdev.git" >&2
    echo "or set SQMRAKDEV_REMOTE=<url>" >&2
    exit 1
fi

./refresh.sh

# the site is what a package manager fetches; the templates and this script are
# not part of it
site_files=(debs Packages Release index.html CydiaIcon.png assets depictions)
for f in Packages.gz Packages.bz2 Packages.xz Packages.zst; do
    [ -f "${f}" ] && site_files+=("${f}")
done
# the nightly channel is a complete flat repository of its own, so the whole
# directory ships as one unit rather than being reassembled here
[ -d nightly ] && site_files+=(nightly)
for f in "${site_files[@]}"; do
    [ -e "${f}" ] || { echo "publish: missing ${f}, run ./refresh.sh" >&2; exit 1; }
done

stage="$(mktemp -d)"
trap 'rm -rf "${stage}"' EXIT
cp -R "${site_files[@]}" "${stage}/"

version="$(sed -n 's/^Version: //p' Packages | tr '\n' ' ' | sed 's/ $//')"
nightly_version=""
[ -f nightly/Packages ] &&
    nightly_version="$(sed -n 's/^Version: //p' nightly/Packages | tr '\n' ' ' | sed 's/ $//')"
label="stable ${version:-unknown}"
[ -n "${nightly_version}" ] && label="${label} + nightly ${nightly_version}"
echo "==> publishing ${label} to ${BRANCH}"

git -C "${stage}" init -q -b "${BRANCH}"
# an empty value here would be worse than none: git reports a missing identity
# clearly, an empty one fails inside the commit
name="$(git config user.name || true)"
email="$(git config user.email || true)"
[ -n "${name}" ] && git -C "${stage}" config user.name "${name}"
[ -n "${email}" ] && git -C "${stage}" config user.email "${email}"
git -C "${stage}" add -A
git -C "${stage}" commit -qm "sqmrakdev ${label}"
git -C "${stage}" push -f "${REMOTE}" "${BRANCH}:${BRANCH}"

echo "==> done; ${BRANCH} now holds one commit with $(du -sh "${stage}/debs" | cut -f1) of packages"
