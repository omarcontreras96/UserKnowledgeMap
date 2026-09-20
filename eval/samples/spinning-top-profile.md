# Spinning top, with MBA profile injected by SessionStart hook

Prompt: Why does a spinning top stay upright instead of falling over?
Model: Claude Code default, headless, profile = data/profile.persona-mba.json. 2026-09-20.

A spinning top stays up because gravity's attempt to tip it gets redirected into a slow sideways swing of its axis instead of a fall. Two ideas make that work.

**Spin momentum.** You already know that a moving object keeps moving unless something pushes on it, and that a heavy fast object is hard to redirect. Physicists call this momentum. A spinning object has a rotational version of the same thing, called angular momentum. Think of it as an arrow pointing along the axle: the faster and heavier the spin, the longer the arrow. The rule is the same as for a rolling ball: a push does not cancel the existing motion, it only nudges it. If a ball is rolling fast east and you give it a short shove north, it veers slightly north-east rather than turning around. Likewise, a small push on a fast-spinning top nudges the direction of its axle a little, instead of flipping it.

**Precession.** Now consider what gravity is doing. A non-spinning top falls by rotating about a horizontal line through the point where it touches the table. That fall is itself a small rotation, with its own short arrow lying horizontally. When you add that small horizontal arrow to the top's big vertical spin arrow, the combined arrow ends up tilted slightly sideways, not downward. So the axle drifts sideways. Gravity keeps pushing, the axle keeps drifting, and the result is that the tip of the axle traces a slow circle around the vertical. That circling is called precession. Gravity's effort is spent moving the axle around the circle rather than bringing it down.

Two things follow from this:

- **Fast spin, slow wobble.** The bigger the spin arrow, the smaller the relative effect of gravity's nudge, so a fast top precesses slowly and looks almost perfectly still.
- **The fall at the end.** Friction with the table and the air gradually shrinks the spin arrow. As it shrinks, gravity's nudge becomes proportionally larger, the precession speeds up and gets wobbly, and eventually the spin is too small to redirect the fall. Then the top drops.

The same effect keeps a rolling bicycle wheel upright and keeps a gyroscope in a ship or aircraft pointing in a fixed direction.
