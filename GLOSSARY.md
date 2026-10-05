# Agent Privacy Guard

A privacy layer that limits disclosure of sensitive values while keeping useful agent work possible.

## Language

**Sensitive value**:
A piece of information covered by the user's privacy policy, such as a personal identifier or a secret.
_Avoid_: Any number, any capitalized word

**Personal data**:
Information about a person whose disclosure the privacy policy restricts.
_Avoid_: Secret (the categories overlap but are not interchangeable)

**Secret**:
A value that grants access or exposes confidential credentials and needs stricter handling than ordinary personal data.
_Avoid_: Personal identifier

**Finding**:
A detected occurrence of a sensitive value, with its category and location in inspected content.
_Avoid_: Proof of complete detection

**Pseudonymization**:
Replacing a sensitive value with a token while retaining a controlled local mapping for authorized restoration.
_Avoid_: Anonymization

**Token**:
A replacement that allows the agent to refer to a sensitive value without receiving the original.
_Avoid_: Encrypted value

**Session vault**:
The locally protected collection of mappings belonging to one agent session.
_Avoid_: Agent memory, public cache

**Restoration**:
Replacing a session token with its original value for a specifically authorized destination.
_Avoid_: Unmask everything

**Inspection**:
Evaluating covered content before allowing it to cross a protected disclosure path.
_Avoid_: Instruction to the agent

**Covered path**:
A disclosure route whose interception and transformation behavior has been demonstrated for a specified supported environment.
_Avoid_: Every action, all tools (without evidence)

**Protected session**:
A session whose required covered paths and active policy have passed the compatibility checks, within documented limits.
_Avoid_: Hooks installed

**Degraded mode**:
A visible reduction in available detection or enforcement capability that requires an explicit policy decision.
_Avoid_: Protected normally

**Content-free journal**:
A record of control events that excludes inspected values, excerpts and reversible mappings.
_Avoid_: Audit of every document read

**Agent adapter**:
The integration that translates an agent's supported interactions into the privacy layer's inspection and restoration contract.
_Avoid_: Universal agent support
