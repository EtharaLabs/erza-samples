test cases passed  : 4/4
self-check failures: 0
Score              : 1.0000
pass@1             : 1
============================= test session starts ==============================
platform linux -- Python 3.11.15, pytest-8.3.2, pluggy-1.6.0 -- /usr/local/bin/python3
rootdir: /root
configfile: ../dev/null
plugins: json-ctrf-0.3.5
collecting ... collected 26 items / 14 deselected / 12 selected

::test_reward_all_instruments_present PASSED                             [  8%]
::test_reward_plausible PASSED                                           [ 16%]
::test_reward_year_fraction PASSED                                       [ 25%]
::test_reward_accrued_interest PASSED                                    [ 33%]
::test_selfcheck_golden_recomputes_from_inputs PASSED                    [ 41%]
::test_selfcheck_isomorphic_invariance PASSED                            [ 50%]
::test_selfcheck_degenerate_submission_scores_zero_without_crashing[empty object-payload0] PASSED [ 58%]
::test_selfcheck_degenerate_submission_scores_zero_without_crashing[results not an object-payload1] PASSED [ 66%]
::test_selfcheck_degenerate_submission_scores_zero_without_crashing[missing an instrument-payload2] PASSED [ 75%]
::test_selfcheck_degenerate_submission_scores_zero_without_crashing[wrong types-payload3] PASSED [ 83%]
::test_selfcheck_degenerate_submission_scores_zero_without_crashing[NaN-payload4] PASSED [ 91%]
::test_selfcheck_degenerate_submission_scores_zero_without_crashing[infinity-payload5] PASSED [100%]

------------------ generated xml file: /tmp/erza_junit.wCZtGD ------------------
====================== 12 passed, 14 deselected in 0.08s =======================
