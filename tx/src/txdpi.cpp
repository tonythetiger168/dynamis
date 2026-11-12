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


// Escape bytes required by JSON while preserving UTF-8 payload bytes.
static void tx_json_string(const char* text) {
    fputc('"', g_log);
    const unsigned char* p = (const unsigned char*)(text ? text : "");
    for (; *p; ++p) {
        if (*p == '"' || *p == 0x5c) { // quote or backslash
            fputc(0x5c, g_log);
            fputc(*p, g_log);
        } else if (*p < 0x20) {
            fprintf(g_log, "%cu%04x", 0x5c, (unsigned)*p);
        } else fputc(*p, g_log);
    }
    fputc('"', g_log);
}

void tx_record(const char* kind, long long t, const char* payload) {
    if (!g_log) return;
    fputs("{\"kind\":", g_log);
    tx_json_string(kind);
    fprintf(g_log, ",\"t\":%lld,\"payload\":", t);
    tx_json_string(payload);
    fputs("}\n", g_log);
    fflush(g_log);   // keep the DB valid even if the sim crashes
}

void tx_close(void) {
    if (g_log) { fclose(g_log); g_log = NULL; }
}

#ifdef __cplusplus
}
#endif
