# sqmrakdev

APT repository for jailbroken iOS. Add it as a source in your package manager,
or open the page and use the buttons on it.

    https://sqmrak.github.io/sqmrakdev/

## Packages

- **Senko** — full-device VLESS, hysteria2 and AmneziaWG client for iOS 5-16, armv7 and
  arm64. <https://github.com/sqmrak/senko>

- **ByeByeDPI** — dpi bypass and telegram for the whole device, iOS 5-16, armv7
  and arm64.

- **Rewind** — youtube music client for iOS 5-16, armv7 and arm64. formerly tunetube.

## Layout

A complete flat repository with its own `Packages`, `Release` and `debs/`.
`./refresh.sh` rebuilds the indexes from the packages sitting in `debs/`, and
`./publish.sh` replaces the `gh-pages` branch with the result as a single
commit. A `nightly/` channel is built too while `nightly/debs/` holds a package.
