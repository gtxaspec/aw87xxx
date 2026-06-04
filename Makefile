# for AWINIC AW87XXX Smart K PA
# Link all objects into a single module (snd-soc-aw87xxx.ko).
# The module name must differ from any constituent object (aw87xxx.o).
snd-soc-aw87xxx-objs := aw87xxx.o aw_device.o aw_monitor.o aw_bin_parse.o aw_dsp.o aw_acf_bin.o
obj-$(CONFIG_SND_SOC_AW87XXX) += snd-soc-aw87xxx.o

# The Awinic bin parser sums firmware bytes through a `char *` and assumes
# unsigned char (vendor build default). With a signed-char toolchain the
# checksum sign-extends high bytes and aw_check_sum() fails. Force unsigned.
ccflags-y += -funsigned-char

# --- out-of-tree convenience targets ---
# Usage: make KDIR=/path/to/kernel ARCH=mips CROSS_COMPILE=mipsel-linux-
KDIR ?= /lib/modules/$(shell uname -r)/build

modules modules_install clean:
	$(MAKE) -C $(KDIR) M=$(CURDIR) CONFIG_SND_SOC_AW87XXX=m $@

.PHONY: modules modules_install clean
