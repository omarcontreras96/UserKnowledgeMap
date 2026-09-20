# Spinning top, control (no profile injected)

Prompt: Why does a spinning top stay upright instead of falling over?
Model: Claude Code default, headless, SessionStart hook pointed at an empty KNOWLEDGE_HOME. 2026-09-20.

A spinning top stays up because of angular momentum and the way torque acts on it. It does not defeat gravity. Gravity still pulls on it, but the pull produces a sideways motion instead of a fall.

Here is the chain of reasoning:

- **A spinning top has angular momentum**, a vector that points along its spin axis. The faster and heavier the spin, the bigger this vector.
- **Gravity applies a torque.** The top's weight acts at its center of mass, above the contact point on the floor. If the top is tilted, that off-center weight tries to rotate it further over.
- **Torque changes angular momentum in the direction of the torque**, not in the direction you'd intuitively expect. Gravity's torque points horizontally, at right angles to both the tilt and the vertical. So it nudges the tip of the angular momentum vector sideways.
- **Sideways nudges make the axis sweep in a circle.** The tilt never grows. Instead the axis traces a slow cone around the vertical. That circling motion is precession, the wobble you see on a real top.

A stationary top has no angular momentum along its axis, so gravity's torque simply rotates it over and it falls. A spinning one converts the same torque into precession.

Friction at the tip and air drag slowly bleed off spin. As angular momentum shrinks, the precession gets faster and wider, the wobble grows, and eventually the top tips over. That is why a top always falls in the end, just not right away.

A gyroscope, a bicycle wheel, and the Earth's axial wobble all work by the same rule.
