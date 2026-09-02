test cases passed : 0/12
Score             : 0.0000
pass@1            : 0
E   AssertionError: /root/results.json does not exist
E   assert False
E    +  where False = <function exists at 0xffffa3be39c0>('/root/results.json')
E    +    where <function exists at 0xffffa3be39c0> = <module 'posixpath' (frozen)>.exists
E    +      where <module 'posixpath' (frozen)> = os.path
_____________________________ test_height[TG-C-t3] _____________________________
/tests/test_outputs.py:29: in test_height
    preds = _load_results()
/tests/test_outputs.py:18: in _load_results
    assert os.path.exists(RESULTS_PATH), f"{RESULTS_PATH} does not exist"
E   AssertionError: /root/results.json does not exist
E   assert False
E    +  where False = <function exists at 0xffffa3be39c0>('/root/results.json')
E    +    where <function exists at 0xffffa3be39c0> = <module 'posixpath' (frozen)>.exists
E    +      where <module 'posixpath' (frozen)> = os.path
_____________________________ test_height[TG-C-t4] _____________________________
/tests/test_outputs.py:29: in test_height
    preds = _load_results()
/tests/test_outputs.py:18: in _load_results
    assert os.path.exists(RESULTS_PATH), f"{RESULTS_PATH} does not exist"
E   AssertionError: /root/results.json does not exist
E   assert False
E    +  where False = <function exists at 0xffffa3be39c0>('/root/results.json')
E    +    where <function exists at 0xffffa3be39c0> = <module 'posixpath' (frozen)>.exists
E    +      where <module 'posixpath' (frozen)> = os.path
---------------- generated xml file: /logs/verifier/results.xml ----------------
=========================== short test summary info ============================
FAILED ::test_height[TG-A-t1] - AssertionError: /root/results.json does not e...
FAILED ::test_height[TG-A-t2] - AssertionError: /root/results.json does not e...
FAILED ::test_height[TG-A-t3] - AssertionError: /root/results.json does not e...
FAILED ::test_height[TG-A-t4] - AssertionError: /root/results.json does not e...
FAILED ::test_height[TG-B-t1] - AssertionError: /root/results.json does not e...
FAILED ::test_height[TG-B-t2] - AssertionError: /root/results.json does not e...
FAILED ::test_height[TG-B-t3] - AssertionError: /root/results.json does not e...
FAILED ::test_height[TG-B-t4] - AssertionError: /root/results.json does not e...
FAILED ::test_height[TG-C-t1] - AssertionError: /root/results.json does not e...
FAILED ::test_height[TG-C-t2] - AssertionError: /root/results.json does not e...
FAILED ::test_height[TG-C-t3] - AssertionError: /root/results.json does not e...
FAILED ::test_height[TG-C-t4] - AssertionError: /root/results.json does not e...
========================= 12 failed, 3 passed in 0.04s =========================
