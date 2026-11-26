# aw87xxx — Awinic Smart-K PA driver

Linux kernel driver for the **Awinic AW87xxx** family of "Smart K" mono Class-D
audio power amplifiers (AW87xxx pid_18 / pid_39 / pid_59 / pid_5a / pid_76 /
pid_9b — e.g. AW87359, AW87519, AW87559 …). The chip is configured over I2C and
driven from per-scene register profiles; it has no I2S/DSP path of its own.

This is Awinic's multi-chip driver (`v2.0.0.10`) packaged to build and run on
**older / minimal kernels** — ones without an ASoC sound card, without the
`POWER_SUPPLY` subsystem, and without a DSP/ADSP. The vendor tree assumes a
modern phone SoC (4.19+, Qualcomm/MTK ADSP for speaker protection, a battery for
vmax scaling, an ALSA card to hang kcontrols on); the changes below make it
portable to systems that have none of that.

## Changes from the vendor tree

| Area | Change | Why |
|------|--------|-----|
| `aw87xxx.c` | add `#include <linux/vmalloc.h>` | newer kernels pull it in transitively; older ones (≈4.4) need it explicitly for `vmalloc`/`vfree` |
| `Makefile` | link all objects into one module `snd-soc-aw87xxx.ko` (`…-objs`) | the vendor `obj-$(CFG) += a.o b.o …` line builds **six** separate modules with unresolved cross-references |
| `Makefile` | `ccflags-y += -funsigned-char` | the bin parser sums firmware bytes through a `char *` and assumes unsigned char (vendor build default). On a **signed-char toolchain** the high bytes sign-extend and `aw_check_sum()` fails (`check sum or check bin data len error`) |
| `aw_dsp.h` | disable `AW_QCOM_OPEN_DSP_PLATFORM` | build in no-DSP mode (register/scene config only) where there is no ADSP |
| `aw87xxx.c`, `aw_monitor.c` | gate ASoC and power-supply code behind `IS_ENABLED(CONFIG_SND_SOC)` / `IS_ENABLED(CONFIG_POWER_SUPPLY)` | so the driver builds where those subsystems are absent; control is via **sysfs**, and VBAT/vmax scaling is skipped where there is no battery |

The driver also builds on 7.x (tested against 7.4 and 4.4.94 and 3.10.14 kernel trees): the reset line is a gpio descriptor from
6.5 on (the `reset-gpio` property is matched by the legacy suffix), the I2C `probe` takes only the client from 6.3 and `remove` returns void from 6.1,
all behind `LINUX_VERSION_CODE` guards (`aw_compat.h`), so the older kernels keep the unchanged code.

The gating is conditional, so the driver still adapts upward: on a kernel that
*does* provide ASoC and `POWER_SUPPLY`, the kcontrol and VBAT paths compile back in.

## Building

Out-of-tree against a configured/built kernel tree:

```sh
make -C "$KDIR" M="$PWD" \
     ARCH=<arch> CROSS_COMPILE=<prefix-> \
     CONFIG_SND_SOC_AW87XXX=m modules
```

Produces `snd-soc-aw87xxx.ko`. `make clean` (with the same `KDIR`) removes the
build artifacts. For a native build, `KDIR` defaults to
`/lib/modules/$(uname -r)/build`.

## Firmware

`v2.0.0.10` loads a **single ACF container** named **`aw87xxx_acf.bin`** (it does
**not** read the older per-scene `aw87xxx_pid_*_*.bin` files). The driver requests
it by bare name, so the firmware loader expects it at:

```
/lib/firmware/aw87xxx_acf.bin
```

If you only have the legacy per-scene bins, `tools/pack_acf.py` repacks them into
the ACF the driver wants (preserving the exact register tuning):

```sh
tools/pack_acf.py --chip aw87559 -o aw87xxx_acf.bin \
    music=aw87xxx_pid_5a_music_0.bin \
    voice=aw87xxx_pid_5a_voice_0.bin \
    fm=aw87xxx_pid_5a_fm_0.bin \
    rcv=aw87xxx_pid_5a_rcv_0.bin \
    off=aw87xxx_pid_5a_off_0.bin
```

It writes a v0.0.0.1 ACF (header + DDE table + the per-scene "header+reg" blocks,
each CRC8-checked) and validates it against every check the driver performs.
`firmware/aw87xxx_acf.bin` is an example built this way for an AW87559.

## Device tree

```dts
aw87xxx_pa@58 {
    compatible = "awinic,aw87xxx_pa";
    reg = <0x58>;
    reset-gpio = <…>;          /* platform-specific specifier */
    pa-channel = <0x00>;
    status = "okay";
};
```

## Usage (sysfs)

Controls live under the I2C device, e.g. for bus 3 / address 0x58
(`/sys/bus/i2c/devices/3-0058/`):

```sh
cat  …/profile                 # list profiles ('>' marks current)
echo Music > …/profile         # power the amp on with the named profile
echo Off   > …/profile         # soft power-down
cat  …/reg                     # dump registers
cat  …/drv_ver
```

Profile names (Music / Voice / Fm / Receiver / Off …) come from the bins present
in the ACF.

## Credits

Based on Awinic's `aw87xxx` driver (`v2.0.0.10`); portability fixes for
minimal/older kernels and the ACF packer added here.
