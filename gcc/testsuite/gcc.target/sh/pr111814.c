/* Verify that __builtin_nan("") produces a constant matches
   architecture specification. */
/* { dg-do compile } */

double d = __builtin_nan ("");

/* { dg-final { scan-assembler "\t\\.word\t2146959359\n\t\\.word\t(?:-1|4294967295)\n" } } */
