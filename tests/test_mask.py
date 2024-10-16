import pytest

from workbook.mask import decode_mask


@pytest.mark.parametrize('size_x, size_y, encoded_mask, expected_labels, expected_nr_pixels, expected_values', [
        (208, 256, 'AgEAaF8B', [1], 1, None),
        (208, 256, 'BwAAYEcJAAEAAZQNAAEABcEDAAEAAMABAAEAAagCAAE=', [1,2,3,9,13], 5, None),
        (208, 256, 'AgEAWDYEywbKBskHyAevAxcHrgUVB68FFQawBhMHsAcRB7IHDwizBw4HtQcMB7cHCwa5BwkGuwcIBrwHBwW+BwUGvwcEBsAHAgbCDsMMxQvGCsgJxwrGC8UMww/BBgIIvwYEB74HBQe9BgcIugcICLkGCgi3BgwItgYNCLQHDgizBhAIsgYRCLAGEwivBhQIrgYVCK0FFwisBRgHrQMaBssE', [1], 562, None),
        (208, 256, 'BwEAAAEAAM4CAAEAzmADAAEAAM4EAAE=', [1, 2, 3, 4], 4, (((0, 0), 1), ((207, 0), 2), ((0, 255), 3), ((207, 255), 4))),
    ])
def test_decode_mask(size_x, size_y, encoded_mask, expected_labels, expected_nr_pixels, expected_values):
    length = size_x * size_y
    decoded_mask = decode_mask(encoded_mask, length)
    non_zero_pixel = [label for label in decoded_mask if label != 0]
    assert len(decoded_mask) == length
    assert len(non_zero_pixel) == expected_nr_pixels
    assert list(set(non_zero_pixel)) == expected_labels
    if expected_values:
        for (x, y), label in expected_values:
            assert decoded_mask[x + y * size_x] == label
