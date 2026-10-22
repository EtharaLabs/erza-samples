test cases passed : 0/12
Score             : 0.0000
pass@1            : 0
E   AssertionError: /root/results.json does not exist
E   assert False
E    +  where False = <function exists at 0xffffa98439c0>('/root/results.json')
E    +    where <function exists at 0xffffa98439c0> = <module 'posixpath' (frozen)>.exists
E    +      where <module 'posixpath' (frozen)> = os.path
___________________________ test_block_mean[GS-C-b3] ___________________________
/tests/test_outputs.py:69: in test_block_mean
    results = _load_results()
/tests/test_outputs.py:33: in _load_results
    assert os.path.exists(RESULTS_PATH), "%s does not exist" % RESULTS_PATH
E   AssertionError: /root/results.json does not exist
E   assert False
E    +  where False = <function exists at 0xffffa98439c0>('/root/results.json')
E    +    where <function exists at 0xffffa98439c0> = <module 'posixpath' (frozen)>.exists
E    +      where <module 'posixpath' (frozen)> = os.path
___________________________ test_block_mean[GS-C-b4] ___________________________
/tests/test_outputs.py:69: in test_block_mean
    results = _load_results()
/tests/test_outputs.py:33: in _load_results
    assert os.path.exists(RESULTS_PATH), "%s does not exist" % RESULTS_PATH
E   AssertionError: /root/results.json does not exist
E   assert False
E    +  where False = <function exists at 0xffffa98439c0>('/root/results.json')
E    +    where <function exists at 0xffffa98439c0> = <module 'posixpath' (frozen)>.exists
E    +      where <module 'posixpath' (frozen)> = os.path
---------------- generated xml file: /logs/verifier/results.xml ----------------
=========================== short test summary info ============================
FAILED ::test_block_mean[GS-A-b1] - AssertionError: /root/results.json does n...
FAILED ::test_block_mean[GS-A-b2] - AssertionError: /root/results.json does n...
FAILED ::test_block_mean[GS-A-b3] - AssertionError: /root/results.json does n...
FAILED ::test_block_mean[GS-A-b4] - AssertionError: /root/results.json does n...
FAILED ::test_block_mean[GS-B-b1] - AssertionError: /root/results.json does n...
FAILED ::test_block_mean[GS-B-b2] - AssertionError: /root/results.json does n...
FAILED ::test_block_mean[GS-B-b3] - AssertionError: /root/results.json does n...
FAILED ::test_block_mean[GS-B-b4] - AssertionError: /root/results.json does n...
FAILED ::test_block_mean[GS-C-b1] - AssertionError: /root/results.json does n...
FAILED ::test_block_mean[GS-C-b2] - AssertionError: /root/results.json does n...
FAILED ::test_block_mean[GS-C-b3] - AssertionError: /root/results.json does n...
FAILED ::test_block_mean[GS-C-b4] - AssertionError: /root/results.json does n...
========================= 12 failed, 4 passed in 0.07s =========================
