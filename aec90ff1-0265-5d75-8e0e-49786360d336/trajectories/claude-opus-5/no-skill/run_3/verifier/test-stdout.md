test cases passed  : 2/4
self-check failures: 0
Score              : 0.5000
pass@1             : 0
============================= test session starts ==============================
platform linux -- Python 3.11.15, pytest-8.3.2, pluggy-1.6.0 -- /usr/local/bin/python3
rootdir: /root
configfile: ../dev/null
plugins: json-ctrf-0.3.5
collecting ... collected 26 items / 14 deselected / 12 selected

::test_reward_all_instruments_present PASSED                             [  8%]
::test_reward_plausible PASSED                                           [ 16%]
::test_reward_year_fraction FAILED                                       [ 25%]
::test_reward_accrued_interest FAILED                                    [ 33%]
::test_selfcheck_golden_recomputes_from_inputs PASSED                    [ 41%]
::test_selfcheck_isomorphic_invariance PASSED                            [ 50%]
::test_selfcheck_degenerate_submission_scores_zero_without_crashing[empty object-payload0] PASSED [ 58%]
::test_selfcheck_degenerate_submission_scores_zero_without_crashing[results not an object-payload1] PASSED [ 66%]
::test_selfcheck_degenerate_submission_scores_zero_without_crashing[missing an instrument-payload2] PASSED [ 75%]
::test_selfcheck_degenerate_submission_scores_zero_without_crashing[wrong types-payload3] PASSED [ 83%]
::test_selfcheck_degenerate_submission_scores_zero_without_crashing[NaN-payload4] PASSED [ 91%]
::test_selfcheck_degenerate_submission_scores_zero_without_crashing[infinity-payload5] PASSED [100%]

=================================== FAILURES ===================================
__________________________ test_reward_year_fraction ___________________________
/tests/test_pytest.py:1043: in test_reward_year_fraction
    assert err <= tol, f"{k} year_fraction {got:.12f} off ref {ref['year_fraction']:.12f} by {err:.3e} (tol {tol})"
E   AssertionError: INST01 year_fraction 0.505555555556 off ref 0.500000000000 by 5.556e-03 (tol 1e-10)
E   assert 0.005555555555555536 <= 1e-10
_________________________ test_reward_accrued_interest _________________________
/tests/test_pytest.py:1053: in test_reward_accrued_interest
    assert err <= tol, f"{k} accrued_interest {got:.8f} off ref {ref['accrued_interest']:.8f} by {err:.3e} (tol {tol})"
E   AssertionError: INST01 accrued_interest 25277.77777778 off ref 25000.00000000 by 2.778e+02 (tol 1e-08)
E   assert 277.7777777777774 <= 1e-08
------------------ generated xml file: /tmp/erza_junit.4nK9Xo ------------------
=========================== short test summary info ============================
FAILED ::test_reward_year_fraction - AssertionError: INST01 year_fraction 0.5...
FAILED ::test_reward_accrued_interest - AssertionError: INST01 accrued_intere...
================= 2 failed, 10 passed, 14 deselected in 0.04s ==================
