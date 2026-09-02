test cases passed : 0/12
Score             : 0.0000
pass@1            : 0
E    +  where 7.948465290979051 = abs((25.741229 - 17.79276370902095))
________________________ test_arc_mean_vtec[RX-3-SV-K] _________________________
/tests/test_outputs.py:93: in test_arc_mean_vtec
    assert abs(got - ref) <= tol, \
E   AssertionError: RX-3 SV-K: got 39.40803 TECU, expected 21.53369 TECU (tol 0.05000 TECU)
E   assert 17.874341774566204 <= 0.05
E    +  where 17.874341774566204 = abs((39.408032 - 21.533690225433794))
________________________ test_arc_mean_vtec[RX-3-SV-M] _________________________
/tests/test_outputs.py:93: in test_arc_mean_vtec
    assert abs(got - ref) <= tol, \
E   AssertionError: RX-3 SV-M: got 39.35301 TECU, expected 36.22064 TECU (tol 0.05000 TECU)
E   assert 3.132366306892102 <= 0.05
E    +  where 3.132366306892102 = abs((39.353007 - 36.220640693107896))
________________________ test_arc_mean_vtec[RX-3-SV-P] _________________________
/tests/test_outputs.py:93: in test_arc_mean_vtec
    assert abs(got - ref) <= tol, \
E   AssertionError: RX-3 SV-P: got 39.42666 TECU, expected 37.67497 TECU (tol 0.05000 TECU)
E   assert 1.7516896601466385 <= 0.05
E    +  where 1.7516896601466385 = abs((39.42666 - 37.67497033985336))
________________________ test_arc_mean_vtec[RX-3-SV-T] _________________________
/tests/test_outputs.py:93: in test_arc_mean_vtec
    assert abs(got - ref) <= tol, \
E   AssertionError: RX-3 SV-T: got 39.27342 TECU, expected 20.63799 TECU (tol 0.05000 TECU)
E   assert 18.635432076701317 <= 0.05
E    +  where 18.635432076701317 = abs((39.273419 - 20.63798692329868))
---------------- generated xml file: /logs/verifier/results.xml ----------------
=========================== short test summary info ============================
FAILED ::test_arc_mean_vtec[RX-1-SV-K] - AssertionError: RX-1 SV-K: got 33.60...
FAILED ::test_arc_mean_vtec[RX-1-SV-P] - AssertionError: RX-1 SV-P: got 33.60...
FAILED ::test_arc_mean_vtec[RX-1-SV-R] - AssertionError: RX-1 SV-R: got 33.72...
FAILED ::test_arc_mean_vtec[RX-1-SV-W] - AssertionError: RX-1 SV-W: got 33.49...
FAILED ::test_arc_mean_vtec[RX-2-SV-M] - AssertionError: RX-2 SV-M: got 25.64...
FAILED ::test_arc_mean_vtec[RX-2-SV-R] - AssertionError: RX-2 SV-R: got 25.74...
FAILED ::test_arc_mean_vtec[RX-2-SV-T] - AssertionError: RX-2 SV-T: got 25.66...
FAILED ::test_arc_mean_vtec[RX-2-SV-W] - AssertionError: RX-2 SV-W: got 25.74...
FAILED ::test_arc_mean_vtec[RX-3-SV-K] - AssertionError: RX-3 SV-K: got 39.40...
FAILED ::test_arc_mean_vtec[RX-3-SV-M] - AssertionError: RX-3 SV-M: got 39.35...
FAILED ::test_arc_mean_vtec[RX-3-SV-P] - AssertionError: RX-3 SV-P: got 39.42...
FAILED ::test_arc_mean_vtec[RX-3-SV-T] - AssertionError: RX-3 SV-T: got 39.27...
========================= 12 failed, 4 passed in 0.05s =========================
