#pragma once
inline bool test_hud_active=false;
inline bool test_hud_available=true;
inline bool wipi_begin_native_hud() { if(!test_hud_available || test_hud_active)return false;test_hud_active=true;return true; }
inline void wipi_end_native_hud() { test_hud_active=false; }
