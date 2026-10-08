# sqmrakdev

<p align="center"><b>apt repo for jailbroken ios 5 to 16, one source</b></p>

> [!NOTE]
> all packages need a jailbreak.

## add

source: `https://sqmrak.github.io/sqmrakdev/`

cydia, sileo and zebra all read it. the page has buttons for each of them.

## packages

- senko: vless, hysteria2 and amneziawg for the whole device. ios 5-16, armv7 and arm64. <https://github.com/sqmrak/senko>
- byebyedpi: dpi bypass and telegram for the whole device. ios 5-16, armv7 and arm64
- rewind: youtube music client. ios 5-16, armv7 and arm64. formerly tunetube

every package is `Architecture: all` and picks the rootful or rootless layout in postinst.

## layout

- `debs/`: the packages
- `Packages`, `Packages.gz`, `.bz2`, `.xz`, `.zst`, `Release`: the index, all written from one `Packages`
- `depictions/`: one page per package
- `published.json`: which bytes went out under which version, the only generated file on `main`

`refresh.sh` refuses to build an index that reuses a published version with other bytes, or that drops a listed deb. a client holding the old index would report a hash mismatch.

## build

```bash
./refresh.sh
./publish.sh
```

`refresh.sh` rebuilds the indexes and pages from `debs/`. `publish.sh` replaces `gh-pages` with the result as one commit, so no old package stays in history. a `nightly/` channel is built too while `nightly/debs/` holds a package.

needs `dpkg-scanpackages`, `gzip`, `bzip2`, `xz`, `python3`, optionally `zstd`.
