test cases passed  : 25/25
self-check failures: 0
Score              : 1.0000
============================= test session starts ==============================
platform linux -- Python 3.11.15, pytest-8.3.2, pluggy-1.6.0 -- /usr/local/bin/python3
rootdir: /root
configfile: ../dev/null
plugins: json-ctrf-0.3.5
collecting ... collected 57 items / 19 deselected / 38 selected

::test_score_local_magnitude_network[wa_peak_amplitude_mm[ST01]] PASSED  [  2%]
::test_score_local_magnitude_network[wa_peak_amplitude_mm[ST02]] PASSED  [  5%]
::test_score_local_magnitude_network[wa_peak_amplitude_mm[ST03]] PASSED  [  7%]
::test_score_local_magnitude_network[wa_peak_amplitude_mm[ST04]] PASSED  [ 10%]
::test_score_local_magnitude_network[wa_peak_amplitude_mm[ST05]] PASSED  [ 13%]
::test_score_local_magnitude_network[wa_peak_amplitude_mm[ST06]] PASSED  [ 15%]
::test_score_local_magnitude_network[wa_peak_amplitude_mm[ST07]] PASSED  [ 18%]
::test_score_local_magnitude_network[wa_peak_amplitude_mm[ST08]] PASSED  [ 21%]
::test_score_local_magnitude_network[hypocentral_distance_km[ST01]] PASSED [ 23%]
::test_score_local_magnitude_network[hypocentral_distance_km[ST02]] PASSED [ 26%]
::test_score_local_magnitude_network[hypocentral_distance_km[ST03]] PASSED [ 28%]
::test_score_local_magnitude_network[hypocentral_distance_km[ST04]] PASSED [ 31%]
::test_score_local_magnitude_network[hypocentral_distance_km[ST05]] PASSED [ 34%]
::test_score_local_magnitude_network[hypocentral_distance_km[ST06]] PASSED [ 36%]
::test_score_local_magnitude_network[hypocentral_distance_km[ST07]] PASSED [ 39%]
::test_score_local_magnitude_network[hypocentral_distance_km[ST08]] PASSED [ 42%]
::test_score_local_magnitude_network[local_magnitude_ml[ST01]] PASSED    [ 44%]
::test_score_local_magnitude_network[local_magnitude_ml[ST02]] PASSED    [ 47%]
::test_score_local_magnitude_network[local_magnitude_ml[ST03]] PASSED    [ 50%]
::test_score_local_magnitude_network[local_magnitude_ml[ST04]] PASSED    [ 52%]
::test_score_local_magnitude_network[local_magnitude_ml[ST05]] PASSED    [ 55%]
::test_score_local_magnitude_network[local_magnitude_ml[ST06]] PASSED    [ 57%]
::test_score_local_magnitude_network[local_magnitude_ml[ST07]] PASSED    [ 60%]
::test_score_local_magnitude_network[local_magnitude_ml[ST08]] PASSED    [ 63%]
::test_score_local_magnitude_network[network_local_magnitude_ml] PASSED  [ 65%]
::test_selfcheck_wood_anderson_calibration PASSED                        [ 68%]
::test_selfcheck_frozen_references_match_live_recompute PASSED           [ 71%]
::test_selfcheck_tolerances_are_positive_and_bind PASSED                 [ 73%]
::test_selfcheck_control_paths_are_measured_live PASSED                  [ 76%]
::test_selfcheck_closed_form_gaps_are_independently_predicted PASSED     [ 78%]
::test_selfcheck_blessed_conventions_do_not_false_fail PASSED            [ 81%]
::test_selfcheck_separable_units PASSED                                  [ 84%]
::test_selfcheck_isomorphic_invariance PASSED                            [ 86%]
::test_selfcheck_there_is_nothing_to_recall PASSED                       [ 89%]
::test_selfcheck_the_chain_is_one_implementation PASSED                  [ 92%]
::test_selfcheck_references_are_physically_plausible PASSED              [ 94%]
::test_selfcheck_the_velocity_form_is_separated PASSED                   [ 97%]
::test_selfcheck_graded_case_count_is_pinned PASSED                      [100%]

=============================== warnings summary ===============================
::test_score_local_magnitude_network[wa_peak_amplitude_mm[ST01]]
  /usr/local/lib/python3.11/site-packages/obspy/core/util/base.py:26: DeprecationWarning: pkg_resources is deprecated as an API. See https://setuptools.pypa.io/en/latest/pkg_resources.html
    import pkg_resources

-- Docs: https://docs.pytest.org/en/stable/how-to/capture-warnings.html
------------------ generated xml file: /tmp/erza_junit.g6ydpi ------------------
================= 38 passed, 19 deselected, 1 warning in 5.45s =================
