# Test coverage map

Each function's cyclomatic complexity (CC, from `radon cc -s`; it counts `and`/`or`
and conditional expressions, not just `if`) and the tests that cover each of its paths.
Aim: one focused unit test per requirement or distinct path; one smoke test per feature.

## Unit tests (tests/test_units.py)

### lqm2csv.py
| Function | CC | Paths | Tests |
|---|---|---|---|
| `memo_title` | 1 | single path | `test_title_is_memo_id_and_creation_date` |
| `describe_object` + `describe_objects` | 8 + 2 | text; text with no DescRaw; bullet starting a run; bullet continuing a run; bullet with no DescRaw; image with name; image without name; thumbnail; run reset by a non-bullet | `test_text_objects_are_concatenated`, `test_missing_desc_raw_adds_nothing_rather_than_none` (both "no DescRaw" paths), `test_bullet_run_starts_on_new_line_and_each_bullet_ends_one`, `test_new_bullet_run_after_text_starts_on_new_line_again`, `test_image_adds_its_file_name_on_its_own_line`, `test_image_without_file_name_adds_nothing`, `test_thumbnail_is_skipped` |
| `extract_images` | 4 | named image extracted; nameless image skipped; non-image with a FileName skipped | `test_only_named_image_objects_are_extracted_into_memo_id_folder` |
| `convert_memo` | 2 | object list present; object list missing (`or []`) | `test_row_is_title_url_and_text_and_images_go_to_the_given_folder`, `test_memo_without_object_list_gives_empty_text` |
| `convert_folder` | 3 | `.lqm` converted; other file skipped; plus file-format requirements | `test_reads_lqm_files_from_folder_that_is_not_the_cwd`, `test_ignores_files_that_are_not_lqm`, `test_returns_one_file_and_title_pair_per_memo_in_name_order`, `test_rows_end_in_single_crlf_not_doubled_cr`, `test_csv_is_utf8_with_byte_order_mark_for_excel` |
| `main` | 2 | printing only | smoke tests |

### csv2keep.py
| Function | CC | Paths | Tests |
|---|---|---|---|
| `get_email` | 2 | from env; prompted | `test_email_comes_from_environment`, `test_email_is_prompted_for_when_not_in_environment` |
| `get_token` | 3 | keyring; env; prompted | `test_saved_keyring_token_is_used_first`, `test_environment_token_is_used_when_keyring_is_empty`, `test_token_is_prompted_for_last` |
| `login` | 3 | accepted; rejected entered token; rejected keyring token | `test_good_login_saves_token_to_keyring`, `test_rejected_entered_token_stops_with_a_clear_message_and_keeps_keyring`, `test_rejected_keyring_token_is_forgotten` |
| `read_rows` | 2 | expected header (with and without Excel's byte order mark); old header refused | `test_first_data_row_is_not_skipped`, `test_byte_order_mark_from_excel_is_ignored`, `test_csv_from_old_lqm2csv_is_refused_with_rerun_advice` |
| `note_from_row` | 2 | with URL; without | `test_url_goes_on_the_first_line_of_the_text`, `test_no_url_means_text_only` |
| `import_notes` | 3 | no rows; rows below the limit; limit reached | `test_empty_csv_creates_nothing_but_still_syncs`, `test_every_row_becomes_a_note_in_order`, `test_syncs_and_pauses_after_every_rate_limit_notes` |
| `main` | 1 | single path | smoke tests |

## Smoke tests (tests/test_smoke.py)
| Feature | Test |
|---|---|
| Convert .lqm exports to notes.csv + images, import them into Keep, save the token, and reuse it on the next run | `test_memos_are_converted_and_imported_and_rerun_reuses_saved_token` |
| A rejected saved token is removed and the run stops before creating any note | `test_rejected_saved_token_is_removed_and_no_note_is_created` |
| Import syncs and pauses after every `RATE_LIMIT` notes | `test_import_syncs_and_pauses_after_every_rate_limit_notes` |
