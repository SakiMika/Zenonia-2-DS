#pragma once
#include <stdint.h>

namespace ZenSav {
// Three character slots (Save0.dat..Save2.dat) plus option.sav live in one
// 128 KiB FAT container: RUNNER_SAVE_BASENAME (stage 1: ZKR1.sav). TEST2+ disables native cartridge EEPROM
// probing for flashcart compatibility. EnableNativeProbe is now an API no-op.
void InitFatFallback();
void EnableNativeProbe();
void Flush();

bool IsPersistentName(const char *name);
int RecordIdForName(const char *name); // Save0..2 => 0..2, option.sav => 3

bool Exists(const char *name, uint32_t *out_len = nullptr);
int Load(const char *name, uint8_t **out_data, uint32_t *out_len);
int Store(const char *name, const uint8_t *data, uint32_t len);
int Remove(const char *name);

const char *BackendName();
}
