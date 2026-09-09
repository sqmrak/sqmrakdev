# sqmrakdev

APT repository for jailbroken iOS. It publishes two channels; add whichever one
you want as a source in your package manager, or open the page and use the
buttons on it.

## stable

    https://sqmrak.github.io/sqmrakdev/

Tested builds. This is the one to give to people who just want the app to work.

## nightly

    https://sqmrak.github.io/sqmrakdev/nightly/

Test builds for testers. They break, and they are meant to: the point is to
find out how before a build reaches the stable channel. A nightly version
always sorts above every stable one, so a manager holding both sources offers
the nightly.

## Packages

- **Senko** — full-device VLESS and AmneziaWG client for iOS 5-15, armv7 and
  arm64. <https://github.com/sqmrak/senko>

## Layout

Each channel is a complete flat repository with its own `Packages`, `Release`
and `debs/`; nothing is shared but the page templates. `./refresh.sh` rebuilds
both from the packages sitting in `debs/` and `nightly/debs/`, and
`./publish.sh` replaces the `gh-pages` branch with the result as a single
commit.
