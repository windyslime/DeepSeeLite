from deepsee.composer.vision_context import MAX_IMAGES_PER_REQUEST
from deepsee.pipeline import image
from deepsee.pipeline.policy import (
    MAX_IMAGE_BYTES,
    MAX_IMAGE_PIXELS,
    MAX_IMAGES_PER_REQUEST as POLICY_MAX_IMAGES_PER_REQUEST,
    SUPPORTED_IMAGE_FORMATS,
)


def test_public_image_aliases_match_canonical_policy():
    assert image.MAX_IMAGE_BYTES == MAX_IMAGE_BYTES
    assert image.MAX_DECODE_PIXELS == MAX_IMAGE_PIXELS
    assert image.SUPPORTED_FORMATS == SUPPORTED_IMAGE_FORMATS
    assert MAX_IMAGES_PER_REQUEST == POLICY_MAX_IMAGES_PER_REQUEST
