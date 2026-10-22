test cases passed : 0/12
Score             : 0.0000
pass@1            : 0
E    +  where 0.41372400000000004 = abs((0.447 - 0.860724))
_____________________________ test_height[TG-C-t1] _____________________________
/tests/test_outputs.py:38: in test_height
    assert abs(got - ref) <= tol, f"{sid} @ {iso}: got {got:.4f} m, expected {ref:.4f} m (tol {tol} m)"
E   AssertionError: TG-C @ 2025-02-10T05:00:00Z: got 1.7200 m, expected -0.2583 m (tol 0.1 m)
E   assert 1.9782980000000001 <= 0.1
E    +  where 1.9782980000000001 = abs((1.72 - -0.258298))
_____________________________ test_height[TG-C-t2] _____________________________
/tests/test_outputs.py:38: in test_height
    assert abs(got - ref) <= tol, f"{sid} @ {iso}: got {got:.4f} m, expected {ref:.4f} m (tol {tol} m)"
E   AssertionError: TG-C @ 2025-05-18T16:00:00Z: got 1.7200 m, expected 1.5441 m (tol 0.1 m)
E   assert 0.17591 <= 0.1
E    +  where 0.17591 = abs((1.72 - 1.54409))
_____________________________ test_height[TG-C-t3] _____________________________
/tests/test_outputs.py:38: in test_height
    assert abs(got - ref) <= tol, f"{sid} @ {iso}: got {got:.4f} m, expected {ref:.4f} m (tol {tol} m)"
E   AssertionError: TG-C @ 2025-08-22T09:00:00Z: got 1.7200 m, expected 2.3730 m (tol 0.1 m)
E   assert 0.6529879999999999 <= 0.1
E    +  where 0.6529879999999999 = abs((1.72 - 2.372988))
_____________________________ test_height[TG-C-t4] _____________________________
/tests/test_outputs.py:38: in test_height
    assert abs(got - ref) <= tol, f"{sid} @ {iso}: got {got:.4f} m, expected {ref:.4f} m (tol {tol} m)"
E   AssertionError: TG-C @ 2025-11-14T21:00:00Z: got 1.7200 m, expected 1.9210 m (tol 0.1 m)
E   assert 0.20096000000000003 <= 0.1
E    +  where 0.20096000000000003 = abs((1.72 - 1.92096))
---------------- generated xml file: /logs/verifier/results.xml ----------------
=========================== short test summary info ============================
FAILED ::test_height[TG-A-t1] - AssertionError: TG-A @ 2025-02-10T05:00:00Z: ...
FAILED ::test_height[TG-A-t2] - AssertionError: TG-A @ 2025-05-18T16:00:00Z: ...
FAILED ::test_height[TG-A-t3] - AssertionError: TG-A @ 2025-08-22T09:00:00Z: ...
FAILED ::test_height[TG-A-t4] - AssertionError: TG-A @ 2025-11-14T21:00:00Z: ...
FAILED ::test_height[TG-B-t1] - AssertionError: TG-B @ 2025-02-10T05:00:00Z: ...
FAILED ::test_height[TG-B-t2] - AssertionError: TG-B @ 2025-05-18T16:00:00Z: ...
FAILED ::test_height[TG-B-t3] - AssertionError: TG-B @ 2025-08-22T09:00:00Z: ...
FAILED ::test_height[TG-B-t4] - AssertionError: TG-B @ 2025-11-14T21:00:00Z: ...
FAILED ::test_height[TG-C-t1] - AssertionError: TG-C @ 2025-02-10T05:00:00Z: ...
FAILED ::test_height[TG-C-t2] - AssertionError: TG-C @ 2025-05-18T16:00:00Z: ...
FAILED ::test_height[TG-C-t3] - AssertionError: TG-C @ 2025-08-22T09:00:00Z: ...
FAILED ::test_height[TG-C-t4] - AssertionError: TG-C @ 2025-11-14T21:00:00Z: ...
========================= 12 failed, 3 passed in 0.04s =========================
