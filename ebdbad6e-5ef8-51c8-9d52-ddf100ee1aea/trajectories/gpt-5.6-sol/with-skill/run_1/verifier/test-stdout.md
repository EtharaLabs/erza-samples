test cases passed : 5/5
Score             : 1.0000
pass@1            : 1
============================= test session starts ==============================
platform linux -- Python 3.11.15, pytest-8.3.4, pluggy-1.6.0 -- /usr/local/bin/python3
rootdir: /root
configfile: ../dev/null
collecting ... collected 16 items

::test_graded_case[group-petroleum_products-residential] PASSED          [  6%]
::test_graded_case[group-petroleum_products-commercial] PASSED           [ 12%]
::test_graded_case[group-petroleum_products-industrial] PASSED           [ 18%]
::test_graded_case[group-coal-commercial] PASSED                         [ 25%]
::test_graded_case[group-coal-industrial_coke_plants] PASSED             [ 31%]
::test_frozen_reference_matches_independent_recompute PASSED             [ 37%]
::test_factors_match_the_independently_published_energy_series PASSED    [ 43%]
::test_published_all_sector_identity_closes PASSED                       [ 50%]
::test_factors_are_inside_the_domain_envelope_and_sector_spread_is_real PASSED [ 56%]
::test_all_sector_average_route_fails_every_graded_case PASSED           [ 62%]
::test_generic_single_factor_route_and_the_orientation_block_fail_everywhere PASSED [ 68%]
::test_plausibility_envelope_and_guess_resistance PASSED                 [ 75%]
::test_isomorphic_invariance_under_rescale_and_relabel PASSED            [ 81%]
::test_tolerances_are_positive_and_bind PASSED                           [ 87%]
::test_every_graded_case_is_scoped_to_one_customer_class PASSED          [ 93%]
::test_ledger_is_intact PASSED                                           [100%]

---------------- generated xml file: /logs/verifier/results.xml ----------------
============================== 16 passed in 0.03s ==============================
