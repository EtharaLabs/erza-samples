test cases passed : 40/51
Score             : 0.7843
pass@1            : 0
E   assert 52.0 <= 1.0
E    +  where 52.0 = abs((30.0 - -22))
_____________________ test_graded_case[P10-fdp_margin_min] _____________________
/tests/test_outputs.py:107: in test_graded_case
    assert abs(got - item["ref"]) <= item["tolerance"], \
E   AssertionError: P10-fdp_margin_min: got -56.000, expected -26.000 (tol 1.000)
E   assert 30.0 <= 1.0
E    +  where 30.0 = abs((-56.0 - -26))
___________________ test_graded_case[P10-binding_margin_min] ___________________
/tests/test_outputs.py:107: in test_graded_case
    assert abs(got - item["ref"]) <= item["tolerance"], \
E   AssertionError: P10-binding_margin_min: got -56.000, expected -26.000 (tol 1.000)
E   assert 30.0 <= 1.0
E    +  where 30.0 = abs((-56.0 - -26))
_____________________ test_graded_case[P11-fdp_margin_min] _____________________
/tests/test_outputs.py:107: in test_graded_case
    assert abs(got - item["ref"]) <= item["tolerance"], \
E   AssertionError: P11-fdp_margin_min: got -19.000, expected 11.000 (tol 1.000)
E   assert 30.0 <= 1.0
E    +  where 30.0 = abs((-19.0 - 11))
_____________________ test_graded_case[P16-fdp_margin_min] _____________________
/tests/test_outputs.py:107: in test_graded_case
    assert abs(got - item["ref"]) <= item["tolerance"], \
E   AssertionError: P16-fdp_margin_min: got 5.000, expected -25.000 (tol 1.000)
E   assert 30.0 <= 1.0
E    +  where 30.0 = abs((5.0 - -25))
---------------- generated xml file: /logs/verifier/results.xml ----------------
=========================== short test summary info ============================
FAILED ::test_graded_case[P01-fdp_margin_min] - AssertionError: P01-fdp_margi...
FAILED ::test_graded_case[P01-binding_margin_min] - AssertionError: P01-bindi...
FAILED ::test_graded_case[P05-fdp_margin_min] - AssertionError: P05-fdp_margi...
FAILED ::test_graded_case[P05-binding_margin_min] - AssertionError: P05-bindi...
FAILED ::test_graded_case[P06-fdp_margin_min] - AssertionError: P06-fdp_margi...
FAILED ::test_graded_case[P06-binding_limit] - AssertionError: P06-binding_li...
FAILED ::test_graded_case[P06-binding_margin_min] - AssertionError: P06-bindi...
FAILED ::test_graded_case[P10-fdp_margin_min] - AssertionError: P10-fdp_margi...
FAILED ::test_graded_case[P10-binding_margin_min] - AssertionError: P10-bindi...
FAILED ::test_graded_case[P11-fdp_margin_min] - AssertionError: P11-fdp_margi...
FAILED ::test_graded_case[P16-fdp_margin_min] - AssertionError: P16-fdp_margi...
======================== 11 failed, 50 passed in 0.10s =========================
