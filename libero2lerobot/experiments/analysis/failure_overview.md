# LIBERO cross-embodiment failure overview (delta replay)

Per-task successful replays / total demos. Tasks sorted by mean success across the 3 strong arms (ur5e/kinova3/iiwa). `n/N`.

## libero_object  (N=10 tasks)

| task | ur5e | kinova3 | iiwa | sawyer |
|---|---|---|---|---|
| pick_up_the_bbq_sauce_and_place_it_in_the_basket | 34/50 | 33/50 | 46/50 | 44/50 |
| pick_up_the_tomato_sauce_and_place_it_in_the_basket | 39/50 | 36/50 | 45/50 | 31/50 |
| pick_up_the_cream_cheese_and_place_it_in_the_basket | 35/50 | 41/50 | 45/50 | 47/50 |
| pick_up_the_milk_and_place_it_in_the_basket | 39/50 | 39/50 | 43/50 | 12/50 |
| pick_up_the_butter_and_place_it_in_the_basket | 35/50 | 41/50 | 46/50 | 26/50 |
| pick_up_the_ketchup_and_place_it_in_the_basket | 40/50 | 40/50 | 43/50 | 30/50 |
| pick_up_the_salad_dressing_and_place_it_in_the_basket | 41/50 | 42/50 | 47/50 | 45/50 |
| pick_up_the_orange_juice_and_place_it_in_the_basket | 41/50 | 45/50 | 46/50 | 44/50 |
| pick_up_the_alphabet_soup_and_place_it_in_the_basket | 47/50 | 43/50 | 46/50 | 21/50 |
| pick_up_the_chocolate_pudding_and_place_it_in_the_basket | 45/50 | 49/50 | 50/50 | 37/50 |

## libero_spatial  (N=10 tasks)

| task | ur5e | kinova3 | iiwa | sawyer |
|---|---|---|---|---|
| pick_up_the_black_bowl_in_the_top_drawer_of_the_wooden_ca... | 22/50 | 8/50 | 34/50 | 0/50 |
| pick_up_the_black_bowl_on_the_stove_and_place_it_on_the_p... | 26/50 | 14/50 | 36/50 | 0/50 |
| pick_up_the_black_bowl_next_to_the_cookie_box_and_place_i... | 1/50 | 37/50 | 41/50 | 0/50 |
| pick_up_the_black_bowl_on_the_ramekin_and_place_it_on_the... | 26/50 | 22/50 | 38/50 | 30/50 |
| pick_up_the_black_bowl_next_to_the_ramekin_and_place_it_o... | 36/50 | 29/50 | 40/50 | 2/50 |
| pick_up_the_black_bowl_on_the_wooden_cabinet_and_place_it... | 37/50 | 29/50 | 43/50 | 0/50 |
| pick_up_the_black_bowl_from_table_center_and_place_it_on_... | 41/50 | 23/50 | 46/50 | 1/50 |
| pick_up_the_black_bowl_between_the_plate_and_the_ramekin_... | 38/50 | 29/50 | 44/50 | 22/50 |
| pick_up_the_black_bowl_next_to_the_plate_and_place_it_on_... | 44/50 | 30/50 | 42/50 | 25/50 |
| pick_up_the_black_bowl_on_the_cookie_box_and_place_it_on_... | 39/50 | 34/50 | 44/50 | 0/50 |

## libero_goal  (N=10 tasks)

| task | ur5e | kinova3 | iiwa | sawyer |
|---|---|---|---|---|
| push_the_plate_to_the_front_of_the_stove | 0/50 | 3/50 | 6/50 | 0/50 |
| open_the_top_drawer_and_put_the_bowl_inside | 27/50 | 8/50 | 32/50 | 0/50 |
| open_the_middle_drawer_of_the_cabinet | 19/50 | 33/50 | 38/50 | 0/50 |
| put_the_wine_bottle_on_the_rack | 14/50 | 37/50 | 41/50 | 0/50 |
| put_the_cream_cheese_in_the_bowl | 35/50 | 38/50 | 38/50 | 0/50 |
| put_the_wine_bottle_on_top_of_the_cabinet | 40/50 | 34/50 | 41/50 | 0/50 |
| put_the_bowl_on_the_plate | 47/50 | 43/50 | 49/50 | 0/50 |
| put_the_bowl_on_the_stove | 45/50 | 45/50 | 50/50 | 4/50 |
| turn_on_the_stove | 48/50 | 49/50 | 43/50 | 36/50 |
| put_the_bowl_on_top_of_the_cabinet | 49/50 | 48/50 | 46/50 | 0/50 |

## libero_10  (N=10 tasks)

| task | ur5e | kinova3 | iiwa | sawyer |
|---|---|---|---|---|
| put_the_black_bowl_in_the_bottom_drawer_of_the_cabinet_an... | 0/50 | 0/50 | 0/50 | 0/50 |
| put_the_white_mug_on_the_plate_and_put_the_chocolate_pudd... | 0/50 | 0/50 | 0/50 | 0/50 |
| put_both_moka_pots_on_the_stove | 0/50 | 0/50 | 0/50 | 0/50 |
| put_the_yellow_and_white_mug_in_the_microwave_and_close_it | 0/50 | 0/50 | 0/50 | 0/50 |
| put_both_the_alphabet_soup_and_the_tomato_sauce_in_the_ba... | 17/50 | 19/50 | 26/50 | 0/50 |
| put_the_white_mug_on_the_left_plate_and_put_the_yellow_an... | 26/50 | 18/50 | 28/50 | 0/50 |
| turn_on_the_stove_and_put_the_moka_pot_on_it | 28/50 | 35/50 | 35/50 | 0/50 |
| put_both_the_alphabet_soup_and_the_cream_cheese_box_in_th... | 31/50 | 32/50 | 35/50 | 0/50 |
| pick_up_the_book_and_place_it_in_the_back_compartment_of_... | 27/50 | 42/50 | 39/50 | 1/50 |
| put_both_the_cream_cheese_box_and_the_butter_in_the_basket | 43/50 | 32/50 | 41/50 | 0/50 |

## libero_90  (N=74 tasks)

| task | ur5e | kinova3 | iiwa | sawyer |
|---|---|---|---|---|
| put_the_black_bowl_in_the_bottom_drawer_of_the_cabinet | 0/50 | 0/50 | 0/50 | 0/50 |
| put_the_wine_bottle_in_the_bottom_drawer_of_the_cabinet | 0/50 | 0/50 | 0/50 | 0/50 |
| put_the_right_moka_pot_on_the_stove | 0/50 | 0/50 | 0/50 | 0/50 |
| pick_up_the_butter_and_put_it_in_the_basket | 0/50 | 0/50 | 0/50 | 0/50 |
| put_the_chocolate_pudding_to_the_left_of_the_plate | 0/50 | 0/50 | 0/50 | 0/50 |
| put_the_chocolate_pudding_to_the_right_of_the_plate | 0/50 | 0/50 | 0/50 | 0/50 |
| pick_up_the_book_on_the_left_and_place_it_on_top_of_the_s... | 5/50 | 3/50 | 6/50 | 0/50 |
| close_the_bottom_drawer_of_the_cabinet_and_open_the_top_d... | 14/50 | 16/50 | 20/50 | 0/50 |
| pick_up_the_yellow_and_white_mug_and_place_it_to_the_righ... | 21/50 | 11/50 | 29/50 | 0/50 |
| put_the_black_bowl_at_the_back_on_the_plate | 16/50 | 15/50 | 35/50 | 0/50 |
| put_the_red_mug_on_the_left_plate | 33/50 | 26/50 | 7/50 | 0/50 |
| pick_up_the_book_and_place_it_in_the_right_compartment_of... | 24/50 | 21/50 | 22/50 | 0/50 |
| put_the_ketchup_in_the_top_drawer_of_the_cabinet | 21/50 | 23/50 | 24/50 | 0/50 |
| stack_the_right_bowl_on_the_left_bowl_and_place_them_in_t... | 24/50 | 18/50 | 27/50 | 0/50 |
| pick_up_the_book_and_place_it_in_the_front_compartment_of... | 20/50 | 21/50 | 29/50 | 0/50 |
| pick_up_the_salad_dressing_and_put_it_in_the_tray | 27/50 | 45/50 | 0/50 | 0/50 |
| put_the_red_mug_on_the_right_plate | 41/50 | 26/50 | 7/50 | 0/50 |
| open_the_top_drawer_of_the_cabinet_and_put_the_bowl_in_it | 10/50 | 30/50 | 37/50 | 0/50 |
| put_the_wine_bottle_on_the_wine_rack | 18/50 | 24/50 | 35/50 | 0/50 |
| put_the_red_mug_on_the_plate | 42/50 | 34/50 | 3/50 | 8/50 |
| pick_up_the_ketchup_and_put_it_in_the_tray | 39/50 | 40/50 | 1/50 | 0/50 |
| stack_the_left_bowl_on_the_right_bowl_and_place_them_in_t... | 18/50 | 23/50 | 39/50 | 0/50 |
| put_the_chocolate_pudding_in_the_top_drawer_of_the_cabine... | 2/50 | 42/50 | 45/50 | 0/50 |
| open_the_bottom_drawer_of_the_cabinet | 17/50 | 30/50 | 45/50 | 2/50 |
| turn_off_the_stove | 22/50 | 33/50 | 38/50 | 1/50 |
| put_the_frying_pan_on_top_of_the_cabinet | 28/50 | 24/50 | 43/50 | 1/50 |
| pick_up_the_book_and_place_it_in_the_back_compartment_of_... | 32/50 | 32/50 | 33/50 | 0/50 |
| stack_the_middle_black_bowl_on_the_back_black_bowl | 33/50 | 24/50 | 43/50 | 0/50 |
| put_the_frying_pan_on_the_cabinet_shelf | 36/50 | 26/50 | 39/50 | 0/50 |
| close_the_top_drawer_of_the_cabinet_and_put_the_black_bow... | 37/50 | 25/50 | 40/50 | 0/50 |
| stack_the_black_bowl_at_the_front_on_the_black_bowl_in_th... | 40/50 | 19/50 | 43/50 | 10/50 |
| put_the_yellow_and_white_mug_to_the_front_of_the_white_mug | 33/50 | 30/50 | 42/50 | 0/50 |
| turn_on_the_stove_and_put_the_frying_pan_on_it | 31/50 | 34/50 | 41/50 | 0/50 |
| put_the_black_bowl_at_the_front_on_the_plate | 38/50 | 27/50 | 42/50 | 9/50 |
| put_the_frying_pan_under_the_cabinet_shelf | 36/50 | 29/50 | 43/50 | 0/50 |
| pick_up_the_red_mug_and_place_it_to_the_right_of_the_caddy | 44/50 | 22/50 | 42/50 | 27/50 |
| open_the_microwave | 41/50 | 31/50 | 37/50 | 0/50 |
| put_the_frying_pan_on_the_stove | 35/50 | 32/50 | 44/50 | 0/50 |
| pick_up_the_orange_juice_and_put_it_in_the_basket | 38/50 | 38/50 | 35/50 | 0/50 |
| put_the_white_mug_on_the_left_plate | 38/50 | 31/50 | 42/50 | 0/50 |
| put_the_white_bowl_on_the_plate | 40/50 | 33/50 | 39/50 | 0/50 |
| put_the_black_bowl_on_the_plate | 35/50 | 37/50 | 42/50 | 0/50 |
| put_the_moka_pot_on_the_stove | 35/50 | 34/50 | 46/50 | 0/50 |
| put_the_white_bowl_to_the_right_of_the_plate | 35/50 | 40/50 | 40/50 | 0/50 |
| put_the_yellow_and_white_mug_on_the_right_plate | 42/50 | 27/50 | 46/50 | 0/50 |
| pick_up_the_ketchup_and_put_it_in_the_basket | 41/50 | 45/50 | 31/50 | 0/50 |
| pick_up_the_white_mug_and_place_it_to_the_right_of_the_caddy | 37/50 | 44/50 | 36/50 | 0/50 |
| close_the_bottom_drawer_of_the_cabinet | 34/50 | 43/50 | 43/50 | 1/50 |
| put_the_white_mug_on_the_plate | 38/50 | 39/50 | 43/50 | 0/50 |
| pick_up_the_book_on_the_right_and_place_it_under_the_cabi... | 38/50 | 38/50 | 44/50 | 0/50 |
| pick_up_the_alphabet_soup_and_put_it_in_the_basket | 38/50 | 40/50 | 45/50 | 0/50 |
| pick_up_the_milk_and_put_it_in_the_basket | 43/50 | 39/50 | 43/50 | 0/50 |
| pick_up_the_book_in_the_middle_and_place_it_on_the_cabine... | 42/50 | 40/50 | 45/50 | 0/50 |
| pick_up_the_alphabet_soup_and_put_it_in_the_tray | 40/50 | 46/50 | 43/50 | 0/50 |
| put_the_white_bowl_on_top_of_the_cabinet | 44/50 | 40/50 | 46/50 | 0/50 |
| pick_up_the_tomato_sauce_and_put_it_in_the_tray | 45/50 | 38/50 | 48/50 | 2/50 |
| put_the_black_bowl_on_top_of_the_cabinet | 43/50 | 43/50 | 48/50 | 0/50 |
| put_the_butter_at_the_front_in_the_top_drawer_of_the_cabi... | 44/50 | 45/50 | 46/50 | 0/50 |
| pick_up_the_book_and_place_it_in_the_left_compartment_of_... | 42/50 | 45/50 | 48/50 | 0/50 |
| pick_up_the_book_on_the_right_and_place_it_on_the_cabinet... | 45/50 | 44/50 | 46/50 | 0/50 |
| put_the_butter_at_the_back_in_the_top_drawer_of_the_cabin... | 47/50 | 43/50 | 46/50 | 0/50 |
| open_the_top_drawer_of_the_cabinet | 39/50 | 49/50 | 48/50 | 0/50 |
| put_the_black_bowl_in_the_top_drawer_of_the_cabinet | 46/50 | 42/50 | 49/50 | 0/50 |
| pick_up_the_cream_cheese_box_and_put_it_in_the_basket | 46/50 | 45/50 | 46/50 | 0/50 |
| pick_up_the_tomato_sauce_and_put_it_in_the_basket | 48/50 | 43/50 | 48/50 | 0/50 |
| pick_up_the_black_bowl_on_the_left_and_put_it_in_the_tray | 45/50 | 46/50 | 48/50 | 0/50 |
| put_the_middle_black_bowl_on_top_of_the_cabinet | 47/50 | 45/50 | 48/50 | 0/50 |
| pick_up_the_butter_and_put_it_in_the_tray | 46/50 | 46/50 | 49/50 | 0/50 |
| pick_up_the_cream_cheese_and_put_it_in_the_tray | 47/50 | 47/50 | 48/50 | 0/50 |
| pick_up_the_chocolate_pudding_and_put_it_in_the_tray | 49/50 | 46/50 | 47/50 | 0/50 |
| put_the_middle_black_bowl_on_the_plate | 49/50 | 45/50 | 49/50 | 6/50 |
| close_the_top_drawer_of_the_cabinet | 47/50 | 50/50 | 49/50 | 14/50 |
| turn_on_the_stove | 50/50 | 47/50 | 49/50 | 41/50 |
| close_the_microwave | 48/50 | 49/50 | 49/50 | 44/50 |
