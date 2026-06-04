#!/usr/bin/env python3
"""
Pack legacy AWINIC aw87xxx per-scene "header+reg" bins into a single
aw87xxx_acf.bin ACF container (v0.0.0.1) that the v2.0.0.10 driver loads.

The v2.0.0.10 aw87xxx driver requests one firmware file, "aw87xxx_acf.bin",
and parses it as an ACF container. Older firmware (and the stock Wyze image)
ships one bin per scene (aw87xxx_pid_5a_music_0.bin, ..._off_0.bin, ...).
Those per-scene bins ARE the ACF's HDR_REG data blocks - this tool just wraps
them with the ACF header + DDE table so the new driver can consume the exact
vendor tuning.

Format reference: aw_acf_bin.h / aw_acf_bin.c (v0.0.0.1 path).
  aw_acf_hdr   = 80 bytes
  aw_acf_dde   = 64 bytes/entry
  data blocks  = concatenated per-scene bins, each CRC8-checked

CRC8 is the driver's aw_crc8_check() (reflected, poly 0x18 form).
"""
import struct
import sys
import argparse

AW_ACF_FILE_ID        = 0x0a15f908
AW_ACF_HDR_VER_0_0_0_1 = 0x00000001
AW_DDE_DEV_DEFAULT_TYPE_ID = 2          # applies regardless of dev bus/addr
AW_BIN_TYPE_HDR_REG   = 4               # per-scene bin = header + reg block

CUSTOMER_NAME_MAX = 16
PROJECT_NAME_MAX  = 24

# AW_PROFILE_* ids (enum aw_bin_dev_profile_id) -> driver g_profile_name[]
PROFILE_ID = {
    "music": 0, "voice": 1, "voip": 2, "ringtone": 3, "ringtone_hs": 4,
    "lowpower": 5, "bypass": 6, "mmi": 7, "fm": 8, "notification": 9,
    "rcv": 10, "receiver": 10, "off": 11,
}


def crc8(data: bytes) -> int:
    """Mirror of aw_crc8_check() in aw_acf_bin.c."""
    crc = 0
    for b in data:
        for _ in range(8):
            if (crc ^ b) & 1:
                crc ^= 0x18
                crc = (crc >> 1) | 0x80
            else:
                crc >>= 1
            b >>= 1
    return crc & 0xff


def cstr(s: str, n: int) -> bytes:
    b = s.encode()[: n - 1]
    return b + b"\0" * (n - len(b))


def pack_dde(dev_name, dev_index, dev_profile, data_type, data_size,
             data_offset, data_crc):
    # struct aw_acf_dde (64 bytes)
    return struct.pack(
        "<i16shhhh iiii 5i",
        AW_DDE_DEV_DEFAULT_TYPE_ID,        # type
        cstr(dev_name, CUSTOMER_NAME_MAX), # dev_name[16]
        dev_index,                         # dev_index
        0,                                 # dev_bus   (unused, default type)
        -1,                                # dev_addr  (0xffff, unused)
        dev_profile,                       # dev_profile
        data_type,                         # data_type
        data_size,                         # data_size
        data_offset,                       # data_offset
        data_crc,                          # data_crc
        0, 0, 0, 0, 0,                     # reserve[5]
    )


def build(chip, project, custom, dev_index, profiles):
    """profiles = list of (profile_name, raw_bytes)."""
    hdr_size = 80
    dde_size = 64
    dde_num = len(profiles)
    ddt_offset = hdr_size
    ddt_size = dde_num * dde_size
    data_base = ddt_offset + ddt_size

    ddes = b""
    blob = b""
    off = data_base
    for name, raw in profiles:
        if len(raw) % 2:
            raise SystemExit(f"{name}: data_size {len(raw)} is odd (driver rejects %2)")
        pid = PROFILE_ID[name.lower()]
        ddes += pack_dde(chip, dev_index, pid, AW_BIN_TYPE_HDR_REG,
                         len(raw), off, crc8(raw))
        blob += raw
        off += len(raw)

    # struct aw_acf_hdr (80 bytes)
    hdr = struct.pack(
        "<i24s16s4s iiii i 3i",
        AW_ACF_FILE_ID,
        cstr(project, PROJECT_NAME_MAX),
        cstr(custom, CUSTOMER_NAME_MAX),
        bytes(4),                  # version[4]
        0,                         # author_id
        ddt_size,                  # ddt_size
        dde_num,                   # dde_num
        ddt_offset,                # ddt_offset
        AW_ACF_HDR_VER_0_0_0_1,    # hdr_version
        0, 0, 0,                   # reserve[3]
    )
    assert len(hdr) == hdr_size, len(hdr)
    assert len(ddes) == ddt_size, len(ddes)
    return hdr + ddes + blob


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--chip", default="aw87559")
    ap.add_argument("--project", default="wyze_v3pro")
    ap.add_argument("--custom", default="thingino")
    ap.add_argument("--dev-index", type=int, default=0)
    ap.add_argument("-o", "--output", default="aw87xxx_acf.bin")
    ap.add_argument("profiles", nargs="+",
                    help="name=path, e.g. music=aw87xxx_pid_5a_music_0.bin")
    a = ap.parse_args()

    profiles = []
    for p in a.profiles:
        name, _, path = p.partition("=")
        profiles.append((name, open(path, "rb").read()))

    out = build(a.chip, a.project, a.custom, a.dev_index, profiles)
    open(a.output, "wb").write(out)
    print(f"wrote {a.output} ({len(out)} bytes), {len(profiles)} profiles, chip={a.chip}")


if __name__ == "__main__":
    main()
