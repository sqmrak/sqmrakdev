#!/usr/bin/env bash
# Rebuild every index and storefront page in this repository from whatever is
# sitting in the channel directories.
#
# The repository publishes two channels. The root is stable, so every manager
# that already holds the repository URL keeps working and keeps getting tested
# builds. nightly/ is a second, complete flat repository for testers, added as
# its own source. Nothing is shared between them but the templates: separate
# Packages, separate Release, separate debs, so a broken nightly cannot reach
# anyone who did not ask for it.
#
# Cydia, Sileo and Zebra all read a flat repository: Packages at the root of
# the channel, the packages under its debs/. Cydia needs Packages.bz2, Sileo
# prefers .zst or .xz, Zebra takes .gz; all are written from the same Packages
# file so the hashes agree whichever one a client picks.
set -euo pipefail

here="$(cd "$(dirname "$0")" && pwd)"
cd "${here}"

# shellcheck source=/dev/null
. ./repo.conf
REPO_URL="${REPO_URL%/}"
REPO_TINT_NIGHTLY="${REPO_TINT_NIGHTLY:-${REPO_TINT}}"

# the landing page of either channel points at both, because a tester who lands
# on the stable page has no other way to discover where the test builds live
channels_html() {
    cat <<HTML
  <h2>Channels</h2>
  <ul>
    <li><a class="pkglink" href="${REPO_URL}/"><span>
      <span class="pkg">stable</span>
      <span class="meta">for everyone &middot; <span class="ver">${REPO_URL}</span></span>
    </span></a></li>
    <li><a class="pkglink" href="${REPO_URL}/nightly/"><span>
      <span class="pkg">nightly</span>
      <span class="meta">test builds, expect breakage &middot; <span class="ver">${REPO_URL}/nightly</span></span>
    </span></a></li>
  </ul>
HTML
}

# $1 channel directory, $2 base url, $3 suite, $4 origin, $5 tint, $6 blurb
build_channel() {
    local dir="$1" url="$2" suite="$3" origin="$4" tint="$5" blurb="$6"

    if [ ! -d "${dir}/debs" ] ||
       [ -z "$(find "${dir}/debs" -maxdepth 1 -name '*.deb' -print -quit)" ]; then
        echo "refresh: no .deb under ${dir}/debs" >&2
        exit 1
    fi

    echo "==> ${suite}: scanning ${dir}/debs"
    (
        cd "${dir}"

        # the pages of a channel are served from that channel, so the icon and
        # the storefront artwork have to sit next to them
        if [ "${dir}" != "." ]; then
            cp -f "${here}/CydiaIcon.png" ./CydiaIcon.png
            rm -rf ./assets && cp -R "${here}/assets" ./assets
        fi

        # a version that has already gone out is never rebuilt with different
        # bytes, and a file that has gone out is never removed while it is still
        # listed. either one leaves package managers reporting a hash mismatch
        # or a missing archive until the user deletes the source and adds it
        # again, which is the one failure this repository must not produce
        python3 "${here}/tools/check_builds.py" "${here}/published.json" \
            "${suite}" debs

        # /dev/null stands in for the override file, and the paths stay relative
        # so Filename: resolves from the channel root. --multiversion keeps every
        # published build listed, so a manager holding an older index still finds
        # the file it expects
        dpkg-scanpackages --multiversion debs /dev/null 2>/dev/null > Packages.raw

        echo "==> ${suite}: writing Packages and depictions"
        REPO_ORIGIN="${origin}" REPO_DESCRIPTION="${blurb}" \
        REPO_TEMPLATE_DIR="${here}" REPO_CHANNELS_HTML="$(channels_html)" \
            python3 "${here}/tools/build_indexes.py" "${url}" "${tint}"
        rm -f Packages.raw

        echo "==> ${suite}: compressing"
        rm -f Packages.gz Packages.bz2 Packages.xz Packages.zst
        gzip -9nk Packages
        bzip2 -9k Packages
        xz -9k Packages
        command -v zstd >/dev/null 2>&1 && zstd -19 -q -k Packages

        echo "==> ${suite}: writing Release"
        hash_block() {
            local algo="$1" cmd="$2" f
            printf '%s:\n' "${algo}"
            for f in Packages Packages.gz Packages.bz2 Packages.xz Packages.zst; do
                [ -f "${f}" ] || continue
                printf ' %s %s %s\n' "$(${cmd} "${f}" | cut -d' ' -f1)" \
                    "$(stat -c%s "${f}")" "${f}"
            done
        }

        {
            printf 'Origin: %s\n' "${origin}"
            printf 'Label: %s\n' "${origin}"
            printf 'Suite: %s\n' "${suite}"
            printf 'Version: 1.0\n'
            printf 'Codename: %s\n' "${suite}"
            # every architecture a jailbreak package manager may ask for. the
            # packages here are Architecture: all and pick rootless or rootful
            # in postinst
            printf 'Architectures: iphoneos-arm iphoneos-arm64 all\n'
            printf 'Components: main\n'
            printf 'Description: %s\n' "${blurb}"
            printf 'Maintainer: %s\n' "${REPO_MAINTAINER}"
            # apt clients compare this against the index they already hold;
            # without it a rebuilt repository looks the same age as the copy in
            # their cache
            printf 'Date: %s\n' "$(date -u '+%a, %d %b %Y %H:%M:%S UTC')"
            hash_block MD5Sum md5sum
            hash_block SHA256 sha256sum
        } > Release
    )
}

build_channel "." "${REPO_URL}" "stable" \
    "${REPO_ORIGIN}" "${REPO_TINT}" "${REPO_DESCRIPTION}"

build_channel "nightly" "${REPO_URL}/nightly" "nightly" \
    "${REPO_ORIGIN} nightly" "${REPO_TINT_NIGHTLY}" "${REPO_DESCRIPTION_NIGHTLY}"

echo "==> done"
for channel in . nightly; do
    printf '   [%s]\n' "$([ "${channel}" = "." ] && echo stable || echo "${channel}")"
    grep -E '^(Package|Version|Filename|Size)' "${channel}/Packages" | sed 's/^/     /'
done
