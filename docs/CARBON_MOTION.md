# Carbon Motion in reels-maker

The ordinary StudioProject engine defaults to productive Carbon motion.
Current configuration, limitations, spacing, sequencing, adaptive timing,
explicit multi-key phases, spatial paths, bounded accent selection and limited
shared-object bridges are documented in [CARBON_ENGINE_DEFAULTS.md](CARBON_ENGINE_DEFAULTS.md).

The six source curves and six timing tokens remain in motionkit/carbon.py.
Advanced choreography is implemented in motionkit/carbon_choreography.py and
called by the regular Studio project build, not a parallel renderer.
Advanced settings are opt-in. Brand fonts/colors, source data and authored
narration cues are not replaced by IBM assets or UI-sized type scales.

This is not the entire Carbon Design System or an aesthetic-quality guarantee.
Native tests, full regressions and actual MP4 review remain release gates.
The approved standalone curve demonstrator is not full-engine acceptance.
