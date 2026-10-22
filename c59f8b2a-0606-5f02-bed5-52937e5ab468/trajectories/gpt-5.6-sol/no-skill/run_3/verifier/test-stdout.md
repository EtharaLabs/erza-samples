test cases passed : 0/12
Score             : 0.0000
pass@1            : 0
E   AssertionError: /root/results.json does not exist
E   assert False
E    +  where False = <function exists at 0xffff9ba239c0>('/root/results.json')
E    +    where <function exists at 0xffff9ba239c0> = <module 'posixpath' (frozen)>.exists
E    +      where <module 'posixpath' (frozen)> = os.path
____________________ test_phase_centre_correction[ANT-C-s3] ____________________
/tests/test_outputs.py:66: in test_phase_centre_correction
    results = _load_results()
/tests/test_outputs.py:31: in _load_results
    assert os.path.exists(RESULTS_PATH), "%s does not exist" % RESULTS_PATH
E   AssertionError: /root/results.json does not exist
E   assert False
E    +  where False = <function exists at 0xffff9ba239c0>('/root/results.json')
E    +    where <function exists at 0xffff9ba239c0> = <module 'posixpath' (frozen)>.exists
E    +      where <module 'posixpath' (frozen)> = os.path
____________________ test_phase_centre_correction[ANT-C-s4] ____________________
/tests/test_outputs.py:66: in test_phase_centre_correction
    results = _load_results()
/tests/test_outputs.py:31: in _load_results
    assert os.path.exists(RESULTS_PATH), "%s does not exist" % RESULTS_PATH
E   AssertionError: /root/results.json does not exist
E   assert False
E    +  where False = <function exists at 0xffff9ba239c0>('/root/results.json')
E    +    where <function exists at 0xffff9ba239c0> = <module 'posixpath' (frozen)>.exists
E    +      where <module 'posixpath' (frozen)> = os.path
---------------- generated xml file: /logs/verifier/results.xml ----------------
=========================== short test summary info ============================
FAILED ::test_phase_centre_correction[ANT-A-s1] - AssertionError: /root/resul...
FAILED ::test_phase_centre_correction[ANT-A-s2] - AssertionError: /root/resul...
FAILED ::test_phase_centre_correction[ANT-A-s3] - AssertionError: /root/resul...
FAILED ::test_phase_centre_correction[ANT-A-s4] - AssertionError: /root/resul...
FAILED ::test_phase_centre_correction[ANT-B-s1] - AssertionError: /root/resul...
FAILED ::test_phase_centre_correction[ANT-B-s2] - AssertionError: /root/resul...
FAILED ::test_phase_centre_correction[ANT-B-s3] - AssertionError: /root/resul...
FAILED ::test_phase_centre_correction[ANT-B-s4] - AssertionError: /root/resul...
FAILED ::test_phase_centre_correction[ANT-C-s1] - AssertionError: /root/resul...
FAILED ::test_phase_centre_correction[ANT-C-s2] - AssertionError: /root/resul...
FAILED ::test_phase_centre_correction[ANT-C-s3] - AssertionError: /root/resul...
FAILED ::test_phase_centre_correction[ANT-C-s4] - AssertionError: /root/resul...
========================= 12 failed, 5 passed in 0.08s =========================
