test cases passed  : 10/31
self-check failures: 0
Score              : 0.3226
pass@1             : 0
============================= test session starts ==============================
platform linux -- Python 3.11.15, pytest-8.3.4, pluggy-1.6.0 -- /usr/local/bin/python3
rootdir: /root
configfile: ../dev/null
collecting ... collected 41 items

::test_graded_case[R0001_head_1_54] PASSED                               [  2%]
::test_graded_case[R0001_amounts_55_270] PASSED                          [  4%]
::test_graded_case[R0001_reserved_and_first_name_271_327] FAILED         [  7%]
::test_graded_case[R0001_second_name_and_address_328_407] FAILED         [  9%]
::test_graded_case[R0001_reserved_and_city_408_487] FAILED               [ 12%]
::test_graded_case[R0001_state_and_postal_488_498] FAILED                [ 14%]
::test_graded_case[R0001_reserved_and_counter_499_543] FAILED            [ 17%]
::test_graded_case[R0001_indicators_and_reserved_544_662] PASSED         [ 19%]
::test_graded_case[R0001_free_text_and_state_withholding_663_734] FAILED [ 21%]
::test_graded_case[R0001_local_withholding_and_program_code_735_750] FAILED [ 24%]
::test_graded_case[R0002_head_1_54] PASSED                               [ 26%]
::test_graded_case[R0002_amounts_55_270] PASSED                          [ 29%]
::test_graded_case[R0002_reserved_and_first_name_271_327] FAILED         [ 31%]
::test_graded_case[R0002_second_name_and_address_328_407] FAILED         [ 34%]
::test_graded_case[R0002_reserved_and_city_408_487] FAILED               [ 36%]
::test_graded_case[R0002_state_and_postal_488_498] FAILED                [ 39%]
::test_graded_case[R0002_reserved_and_counter_499_543] FAILED            [ 41%]
::test_graded_case[R0002_indicators_and_reserved_544_662] PASSED         [ 43%]
::test_graded_case[R0002_free_text_and_state_withholding_663_734] FAILED [ 46%]
::test_graded_case[R0002_local_withholding_and_program_code_735_750] FAILED [ 48%]
::test_graded_case[R0003_head_1_54] PASSED                               [ 51%]
::test_graded_case[R0003_amounts_55_270] PASSED                          [ 53%]
::test_graded_case[R0003_reserved_and_first_name_271_327] FAILED         [ 56%]
::test_graded_case[R0003_second_name_and_address_328_407] FAILED         [ 58%]
::test_graded_case[R0003_reserved_and_city_408_487] FAILED               [ 60%]
::test_graded_case[R0003_state_and_postal_488_498] FAILED                [ 63%]
::test_graded_case[R0003_reserved_and_counter_499_543] FAILED            [ 65%]
::test_graded_case[R0003_indicators_and_reserved_544_662] PASSED         [ 68%]
::test_graded_case[R0003_free_text_and_state_withholding_663_734] FAILED [ 70%]
::test_graded_case[R0003_local_withholding_and_program_code_735_750] FAILED [ 73%]
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
___________ test_graded_case[R0001_reserved_and_first_name_271_327] ____________
/tests/test_output.py:165: in test_graded_case
    assert abs(got - ref) <= tol, \
E   AssertionError: R0001_reserved_and_first_name_271_327: 0 of 3 field(s) decode back to the payee record - blank_271_286 reserved positions carry ' HERNANDEZ ROSA ', not blanks; foreign_country_indicator the foreign-address indicator must carry '1' or a blank, got 'M'; first_payee_name_line decodes to '', but the payee record carries 'HERNANDEZ ROSA M'
E   assert 3.0 <= 0.5
E    +  where 3.0 = abs((0.0 - 3.0))
___________ test_graded_case[R0001_second_name_and_address_328_407] ____________
/tests/test_output.py:165: in test_graded_case
    assert abs(got - ref) <= tol, \
E   AssertionError: R0001_second_name_and_address_328_407: 1 of 2 field(s) decode back to the payee record - payee_mailing_address leading blanks in a left-justified field: '                        3184 CALLE VERDE'
E   assert 1.0 <= 0.5
E    +  where 1.0 = abs((1.0 - 2.0))
______________ test_graded_case[R0001_reserved_and_city_408_487] _______________
/tests/test_output.py:165: in test_graded_case
    assert abs(got - ref) <= tol, \
E   AssertionError: R0001_reserved_and_city_408_487: 0 of 2 field(s) decode back to the payee record - blank_408_447 reserved positions carry ' APT 12                                 ', not blanks; payee_city leading blanks in a left-justified field: '                        CHARLOTTE       '
E   assert 2.0 <= 0.5
E    +  where 2.0 = abs((0.0 - 2.0))
_______________ test_graded_case[R0001_state_and_postal_488_498] _______________
/tests/test_output.py:165: in test_graded_case
    assert abs(got - ref) <= tol, \
E   AssertionError: R0001_state_and_postal_488_498: 0 of 2 field(s) decode back to the payee record - payee_state decodes to '', but the payee record carries 'NC'; payee_zip_code postal code '' is neither five nor nine digits
E   assert 2.0 <= 0.5
E    +  where 2.0 = abs((0.0 - 2.0))
_____________ test_graded_case[R0001_reserved_and_counter_499_543] _____________
/tests/test_output.py:165: in test_graded_case
    assert abs(got - ref) <= tol, \
E   AssertionError: R0001_reserved_and_counter_499_543: 1 of 3 field(s) decode back to the payee record - record_sequence_number a sequence number must be all digits, got '        '; blank_508_543 reserved positions carry '    NC28202     00000003            ', not blanks
E   assert 2.0 <= 0.5
E    +  where 2.0 = abs((1.0 - 3.0))
_______ test_graded_case[R0001_free_text_and_state_withholding_663_734] ________
/tests/test_output.py:165: in test_graded_case
    assert abs(got - ref) <= tol, \
E   AssertionError: R0001_free_text_and_state_withholding_663_734: 0 of 2 field(s) decode back to the payee record - special_data_entries decodes to '00000009237500000000000037', but the payee record carries ''; state_income_tax_withheld a payment amount field must be all digits, got '            '
E   assert 2.0 <= 0.5
E    +  where 2.0 = abs((0.0 - 2.0))
______ test_graded_case[R0001_local_withholding_and_program_code_735_750] ______
/tests/test_output.py:165: in test_graded_case
    assert abs(got - ref) <= tol, \
E   AssertionError: R0001_local_withholding_and_program_code_735_750: 1 of 3 field(s) decode back to the payee record - local_income_tax_withheld a payment amount field must be all digits, got '            '; combined_federal_state_code decodes to '', but the payee record carries '37'
E   assert 2.0 <= 0.5
E    +  where 2.0 = abs((1.0 - 3.0))
___________ test_graded_case[R0002_reserved_and_first_name_271_327] ____________
/tests/test_output.py:165: in test_graded_case
    assert abs(got - ref) <= tol, \
E   AssertionError: R0002_reserved_and_first_name_271_327: 1 of 3 field(s) decode back to the payee record - blank_271_286 reserved positions carry ' PINEHURST FARMS', not blanks; first_payee_name_line decodes to 'COOPERATIVE             AND MIDLAND GRAI', but the payee record carries 'PINEHURST FARMS COOPERATIVE'
E   assert 2.0 <= 0.5
E    +  where 2.0 = abs((1.0 - 3.0))
___________ test_graded_case[R0002_second_name_and_address_328_407] ____________
/tests/test_output.py:165: in test_graded_case
    assert abs(got - ref) <= tol, \
E   AssertionError: R0002_second_name_and_address_328_407: 0 of 2 field(s) decode back to the payee record - second_payee_name_line decodes to 'N PARTNERS LLC', but the payee record carries 'AND MIDLAND GRAIN PARTNERS LLC'; payee_mailing_address leading blanks in a left-justified field: '                        1420 COUNTY ROAD'
E   assert 2.0 <= 0.5
E    +  where 2.0 = abs((0.0 - 2.0))
______________ test_graded_case[R0002_reserved_and_city_408_487] _______________
/tests/test_output.py:165: in test_graded_case
    assert abs(got - ref) <= tol, \
E   AssertionError: R0002_reserved_and_city_408_487: 0 of 2 field(s) decode back to the payee record - blank_408_447 reserved positions carry ' K                                      ', not blanks; payee_city leading blanks in a left-justified field: '                        FOND DU LAC     '
E   assert 2.0 <= 0.5
E    +  where 2.0 = abs((0.0 - 2.0))
_______________ test_graded_case[R0002_state_and_postal_488_498] _______________
/tests/test_output.py:165: in test_graded_case
    assert abs(got - ref) <= tol, \
E   AssertionError: R0002_state_and_postal_488_498: 0 of 2 field(s) decode back to the payee record - payee_state decodes to '', but the payee record carries 'WI'; payee_zip_code postal code '' is neither five nor nine digits
E   assert 2.0 <= 0.5
E    +  where 2.0 = abs((0.0 - 2.0))
_____________ test_graded_case[R0002_reserved_and_counter_499_543] _____________
/tests/test_output.py:165: in test_graded_case
    assert abs(got - ref) <= tol, \
E   AssertionError: R0002_reserved_and_counter_499_543: 1 of 3 field(s) decode back to the payee record - record_sequence_number a sequence number must be all digits, got '        '; blank_508_543 reserved positions carry '    WI549359102 00000004            ', not blanks
E   assert 2.0 <= 0.5
E    +  where 2.0 = abs((1.0 - 3.0))
_______ test_graded_case[R0002_free_text_and_state_withholding_663_734] ________
/tests/test_output.py:165: in test_graded_case
    assert abs(got - ref) <= tol, \
E   AssertionError: R0002_free_text_and_state_withholding_663_734: 0 of 2 field(s) decode back to the payee record - special_data_entries decodes to '00000014623000000000000055', but the payee record carries ''; state_income_tax_withheld a payment amount field must be all digits, got '            '
E   assert 2.0 <= 0.5
E    +  where 2.0 = abs((0.0 - 2.0))
______ test_graded_case[R0002_local_withholding_and_program_code_735_750] ______
/tests/test_output.py:165: in test_graded_case
    assert abs(got - ref) <= tol, \
E   AssertionError: R0002_local_withholding_and_program_code_735_750: 1 of 3 field(s) decode back to the payee record - local_income_tax_withheld a payment amount field must be all digits, got '            '; combined_federal_state_code decodes to '', but the payee record carries '55'
E   assert 2.0 <= 0.5
E    +  where 2.0 = abs((1.0 - 3.0))
___________ test_graded_case[R0003_reserved_and_first_name_271_327] ____________
/tests/test_output.py:165: in test_graded_case
    assert abs(got - ref) <= tol, \
E   AssertionError: R0003_reserved_and_first_name_271_327: 1 of 3 field(s) decode back to the payee record - blank_271_286 reserved positions carry ' OKEEFE DANIEL J', not blanks; first_payee_name_line decodes to '', but the payee record carries 'OKEEFE DANIEL J'
E   assert 2.0 <= 0.5
E    +  where 2.0 = abs((1.0 - 3.0))
___________ test_graded_case[R0003_second_name_and_address_328_407] ____________
/tests/test_output.py:165: in test_graded_case
    assert abs(got - ref) <= tol, \
E   AssertionError: R0003_second_name_and_address_328_407: 1 of 2 field(s) decode back to the payee record - payee_mailing_address leading blanks in a left-justified field: '                        PO BOX 4471     '
E   assert 1.0 <= 0.5
E    +  where 1.0 = abs((1.0 - 2.0))
______________ test_graded_case[R0003_reserved_and_city_408_487] _______________
/tests/test_output.py:165: in test_graded_case
    assert abs(got - ref) <= tol, \
E   AssertionError: R0003_reserved_and_city_408_487: 1 of 2 field(s) decode back to the payee record - payee_city leading blanks in a left-justified field: '                        EL PASO         '
E   assert 1.0 <= 0.5
E    +  where 1.0 = abs((1.0 - 2.0))
_______________ test_graded_case[R0003_state_and_postal_488_498] _______________
/tests/test_output.py:165: in test_graded_case
    assert abs(got - ref) <= tol, \
E   AssertionError: R0003_state_and_postal_488_498: 0 of 2 field(s) decode back to the payee record - payee_state decodes to '', but the payee record carries 'TX'; payee_zip_code postal code '' is neither five nor nine digits
E   assert 2.0 <= 0.5
E    +  where 2.0 = abs((0.0 - 2.0))
_____________ test_graded_case[R0003_reserved_and_counter_499_543] _____________
/tests/test_output.py:165: in test_graded_case
    assert abs(got - ref) <= tol, \
E   AssertionError: R0003_reserved_and_counter_499_543: 1 of 3 field(s) decode back to the payee record - record_sequence_number a sequence number must be all digits, got '        '; blank_508_543 reserved positions carry '    TX799120044 00000005            ', not blanks
E   assert 2.0 <= 0.5
E    +  where 2.0 = abs((1.0 - 3.0))
_______ test_graded_case[R0003_free_text_and_state_withholding_663_734] ________
/tests/test_output.py:165: in test_graded_case
    assert abs(got - ref) <= tol, \
E   AssertionError: R0003_free_text_and_state_withholding_663_734: 0 of 2 field(s) decode back to the payee record - special_data_entries decodes to '000000000000000000000000', but the payee record carries ''; state_income_tax_withheld a payment amount field must be all digits, got '            '
E   assert 2.0 <= 0.5
E    +  where 2.0 = abs((0.0 - 2.0))
______ test_graded_case[R0003_local_withholding_and_program_code_735_750] ______
/tests/test_output.py:165: in test_graded_case
    assert abs(got - ref) <= tol, \
E   AssertionError: R0003_local_withholding_and_program_code_735_750: 2 of 3 field(s) decode back to the payee record - local_income_tax_withheld a payment amount field must be all digits, got '            '
E   assert 1.0 <= 0.5
E    +  where 1.0 = abs((2.0 - 3.0))
------------------ generated xml file: /tmp/erza_junit.VDlZ4Z ------------------
=========================== short test summary info ============================
FAILED ::test_graded_case[R0001_reserved_and_first_name_271_327] - AssertionE...
FAILED ::test_graded_case[R0001_second_name_and_address_328_407] - AssertionE...
FAILED ::test_graded_case[R0001_reserved_and_city_408_487] - AssertionError: ...
FAILED ::test_graded_case[R0001_state_and_postal_488_498] - AssertionError: R...
FAILED ::test_graded_case[R0001_reserved_and_counter_499_543] - AssertionErro...
FAILED ::test_graded_case[R0001_free_text_and_state_withholding_663_734] - As...
FAILED ::test_graded_case[R0001_local_withholding_and_program_code_735_750]
FAILED ::test_graded_case[R0002_reserved_and_first_name_271_327] - AssertionE...
FAILED ::test_graded_case[R0002_second_name_and_address_328_407] - AssertionE...
FAILED ::test_graded_case[R0002_reserved_and_city_408_487] - AssertionError: ...
FAILED ::test_graded_case[R0002_state_and_postal_488_498] - AssertionError: R...
FAILED ::test_graded_case[R0002_reserved_and_counter_499_543] - AssertionErro...
FAILED ::test_graded_case[R0002_free_text_and_state_withholding_663_734] - As...
FAILED ::test_graded_case[R0002_local_withholding_and_program_code_735_750]
FAILED ::test_graded_case[R0003_reserved_and_first_name_271_327] - AssertionE...
FAILED ::test_graded_case[R0003_second_name_and_address_328_407] - AssertionE...
FAILED ::test_graded_case[R0003_reserved_and_city_408_487] - AssertionError: ...
FAILED ::test_graded_case[R0003_state_and_postal_488_498] - AssertionError: R...
FAILED ::test_graded_case[R0003_reserved_and_counter_499_543] - AssertionErro...
FAILED ::test_graded_case[R0003_free_text_and_state_withholding_663_734] - As...
FAILED ::test_graded_case[R0003_local_withholding_and_program_code_735_750]
======================== 21 failed, 20 passed in 0.11s =========================
