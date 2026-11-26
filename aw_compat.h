/* SPDX-License-Identifier: GPL-2.0 */
#ifndef _AW_COMPAT_H_
#define _AW_COMPAT_H_

#include <linux/version.h>

/* the legacy gpio number API is gone from 7.x: use a gpio descriptor there */
#if LINUX_VERSION_CODE >= KERNEL_VERSION(6, 5, 0)
#define AW_USE_GPIOD
#endif

#endif
