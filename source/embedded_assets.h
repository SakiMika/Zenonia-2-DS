#pragma once
#include <stdint.h>
#include <stddef.h>

struct EmbeddedAssetView {
    const uint8_t *data;
    uint32_t size;
};

// Legacy API name; all payloads now come from a FAT folder, not the NDS.
// Call once AFTER wipi_init_storage() has mounted libfat.
bool embedded_assets_init(void);
const char *embedded_asset_root(void);
// Confines resource names to the selected /zenonia2nds/ folder.
bool embedded_asset_path(const char *name, char *out, size_t cap);
bool embedded_asset_find(const char *name, EmbeddedAssetView *out);
// Metadata-only lookup: no payload read or temporary allocation.
bool embedded_asset_size(const char *name, uint32_t *out_size);
// Read directly to caller storage. WIPI-compatible errors: -9 bad buffer,
// -12 missing/I/O error, -18 insufficient capacity; zero on success.
int embedded_asset_read(const char *name, void *dst, uint32_t cap);
void embedded_asset_release_cache(void);
