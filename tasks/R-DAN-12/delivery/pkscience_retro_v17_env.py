"""Task-shipped environment integration for author 1.0.17, loaded before creation."""
import json
from pathlib import Path
from template_lbg import TemplateNestedLBG
from pkscience_eval.retro import RetroTripleLBG
from retro_v17 import install, REVISION

install(RetroTripleLBG)


class RevisionNestedLBG(TemplateNestedLBG):
    def __init__(self, environment_dir, *args, **kwargs):
        marker = Path(environment_dir).parent/'delivery/retro-runtime.json'
        if json.loads(marker.read_text()).get('runtime_revision') != REVISION:
            raise ValueError('Author 1.0.17 runtime requires its exact task revision')
        if not getattr(RetroTripleLBG, '_pkscience_v17_installed', False):
            raise RuntimeError('Author 1.0.17 runtime hook not installed')
        super().__init__(environment_dir, *args, **kwargs)
