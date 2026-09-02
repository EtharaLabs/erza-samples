test cases passed : 0/12
Score             : 0.0000
pass@1            : 0
E    +  where 7.996236290979052 = abs((25.789 - 17.79276370902095))
________________________ test_arc_mean_vtec[RX-3-SV-K] _________________________
/tests/test_outputs.py:93: in test_arc_mean_vtec
    assert abs(got - ref) <= tol, \
E   AssertionError: RX-3 SV-K: got 39.29600 TECU, expected 21.53369 TECU (tol 0.05000 TECU)
E   assert 17.762309774566205 <= 0.05
E    +  where 17.762309774566205 = abs((39.296 - 21.533690225433794))
________________________ test_arc_mean_vtec[RX-3-SV-M] _________________________
/tests/test_outputs.py:93: in test_arc_mean_vtec
    assert abs(got - ref) <= tol, \
E   AssertionError: RX-3 SV-M: got 39.23400 TECU, expected 36.22064 TECU (tol 0.05000 TECU)
E   assert 3.013359306892106 <= 0.05
E    +  where 3.013359306892106 = abs((39.234 - 36.220640693107896))
________________________ test_arc_mean_vtec[RX-3-SV-P] _________________________
/tests/test_outputs.py:93: in test_arc_mean_vtec
    assert abs(got - ref) <= tol, \
E   AssertionError: RX-3 SV-P: got 39.23100 TECU, expected 37.67497 TECU (tol 0.05000 TECU)
E   assert 1.556029660146642 <= 0.05
E    +  where 1.556029660146642 = abs((39.231 - 37.67497033985336))
________________________ test_arc_mean_vtec[RX-3-SV-T] _________________________
/tests/test_outputs.py:93: in test_arc_mean_vtec
    assert abs(got - ref) <= tol, \
E   AssertionError: RX-3 SV-T: got 39.25400 TECU, expected 20.63799 TECU (tol 0.05000 TECU)
E   assert 18.616013076701318 <= 0.05
E    +  where 18.616013076701318 = abs((39.254 - 20.63798692329868))
---------------- generated xml file: /logs/verifier/results.xml ----------------
=========================== short test summary info ============================
FAILED ::test_arc_mean_vtec[RX-1-SV-K] - AssertionError: RX-1 SV-K: got 33.76...
FAILED ::test_arc_mean_vtec[RX-1-SV-P] - AssertionError: RX-1 SV-P: got 33.74...
FAILED ::test_arc_mean_vtec[RX-1-SV-R] - AssertionError: RX-1 SV-R: got 33.70...
FAILED ::test_arc_mean_vtec[RX-1-SV-W] - AssertionError: RX-1 SV-W: got 33.86...
FAILED ::test_arc_mean_vtec[RX-2-SV-M] - AssertionError: RX-2 SV-M: got 25.75...
FAILED ::test_arc_mean_vtec[RX-2-SV-R] - AssertionError: RX-2 SV-R: got 25.72...
FAILED ::test_arc_mean_vtec[RX-2-SV-T] - AssertionError: RX-2 SV-T: got 25.73...
FAILED ::test_arc_mean_vtec[RX-2-SV-W] - AssertionError: RX-2 SV-W: got 25.78...
FAILED ::test_arc_mean_vtec[RX-3-SV-K] - AssertionError: RX-3 SV-K: got 39.29...
FAILED ::test_arc_mean_vtec[RX-3-SV-M] - AssertionError: RX-3 SV-M: got 39.23...
FAILED ::test_arc_mean_vtec[RX-3-SV-P] - AssertionError: RX-3 SV-P: got 39.23...
FAILED ::test_arc_mean_vtec[RX-3-SV-T] - AssertionError: RX-3 SV-T: got 39.25...
========================= 12 failed, 4 passed in 0.06s =========================
