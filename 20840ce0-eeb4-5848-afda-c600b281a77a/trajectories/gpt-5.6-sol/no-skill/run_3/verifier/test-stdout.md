test cases passed : 22/31
Score             : 0.7097
pass@1            : 0
    assert abs(got - ref) <= tol, \
E   AssertionError: R0002_state_and_postal_488_498: 0 of 2 field(s) decode back to the payee record - payee_state decodes to '', but the payee record carries 'WI'; payee_zip_code postal code '' is neither five nor nine digits
E   assert 2.0 <= 0.5
E    +  where 2.0 = abs((0.0 - 2.0))
_____________ test_graded_case[R0002_reserved_and_counter_499_543] _____________
/tests/test_outputs.py:165: in test_graded_case
    assert abs(got - ref) <= tol, \
E   AssertionError: R0002_reserved_and_counter_499_543: 1 of 3 field(s) decode back to the payee record - blank_499 reserved positions carry '0', not blanks; record_sequence_number a sequence number must be all digits, got '0000004 '
E   assert 2.0 <= 0.5
E    +  where 2.0 = abs((1.0 - 3.0))
______________ test_graded_case[R0003_reserved_and_city_408_487] _______________
/tests/test_outputs.py:165: in test_graded_case
    assert abs(got - ref) <= tol, \
E   AssertionError: R0003_reserved_and_city_408_487: 0 of 2 field(s) decode back to the payee record - blank_408_447 reserved positions carry 'EL PASO                                 ', not blanks; payee_city decodes to 'TX799120044', but the payee record carries 'EL PASO'
E   assert 2.0 <= 0.5
E    +  where 2.0 = abs((0.0 - 2.0))
_______________ test_graded_case[R0003_state_and_postal_488_498] _______________
/tests/test_outputs.py:165: in test_graded_case
    assert abs(got - ref) <= tol, \
E   AssertionError: R0003_state_and_postal_488_498: 0 of 2 field(s) decode back to the payee record - payee_state decodes to '', but the payee record carries 'TX'; payee_zip_code postal code '' is neither five nor nine digits
E   assert 2.0 <= 0.5
E    +  where 2.0 = abs((0.0 - 2.0))
_____________ test_graded_case[R0003_reserved_and_counter_499_543] _____________
/tests/test_outputs.py:165: in test_graded_case
    assert abs(got - ref) <= tol, \
E   AssertionError: R0003_reserved_and_counter_499_543: 1 of 3 field(s) decode back to the payee record - blank_499 reserved positions carry '0', not blanks; record_sequence_number a sequence number must be all digits, got '0000005 '
E   assert 2.0 <= 0.5
E    +  where 2.0 = abs((1.0 - 3.0))
---------------- generated xml file: /logs/verifier/results.xml ----------------
=========================== short test summary info ============================
FAILED ::test_graded_case[R0001_reserved_and_city_408_487] - AssertionError: ...
FAILED ::test_graded_case[R0001_state_and_postal_488_498] - AssertionError: R...
FAILED ::test_graded_case[R0001_reserved_and_counter_499_543] - AssertionErro...
FAILED ::test_graded_case[R0002_reserved_and_city_408_487] - AssertionError: ...
FAILED ::test_graded_case[R0002_state_and_postal_488_498] - AssertionError: R...
FAILED ::test_graded_case[R0002_reserved_and_counter_499_543] - AssertionErro...
FAILED ::test_graded_case[R0003_reserved_and_city_408_487] - AssertionError: ...
FAILED ::test_graded_case[R0003_state_and_postal_488_498] - AssertionError: R...
FAILED ::test_graded_case[R0003_reserved_and_counter_499_543] - AssertionErro...
========================= 9 failed, 32 passed in 0.14s =========================
