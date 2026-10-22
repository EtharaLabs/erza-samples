test cases passed : 0/12
Score             : 0.0000
pass@1            : 0
E    +  where 4.299989290979049 = abs((22.092753 - 17.79276370902095))
________________________ test_arc_mean_vtec[RX-3-SV-K] _________________________
/tests/test_outputs.py:93: in test_arc_mean_vtec
    assert abs(got - ref) <= tol, \
E   AssertionError: RX-3 SV-K: got 25.97450 TECU, expected 21.53369 TECU (tol 0.05000 TECU)
E   assert 4.440813774566205 <= 0.05
E    +  where 4.440813774566205 = abs((25.974504 - 21.533690225433794))
________________________ test_arc_mean_vtec[RX-3-SV-M] _________________________
/tests/test_outputs.py:93: in test_arc_mean_vtec
    assert abs(got - ref) <= tol, \
E   AssertionError: RX-3 SV-M: got 25.87510 TECU, expected 36.22064 TECU (tol 0.05000 TECU)
E   assert 10.345543693107896 <= 0.05
E    +  where 10.345543693107896 = abs((25.875097 - 36.220640693107896))
________________________ test_arc_mean_vtec[RX-3-SV-P] _________________________
/tests/test_outputs.py:93: in test_arc_mean_vtec
    assert abs(got - ref) <= tol, \
E   AssertionError: RX-3 SV-P: got 25.91214 TECU, expected 37.67497 TECU (tol 0.05000 TECU)
E   assert 11.762832339853361 <= 0.05
E    +  where 11.762832339853361 = abs((25.912138 - 37.67497033985336))
________________________ test_arc_mean_vtec[RX-3-SV-T] _________________________
/tests/test_outputs.py:93: in test_arc_mean_vtec
    assert abs(got - ref) <= tol, \
E   AssertionError: RX-3 SV-T: got 25.94509 TECU, expected 20.63799 TECU (tol 0.05000 TECU)
E   assert 5.307100076701321 <= 0.05
E    +  where 5.307100076701321 = abs((25.945087 - 20.63798692329868))
---------------- generated xml file: /logs/verifier/results.xml ----------------
=========================== short test summary info ============================
FAILED ::test_arc_mean_vtec[RX-1-SV-K] - AssertionError: RX-1 SV-K: got 17.91...
FAILED ::test_arc_mean_vtec[RX-1-SV-P] - AssertionError: RX-1 SV-P: got 18.01...
FAILED ::test_arc_mean_vtec[RX-1-SV-R] - AssertionError: RX-1 SV-R: got 17.95...
FAILED ::test_arc_mean_vtec[RX-1-SV-W] - AssertionError: RX-1 SV-W: got 18.02...
FAILED ::test_arc_mean_vtec[RX-2-SV-M] - AssertionError: RX-2 SV-M: got 22.10...
FAILED ::test_arc_mean_vtec[RX-2-SV-R] - AssertionError: RX-2 SV-R: got 21.89...
FAILED ::test_arc_mean_vtec[RX-2-SV-T] - AssertionError: RX-2 SV-T: got 22.03...
FAILED ::test_arc_mean_vtec[RX-2-SV-W] - AssertionError: RX-2 SV-W: got 22.09...
FAILED ::test_arc_mean_vtec[RX-3-SV-K] - AssertionError: RX-3 SV-K: got 25.97...
FAILED ::test_arc_mean_vtec[RX-3-SV-M] - AssertionError: RX-3 SV-M: got 25.87...
FAILED ::test_arc_mean_vtec[RX-3-SV-P] - AssertionError: RX-3 SV-P: got 25.91...
FAILED ::test_arc_mean_vtec[RX-3-SV-T] - AssertionError: RX-3 SV-T: got 25.94...
========================= 12 failed, 4 passed in 0.05s =========================
