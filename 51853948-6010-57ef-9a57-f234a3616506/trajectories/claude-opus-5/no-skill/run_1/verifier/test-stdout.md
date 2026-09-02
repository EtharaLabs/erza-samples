test cases passed : 0/12
Score             : 0.0000
pass@1            : 0
E    +  where 57073.62375 = abs((221501.1 - 164427.47625))
___________________________ test_block_mean[GS-C-b1] ___________________________
/tests/test_outputs.py:80: in test_block_mean
    assert abs(got - ref) <= tol, \
E   AssertionError: GS-C b1: got 5608.2000 cfs, expected 6239.5194 cfs (tol 12.4790 cfs)
E   assert 631.319375 <= 12.479039
E    +  where 631.319375 = abs((5608.2 - 6239.519375))
___________________________ test_block_mean[GS-C-b2] ___________________________
/tests/test_outputs.py:80: in test_block_mean
    assert abs(got - ref) <= tol, \
E   AssertionError: GS-C b2: got 5972.3000 cfs, expected 6711.2269 cfs (tol 13.4225 cfs)
E   assert 738.9268750000001 <= 13.422454
E    +  where 738.9268750000001 = abs((5972.3 - 6711.226875))
___________________________ test_block_mean[GS-C-b3] ___________________________
/tests/test_outputs.py:80: in test_block_mean
    assert abs(got - ref) <= tol, \
E   AssertionError: GS-C b3: got 6489.4000 cfs, expected 7360.8387 cfs (tol 14.7217 cfs)
E   assert 871.4387500000003 <= 14.721678
E    +  where 871.4387500000003 = abs((6489.4 - 7360.83875))
___________________________ test_block_mean[GS-C-b4] ___________________________
/tests/test_outputs.py:80: in test_block_mean
    assert abs(got - ref) <= tol, \
E   AssertionError: GS-C b4: got 7395.1000 cfs, expected 8452.7090 cfs (tol 16.9054 cfs)
E   assert 1057.6089583333323 <= 16.905418
E    +  where 1057.6089583333323 = abs((7395.1 - 8452.708958333333))
---------------- generated xml file: /logs/verifier/results.xml ----------------
=========================== short test summary info ============================
FAILED ::test_block_mean[GS-A-b1] - AssertionError: GS-A b1: got 6502.5000 cf...
FAILED ::test_block_mean[GS-A-b2] - AssertionError: GS-A b2: got 7469.0000 cf...
FAILED ::test_block_mean[GS-A-b3] - AssertionError: GS-A b3: got 8177.1000 cf...
FAILED ::test_block_mean[GS-A-b4] - AssertionError: GS-A b4: got 8711.9000 cf...
FAILED ::test_block_mean[GS-B-b1] - AssertionError: GS-B b1: got 128118.4000 ...
FAILED ::test_block_mean[GS-B-b2] - AssertionError: GS-B b2: got 167311.4000 ...
FAILED ::test_block_mean[GS-B-b3] - AssertionError: GS-B b3: got 204882.0000 ...
FAILED ::test_block_mean[GS-B-b4] - AssertionError: GS-B b4: got 221501.1000 ...
FAILED ::test_block_mean[GS-C-b1] - AssertionError: GS-C b1: got 5608.2000 cf...
FAILED ::test_block_mean[GS-C-b2] - AssertionError: GS-C b2: got 5972.3000 cf...
FAILED ::test_block_mean[GS-C-b3] - AssertionError: GS-C b3: got 6489.4000 cf...
FAILED ::test_block_mean[GS-C-b4] - AssertionError: GS-C b4: got 7395.1000 cf...
========================= 12 failed, 4 passed in 0.06s =========================
