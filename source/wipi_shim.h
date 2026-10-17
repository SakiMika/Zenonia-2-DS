#pragma once
#include <nds.h>
#include <stdint.h>

void wipi_init_video(PrintConsole *log_console);
void wipi_init_storage(void);
void wipi_flush_storage(void);
void wipi_poll(void);
uint32_t wipi_get_import_table(uint32_t table);
void *wipi_get_import_function(uint32_t table, uint32_t index);
void wipi_present(void);
void wipi_debug_dump(const char *tag);

bool wipi_start_clet(void);
void wipi_paint_clet(void);
void wipi_dispatch_keys(uint32_t keys_down, uint32_t keys_up);
void wipi_handle_touch(uint32_t keys_down, int x, int y);
void wipi_set_log_visible(bool visible);
bool wipi_log_visible(void);
void wipi_note_sound_request(int id, int arg2, int flag);

struct WipiCletState {
    uint32_t register_arg0;
    uint32_t register_arg1;
    uint32_t callbacks[6]; // start, pause, resume, destroy, paint, event
    bool registered;
    bool started;
};
const WipiCletState *wipi_clet_state(void);

// Scoped HUD geometry guard; HUD and gameplay draw directly into the TOP RGB565 LCD.
// SUB supports the SELECT minimap and settings; no virtual quickbar keys.
bool wipi_begin_native_hud(void);
void wipi_end_native_hud(void);

// SELECT relocates only the native minimap draw; cached screen aliases are scoped.
bool wipi_prepare_minimap(void);
bool wipi_begin_minimap(int width,int height);
bool wipi_minimap_has_pixels(void);
void wipi_end_minimap(void);
void wipi_toggle_minimap(void);
// TEST4: native minimap capture/cache; the game/audio clocks remain unchanged.
void wipi_invalidate_minimap_cache(void);
bool wipi_try_cached_minimap(uint32_t self,uint32_t map,int width,int height,uint32_t *result);
void wipi_store_minimap_cache(uint32_t result);
