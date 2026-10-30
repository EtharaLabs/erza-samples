#!/bin/bash
# FORGE-CANARY-BEGIN
# FORGE-CANARY-SLOT-1: 0000000000000000000000000000000000000000000000000000000000000000
# FORGE-CANARY-SLOT-2: 0000000000000000000000000000000000000000000000000000000000000000
# FORGE-CANARY-SLOT-3: 0000000000000000000000000000000000000000000000000000000000000000
# FORGE-CANARY-END
# Reference solution: apply the upstream fixes for regress#197 to #200 and boa#5572/#5574/#5575 to src/, then write the note.
set -euo pipefail
cd /workspace/regress
patch -p1 --no-backup-if-mismatch <<'PATCH'
diff --git a/src/classicalbacktrack.rs b/src/classicalbacktrack.rs
index 0e185d4..0197b70 100644
--- a/src/classicalbacktrack.rs
+++ b/src/classicalbacktrack.rs
@@ -137,23 +137,38 @@ impl<'a, Input: InputIndexer> MatchAttempter<'a, Input> {
         pos: Input::Position,
         loop_fields: &LoopFields,
         loop_data: &mut LoopData<Input::Position>,
+        iteration: usize,
     ) {
         bts.push(BacktrackInsn::SetLoopData {
             id: loop_fields.loop_id,
             data: *loop_data,
         });
-        loop_data.iters += 1;
+        loop_data.iters = iteration + 1;
         loop_data.entry = pos;
     }
 
+    /// Executes a loop starting at the given instruction pointer.
+    ///
+    /// # Arguments
+    ///
+    /// * `loop_fields` - Metadata describing the loop.
+    /// * `pos` - The current position in the input.
+    /// * `ip` - The instruction pointer of the loop itself.
+    /// * `iteration` - Which iteration of the loop this is.
+    ///   This is generally the same as `loop_data.iteration`, except on the `EnterLoop` instruction.
+    ///   In that case `iteration` is 0, and `loop_data.iteration` contains the iteration to restore.
+    ///
+    /// # Returns
+    ///
+    /// The next instruction pointer, or `None` if execution cannot continue.
     fn run_loop(
         &mut self,
         loop_fields: &'a LoopFields,
         pos: Input::Position,
         ip: IP,
+        iteration: usize,
     ) -> Option<IP> {
         let loop_data = &mut self.s.loops[loop_fields.loop_id as usize];
-        let iteration = loop_data.iters;
 
         let do_taken = iteration < loop_fields.max_iters;
         let do_not_taken = iteration >= loop_fields.min_iters;
@@ -180,7 +195,13 @@ impl<'a, Input: InputIndexer> MatchAttempter<'a, Input> {
             }
             (true, false) => {
                 // Only entering is viable.
-                MatchAttempter::prepare_to_enter_loop(&mut self.bts, pos, loop_fields, loop_data);
+                MatchAttempter::prepare_to_enter_loop(
+                    &mut self.bts,
+                    pos,
+                    loop_fields,
+                    loop_data,
+                    iteration,
+                );
                 Some(loop_taken_ip)
             }
             (true, true) if !loop_fields.greedy => {
@@ -190,7 +211,10 @@ impl<'a, Input: InputIndexer> MatchAttempter<'a, Input> {
                 self.bts.push(BacktrackInsn::EnterNonGreedyLoop {
                     ip,
                     orig_pos,
-                    data: *loop_data,
+                    data: LoopData {
+                        iters: iteration,
+                        entry: pos,
+                    },
                 });
                 Some(loop_not_taken_ip)
             }
@@ -201,7 +225,13 @@ impl<'a, Input: InputIndexer> MatchAttempter<'a, Input> {
                     ip: loop_not_taken_ip,
                     pos,
                 });
-                MatchAttempter::prepare_to_enter_loop(&mut self.bts, pos, loop_fields, loop_data);
+                MatchAttempter::prepare_to_enter_loop(
+                    &mut self.bts,
+                    pos,
+                    loop_fields,
+                    loop_data,
+                    iteration,
+                );
                 Some(loop_taken_ip)
             }
         }
@@ -570,11 +600,12 @@ impl<'a, Input: InputIndexer> MatchAttempter<'a, Input> {
                     };
                     let loop_data = self.s.loops.mat(loop_fields.loop_id as usize);
                     // Need to restore the position should we backtrack out of the loop (#131).
+                    // Also restore the count (#206).
                     *bt = BacktrackInsn::SetLoopData {
                         id: loop_fields.loop_id,
                         data: LoopData {
                             entry: orig_pos,
-                            ..data
+                            iters: loop_data.iters,
                         },
                     };
                     *loop_data = data;
@@ -583,6 +614,7 @@ impl<'a, Input: InputIndexer> MatchAttempter<'a, Input> {
                         *pos,
                         loop_fields,
                         loop_data,
+                        data.iters,
                     );
                     return true;
                 }
@@ -853,6 +885,10 @@ impl<'a, Input: InputIndexer> MatchAttempter<'a, Input> {
 
                     &Insn::EndCaptureGroup(cg_idx) => {
                         let cg = self.s.groups.mat(cg_idx as usize);
+                        self.bts.push(BacktrackInsn::SetCaptureGroup {
+                            id: cg_idx,
+                            data: *cg,
+                        });
                         if Dir::FORWARD {
                             debug_assert!(
                                 cg.start_matched(),
@@ -954,8 +990,8 @@ impl<'a, Input: InputIndexer> MatchAttempter<'a, Input> {
 
                     Insn::EnterLoop(fields) => {
                         // Entering a loop, not re-entering it.
-                        self.s.loops.mat(fields.loop_id as usize).iters = 0;
-                        match self.run_loop(fields, pos, ip) {
+                        // Pass 0 as this is the first iteration.
+                        match self.run_loop(fields, pos, ip, 0) {
                             Some(next_ip) => {
                                 ip = next_ip;
                                 continue 'nextinsn;
@@ -968,7 +1004,10 @@ impl<'a, Input: InputIndexer> MatchAttempter<'a, Input> {
 
                     &Insn::LoopAgain { begin } => {
                         let act = match re.insns.iat(begin as IP) {
-                            Insn::EnterLoop(fields) => self.run_loop(fields, pos, begin as IP),
+                            Insn::EnterLoop(fields) => {
+                                let iteration = self.s.loops.mat(fields.loop_id as usize).iters;
+                                self.run_loop(fields, pos, begin as IP, iteration)
+                            }
                             _ => rs_unreachable!("EnterLoop should always refer to loop field"),
                         };
                         match act {
diff --git a/src/ir.rs b/src/ir.rs
index ae0f5df..fc1093c 100644
--- a/src/ir.rs
+++ b/src/ir.rs
@@ -84,7 +84,7 @@ pub enum Node {
     /// Indices are 1-based. That is, it matches JS syntax: \1 is the first capture group,
     /// not everything.
     /// A backreference that logically may match multiple capture groups (through shared names)
-    /// are emitted through alternations of backreferences.
+    /// is emitted as a concatenation of backreferences.
     BackRef { group: u32, icase: bool },
 
     /// A bracket.
diff --git a/src/parse.rs b/src/parse.rs
index 40e1701..dd94df0 100644
--- a/src/parse.rs
+++ b/src/parse.rs
@@ -62,6 +62,19 @@ enum ClassAtom {
 struct ClassSet {
     codepoints: CodePointSet,
     alternatives: ClassSetAlternativeStrings,
+    /// Whether this ClassSet "may match strings."
+    /// This is required to emit errors when certain string-bearing ClassSets are negated.
+    /// This implements the "MayContainStrings" semantics from ECMA-262 - whether
+    /// the class always matches one character (false), or may match strings (true).
+    /// Note (per the spec) this does NOT interrogate the resulting class, but rather the
+    /// flag is flipped to true whenever a string-bearing operand is found in a position
+    /// that can contribute strings (e.g. union). Refer to the ECMA-262 spec for the gory details.
+    /// Note this can be true EVEN IF the ClassSet only ever matches one character;
+    /// the set `[\q{a|ab}--\q{ab}]` leaves only "a" but `may_contain_strings` is still
+    /// true because of the contribution of the string-bearing item.
+    /// In short, this is used exclusively to report syntax errors per the spec. It does not affect
+    /// what the class matches.
+    may_contain_strings: bool,
 }
 
 impl ClassSet {
@@ -69,10 +82,27 @@ impl ClassSet {
         ClassSet {
             codepoints: CodePointSet::new(),
             alternatives: ClassSetAlternativeStrings::new(),
+            may_contain_strings: false,
         }
     }
 
-    fn node(self, icase: bool, negate_set: bool) -> ir::Node {
+    /// Prepare this set to be inverted.
+    /// A negated class must not contain strings. The remaining alternatives
+    /// are single code points, so move them to the code point set, and clear
+    /// the alternatives set.
+    fn prepare_negation(&mut self) -> Result<(), Error> {
+        if self.may_contain_strings {
+            return error("Negated character class may contain strings");
+        }
+        for alternative in mem::take(&mut self.alternatives.0) {
+            // Should not contain an alternative with multiple code points, i.e. a string.
+            debug_assert_eq!(alternative.len(), 1, "Should only have single code points");
+            self.codepoints.add_one(alternative[0]);
+        }
+        Ok(())
+    }
+
+    fn node(mut self, icase: bool, negate_set: bool) -> ir::Node {
         let codepoints = if icase {
             unicode::add_icase_code_points(self.codepoints)
         } else {
@@ -88,11 +118,24 @@ impl ClassSet {
         } else if codepoints_empty {
             self.alternatives.into_node(icase)
         } else {
-            make_alt(Vec::from([self.alternatives.into_node(icase), bracket]))
+            // The empty string is the shortest alternative, so it must come
+            // after the single code points.
+            let has_empty = self.alternatives.0.iter().any(|s| s.is_empty());
+            self.alternatives.0.retain(|s| !s.is_empty());
+            let mut nodes = Vec::new();
+            if !self.alternatives.0.is_empty() {
+                nodes.push(self.alternatives.into_node(icase));
+            }
+            nodes.push(bracket);
+            if has_empty {
+                nodes.push(ir::Node::Empty);
+            }
+            make_alt(nodes)
         }
     }
 
     fn union_operand(&mut self, operand: ClassSetOperand) {
+        self.may_contain_strings |= operand.may_contain_strings();
         match operand {
             ClassSetOperand::ClassSetCharacter(c) => {
                 self.codepoints.add_one(c);
@@ -104,13 +147,14 @@ impl ClassSet {
                 self.codepoints.add_set(class.codepoints);
                 self.alternatives.extend(class.alternatives);
             }
-            ClassSetOperand::ClassStringDisjunction(s) => {
+            ClassSetOperand::ClassStringDisjunction(s, _) => {
                 self.alternatives.extend(s);
             }
         }
     }
 
     fn intersect_operand(&mut self, operand: ClassSetOperand) {
+        self.may_contain_strings &= operand.may_contain_strings();
         match operand {
             ClassSetOperand::ClassSetCharacter(c) => {
                 if self.codepoints.contains(c) {
@@ -162,7 +206,7 @@ impl ClassSet {
                 self.alternatives.intersect(&class.alternatives);
                 self.alternatives.extend(retained_alternatives);
             }
-            ClassSetOperand::ClassStringDisjunction(s) => {
+            ClassSetOperand::ClassStringDisjunction(s, _) => {
                 let mut retained = CodePointSet::new();
                 for alternative in &s.0 {
                     if alternative.len() == 1 && self.codepoints.contains(alternative[0]) {
@@ -209,7 +253,7 @@ impl ClassSet {
                 self.alternatives.remove(&alternatives_removed);
                 self.alternatives.remove(&class.alternatives);
             }
-            ClassSetOperand::ClassStringDisjunction(s) => {
+            ClassSetOperand::ClassStringDisjunction(s, _) => {
                 let mut to_remove = CodePointSet::new();
                 for alternative in &s.0 {
                     if alternative.len() == 1 && self.codepoints.contains(alternative[0]) {
@@ -229,7 +273,20 @@ enum ClassSetOperand {
     ClassSetCharacter(CodePoint),
     CharacterClassEscape(CodePointSet),
     Class(ClassSet),
-    ClassStringDisjunction(ClassSetAlternativeStrings),
+    /// The flag is the MayContainStrings static semantics of the operand.
+    ClassStringDisjunction(ClassSetAlternativeStrings, bool),
+}
+
+impl ClassSetOperand {
+    fn may_contain_strings(&self) -> bool {
+        match self {
+            ClassSetOperand::ClassSetCharacter(_) | ClassSetOperand::CharacterClassEscape(_) => {
+                false
+            }
+            ClassSetOperand::Class(class) => class.may_contain_strings,
+            ClassSetOperand::ClassStringDisjunction(_, may_contain_strings) => *may_contain_strings,
+        }
+    }
 }
 
 /// A list of strings matching some property, for use in 'v' regular expressions.
@@ -680,10 +737,11 @@ where
                 '[' if self.flags.unicode_sets => {
                     self.consume('[');
                     let negate_set = self.try_consume('^');
-                    result.push(
-                        self.consume_class_set_expression(negate_set)?
-                            .node(self.flags.icase, negate_set),
-                    );
+                    let mut class_set = self.consume_class_set_expression()?;
+                    if negate_set {
+                        class_set.prepare_negation()?;
+                    }
+                    result.push(class_set.node(self.flags.icase, negate_set));
                 }
 
                 '[' => {
@@ -1023,8 +1081,7 @@ where
     }
 
     // CharacterClass :: ClassContents :: ClassSetExpression
-    // `in_negated_class` forbids string operands. It does not invert the result.
-    fn consume_class_set_expression(&mut self, in_negated_class: bool) -> Result<ClassSet, Error> {
+    fn consume_class_set_expression(&mut self) -> Result<ClassSet, Error> {
         let mut result = ClassSet::new();
 
         let first = match self.peek() {
@@ -1032,7 +1089,7 @@ where
                 self.consume(']');
                 return Ok(result);
             }
-            Some(_) => self.consume_class_set_operand(in_negated_class)?,
+            Some(_) => self.consume_class_set_operand()?,
             None => {
                 return error("Unbalanced class set bracket");
             }
@@ -1050,16 +1107,9 @@ where
                 result.union_operand(first);
                 return Ok(result);
             }
-            Some(0x26 /* & */) => {
-                self.consume('&');
-                if self.peek() == Some(0x26 /* & */) {
-                    self.consume('&');
-                    result.union_operand(first.clone());
-                    ClassSetOperator::Intersection
-                } else {
-                    result.codepoints.add_one(0x26 /* & */);
-                    ClassSetOperator::Union
-                }
+            Some(0x26 /* & */) if self.try_consume_str("&&") => {
+                result.union_operand(first.clone());
+                ClassSetOperator::Intersection
             }
             Some(0x2D /* - */) => {
                 self.consume('-');
@@ -1071,7 +1121,7 @@ where
                     match first {
                         ClassSetOperand::ClassSetCharacter(first) => {
                             let ClassSetOperand::ClassSetCharacter(last) =
-                                self.consume_class_set_operand(in_negated_class)?
+                                self.consume_class_set_operand()?
                             else {
                                 return error("Invalid class set range");
                             };
@@ -1104,7 +1154,7 @@ where
                             self.consume(']');
                             return Ok(result);
                         }
-                        Some(_) => self.consume_class_set_operand(in_negated_class)?,
+                        Some(_) => self.consume_class_set_operand()?,
                         None => return error("Unbalanced class set bracket"),
                     };
                     if self.peek() == Some(0x2D /* - */) {
@@ -1112,7 +1162,7 @@ where
                         match operand {
                             ClassSetOperand::ClassSetCharacter(first) => {
                                 let ClassSetOperand::ClassSetCharacter(last) =
-                                    self.consume_class_set_operand(in_negated_class)?
+                                    self.consume_class_set_operand()?
                                 else {
                                     return error("Invalid class set range");
                                 };
@@ -1133,7 +1183,7 @@ where
             // ClassIntersection :: ClassSetOperand && [lookahead ≠ &]
             ClassSetOperator::Intersection => {
                 loop {
-                    let operand = self.consume_class_set_operand(in_negated_class)?;
+                    let operand = self.consume_class_set_operand()?;
                     result.intersect_operand(operand);
                     match self.next() {
                         Some(0x5D /* ] */) => return Ok(result),
@@ -1149,7 +1199,7 @@ where
             // ClassSubtraction :: ClassSubtraction -- ClassSetOperand
             ClassSetOperator::Subtraction => {
                 loop {
-                    let operand = self.consume_class_set_operand(in_negated_class)?;
+                    let operand = self.consume_class_set_operand()?;
                     result.subtract_operand(operand);
                     match self.next() {
                         Some(0x5D /* ] */) => return Ok(result),
@@ -1165,10 +1215,7 @@ where
         }
     }
 
-    fn consume_class_set_operand(
-        &mut self,
-        in_negated_class: bool,
-    ) -> Result<ClassSetOperand, Error> {
+    fn consume_class_set_operand(&mut self) -> Result<ClassSetOperand, Error> {
         use ClassSetOperand::*;
         let Some(cp) = self.peek() else {
             return error("Empty class set operand");
@@ -1183,8 +1230,14 @@ where
                 }
                 self.consume('[');
                 let negate_set = self.try_consume('^');
-                let mut result = self.consume_class_set_expression(negate_set)?;
+                let mut result = self.consume_class_set_expression()?;
                 if negate_set {
+                    result.prepare_negation()?;
+                    // With the i flag, the complement is computed after case
+                    // folding, so close the set under case before inverting.
+                    if self.flags.icase {
+                        result.codepoints = unicode::add_icase_code_points(result.codepoints);
+                    }
                     result.codepoints = result.codepoints.inverted();
                 }
                 self.depth -= 1;
@@ -1208,22 +1261,20 @@ where
                         }
                         let mut alternatives = Vec::new();
                         let mut alternative = Vec::new();
+                        // ClassString :: [empty] is a string, so it may contain strings too.
+                        let mut may_contain_strings = false;
                         loop {
                             match self.peek() {
                                 Some(0x7D /* } */) => {
                                     self.consume('}');
-                                    if !alternative.is_empty() {
-                                        alternatives.push(alternative.into_boxed_slice());
-                                    }
+                                    may_contain_strings |= alternative.len() != 1;
+                                    alternatives.push(alternative.into_boxed_slice());
                                     break;
                                 }
                                 Some(0x7C /* | */) => {
                                     self.consume('|');
-                                    if !alternative.is_empty() {
-                                        let alternative = mem::take(&mut alternative).into_boxed_slice();
-                                        alternatives.push(alternative);
-
-                                    }
+                                    may_contain_strings |= alternative.len() != 1;
+                                    alternatives.push(mem::take(&mut alternative).into_boxed_slice());
                                 }
                                 Some(_) => {
                                     alternative.push(self.consume_class_set_character()?);
@@ -1233,7 +1284,7 @@ where
                                 }
                             }
                         }
-                        Ok(ClassStringDisjunction(ClassSetAlternativeStrings(alternatives)))
+                        Ok(ClassStringDisjunction(ClassSetAlternativeStrings(alternatives), may_contain_strings))
                     }
                     // CharacterClassEscape :: d
                     0x64 /* d */ => {
@@ -1274,9 +1325,8 @@ where
                                     intervals.to_vec(),
                                 )))
                             }
-                            PropertyEscapeKind::StringSet(_) if in_negated_class => error("Invalid character escape"),
                             PropertyEscapeKind::StringSet(strings) => {
-                                Ok(ClassStringDisjunction(ClassSetAlternativeStrings(strings.iter().map(|s| Box::from(*s)).collect())))
+                                Ok(ClassStringDisjunction(ClassSetAlternativeStrings(strings.iter().map(|s| Box::from(*s)).collect()), true))
                             }
                         }
                     }
@@ -1714,20 +1764,21 @@ where
                         }
                     }
                     _ => {
-                        // Unusual case of multiple groups sharing a name: the backref should try each in turn.
-                        // Lower to alternations of backreferences. Reverse to keep it right-associative: a | (b | (c | d))...
+                        // Unusual case of multiple groups sharing a name. These groups are in
+                        // different alternatives, so at most one of them can participate. A
+                        // backreference to a group that did not participate matches the empty
+                        // string, so a concatenation of the backreferences matches exactly the
+                        // group that participated.
                         let icase = self.flags.icase;
-                        let backrefs =
+                        make_cat(
                             group_indices
                                 .iter()
-                                .rev()
                                 .map(|group_index| ir::Node::BackRef {
                                     group: *group_index + 1,
                                     icase,
-                                });
-                        backrefs
-                            .reduce(|right, left| ir::Node::Alt(Box::new(left), Box::new(right)))
-                            .unwrap()
+                                })
+                                .collect(),
+                        )
                     }
                 };
                 Ok(node)
PATCH
mkdir -p /workspace/output
cat > /workspace/output/ROOT_CAUSE.md <<'NOTE'
# Root cause: six faults across the class-set parser, backreference lowering, and the backtracker

## 1. The cause of each failure

- F1, a single `&` in a class set. The union loop in `parse.rs` treats a lone `&` as the start of an operator, keeps `&` and drops the operand before it, and rejects `&` as a range endpoint. In the 22.2.1 grammar only `&&` is an operator (ClassIntersection); a single `&` is a ClassSetCharacter. Examples under `v`: `[x&]` must match `x` and `&`; `[x&-z]` is a valid range.
- F2, negated classes with strings. A negated class complements only its code points, ignores its `\q{}` strings, drops empty `\q{}` alternatives, and never computes MayContainStrings. The 22.2.1.1 early errors make `[^` ClassContents `]` a SyntaxError when MayContainStrings of ClassContents is true, and 22.2.2.9 (ClassStringDisjunction, CompileCharacterClass) makes `\q{x}` the set `{x}`. Examples under `v`: `[^\q{x}]` must not match `x`; `[^\q{xy}]` must be a SyntaxError; `^[\q{}]$` must match the empty string.
- F3, case folding and complement under `v` and `i`. A nested negated class is inverted before case closure, so the enclosing class adds back case variants of the excluded characters. Section 22.2.2.9 (CompileToCharSet for NestedClass `[^` ClassContents `]`) applies MaybeSimpleCaseFolding and then CharacterComplement over AllCharacters, which under `v` and `i` holds only code points whose simple case folding is themselves. Examples under `iv`: `[[^k]]` must not match `K` or `k`; `[[^a]x]` must not match `A`.
- F4, duplicate-name backreferences. A backreference to a name shared by several groups is lowered to an alternation of backreferences, so the group that did not participate matches the empty string first. BackreferenceMatcher (22.2.2.7.2) uses the one defined group of the name. Example: `(?:(?<d>xy)|(?<d>xz))\k<d>` on `xzxz` must match `0..4`.
- F5, loop iteration state. `EnterLoop` resets the inner loop's iteration count without saving it, so backtracking into an earlier iteration of an enclosing loop restores the wrong count; the same lost count disables the empty-iteration check. RepeatMatcher (22.2.2.3.1) keeps each expansion's own state on backtrack and fails an empty iteration once min is reached. Examples: `(?:(?:b+)+){2}` on `bb` must match; `(?:(?:c?)*)*d` on `c` must end with no match, not exhaust the budget; `^(?:(?:y(?:z??))+)+$` must match `yz`.
- F6, capture undo on backtrack. `EndCaptureGroup` writes a group's end without pushing an undo entry, so after backtracking to another alternative a backreference sees the range written on the abandoned path. In 22.2.2 captures are part of the matcher state passed to the continuation, so an abandoned path leaves no trace. Examples: `(b|b\1)d` on `bbd` must match `1..3` with group 1 at `1..2`; the same shape inside lookbehind, such as `(?<=(b)(b|\1a|a\2))\1` on `baab`, must not match.

## 2. Why the crate's own tests passed

The tests in `tests/unicodesets.rs` covered single-level complements, strings outside negated classes, and `&&` but never a single `&`; the duplicate-name tests checked named group ranges, and the backreference case was a commented-out TODO; the loop and backreference tests never backtracked into an earlier outer iteration or across a group end.

## 3. Other affected patterns

F3: any negated nested class or `\P{...}` under `v` and `i` whose complement should exclude case variants. F2: every negated class with `\q{}` strings, empty `\q{}` alternatives, and the MayContainStrings early errors, including the subtraction rule that takes MayContainStrings from the first operand. F1: a single `&` anywhere in a class set, including range endpoints. F4: every backreference to a duplicated name, inside quantifiers and lookbehind. F5: nested quantifiers whose match needs backtracking into an earlier outer iteration, and nested quantifiers over bodies that can match empty. F6: every backreference evaluated after backtracking across the end of the group, forward or inside lookbehind.

## 4. What the repair changes

- F1: only `&&` starts an intersection; a single `&` is parsed as a class set character in the union loop.
- F2: the class-set tracks MayContainStrings per operand and expression (union: any; intersection: both; subtraction: first), raises the early error for a negated class that may contain strings, folds single-code-point strings into the code point set before complementing, and keeps the empty alternative after the single code points.
- F3: under `i`, the nested set is closed under case before it is inverted.
- F4: the backreference to a duplicated name is lowered to a concatenation of the backreferences, so the unset ones match empty and the set one matches.
- F5: entering a loop restores, on backtrack, the loop state it overwrites (upstream passes the iteration explicitly and reuses the SetLoopData entry).
- F6: ending a capture group pushes the group's old value onto the backtrack stack before writing the end.

## 5. Behaviours left unchanged

Patterns without `v` class sets, duplicate names, nested quantifiers, or backreferences after a group end; the UTF-16 and UCS-2 entry points; the budget API; the public API; and the existing tests.

## 6. How the correct results were determined for the patterns tested

For every pattern tested, from section 22.2 of the shipped specification: the grammar and early errors for syntax, CompileToCharSet with MaybeSimpleCaseFolding, CharacterComplement, and AllCharacters for class sets, and the Matcher, RepeatMatcher, and BackreferenceMatcher algorithms, applied by hand or by an executable transcription.

## 7. A check for each cause

Compare the engine with a transcription of the cited section 22.2 algorithms on generated patterns of each shape: nested complements under `iv`; negated classes with `\q{}` and the early errors; single `&` in class sets; duplicate-name backreferences; nested quantifiers that backtrack into earlier iterations or match empty, under a backtrack budget; backreferences after backtracking across a group end, forward and in lookbehind.

## 8. Interactions

F5 and F6 share the backtracking undo log: both are writes to matcher state without an undo entry, and a pattern can need both. F4 depends on unset backreferences matching empty, the same rule F6 restores. F2 and F3 both act on the complement step of a negated class set.

## 9. Not established

Whether `&&` and `--` under `i` and `v`, the Kelvin sign with `\b` under `iv`, and `i` without `u` or `v` on U+017F follow the specification.
NOTE
