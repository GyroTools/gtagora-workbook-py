from typing import List

import base64

MASK_TYPE_EMPTY = 0
MASK_TYPE_FILLED = 1
MASK_TYPE_BITMASK1 = 2
MASK_TYPE_BITMASK2 = 3
MASK_TYPE_BITMASK3 = 4
MASK_TYPE_BYTE_ARRAY = 5
MASK_TYPE_REGULAR1 = 6
MASK_TYPE_REGULAR2 = 7
MASK_TYPE_REGULAR3 = 8


def _get_nr_bytes(mask_type):
    if mask_type in [MASK_TYPE_REGULAR2, MASK_TYPE_BITMASK2]:
        return 2, [8, 0]
    elif mask_type in [MASK_TYPE_REGULAR3, MASK_TYPE_BITMASK3]:
        return 3, [16, 8, 0]
    else:
        return 1, [0]


def decode_mask(b64mask, length):
    encoded_mask = base64.b64decode(b64mask)

    mask = [0] * length
    if encoded_mask:
        mask_type = encoded_mask[0]
        nr_bytes, shifts = _get_nr_bytes(mask_type)

        if mask_type == MASK_TYPE_EMPTY:
            return mask
        elif mask_type == MASK_TYPE_FILLED:
            return [1] * length
        elif mask_type == MASK_TYPE_BYTE_ARRAY:
            return list(encoded_mask[1:length + 1])
        elif mask_type in [MASK_TYPE_BITMASK1, MASK_TYPE_BITMASK2, MASK_TYPE_BITMASK3]:
            label = encoded_mask[1]
            target_index = int.from_bytes(encoded_mask[2:5], byteorder='big')
            source_index = 5
            entries = (len(encoded_mask) - 5) // nr_bytes

            values = encoded_mask[source_index:]
            run_lengths_target_inds = [0] * entries
            for i in range(entries):
                for b in range(nr_bytes):
                    shift = shifts[b]
                    run_lengths_target_inds[i] += values[i * nr_bytes + b] << shift

            for i in range(0, len(run_lengths_target_inds), 2):
                run_length = run_lengths_target_inds[i]
                target_index_increment = run_lengths_target_inds[i + 1] if i + 1 < len(run_lengths_target_inds) else 0
                mask[target_index:target_index + run_length] = [label] * run_length
                target_index += run_length + target_index_increment

        elif mask_type in [MASK_TYPE_REGULAR1, MASK_TYPE_REGULAR2, MASK_TYPE_REGULAR3]:
            target_index = 0
            label = encoded_mask[1]
            run_length = int.from_bytes(encoded_mask[2:5], byteorder='big')
            source_index = 5
            mask[target_index:target_index + run_length] = [label] * run_length
            target_index += run_length
            step = nr_bytes + 1
            entries = (len(encoded_mask) - 5) // step

            values = encoded_mask[source_index:]
            for i in range(entries):
                label = values[i * step]
                run_length = 0
                for b in range(nr_bytes):
                    shift = shifts[b]
                    run_length += values[i * step + b + 1] << shift
                mask[target_index:target_index + run_length] = [label] * run_length
                target_index += run_length

    return mask
