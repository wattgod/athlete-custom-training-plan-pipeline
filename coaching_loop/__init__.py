"""coaching_loop — CL-T0a read-only spike package.

New rolling orchestration layer per docs/COACHING_LOOP_SPEC.md. This
package is additive: it does not modify any existing pipeline module.
Exclusions (coaching_loop.exclusions) may be imported by other pipeline
code in future tickets; for T0a it is imported only within this package.
"""
