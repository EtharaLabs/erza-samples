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
/tests/test_output.py:1161: in test_score_arc_mean_vtec
    assert abs(got - ref) <= tol, \
E   AssertionError: RX-1 SV-K: got 28.84900 TECU, expected 34.61053 TECU (tol 0.05000 TECU)
E   assert 5.761529124463269 <= 0.05
E    +  where 5.761529124463269 = abs((28.849 - 34.61052912446327))
_____________________ test_score_arc_mean_vtec[RX-1-SV-P] ______________________
/tests/test_output.py:1161: in test_score_arc_mean_vtec
    assert abs(got - ref) <= tol, \
E   AssertionError: RX-1 SV-P: got 27.47100 TECU, expected 29.57277 TECU (tol 0.05000 TECU)
E   assert 2.101770604689552 <= 0.05
E    +  where 2.101770604689552 = abs((27.471 - 29.572770604689552))
_____________________ test_score_arc_mean_vtec[RX-1-SV-R] ______________________
/tests/test_output.py:1161: in test_score_arc_mean_vtec
    assert abs(got - ref) <= tol, \
E   AssertionError: RX-1 SV-R: got 3.43400 TECU, expected 23.12946 TECU (tol 0.05000 TECU)
E   assert 19.695462268853344 <= 0.05
E    +  where 19.695462268853344 = abs((3.434 - 23.129462268853345))
_____________________ test_score_arc_mean_vtec[RX-1-SV-W] ______________________
/tests/test_output.py:1161: in test_score_arc_mean_vtec
    assert abs(got - ref) <= tol, \
E   AssertionError: RX-1 SV-W: got 15.99800 TECU, expected 36.72052 TECU (tol 0.05000 TECU)
E   assert 20.722521715185295 <= 0.05
E    +  where 20.722521715185295 = abs((15.998 - 36.72052171518529))
_____________________ test_score_arc_mean_vtec[RX-2-SV-M] ______________________
/tests/test_output.py:1161: in test_score_arc_mean_vtec
    assert abs(got - ref) <= tol, \
E   AssertionError: RX-2 SV-M: got 26.83100 TECU, expected 28.54692 TECU (tol 0.05000 TECU)
E   assert 1.7159178431216482 <= 0.05
E    +  where 1.7159178431216482 = abs((26.831 - 28.546917843121648))
_____________________ test_score_arc_mean_vtec[RX-2-SV-R] ______________________
/tests/test_output.py:1161: in test_score_arc_mean_vtec
    assert abs(got - ref) <= tol, \
E   AssertionError: RX-2 SV-R: got 6.50700 TECU, expected 22.00683 TECU (tol 0.05000 TECU)
E   assert 15.499827220821617 <= 0.05
E    +  where 15.499827220821617 = abs((6.507 - 22.006827220821616))
_____________________ test_score_arc_mean_vtec[RX-2-SV-T] ______________________
/tests/test_output.py:1161: in test_score_arc_mean_vtec
    assert abs(got - ref) <= tol, \
E   AssertionError: RX-2 SV-T: got 28.00900 TECU, expected 24.18029 TECU (tol 0.05000 TECU)
E   assert 3.828712357434572 <= 0.05
E    +  where 3.828712357434572 = abs((28.009 - 24.18028764256543))
_____________________ test_score_arc_mean_vtec[RX-2-SV-W] ______________________
/tests/test_output.py:1161: in test_score_arc_mean_vtec
    assert abs(got - ref) <= tol, \
E   AssertionError: RX-2 SV-W: got -0.05900 TECU, expected 17.79276 TECU (tol 0.05000 TECU)
E   assert 17.85176370902095 <= 0.05
E    +  where 17.85176370902095 = abs((-0.059 - 17.79276370902095))
_____________________ test_score_arc_mean_vtec[RX-3-SV-K] ______________________
/tests/test_output.py:1161: in test_score_arc_mean_vtec
    assert abs(got - ref) <= tol, \
E   AssertionError: RX-3 SV-K: got 36.30800 TECU, expected 21.53369 TECU (tol 0.05000 TECU)
E   assert 14.774309774566206 <= 0.05
E    +  where 14.774309774566206 = abs((36.308 - 21.533690225433794))
_____________________ test_score_arc_mean_vtec[RX-3-SV-M] ______________________
/tests/test_output.py:1161: in test_score_arc_mean_vtec
    assert abs(got - ref) <= tol, \
E   AssertionError: RX-3 SV-M: got 53.58000 TECU, expected 36.22064 TECU (tol 0.05000 TECU)
E   assert 17.359359306892102 <= 0.05
E    +  where 17.359359306892102 = abs((53.58 - 36.220640693107896))
_____________________ test_score_arc_mean_vtec[RX-3-SV-P] ______________________
/tests/test_output.py:1161: in test_score_arc_mean_vtec
    assert abs(got - ref) <= tol, \
E   AssertionError: RX-3 SV-P: got 59.17900 TECU, expected 37.67497 TECU (tol 0.05000 TECU)
E   assert 21.504029660146642 <= 0.05
E    +  where 21.504029660146642 = abs((59.179 - 37.67497033985336))
_____________________ test_score_arc_mean_vtec[RX-3-SV-T] ______________________
/tests/test_output.py:1161: in test_score_arc_mean_vtec
    assert abs(got - ref) <= tol, \
E   AssertionError: RX-3 SV-T: got 44.60500 TECU, expected 20.63799 TECU (tol 0.05000 TECU)
E   assert 23.967013076701317 <= 0.05
E    +  where 23.967013076701317 = abs((44.605 - 20.63798692329868))
------------------ generated xml file: /tmp/erza_junit.DchONa ------------------
=========================== short test summary info ============================
FAILED ::test_score_arc_mean_vtec[RX-1-SV-K] - AssertionError: RX-1 SV-K: got...
FAILED ::test_score_arc_mean_vtec[RX-1-SV-P] - AssertionError: RX-1 SV-P: got...
FAILED ::test_score_arc_mean_vtec[RX-1-SV-R] - AssertionError: RX-1 SV-R: got...
FAILED ::test_score_arc_mean_vtec[RX-1-SV-W] - AssertionError: RX-1 SV-W: got...
FAILED ::test_score_arc_mean_vtec[RX-2-SV-M] - AssertionError: RX-2 SV-M: got...
FAILED ::test_score_arc_mean_vtec[RX-2-SV-R] - AssertionError: RX-2 SV-R: got...
FAILED ::test_score_arc_mean_vtec[RX-2-SV-T] - AssertionError: RX-2 SV-T: got...
FAILED ::test_score_arc_mean_vtec[RX-2-SV-W] - AssertionError: RX-2 SV-W: got...
FAILED ::test_score_arc_mean_vtec[RX-3-SV-K] - AssertionError: RX-3 SV-K: got...
FAILED ::test_score_arc_mean_vtec[RX-3-SV-M] - AssertionError: RX-3 SV-M: got...
FAILED ::test_score_arc_mean_vtec[RX-3-SV-P] - AssertionError: RX-3 SV-P: got...
FAILED ::test_score_arc_mean_vtec[RX-3-SV-T] - AssertionError: RX-3 SV-T: got...
================= 12 failed, 5 passed, 18 deselected in 0.12s ==================
