test cases passed  : 1/18
self-check failures: 0
Score              : 0.0556
============================= test session starts ==============================
platform linux -- Python 3.11.15, pytest-8.3.2, pluggy-1.6.0 -- /usr/local/bin/python3
rootdir: /root
configfile: ../dev/null
plugins: json-ctrf-0.3.5
collecting ... collected 41 items / 14 deselected / 27 selected

::test_score_assigned_value[PTR-01] PASSED                               [  3%]
::test_score_assigned_value[PTR-02] FAILED                               [  7%]
::test_score_assigned_value[PTR-03] FAILED                               [ 11%]
::test_score_assigned_value[PTR-04] FAILED                               [ 14%]
::test_score_assigned_value[PTR-05] FAILED                               [ 18%]
::test_score_assigned_value[PTR-06] FAILED                               [ 22%]
::test_score_robust_scale[PTR-01] FAILED                                 [ 25%]
::test_score_robust_scale[PTR-02] FAILED                                 [ 29%]
::test_score_robust_scale[PTR-03] FAILED                                 [ 33%]
::test_score_robust_scale[PTR-04] FAILED                                 [ 37%]
::test_score_robust_scale[PTR-05] FAILED                                 [ 40%]
::test_score_robust_scale[PTR-06] FAILED                                 [ 44%]
::test_score_zeta_prime[PTR-01] FAILED                                   [ 48%]
::test_score_zeta_prime[PTR-02] FAILED                                   [ 51%]
::test_score_zeta_prime[PTR-03] FAILED                                   [ 55%]
::test_score_zeta_prime[PTR-04] FAILED                                   [ 59%]
::test_score_zeta_prime[PTR-05] FAILED                                   [ 62%]
::test_score_zeta_prime[PTR-06] FAILED                                   [ 66%]
::test_selfcheck_frozen_references_match_a_live_recompute PASSED         [ 70%]
::test_selfcheck_control_routes_are_measured_live_and_clear_two_tolerances PASSED [ 74%]
::test_selfcheck_the_graded_cases_are_separable PASSED                   [ 77%]
::test_selfcheck_isomorphic_invariance_under_relabel_and_rescale PASSED  [ 81%]
::test_selfcheck_tolerances_are_positive_and_bind PASSED                 [ 85%]
::test_selfcheck_house_constants_are_load_bearing PASSED                 [ 88%]
::test_selfcheck_no_reference_value_leaks_into_the_agent_visible_tree PASSED [ 92%]
::test_selfcheck_the_decoy_and_round_guesses_fail_everywhere PASSED      [ 96%]
::test_selfcheck_graded_case_count_is_pinned PASSED                      [100%]

=================================== FAILURES ===================================
______________________ test_score_assigned_value[PTR-02] _______________________
/tests/test_output.py:1162: in test_score_assigned_value
    _graded(item, res)
/tests/test_output.py:1152: in _graded
    assert err <= tol, (
E   AssertionError: PTR-02 assigned_value: got 0.225239, reference 0.223405963, off by 0.00183304 (tol 1.8435e-05, 99.43x)
E   assert 0.0018330370923924921 <= 1.843498250483931e-05
______________________ test_score_assigned_value[PTR-03] _______________________
/tests/test_output.py:1162: in test_score_assigned_value
    _graded(item, res)
/tests/test_output.py:1152: in _graded
    assert err <= tol, (
E   AssertionError: PTR-03 assigned_value: got 12.462101, reference 12.4527557, off by 0.00934525 (tol 0.000360892, 25.89x)
E   assert 0.009345254784317802 <= 0.000360891923453944
______________________ test_score_assigned_value[PTR-04] _______________________
/tests/test_output.py:1162: in test_score_assigned_value
    _graded(item, res)
/tests/test_output.py:1152: in _graded
    assert err <= tol, (
E   AssertionError: PTR-04 assigned_value: got 48.372586, reference 48.2930342, off by 0.0795518 (tol 0.00235889, 33.72x)
E   assert 0.07955181861670724 <= 0.002358892211947516
______________________ test_score_assigned_value[PTR-05] _______________________
/tests/test_output.py:1162: in test_score_assigned_value
    _graded(item, res)
/tests/test_output.py:1152: in _graded
    assert err <= tol, (
E   AssertionError: PTR-05 assigned_value: got 26.547235, reference 26.5400526, off by 0.00718245 (tol 0.000304841, 23.56x)
E   assert 0.007182446833272849 <= 0.0003048408506654346
______________________ test_score_assigned_value[PTR-06] _______________________
/tests/test_output.py:1162: in test_score_assigned_value
    _graded(item, res)
/tests/test_output.py:1152: in _graded
    assert err <= tol, (
E   AssertionError: PTR-06 assigned_value: got 315.52, reference 313.320975, off by 2.19903 (tol 0.0257342, 85.45x)
E   assert 2.199025004632631 <= 0.025734242151229724
_______________________ test_score_robust_scale[PTR-01] ________________________
/tests/test_output.py:1170: in test_score_robust_scale
    _graded(item, res)
/tests/test_output.py:1152: in _graded
    assert err <= tol, (
E   AssertionError: PTR-01 robust_scale: got 0.196057, reference 0.212453447, off by 0.0163964 (tol 0.00212453, 7.72x)
E   assert 0.016396447497649763 <= 0.0021245344749764978
_______________________ test_score_robust_scale[PTR-02] ________________________
/tests/test_output.py:1170: in test_score_robust_scale
    _graded(item, res)
/tests/test_output.py:1152: in _graded
    assert err <= tol, (
E   AssertionError: PTR-02 robust_scale: got 0.012162, reference 0.00921749125, off by 0.00294451 (tol 9.21749e-05, 31.94x)
E   assert 0.002944508747580345 <= 9.217491252419655e-05
_______________________ test_score_robust_scale[PTR-03] ________________________
/tests/test_output.py:1170: in test_score_robust_scale
    _graded(item, res)
/tests/test_output.py:1152: in _graded
    assert err <= tol, (
E   AssertionError: PTR-03 robust_scale: got 0.18937, reference 0.180445962, off by 0.00892404 (tol 0.00180446, 4.95x)
E   assert 0.008924038273028012 <= 0.00180445961726972
_______________________ test_score_robust_scale[PTR-04] ________________________
/tests/test_output.py:1170: in test_score_robust_scale
    _graded(item, res)
/tests/test_output.py:1152: in _graded
    assert err <= tol, (
E   AssertionError: PTR-04 robust_scale: got 1.253619, reference 1.17944611, off by 0.0741729 (tol 0.0117945, 6.29x)
E   assert 0.07417289402624205 <= 0.01179446105973758
_______________________ test_score_robust_scale[PTR-05] ________________________
/tests/test_output.py:1170: in test_score_robust_scale
    _graded(item, res)
/tests/test_output.py:1152: in _graded
    assert err <= tol, (
E   AssertionError: PTR-05 robust_scale: got 0.174903, reference 0.152420425, off by 0.0224826 (tol 0.0015242, 14.75x)
E   assert 0.022482574667282706 <= 0.001524204253327173
_______________________ test_score_robust_scale[PTR-06] ________________________
/tests/test_output.py:1170: in test_score_robust_scale
    _graded(item, res)
/tests/test_output.py:1152: in _graded
    assert err <= tol, (
E   AssertionError: PTR-06 robust_scale: got 16.905426, reference 12.8671211, off by 4.0383 (tol 0.128671, 31.38x)
E   assert 4.038304924385137 <= 0.12867121075614862
________________________ test_score_zeta_prime[PTR-01] _________________________
/tests/test_output.py:1178: in test_score_zeta_prime
    _graded(item, res)
/tests/test_output.py:1152: in _graded
    assert err <= tol, (
E   AssertionError: PTR-01 zeta_prime: got 0.915913, reference 2.73536482, off by 1.81945 (tol 0.02, 90.97x)
E   assert 1.8194518236841992 <= 0.02
________________________ test_score_zeta_prime[PTR-02] _________________________
/tests/test_output.py:1178: in test_score_zeta_prime
    _graded(item, res)
/tests/test_output.py:1152: in _graded
    assert err <= tol, (
E   AssertionError: PTR-02 zeta_prime: got -1.307216, reference -3.44422389, off by 2.13701 (tol 0.02, 106.85x)
E   assert 2.137007888723109 <= 0.02
________________________ test_score_zeta_prime[PTR-03] _________________________
/tests/test_output.py:1178: in test_score_zeta_prime
    _graded(item, res)
/tests/test_output.py:1152: in _graded
    assert err <= tol, (
E   AssertionError: PTR-03 zeta_prime: got 0.34557, reference 2.54553029, off by 2.19996 (tol 0.02, 110.00x)
E   assert 2.1999602870857666 <= 0.02
________________________ test_score_zeta_prime[PTR-04] _________________________
/tests/test_output.py:1178: in test_score_zeta_prime
    _graded(item, res)
/tests/test_output.py:1152: in _graded
    assert err <= tol, (
E   AssertionError: PTR-04 zeta_prime: got 0.732654, reference 2.1122518, off by 1.3796 (tol 0.02, 68.98x)
E   assert 1.3795977957886665 <= 0.02
________________________ test_score_zeta_prime[PTR-05] _________________________
/tests/test_output.py:1178: in test_score_zeta_prime
    _graded(item, res)
/tests/test_output.py:1152: in _graded
    assert err <= tol, (
E   AssertionError: PTR-05 zeta_prime: got 0.855758, reference 3.0268842, off by 2.17113 (tol 0.02, 108.56x)
E   assert 2.171126197065006 <= 0.02
________________________ test_score_zeta_prime[PTR-06] _________________________
/tests/test_output.py:1178: in test_score_zeta_prime
    _graded(item, res)
/tests/test_output.py:1152: in _graded
    assert err <= tol, (
E   AssertionError: PTR-06 zeta_prime: got 1.20186, reference 3.7646675, off by 2.56281 (tol 0.02, 128.14x)
E   assert 2.5628075006130184 <= 0.02
------------------ generated xml file: /tmp/erza_junit.29E2Et ------------------
=========================== short test summary info ============================
FAILED ::test_score_assigned_value[PTR-02] - AssertionError: PTR-02 assigned_...
FAILED ::test_score_assigned_value[PTR-03] - AssertionError: PTR-03 assigned_...
FAILED ::test_score_assigned_value[PTR-04] - AssertionError: PTR-04 assigned_...
FAILED ::test_score_assigned_value[PTR-05] - AssertionError: PTR-05 assigned_...
FAILED ::test_score_assigned_value[PTR-06] - AssertionError: PTR-06 assigned_...
FAILED ::test_score_robust_scale[PTR-01] - AssertionError: PTR-01 robust_scal...
FAILED ::test_score_robust_scale[PTR-02] - AssertionError: PTR-02 robust_scal...
FAILED ::test_score_robust_scale[PTR-03] - AssertionError: PTR-03 robust_scal...
FAILED ::test_score_robust_scale[PTR-04] - AssertionError: PTR-04 robust_scal...
FAILED ::test_score_robust_scale[PTR-05] - AssertionError: PTR-05 robust_scal...
FAILED ::test_score_robust_scale[PTR-06] - AssertionError: PTR-06 robust_scal...
FAILED ::test_score_zeta_prime[PTR-01] - AssertionError: PTR-01 zeta_prime: g...
FAILED ::test_score_zeta_prime[PTR-02] - AssertionError: PTR-02 zeta_prime: g...
FAILED ::test_score_zeta_prime[PTR-03] - AssertionError: PTR-03 zeta_prime: g...
FAILED ::test_score_zeta_prime[PTR-04] - AssertionError: PTR-04 zeta_prime: g...
FAILED ::test_score_zeta_prime[PTR-05] - AssertionError: PTR-05 zeta_prime: g...
FAILED ::test_score_zeta_prime[PTR-06] - AssertionError: PTR-06 zeta_prime: g...
================= 17 failed, 10 passed, 14 deselected in 0.31s =================
