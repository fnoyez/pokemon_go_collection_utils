import io

import pytest
from PIL import Image

from pokemon_go_collection.sources import icons as icons_m


def get_crop_icon_to_content_test_data():
    test_cases = [
        {
            "id": "margins-cropped",
            "canvas_size": (256, 256),
            "content_box": (78, 130, 194, 226),
            "expected_size": (116, 96),
        },
        {
            "id": "already-cropped-unchanged",
            "canvas_size": (98, 106),
            "content_box": (0, 0, 98, 106),
            "expected_size": (98, 106),
        },
    ]

    return [
        pytest.param(
            test_case["canvas_size"],
            test_case["content_box"],
            test_case["expected_size"],
            id=test_case["id"],
        )
        for test_case in test_cases
    ]


@pytest.mark.parametrize(
    "canvas_size,content_box,expected_size",
    get_crop_icon_to_content_test_data(),
)
def test_crop_icon_to_content(canvas_size, content_box, expected_size):
    content = make_icon(canvas_size, content_box)

    actual_size = Image.open(io.BytesIO(icons_m.crop_icon_to_content(content))).size

    assert actual_size == expected_size


def make_icon(canvas_size, content_box):
    image = Image.new("RGBA", canvas_size, (0, 0, 0, 0))
    image.paste((255, 200, 0, 255), content_box)
    output = io.BytesIO()
    image.save(output, format="PNG")
    return output.getvalue()
