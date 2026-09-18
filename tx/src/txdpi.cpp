// SPDX-License-Identifier: Apache-2.0
// txdpi.c — simulator-agnostic transaction recorder (DPI-C).
// Compile this file together with your simulation (Verilator/VCS/Xcelium
// all support DPI-C). Produces a JSONL transaction database:
//   {"kind": "...", "t": 123, "payload": "addr=3,data=7"}
// One line per recorded transaction — streamable, diff-able, tool-able.

#include <stdio.h>
#include <stdlib.h>
#include "svdpi.h"

#ifdef __cplusplus
extern "C" {
#endif

static FILE* g_log = NULL;

void tx_open(const char* path) {
    if (g_log) fclose(g_log);
    g_log = fopen(path, "w");
    if (!g_log) {
        fprintf(stderr, "txrecorder: cannot open %s\n", path);
        exit(1);
    }
}

void tx_record(const char* kind, long long t, const char* payload) {
    if (!g_log) return;
    fprintf(g_log, "{\"kind\":\"%s\",\"t\":%lld,\"payload\":\"%s\"}\n",
            kind, t, payload ? payload : "");
    fflush(g_log);   // keep the DB valid even if the sim crashes
}

void tx_close(void) {
    if (g_log) { fclose(g_log); g_log = NULL; }
}

#ifdef __cplusplus
}
#endif
