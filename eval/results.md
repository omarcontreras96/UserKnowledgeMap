# Eval: does the knowledge profile change the explanation?

Generator: claude -p (configured default). Judge: gpt-5. Persona: mba. 10 questions x 3 conditions. Run 2026-09-20T23:53:00+00:00.

Conditions: **A** no learner info, **B** one-line bio, **C** full profile block (what the SessionStart hook injects). Lower is better for unexplained and followups; `new` should be <= 2 under C's rules; words shows whether C just makes answers longer.

## Means per condition

| condition | unexplained deps | followup questions | new concepts (defined) | words |
|---|---|---|---|---|
| A (none) | 4.30 | 4.10 | 6.70 | 380 |
| B (bio) | 1.40 | 2.70 | 7.00 | 430 |
| C (tree) | 0.90 | 2.10 | 6.70 | 421 |

### Same, only the six questions in areas the persona does not know

| condition | unexplained deps | followup questions | new concepts | words |
|---|---|---|---|---|
| A (none) | 5.50 | 5.50 | 7.83 | 336 |
| B (bio) | 1.50 | 3.00 | 8.00 | 384 |
| C (tree) | 0.83 | 2.50 | 5.83 | 414 |

## Per question (unexplained deps / followups)

| question | area | A | B | C |
|---|---|---|---|---|
| phys-top | physics (unknown) | 7 / 5 | 4 / 3 | 2 / 2 |
| phys-sky | physics (unknown) | 7 / 6 | 1 / 2 | 2 / 2 |
| math-deriv | calculus (unknown) | 5 / 4 | 0 / 4 | 0 / 4 |
| math-linind | linear algebra (unknown) | 1 / 4 | 0 / 3 | 0 / 3 |
| logic-contra | logic (unknown) | 1 / 3 | 0 / 2 | 0 / 3 |
| cs-bigo | algorithms (unknown) | 12 / 11 | 4 / 4 | 1 / 1 |
| lit-narrator | literature (exposed) | 7 / 2 | 4 / 3 | 1 / 1 |
| hist-bretton | modern history (exposed) + economics (known) | 3 / 3 | 1 / 2 | 3 / 3 |
| econ-monopoly | microeconomics (known, control) | 0 / 0 | 0 / 1 | 0 / 0 |
| econ-policy | macroeconomics (known, control) | 0 / 3 | 0 / 3 | 0 / 2 |

## What the learner got lost on (unexplained dependencies, by answer)

**phys-top** (physics (unknown)): Why does a spinning top stay upright instead of falling over?
- A: unexplained = ['angular momentum', 'center of mass', 'vector', 'direction of torque (torque vector/right-hand-rule idea)', 'gravitational torque', '“sleeps” (top spinning in place, rising vertical)', 'friction torque can raise the center of mass']; learner asks about = ['angular momentum', 'vector', 'direction of torque (torque vector/right-hand-rule idea)', 'center of mass', '“sleeps” (top spinning in place, rising vertical)']
- B: unexplained = ['Rotational momentum (amount of rotation a spinning object carries)', 'Gyroscope (device that uses spinning to maintain orientation)', 'Spin-stabilized satellites', 'Gyroscopes in navigation']; learner asks about = ['Rotational momentum (amount of rotation a spinning object carries)', 'Right-angle response of a spinning object to a push (moves 90° to the push)', 'Gyroscope (device that uses spinning to maintain orientation)']
- C: unexplained = ['vector cross products', 'linear algebra']; learner asks about = ['right-angle response of spin to a push (change is at right angles to the push)', 'precession (slow circling of the axis)']

**phys-sky** (physics (unknown)): Why is the sky blue but sunsets are red?
- A: unexplained = ['Wavelength', '1/λ^4 dependence (scattering strength vs wavelength)', 'Nanometer (nm) as a unit of light wavelength', 'The sun emits less violet than blue (solar spectrum intensity differences)', 'Red and orange end of the spectrum', 'Dust, smoke, volcanic aerosols (particles in air)', 'Absorption of shorter wavelengths by particles/air']; learner asks about = ['Wavelength', '1/λ^4 dependence (scattering strength vs wavelength)', 'Nanometer (nm) as a unit of light wavelength', 'Red and orange end of the spectrum', 'Dust, smoke, volcanic aerosols (particles in air)', 'Absorption of shorter wavelengths by particles/air']
- B: unexplained = ['The Sun emits less violet than other visible colors']; learner asks about = ['The Sun emits less violet than other visible colors', 'Wavelength of light (short = blue/violet, long = red/orange)']
- C: unexplained = ['Shorter vs longer light waves (blue has shorter wavelength than red)', 'Quantitative difference: blue is scattered ~5–6x more than red']; learner asks about = ['Shorter vs longer light waves (blue has shorter wavelength than red)', 'Quantitative difference: blue is scattered ~5–6x more than red']

**math-deriv** (calculus (unknown)): My analyst said the derivative of our cost function is zero at the optimum. What does that actually mean?
- A: unexplained = ['candidate points (solutions where derivative = 0)', 'second derivative', 'Lagrange multipliers', 'differentiability/derivative may not exist', 'second-order check']; learner asks about = ['second derivative', 'candidate points', 'Lagrange multipliers', 'local vs global minimum']
- B: unexplained = none; learner asks about = ['multiple inputs (slopes with respect to each input)', 'how to test minimum vs maximum without a graph', 'how to check for local vs global minimum in practice', 'how to detect a binding constraint']
- C: unexplained = none; learner asks about = ['second derivative', 'curve bends upward', 'boundary optimum', 'local vs global minimum']

**math-linind** (linear algebra (unknown)): A data scientist told me two of our KPIs are 'linearly dependent' so one is redundant. What does linearly dependent mean?
- A: unexplained = ['deterministic function (one variable computed exactly from another)']; learner asks about = ['deterministic function', 'weighted sum', 'whether A = 2×B + constant counts as linear dependence (constant offset/intercept)', 'how to test for linear dependence in data']
- B: unexplained = none; learner asks about = ['Test for linear dependence in practice', 'Decision rule when correlation is high but not perfect', 'Unstable coefficients (what it looks like in practice)']
- C: unexplained = none; learner asks about = ['how to test linear dependence', 'difference between linear dependence and correlation', 'which KPI to drop in regression']

**logic-contra** (logic (unknown)): What is a proof by contradiction, and why is it considered valid?
- A: unexplained = ['classical logic']; learner asks about = ['classical logic', 'law of the excluded middle', 'lowest terms']
- B: unexplained = none; learner asks about = ['law of the excluded middle', 'constructivists (constructive vs non-constructive proofs)']
- C: unexplained = none; learner asks about = ['Non-constructive existence proof (existence via contradiction without exhibiting an example)', 'Constructivists (constructivism in mathematics)', 'Valid reasoning (truth-preserving inference)']

**cs-bigo** (algorithms (unknown)): Our engineers say switching to an O(n log n) algorithm from an O(n^2) one will fix the slowdown. What do those notations mean and why would it help?
- A: unexplained = ['Algorithm', 'Logarithm (log)', 'Nested loop', 'Merge sort', 'Hash map', 'Sorted index', 'Nested scans', 'Database round trips', 'Lock contention', 'Memory pressure', 'Profile (performance profiling)', 'Code path']; learner asks about = ['Algorithm', 'Logarithm (log)', 'Nested loop', 'Merge sort', 'Hash map', 'Nested scans', 'Profile (performance profiling)', 'Database round trips', 'Lock contention', 'Memory pressure', 'Crossover point between O(n^2) and O(n log n)']
- B: unexplained = ['Algorithm', 'Nested loop', 'All-pairs comparison', 'Constant factors (hidden by Big-O)']; learner asks about = ['algorithm', 'nested loop', 'all-pairs comparison', 'constant factors']
- C: unexplained = ['Algorithm']; learner asks about = ['Algorithm']

**lit-narrator** (literature (exposed)): What is an unreliable narrator, and why would an author choose to use one?
- A: unexplained = ['Humbert Humbert (Lolita)', 'Lolita (novel)', 'Stevens (The Remains of the Day)', 'The Remains of the Day (novel)', 'Room (novel)', 'The Tell-Tale Heart', 'The Murder of Roger Ackroyd']; learner asks about = ['dramatic irony', 'first-person narration']
- B: unexplained = ['retroactive reframing', 'The Murder of Roger Ackroyd (example)', 'The Remains of the Day (example)', 'Rashomon (example)']; learner asks about = ['retroactive reframing', 'omniscient narrator', 'Rashomon (example)']
- C: unexplained = ['Rashomon (film/example of contradictory accounts)']; learner asks about = ['Rashomon']

**hist-bretton** (modern history (exposed) + economics (known)): Why did the Bretton Woods system collapse in the early 1970s?
- A: unexplained = ['Two-tier gold market', 'Fundamental disequilibrium (IMF term)', 'Eurodollar markets']; learner asks about = ['Two-tier gold market', 'Fundamental disequilibrium (IMF term)', 'Eurodollar markets']
- B: unexplained = ['Exchange rate bands (wider bands)']; learner asks about = ['Exchange rate bands (wider bands)', 'Smithsonian Agreement']
- C: unexplained = ['London Gold Pool', 'Two-tier gold market', 'Smithsonian Agreement']; learner asks about = ['London Gold Pool', 'Two-tier gold market', 'Smithsonian Agreement']

**econ-monopoly** (microeconomics (known, control)): Why does a monopolist produce less than a competitive market would, and who loses from that?
- A: unexplained = none; learner asks about = nothing
- B: unexplained = none; learner asks about = ['Deadweight loss']
- C: unexplained = none; learner asks about = nothing

**econ-policy** (macroeconomics (known, control)): When inflation is high, what is the difference between using fiscal policy and monetary policy to fight it?
- A: unexplained = none; learner asks about = ['Central bank balance sheet (shrinking the balance sheet)', 'Credit conditions (tightening)', 'Inflation expectations (anchoring)']
- B: unexplained = none; learner asks about = ['central bank balance sheet shrinking (quantitative tightening)', 'credit channel (transmission mechanism)', '2022–2023 US example of loose fiscal and rapid rate hikes']
- C: unexplained = none; learner asks about = ['central bank balance sheet', 'financial stability risk as a constraint on rate hikes']

## Method notes

- The judge holds the persona's profile (the lists, not the rules) and classifies every concept the answer relies on. `unexplained` counts concepts used without an inline definition that the persona does not know. `followups` counts 'what is X?' questions in a simulated next message.
- Generator and judge are different model families to reduce self-preference.
- n = 10 questions; treat differences under ~1 point as noise. Raw judgments are in results.json.
