/*
 * Copyright (C) 1997-2024 Free Software Foundation, Inc.
 *
 * This file is free software; you can redistribute it and/or modify it
 * under the terms of the GNU General Public License as published by the
 * Free Software Foundation; either version 3, or (at your option) any
 * later version.
 *
 * This file is distributed in the hope that it will be useful, but
 * WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
 * General Public License for more details.
 *
 * Under Section 7 of GPL version 3, you are granted additional
 * permissions described in the GCC Runtime Library Exception, version
 * 3.1, as published by the Free Software Foundation.
 *
 * You should have received a copy of the GNU General Public License and
 * a copy of the GCC Runtime Library Exception along with this program;
 * see the files COPYING3 and COPYING.RUNTIME respectively.  If not, see
 * <http://www.gnu.org/licenses/>.
 */


#include "sfp-machine.h"

#define HUGE_VAL (__builtin_huge_val ())

void
__sfp_handle_exceptions (int _fex)
{
  /* Raise exceptions represented by _FEX.  But we must raise only one
     signal at a time.  It is important that if the overflow/underflow
     exception and the divide by zero exception are given at the same
     time, the overflow/underflow exception follows the divide by zero
     exception.  */

#ifdef __SH_FPU_ANY__
#if !defined(__SH2E__)
  if (_fex & FP_EX_INEXACT)
  {
    double d = 1.0, x = 3.0;
    __asm__ __volatile__ ("fdiv %1, %0" : "+d" (d) : "d" (x));
  }

  if (_fex & FP_EX_UNDERFLOW)
  {
    long double d = __LDBL_MIN__, x = 10;
    __asm__ __volatile__ ("fdiv %1, %0" : "+d" (d) : "d" (x));
  }

  if (_fex & FP_EX_OVERFLOW)
  {
    long double d = __LDBL_MAX__;
    __asm__ __volatile__ ("fmul %0, %0" : "+d" (d) : "d" (d));
  }
#endif

  if (_fex & FP_EX_DIVZERO)
  {
    double d = 1.0, x = 0.0;
    __asm__ __volatile__ ("fdiv %1, %0" : "+d" (d) : "d" (x));
  }

  if (_fex & FP_EX_INVALID)
  {
    double d = HUGE_VAL, x = 0.0;
    __asm__ __volatile__ ("fmul %1, %0" : "+d" (d) : "d" (x));
  }
#endif
}
