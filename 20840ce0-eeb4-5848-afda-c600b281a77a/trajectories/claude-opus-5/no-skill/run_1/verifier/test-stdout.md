test cases passed  : 25/31
self-check failures: 0
Score              : 0.8065
pass@1             : 0
============================= test session starts ==============================
platform linux -- Python 3.11.15, pytest-8.3.4, pluggy-1.6.0 -- /usr/local/bin/python3
rootdir: /root
configfile: ../dev/null
collecting ... collected 41 items

::test_graded_case[R0001_head_1_54] FAILED                               [  2%]
::test_graded_case[R0001_amounts_55_270] FAILED                          [  4%]
::test_graded_case[R0001_reserved_and_first_name_271_327] PASSED         [  7%]
::test_graded_case[R0001_second_name_and_address_328_407] PASSED         [  9%]
::test_graded_case[R0001_reserved_and_city_408_487] PASSED               [ 12%]
::test_graded_case[R0001_state_and_postal_488_498] PASSED                [ 14%]
::test_graded_case[R0001_reserved_and_counter_499_543] PASSED            [ 17%]
::test_graded_case[R0001_indicators_and_reserved_544_662] PASSED         [ 19%]
::test_graded_case[R0001_free_text_and_state_withholding_663_734] PASSED [ 21%]
::test_graded_case[R0001_local_withholding_and_program_code_735_750] PASSED [ 24%]
::test_graded_case[R0002_head_1_54] FAILED                               [ 26%]
::test_graded_case[R0002_amounts_55_270] FAILED                          [ 29%]
::test_graded_case[R0002_reserved_and_first_name_271_327] PASSED         [ 31%]
::test_graded_case[R0002_second_name_and_address_328_407] PASSED         [ 34%]
::test_graded_case[R0002_reserved_and_city_408_487] PASSED               [ 36%]
::test_graded_case[R0002_state_and_postal_488_498] PASSED                [ 39%]
::test_graded_case[R0002_reserved_and_counter_499_543] PASSED            [ 41%]
::test_graded_case[R0002_indicators_and_reserved_544_662] PASSED         [ 43%]
::test_graded_case[R0002_free_text_and_state_withholding_663_734] PASSED [ 46%]
::test_graded_case[R0002_local_withholding_and_program_code_735_750] PASSED [ 48%]
::test_graded_case[R0003_head_1_54] FAILED                               [ 51%]
::test_graded_case[R0003_amounts_55_270] FAILED                          [ 53%]
::test_graded_case[R0003_reserved_and_first_name_271_327] PASSED         [ 56%]
::test_graded_case[R0003_second_name_and_address_328_407] PASSED         [ 58%]
::test_graded_case[R0003_reserved_and_city_408_487] PASSED               [ 60%]
::test_graded_case[R0003_state_and_postal_488_498] PASSED                [ 63%]
::test_graded_case[R0003_reserved_and_counter_499_543] PASSED            [ 65%]
::test_graded_case[R0003_indicators_and_reserved_544_662] PASSED         [ 68%]
::test_graded_case[R0003_free_text_and_state_withholding_663_734] PASSED [ 70%]
::test_graded_case[R0003_local_withholding_and_program_code_735_750] PASSED [ 73%]
::test_graded_case[answer_file_shape_and_charset] PASSED                 [ 75%]
::test_field_table_is_contiguous_and_totals_750 PASSED                   [ 78%]
::test_every_position_belongs_to_exactly_one_graded_group PASSED         [ 80%]
::test_frozen_golden_records_decode_to_the_payee_data PASSED             [ 82%]
::test_permitted_readings_of_the_specification_do_not_false_fail PASSED  [ 85%]
::test_control_paths_are_measured_live_and_clear_the_tolerance PASSED    [ 87%]
::test_plausibility_envelope_and_guess_resistance PASSED                 [ 90%]
::test_no_assembled_record_reaches_the_agent PASSED                      [ 92%]
::test_isomorphic_invariance_under_relabel_and_reindex PASSED            [ 95%]
::test_amount_convention_alone_does_not_carry_the_task PASSED            [ 97%]
::test_tolerances_are_positive_and_the_case_set_is_well_formed PASSED    [100%]

=================================== FAILURES ===================================
______________________ test_graded_case[R0001_head_1_54] _______________________
/tests/test_output.py:165: in test_graded_case
    assert abs(got - ref) <= tol, \
E   AssertionError: R0001_head_1_54: 8 of 9 field(s) decode back to the payee record - blank_45_54 reserved positions carry '    000001', not blanks
E   assert 1.0 <= 0.5
E    +  where 1.0 = abs((8.0 - 9.0))
____________________ test_graded_case[R0001_amounts_55_270] ____________________
/tests/test_output.py:165: in test_graded_case
    assert abs(got - ref) <= tol, \
E   AssertionError: R0001_amounts_55_270: 15 of 18 field(s) decode back to the payee record - amount_1 decodes to Decimal('8450000000'), but the payee record carries Decimal('18450.00'); amount_4 decodes to Decimal('2767500000'), but the payee record carries Decimal('2767.50'); amount_J a payment amount field must be all digits, got '000000      '
E   assert 3.0 <= 0.5
E    +  where 3.0 = abs((15.0 - 18.0))
______________________ test_graded_case[R0002_head_1_54] _______________________
/tests/test_output.py:165: in test_graded_case
    assert abs(got - ref) <= tol, \
E   AssertionError: R0002_head_1_54: 8 of 9 field(s) decode back to the payee record - blank_45_54 reserved positions carry '    000000', not blanks
E   assert 1.0 <= 0.5
E    +  where 1.0 = abs((8.0 - 9.0))
____________________ test_graded_case[R0002_amounts_55_270] ____________________
/tests/test_output.py:165: in test_graded_case
    assert abs(got - ref) <= tol, \
E   AssertionError: R0002_amounts_55_270: 12 of 18 field(s) decode back to the payee record - amount_2 decodes to Decimal('7315200000'), but the payee record carries Decimal('7315.20'); amount_5 decodes to Decimal('0.02'), but the payee record carries Decimal('0.00'); amount_6 decodes to Decimal('4980000000'), but the payee record carries Decimal('24980.00'); amount_A decodes to Decimal('1150000000'), but the payee record carries Decimal('1150.00')
E   assert 6.0 <= 0.5
E    +  where 6.0 = abs((12.0 - 18.0))
______________________ test_graded_case[R0003_head_1_54] _______________________
/tests/test_output.py:165: in test_graded_case
    assert abs(got - ref) <= tol, \
E   AssertionError: R0003_head_1_54: 8 of 9 field(s) decode back to the payee record - blank_45_54 reserved positions carry '    000000', not blanks
E   assert 1.0 <= 0.5
E    +  where 1.0 = abs((8.0 - 9.0))
____________________ test_graded_case[R0003_amounts_55_270] ____________________
/tests/test_output.py:165: in test_graded_case
    assert abs(got - ref) <= tol, \
E   AssertionError: R0003_amounts_55_270: 13 of 18 field(s) decode back to the payee record - amount_3 decodes to Decimal('5400000000'), but the payee record carries Decimal('5400.00'); amount_8 decodes to Decimal('2140750000'), but the payee record carries Decimal('2140.75'); amount_C decodes to Decimal('0.03'), but the payee record carries Decimal('0.00'); amount_D decodes to Decimal('1000000000'), but the payee record carries Decimal('31000.00')
E   assert 5.0 <= 0.5
E    +  where 5.0 = abs((13.0 - 18.0))
------------------ generated xml file: /tmp/erza_junit.QgxSci ------------------
=========================== short test summary info ============================
FAILED ::test_graded_case[R0001_head_1_54] - AssertionError: R0001_head_1_54:...
FAILED ::test_graded_case[R0001_amounts_55_270] - AssertionError: R0001_amoun...
FAILED ::test_graded_case[R0002_head_1_54] - AssertionError: R0002_head_1_54:...
FAILED ::test_graded_case[R0002_amounts_55_270] - AssertionError: R0002_amoun...
FAILED ::test_graded_case[R0003_head_1_54] - AssertionError: R0003_head_1_54:...
FAILED ::test_graded_case[R0003_amounts_55_270] - AssertionError: R0003_amoun...
========================= 6 failed, 35 passed in 0.06s =========================
