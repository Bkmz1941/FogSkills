# PARAMS.md — словарь `human_skin_params.json` по вещам

> Снято с файла `BlenderWork/human_skin_params.json` 2026-09-07 — это ЖИВЫЕ
> значения, а не пересказ. Все длины в МЕТРАХ мировых координат (рост фигуры
> 1.83 м), кроме параметров швов (`pocket_*`, `fly_*`) — они в ЛОКАЛЬНЫХ
> единицах сетки штанов, где 1 = 1 см (P190).
>
> Что каждая группа делает — `BLENDER.md` здесь (раздел «Эталон штанов»,
> «Футболка», «Обувь»). Правило: меняем ОДНО число, смотрим на паре фигур,
> и только потом переносим.

## Штаны: профиль и посадка

| параметр | значение |
|---|---|
| `export_ease` | `0.2` |
| `export_ease_crotch` | `0.7` |
| `pants_apex_fade` | `0.025` |
| `pants_apex_r` | `0.035` |
| `pants_apex_smooth` | `30` |
| `pants_arch_fade` | `0.03` |
| `pants_arch_half` | `0.055` |
| `pants_arch_r` | `0.032` |
| `pants_belt_gap` | `0.02` |
| `pants_belt_lo` | `0.995` |
| `pants_belt_top` | `1.08` |
| `pants_blend_hi` | `0.92` |
| `pants_blend_lo` | `0.8` |
| `pants_calf_r` | `0.0825` |
| `pants_calf_z` | `0.385` |
| `pants_crotch_band` | `0.025` |
| `pants_crotch_drop` | `0.01` |
| `pants_crotch_fade` | `0.04` |
| `pants_crotch_gap` | `0.0` |
| `pants_crotch_r` | `0.07` |
| `pants_crotch_relax` | `0` |
| `pants_crotch_smooth` | `15` |
| `pants_fix_fade` | `0.05` |
| `pants_fix_r` | `0.1` |
| `pants_hem_r` | `0.066` |
| `pants_hem_z` | `0.135` |
| `pants_hip_ease` | `0.01` |
| `pants_hip_smooth` | `0` |
| `pants_knee_r` | `0.0805` |
| `pants_knee_z` | `0.49` |
| `pants_line_smooth` | `4` |
| `pants_min_ease` | `0.005` |
| `pants_polish` | `3` |
| `pants_round` | `0.6` |
| `pants_round_hi` | `0.75` |
| `pants_round_lo` | `0.55` |
| `pants_side_mix` | `0.05` |
| `pants_smooth` | `16` |
| `pants_thickness` | `0.005` |
| `pants_thigh_r` | `0.098` |
| `pants_thigh_z` | `0.8` |
| `pants_waist_trim` | `-0.015` |
| `pants_waist_z` | `1.1` |
| `pants_wall_band` | `0.035` |
| `pants_wall_face` | `0.012` |
| `pants_wall_face_out` | `0.05` |
| `pants_wall_smooth` | `6` |
| `pants_weight_smooth` | `30` |
| `slim_thigh` | `0.93` |
| `slim_z_end` | `1.1` |
| `slim_z_full` | `0.7` |
| `slim_z_in` | `0.35` |
| `slim_z_out` | `1.0` |
| `tight_bands` | `[[0.3, 0.48, 0.05], [0.48, 0.6, 0.04], [0.62, 0.78, 0.035]]` |
| `tight_max_grow` | `0.04` |
| `tight_min_gap` | `0.006` |
| `tight_ramp` | `0.04` |

## Ремень, шлёвки, пряжка

| параметр | значение |
|---|---|
| `belt_lift` | `0.0065` |
| `belt_thick` | `0.002` |
| `belt_tilt_x` | `-0.006` |
| `belt_tilt_y` | `0.003` |
| `belt_wave_r` | `0.5` |
| `belt_wave_z` | `1.0` |
| `belt_z0` | `1.065` |
| `belt_z1` | `1.109` |
| `buckle_color` | `[0.3, 0.25, 0.15]` |
| `buckle_depth` | `0.005` |
| `buckle_h` | `0.042` |
| `buckle_out` | `0.009` |
| `buckle_roll_deg` | `3.0` |
| `buckle_w` | `0.05` |
| `buckle_x_off` | `0.0` |
| `loop_angles` | `[-124.0, -50.0, 2.0, 176.0, 66.0, 116.0]` |
| `loop_h` | `0.068` |
| `loop_lift_end` | `0.001` |
| `loop_lift_mid` | `0.014` |
| `loop_thick` | `0.003` |
| `loop_w` | `0.01` |

## Швы: карманы и ширинка

| параметр | значение |
|---|---|
| `fly_len` | `15.5` |
| `fly_x` | `3.2` |
| `fly_y_top` | `109.0` |
| `pocket_j_deg` | `50.0` |
| `pocket_j_drop` | `17.0` |
| `pocket_j_span` | `38.0` |
| `pocket_lift` | `0.07` |
| `pocket_seam_w` | `1.0` |
| `pocket_wobble` | `0.05` |
| `pocket_y_top` | `109.0` |
| `pocket_zc` | `2.0` |

## Футболка

| параметр | значение |
|---|---|
| `collar_h` | `0.02` |
| `collar_in` | `0.002` |
| `collar_out` | `0.005` |
| `collar_r` | `0.0068` |
| `collar_thick` | `0.012` |
| `shirt_chest_z` | `1.33` |
| `shirt_cover_gap` | `0.001` |
| `shirt_cover_sets` | `["", "_Home"]` |
| `shirt_cover_smooth` | `2` |
| `shirt_ease` | `0.008` |
| `shirt_hem_ease` | `0.012` |
| `shirt_hem_z` | `0.96` |
| `shirt_neck_back` | `[0.082, 1.545]` |
| `shirt_neck_floor` | `1.3` |
| `shirt_neck_front` | `[-0.113, 1.48]` |
| `shirt_neck_side` | `[0.105, 1.54]` |
| `shirt_neck_top` | `1.565` |
| `shirt_neck_w_z` | `1.36` |
| `shirt_pit_anchor` | `[0.205, -0.045, 1.405]` |
| `shirt_pit_ext` | `0.06` |
| `shirt_pit_push` | `0.0` |
| `shirt_pit_r` | `0.1` |
| `shirt_pit_smooth` | `25` |
| `shirt_pit_split` | `false` |
| `shirt_pit_split_x` | `0.2` |
| `shirt_pit_split_z` | `1.45` |
| `shirt_pit_thin` | `0.25` |
| `shirt_pit_thin_r` | `0.11` |
| `shirt_pit_tuck` | `0.005` |
| `shirt_pit_w_iter` | `8` |
| `shirt_pit_w_r` | `0.1` |
| `shirt_pit_w_torso_only` | `false` |
| `shirt_sleeve_ease` | `0.012` |
| `shirt_sleeve_under` | `0.012` |
| `shirt_sleeve_x` | `0.335` |
| `shirt_smooth` | `4` |
| `shirt_straight` | `false` |
| `shirt_thickness` | `0.004` |
| `shirt_waist_z` | `1.17` |

## Обувь: кроссовки

| параметр | значение |
|---|---|
| `lace_jitter` | `0.004` |
| `lace_len_var` | `0.08` |
| `lace_lift_leg` | `0.018` |
| `lace_lift_toe` | `0.006` |
| `lace_line_color` | `[0.03, 0.03, 0.03]` |
| `lace_line_lift` | `0.002` |
| `lace_line_thick` | `0.004` |
| `lace_line_w` | `0.008` |
| `lace_lines` | `3` |
| `lace_tilt_deg` | `6.0` |
| `lace_width` | `0.06` |
| `lace_y` | `[-0.17, -0.03]` |
| `logo_lift` | `0.0015` |
| `logo_run` | `0.04` |
| `logo_thick` | `0.0015` |
| `logo_w` | `0.018` |
| `logo_y` | `-0.02` |
| `logo_z0` | `0.035` |
| `logo_z1` | `0.085` |
| `shoe_color` | `[0.92, 0.92, 0.9]` |
| `shoe_ease` | `0.006` |
| `shoe_min_gap` | `0.0015` |
| `shoe_relax` | `2` |
| `shoe_thickness` | `0.004` |
| `shoe_top_z` | `0.132` |
| `shoe_variants` | `{"Grey": {"upper": ["shoe_grey", [0.42, 0.42, 0.43]], "sole": ["shoe_sole_white", [0.92, 0.92, 0.9]], "lines": ["lace_line_white", [0.92, 0.92, 0.9]], "logo": ["lace_line_white", [0.92, 0.92, 0.9]]}}` |
| `sock` | `false` |
| `sock_color` | `[0.86, 0.86, 0.84]` |
| `sock_ease` | `0.0015` |
| `sock_thickness` | `0.001` |
| `sock_top_z` | `0.135` |
| `sole_color` | `[0.8, 0.8, 0.78]` |
| `sole_height` | `0.025` |
| `sole_out` | `0.003` |
| `sole_smooth` | `3` |
| `sole_step` | `0.006` |

## Тапочки

| параметр | значение |
|---|---|
| `slipper_color` | `[0.06, 0.06, 0.07]` |
| `slipper_edge_side_y` | `-0.085` |
| `slipper_edge_top_y` | `-0.045` |
| `slipper_edge_top_z` | `0.08` |
| `slipper_insole_color` | `[0.36, 0.38, 0.42]` |
| `slipper_insole_h` | `0.004` |
| `slipper_rim_r` | `0.004` |
| `slipper_sole_bevel` | `0.005` |
| `slipper_sole_color` | `[0.14, 0.14, 0.15]` |
| `slipper_sole_height` | `0.015` |
| `slipper_sole_out` | `0.004` |
| `slipper_thickness` | `0.006` |

## Куртка (`jacket_base`, поверх них `jacket_variants.V1.params`)

| параметр | значение |
|---|---|
| `shirt_hem_z` | `0.86` |
| `shirt_sleeve_x` | `0.66` |
| `shirt_ease` | `0.016` |
| `shirt_sleeve_ease` | `0.022` |
| `shirt_sleeve_under` | `0.016` |
| `shirt_hem_ease` | `0.018` |
| `shirt_waist_z` | `1.12` |
| `shirt_chest_z` | `1.3` |
| `shirt_straight` | `false` |
| `shirt_thickness` | `0.005` |
| `shirt_neck_top` | `1.59` |
| `shirt_neck_front` | `[-0.12, 1.5]` |
| `shirt_neck_back` | `[0.09, 1.535]` |
| `shirt_neck_side` | `[0.115, 1.56]` |
| `shirt_neck_floor` | `1.3` |
| `shirt_neck_ease` | `0.01` |
| `shirt_neck_ease_z` | `1.4` |
| `shirt_cover_parts` | `["Shirt", "Pants", "Belt", "Loops", "Buckle", "Waistband", "Cord0", "Cord1"]` |
| `shirt_cover_sets` | `[""]` |
| `shirt_cover_top` | `1.45` |
| `shirt_cover_smooth` | `3` |
| `shirt_collar_stand` | `0.065` |
| `shirt_collar_flare` | `0.012` |
| `shirt_collar_thick` | `0.005` |
| `jacket_crumple` | `0.01` |
| `jacket_crumple_freq` | `10.0` |
| `jacket_fold` | `0.005` |
| `jacket_crumple_seed` | `3.0` |
| `jacket_crumple_fade` | `[1.4, 1.48]` |
| `jacket_placket_w` | `0.04` |
| `jacket_placket_top` | `1.495` |
| `jacket_placket_lift` | `0.0015` |
| `jacket_placket_thick` | `0.003` |
| `jacket_cuff_x0` | `0.6` |
| `jacket_cuff_x1` | `0.66` |
| `jacket_cuff_lift` | `0.0015` |
| `jacket_cuff_thick` | `0.004` |
| `jacket_band_lift` | `0.0015` |
| `jacket_band_thick` | `0.006` |
| `jacket_line_w` | `0.005` |
| `jacket_line_lift` | `0.0012` |
| `jacket_line_jitter` | `0.0008` |
| `jacket_button_r` | `0.007` |
| `jacket_button_lift` | `0.004` |
| `jacket_button_thick` | `0.002` |
| `jacket_hood_z` | `1.6` |
| `jacket_hood_cols` | `15` |
| `jacket_hood_ridge` | `0.02` |
| `jacket_hood_thick` | `0.006` |
| `jacket_hood_rows` | `[[0.0, 0.085, 0.008], [0.03, 0.12, 0.03], [0.07, 0.145, 0.048], [0.12, 0.145, 0.052], [0.17, 0.125, 0.044], [0.22, 0.09, 0.028], [0.255, 0.05, 0.014], [0.27, 0.02, 0.006]]` |
| `jacket_hood_neck_y` | `0.105` |
| `shirt_zones` | `["torso", "arms", "hands", "legs", "head"]` |
| `shirt_collar_front` | `0.55` |
| `jacket_hood_edge` | `0.006` |
| `jacket_pocket_bulge` | `0.006` |
| `jacket_pocket_fold` | `0.004` |
| `jacket_pocket_round` | `0.02` |
| `jacket_zip_top` | `1.47` |
| `jacket_zip_inset` | `0.004` |
| `jacket_zip_w` | `0.007` |
| `jacket_zip_lift` | `0.0015` |
| `jacket_zip_slider` | `[0.012, 0.007, 0.018]` |
| `jacket_zip_tab` | `[0.008, 0.002, 0.02]` |

Вариант V1: `params` {"shirt_front_open": [0.012, 0.045]}; `pockets` [[0.9, 0.995, 0.05, 0.175]]; `look` — cotton/rib цвет ткани, stitch охра, zip чёрный.

## Тело, веса, поза (общие с файлом тела)

| параметр | значение |
|---|---|
| `arm_end_fade` | `0.12` |
| `arm_fix_fade` | `0.22` |
| `arm_fix_from` | `-0.05` |
| `arm_fix_iters` | `0.0` |
| `arm_fix_lambda` | `0.0` |
| `arm_fix_min_arm` | `0.45` |
| `arm_fix_round` | `0.0` |
| `arm_fix_slice` | `0.025` |
| `arm_fix_to` | `0.65` |
| `arm_rebuild_lambda` | `1.2` |
| `arm_rebuild_min_w` | `0.55` |
| `arm_rebuild_polish` | `8` |
| `arm_rebuild_strength` | `1.0` |
| `arm_start_fade` | `0.18` |
| `armpit_iters` | `0.0` |
| `armpit_keep_volume` | `true` |
| `armpit_lambda` | `0.0` |
| `armpit_radius` | `0.0` |
| `armpit_x` | `0.22` |
| `armpit_y` | `0.0` |
| `armpit_z` | `1.375` |
| `back_smooth` | `6` |
| `blade_a` | `0.085` |
| `blade_b` | `0.06` |
| `blade_cx` | `0.1` |
| `blade_cz` | `1.4` |
| `blade_height` | `0.0` |
| `blade_tilt_deg` | `15.0` |
| `cap_drop` | `0.45` |
| `cap_iters` | `30` |
| `cap_keep_volume` | `true` |
| `cap_lambda` | `3.0` |
| `cap_radius` | `0.0` |
| `cap_sphere_radius` | `0.0` |
| `cap_x` | `0.23` |
| `cap_x_fade` | `0.06` |
| `cap_x_max` | `0.4` |
| `cap_y` | `0.02` |
| `crotch_relax_drop` | `0.02` |
| `crotch_relax_iters` | `20` |
| `crotch_relax_lambda` | `2.0` |
| `crotch_relax_radius` | `0.0` |
| `crotch_top` | `0.87` |
| `crotch_w_drop` | `0.015` |
| `crotch_w_rx` | `0.035` |
| `crotch_w_ry` | `0.1` |
| `crotch_w_rz` | `0.0` |
| `crotch_w_smooth` | `8` |
| `crotch_w_strength` | `1.0` |
| `crotch_w_y` | `0.0` |
| `delt_w_arm_band` | `0.01` |
| `delt_w_arm_fade` | `0.07` |
| `delt_w_dx` | `0.04` |
| `delt_w_dy` | `0.0` |
| `delt_w_dz` | `0.035` |
| `delt_w_expand` | `0.15` |
| `delt_w_radius` | `0.0` |
| `delt_w_smooth` | `12` |
| `delt_w_strength` | `1.0` |
| `deltoid_hi` | `0.0` |
| `deltoid_lo` | `0.0` |
| `export_tris` | `20000` |
| `fold_w_dx` | `-0.01` |
| `fold_w_dy` | `0.06` |
| `fold_w_dz` | `0.06` |
| `fold_w_radius` | `0.0` |
| `fold_w_smooth` | `6` |
| `fold_w_strength` | `1.0` |
| `fold_w_xmax` | `0.03` |
| `freeze` | `true` |
| `front_w_dx` | `0.02` |
| `front_w_dy` | `0.05` |
| `front_w_dz` | `0.03` |
| `front_w_expand` | `0.1` |
| `front_w_radius` | `0.0` |
| `front_w_repeat` | `24` |
| `front_w_ymax` | `0.01` |
| `idle_arm_fwd` | `9.0` |
| `idle_arm_out` | `-5.0` |
| `idle_forearm_bend` | `10.0` |
| `idle_free_out` | `0.0` |
| `idle_free_shin` | `0.0` |
| `idle_free_side` | `"R"` |
| `idle_free_thigh` | `0.0` |
| `idle_hand_in` | `10.0` |
| `idle_hip_tilt` | `0.0` |
| `idle_lean_chest` | `8.0` |
| `idle_lean_head` | `6.0` |
| `idle_lean_neck` | `5.0` |
| `idle_lean_spine` | `5.0` |
| `idle_shoulder_down` | `8.0` |
| `idle_shoulder_fwd` | `12.0` |
| `pit_back_depth` | `0.0` |
| `pit_back_rx` | `0.065` |
| `pit_back_ry` | `0.1` |
| `pit_back_rz` | `0.065` |
| `pit_back_x` | `0.225` |
| `pit_back_y` | `0.055` |
| `pit_back_z` | `1.39` |
| `pit_fill_rx` | `0.0` |
| `pit_fill_ry` | `0.06` |
| `pit_fill_rz` | `0.04` |
| `pit_fill_x` | `0.215` |
| `pit_fill_y` | `-0.005` |
| `pit_fill_z` | `1.362` |
| `pit_lower_depth` | `0.0` |
| `pit_lower_rx` | `0.05` |
| `pit_lower_ry` | `0.09` |
| `pit_lower_rz` | `0.035` |
| `pit_lower_x` | `0.225` |
| `pit_lower_y` | `0.0` |
| `pit_lower_z` | `1.385` |
| `rear_delt_dx` | `0.01` |
| `rear_delt_dy` | `0.06` |
| `rear_delt_dz` | `-0.055` |
| `rear_delt_height` | `0.0` |
| `rear_delt_radius` | `0.07` |
| `rear_delt_smooth` | `10` |
| `rear_w_dx` | `0.03` |
| `rear_w_dy` | `0.05` |
| `rear_w_dz` | `0.02` |
| `rear_w_expand` | `0.1` |
| `rear_w_radius` | `0.0` |
| `rear_w_repeat` | `18` |
| `rear_w_ymin` | `0.01` |
| `remesh_polish` | `0.0` |
| `remesh_voxel` | `0.0` |
| `ridge_height` | `0.0` |
| `ridge_width` | `0.015` |
| `ridge_x0` | `0.045` |
| `ridge_x1` | `0.19` |
| `ridge_z0` | `1.455` |
| `ridge_z1` | `1.49` |
| `round_steps` | `8` |
| `shoulder_radius` | `0.0` |
| `slot_bottom` | `0.3` |
| `slot_low_half` | `0.03` |
| `slot_low_z` | `0.62` |
| `slot_top_half` | `0.016` |
| `slouch_down_deg` | `0.0` |
| `slouch_forward_deg` | `0.0` |
| `spine_groove` | `0.0` |
| `spine_width` | `0.024` |
| `weights` | `"orig"` |
| `weights_shoulder_floor` | `0.1` |
| `weights_shoulder_radius` | `0.0` |
| `weights_shoulder_repeat` | `0.0` |
| `weights_smooth_repeat` | `80` |

