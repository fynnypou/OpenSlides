from typing import Any, Dict

from ..utils.projector import AllData, register_projector_slide


# Important: All functions have to be prune. This means, that thay can only
#            access the data, that they get as argument and do not have any
#            side effects. They are called from an async context. So they have
#            to be fast!


def mediafile_slide(all_data: AllData, element: Dict[str, Any]) -> Dict[str, Any]:
    """
    Slide for Mediafile.
    """
    return {"error": "TODO"}


def register_projector_slides() -> None:
    register_projector_slide("mediafiles/mediafile", mediafile_slide)
