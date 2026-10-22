test cases passed : 41/51
Score             : 0.8039
pass@1            : 0
E   AssertionError: P11-fdp_margin_min: got -19.000, expected 11.000 (tol 1.000)
E   assert 30.0 <= 1.0
E    +  where 30.0 = abs((-19.0 - 11))
_____________________ test_graded_case[P12-fdp_margin_min] _____________________
/tests/test_outputs.py:107: in test_graded_case
    assert abs(got - item["ref"]) <= item["tolerance"], \
E   AssertionError: P12-fdp_margin_min: got 134.000, expected 14.000 (tol 1.000)
E   assert 120.0 <= 1.0
E    +  where 120.0 = abs((134.0 - 14))
_____________________ test_graded_case[P13-fdp_margin_min] _____________________
/tests/test_outputs.py:107: in test_graded_case
    assert abs(got - item["ref"]) <= item["tolerance"], \
E   AssertionError: P13-fdp_margin_min: got 81.000, expected 21.000 (tol 1.000)
E   assert 60.0 <= 1.0
E    +  where 60.0 = abs((81.0 - 21))
_____________________ test_graded_case[P15-fdp_margin_min] _____________________
/tests/test_outputs.py:107: in test_graded_case
    assert abs(got - item["ref"]) <= item["tolerance"], \
E   AssertionError: P15-fdp_margin_min: got 134.000, expected 14.000 (tol 1.000)
E   assert 120.0 <= 1.0
E    +  where 120.0 = abs((134.0 - 14))
_____________________ test_graded_case[P16-fdp_margin_min] _____________________
/tests/test_outputs.py:107: in test_graded_case
    assert abs(got - item["ref"]) <= item["tolerance"], \
E   AssertionError: P16-fdp_margin_min: got 65.000, expected -25.000 (tol 1.000)
E   assert 90.0 <= 1.0
E    +  where 90.0 = abs((65.0 - -25))
---------------- generated xml file: /logs/verifier/results.xml ----------------
=========================== short test summary info ============================
FAILED ::test_graded_case[P05-fdp_margin_min] - AssertionError: P05-fdp_margi...
FAILED ::test_graded_case[P05-binding_margin_min] - AssertionError: P05-bindi...
FAILED ::test_graded_case[P06-fdp_margin_min] - AssertionError: P06-fdp_margi...
FAILED ::test_graded_case[P06-binding_limit] - AssertionError: P06-binding_li...
FAILED ::test_graded_case[P06-binding_margin_min] - AssertionError: P06-bindi...
FAILED ::test_graded_case[P11-fdp_margin_min] - AssertionError: P11-fdp_margi...
FAILED ::test_graded_case[P12-fdp_margin_min] - AssertionError: P12-fdp_margi...
FAILED ::test_graded_case[P13-fdp_margin_min] - AssertionError: P13-fdp_margi...
FAILED ::test_graded_case[P15-fdp_margin_min] - AssertionError: P15-fdp_margi...
FAILED ::test_graded_case[P16-fdp_margin_min] - AssertionError: P16-fdp_margi...
======================== 10 failed, 51 passed in 0.11s =========================
