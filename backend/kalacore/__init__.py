# KalaCore – art pattern analysis engine for KalaOS
#
# Exposes the primary public entry-points from each phase module so callers
# can do:   from kalacore import analyze, compose, flow, …

from .pattern_engine import analyze
from .art_genome     import ArtGenome
from .ethics         import check_request as check_ethics
from .existential    import analyze_existential
from .kalacraft      import analyze_craft
from .kalasignal     import analyze_signal
from .kalacomposer   import compose
from .kalaflow       import flow
from .kalacustody    import custody
from .temporal       import analyze_temporal
from .kalavisual     import analyze_visual, generate_image_concept, animate_canvas_objects
from .kalaproducer   import produce
from .kalaanimation  import generate_animation_plan, parse_storyboard

__all__ = [
    "analyze",
    "ArtGenome",
    "check_ethics",
    "analyze_existential",
    "analyze_craft",
    "analyze_signal",
    "compose",
    "flow",
    "custody",
    "analyze_temporal",
    "analyze_visual",
    "generate_image_concept",
    "animate_canvas_objects",
    "produce",
    "generate_animation_plan",
    "parse_storyboard",
]
