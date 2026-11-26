# sqmrakdev

## add

source: <https://sqmrak.github.io/sqmrakdev/>

cydia, sileo and zebra all read it. the page has buttons for each of them.

## packages

- shiro: cloudflare warp for the whole device. ios 5+, armv7, arm64 and arm64e
- senko: vless, hysteria2 and amneziawg for the whole device. ios 4.3+, armv7 and arm64.
- byebyedpi: dpi bypass and telegram for the whole device. ios 5+, armv7 and arm64
- rewind: youtube music client. ios 5+, armv7 and arm64. formerly tunetube
- shapka: 4pda forum client. ios 5+, armv7 and arm64
- weeabu: pikabu client. ios 5+, armv7 and arm64
- yozora: webkit port, two packages. `Yozora (arm64)` for 64-bit devices on iOS 7+, `Yozora (armv7)` for 32-bit devices and 64-bit ones up to iOS 10. each refuses a device that cannot run it

every package but weeabu is `Architecture: all` and picks the rootful or rootless layout in postinst. weeabu is `iphoneos-arm`, rootful only.
