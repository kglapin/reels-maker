"""Enable python -m reels_maker as an alternative to the installed command."""
from .cli import main

raise SystemExit(main())
