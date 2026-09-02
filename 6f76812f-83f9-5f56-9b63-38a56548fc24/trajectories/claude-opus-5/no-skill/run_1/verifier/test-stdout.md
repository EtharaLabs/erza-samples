test cases passed  : 0/12
self-check failures: 0
Score              : 0.0000
============================= test session starts ==============================
platform linux -- Python 3.11.15, pytest-8.3.4, pluggy-1.6.0 -- /usr/local/bin/python3
rootdir: /root
configfile: ../dev/null
collecting ... collected 35 items / 18 deselected / 17 selected

::test_score_arc_mean_vtec[RX-1-SV-K] FAILED                             [  5%]
::test_score_arc_mean_vtec[RX-1-SV-P] FAILED                             [ 11%]
::test_score_arc_mean_vtec[RX-1-SV-R] FAILED                             [ 17%]
::test_score_arc_mean_vtec[RX-1-SV-W] FAILED                             [ 23%]
::test_score_arc_mean_vtec[RX-2-SV-M] FAILED                             [ 29%]
::test_score_arc_mean_vtec[RX-2-SV-R] FAILED                             [ 35%]
::test_score_arc_mean_vtec[RX-2-SV-T] FAILED                             [ 41%]
::test_score_arc_mean_vtec[RX-2-SV-W] FAILED                             [ 47%]
::test_score_arc_mean_vtec[RX-3-SV-K] FAILED                             [ 52%]
::test_score_arc_mean_vtec[RX-3-SV-M] FAILED                             [ 58%]
::test_score_arc_mean_vtec[RX-3-SV-P] FAILED                             [ 64%]
::test_score_arc_mean_vtec[RX-3-SV-T] FAILED                             [ 70%]
::test_selfcheck_frozen_reference_matches_live_recompute PASSED          [ 76%]
::test_selfcheck_plausibility_and_guess_resistance PASSED                [ 82%]
::test_selfcheck_isomorphic_invariance_under_relabel_and_rescale PASSED  [ 88%]
::test_selfcheck_tolerances_are_positive_and_bind PASSED                 [ 94%]
::test_selfcheck_graded_case_count_is_pinned PASSED                      [100%]

=================================== FAILURES ===================================
_____________________ test_score_arc_mean_vtec[RX-1-SV-K] ______________________
/tests/test_output.py:1147: in test_score_arc_mean_vtec
    results = _load_results()
/tests/test_output.py:1097: in _load_results
    assert os.path.exists(RESULTS_PATH), "%s does not exist" % RESULTS_PATH
E   AssertionError: /root/results.json does not exist
E   assert False
E    +  where False = <function exists at 0xffffb41339c0>('/root/results.json')
E    +    where <function exists at 0xffffb41339c0> = <module 'posixpath' (frozen)>.exists
E    +      where <module 'posixpath' (frozen)> = os.path
_____________________ test_score_arc_mean_vtec[RX-1-SV-P] ______________________
/tests/test_output.py:1147: in test_score_arc_mean_vtec
    results = _load_results()
/tests/test_output.py:1097: in _load_results
    assert os.path.exists(RESULTS_PATH), "%s does not exist" % RESULTS_PATH
E   AssertionError: /root/results.json does not exist
E   assert False
E    +  where False = <function exists at 0xffffb41339c0>('/root/results.json')
E    +    where <function exists at 0xffffb41339c0> = <module 'posixpath' (frozen)>.exists
E    +      where <module 'posixpath' (frozen)> = os.path
_____________________ test_score_arc_mean_vtec[RX-1-SV-R] ______________________
/tests/test_output.py:1147: in test_score_arc_mean_vtec
    results = _load_results()
/tests/test_output.py:1097: in _load_results
    assert os.path.exists(RESULTS_PATH), "%s does not exist" % RESULTS_PATH
E   AssertionError: /root/results.json does not exist
E   assert False
E    +  where False = <function exists at 0xffffb41339c0>('/root/results.json')
E    +    where <function exists at 0xffffb41339c0> = <module 'posixpath' (frozen)>.exists
E    +      where <module 'posixpath' (frozen)> = os.path
_____________________ test_score_arc_mean_vtec[RX-1-SV-W] ______________________
/tests/test_output.py:1147: in test_score_arc_mean_vtec
    results = _load_results()
/tests/test_output.py:1097: in _load_results
    assert os.path.exists(RESULTS_PATH), "%s does not exist" % RESULTS_PATH
E   AssertionError: /root/results.json does not exist
E   assert False
E    +  where False = <function exists at 0xffffb41339c0>('/root/results.json')
E    +    where <function exists at 0xffffb41339c0> = <module 'posixpath' (frozen)>.exists
E    +      where <module 'posixpath' (frozen)> = os.path
_____________________ test_score_arc_mean_vtec[RX-2-SV-M] ______________________
/tests/test_output.py:1147: in test_score_arc_mean_vtec
    results = _load_results()
/tests/test_output.py:1097: in _load_results
    assert os.path.exists(RESULTS_PATH), "%s does not exist" % RESULTS_PATH
E   AssertionError: /root/results.json does not exist
E   assert False
E    +  where False = <function exists at 0xffffb41339c0>('/root/results.json')
E    +    where <function exists at 0xffffb41339c0> = <module 'posixpath' (frozen)>.exists
E    +      where <module 'posixpath' (frozen)> = os.path
_____________________ test_score_arc_mean_vtec[RX-2-SV-R] ______________________
/tests/test_output.py:1147: in test_score_arc_mean_vtec
    results = _load_results()
/tests/test_output.py:1097: in _load_results
    assert os.path.exists(RESULTS_PATH), "%s does not exist" % RESULTS_PATH
E   AssertionError: /root/results.json does not exist
E   assert False
E    +  where False = <function exists at 0xffffb41339c0>('/root/results.json')
E    +    where <function exists at 0xffffb41339c0> = <module 'posixpath' (frozen)>.exists
E    +      where <module 'posixpath' (frozen)> = os.path
_____________________ test_score_arc_mean_vtec[RX-2-SV-T] ______________________
/tests/test_output.py:1147: in test_score_arc_mean_vtec
    results = _load_results()
/tests/test_output.py:1097: in _load_results
    assert os.path.exists(RESULTS_PATH), "%s does not exist" % RESULTS_PATH
E   AssertionError: /root/results.json does not exist
E   assert False
E    +  where False = <function exists at 0xffffb41339c0>('/root/results.json')
E    +    where <function exists at 0xffffb41339c0> = <module 'posixpath' (frozen)>.exists
E    +      where <module 'posixpath' (frozen)> = os.path
_____________________ test_score_arc_mean_vtec[RX-2-SV-W] ______________________
/tests/test_output.py:1147: in test_score_arc_mean_vtec
    results = _load_results()
/tests/test_output.py:1097: in _load_results
    assert os.path.exists(RESULTS_PATH), "%s does not exist" % RESULTS_PATH
E   AssertionError: /root/results.json does not exist
E   assert False
E    +  where False = <function exists at 0xffffb41339c0>('/root/results.json')
E    +    where <function exists at 0xffffb41339c0> = <module 'posixpath' (frozen)>.exists
E    +      where <module 'posixpath' (frozen)> = os.path
_____________________ test_score_arc_mean_vtec[RX-3-SV-K] ______________________
/tests/test_output.py:1147: in test_score_arc_mean_vtec
    results = _load_results()
/tests/test_output.py:1097: in _load_results
    assert os.path.exists(RESULTS_PATH), "%s does not exist" % RESULTS_PATH
E   AssertionError: /root/results.json does not exist
E   assert False
E    +  where False = <function exists at 0xffffb41339c0>('/root/results.json')
E    +    where <function exists at 0xffffb41339c0> = <module 'posixpath' (frozen)>.exists
E    +      where <module 'posixpath' (frozen)> = os.path
_____________________ test_score_arc_mean_vtec[RX-3-SV-M] ______________________
/tests/test_output.py:1147: in test_score_arc_mean_vtec
    results = _load_results()
/tests/test_output.py:1097: in _load_results
    assert os.path.exists(RESULTS_PATH), "%s does not exist" % RESULTS_PATH
E   AssertionError: /root/results.json does not exist
E   assert False
E    +  where False = <function exists at 0xffffb41339c0>('/root/results.json')
E    +    where <function exists at 0xffffb41339c0> = <module 'posixpath' (frozen)>.exists
E    +      where <module 'posixpath' (frozen)> = os.path
_____________________ test_score_arc_mean_vtec[RX-3-SV-P] ______________________
/tests/test_output.py:1147: in test_score_arc_mean_vtec
    results = _load_results()
/tests/test_output.py:1097: in _load_results
    assert os.path.exists(RESULTS_PATH), "%s does not exist" % RESULTS_PATH
E   AssertionError: /root/results.json does not exist
E   assert False
E    +  where False = <function exists at 0xffffb41339c0>('/root/results.json')
E    +    where <function exists at 0xffffb41339c0> = <module 'posixpath' (frozen)>.exists
E    +      where <module 'posixpath' (frozen)> = os.path
_____________________ test_score_arc_mean_vtec[RX-3-SV-T] ______________________
/tests/test_output.py:1147: in test_score_arc_mean_vtec
    results = _load_results()
/tests/test_output.py:1097: in _load_results
    assert os.path.exists(RESULTS_PATH), "%s does not exist" % RESULTS_PATH
E   AssertionError: /root/results.json does not exist
E   assert False
E    +  where False = <function exists at 0xffffb41339c0>('/root/results.json')
E    +    where <function exists at 0xffffb41339c0> = <module 'posixpath' (frozen)>.exists
E    +      where <module 'posixpath' (frozen)> = os.path
------------------ generated xml file: /tmp/erza_junit.z3GU14 ------------------
=========================== short test summary info ============================
FAILED ::test_score_arc_mean_vtec[RX-1-SV-K] - AssertionError: /root/results....
FAILED ::test_score_arc_mean_vtec[RX-1-SV-P] - AssertionError: /root/results....
FAILED ::test_score_arc_mean_vtec[RX-1-SV-R] - AssertionError: /root/results....
FAILED ::test_score_arc_mean_vtec[RX-1-SV-W] - AssertionError: /root/results....
FAILED ::test_score_arc_mean_vtec[RX-2-SV-M] - AssertionError: /root/results....
FAILED ::test_score_arc_mean_vtec[RX-2-SV-R] - AssertionError: /root/results....
FAILED ::test_score_arc_mean_vtec[RX-2-SV-T] - AssertionError: /root/results....
FAILED ::test_score_arc_mean_vtec[RX-2-SV-W] - AssertionError: /root/results....
FAILED ::test_score_arc_mean_vtec[RX-3-SV-K] - AssertionError: /root/results....
FAILED ::test_score_arc_mean_vtec[RX-3-SV-M] - AssertionError: /root/results....
FAILED ::test_score_arc_mean_vtec[RX-3-SV-P] - AssertionError: /root/results....
FAILED ::test_score_arc_mean_vtec[RX-3-SV-T] - AssertionError: /root/results....
================= 12 failed, 5 passed, 18 deselected in 0.14s ==================
