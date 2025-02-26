from typing import List

import base64
import array 

MASK_TYPE_EMPTY = 0
MASK_TYPE_FILLED = 1
MASK_TYPE_BITMASK1 = 2
MASK_TYPE_BITMASK2 = 3
MASK_TYPE_BITMASK3 = 4
MASK_TYPE_BYTE_ARRAY = 5
MASK_TYPE_REGULAR1 = 6
MASK_TYPE_REGULAR2 = 7
MASK_TYPE_REGULAR3 = 8

import base64

def compress_slice_rle(encode):
    values = None

    if len(encode) == 1 and encode[0] == MASK_TYPE_EMPTY:
        values = bytearray(1)
        values[0] = MASK_TYPE_EMPTY
    
    elif len(encode) == 2 and encode[0] == MASK_TYPE_FILLED:
        values = bytearray(2)
        values[0] = MASK_TYPE_FILLED
        values[1] = encode[1]

    elif len(encode) >= 2 and MASK_TYPE_BITMASK1 <= encode[0] <= MASK_TYPE_REGULAR3:
        values = bytearray(len(encode))
        for v_index in range(len(encode)):
            values[v_index] = encode[v_index]

    return base64.b64encode(bytes(values)).decode('utf-8')


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
            return [encoded_mask[1]] * length
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

def encode_mask(mask_array):

    v_label_stack = []
    v_length_stack = []
    v_index = 0
    new_mask = None

    while v_index < len(mask_array):
        v_current_value = mask_array[v_index]
        v_length = 1
        v_index += 1

        while v_index < len(mask_array) and mask_array[v_index] == v_current_value:
            v_index += 1
            v_length += 1
        if v_index < len(mask_array) or v_current_value != 0:
            # do not store trailing 0's
            v_label_stack.append(v_current_value)
            v_length_stack.append(v_length)

    v_set = set(v for v in v_label_stack if v != 0)
    v_max_length = 0
    for length in v_length_stack[1:]:
        if length > v_max_length:
            v_max_length = length


    v_length_byte_size = 3
    if v_max_length < 256:
        v_length_byte_size = 1
    elif v_max_length < 65536:
        v_length_byte_size = 2

    if len(v_label_stack) == 0:
        # empty mask
        new_mask = compress_slice_rle([MASK_TYPE_EMPTY])
    elif len(v_label_stack) == 1 and v_length_stack[0] == len(mask_array):
        # homogeneous mask
        new_mask = compress_slice_rle([MASK_TYPE_FILLED, v_label_stack[0]])
    elif len(v_label_stack) > len(mask_array) / 4:
        # byte ARRAY
        new_mask = compress_slice_rle([MASK_TYPE_BYTE_ARRAY] + mask_array)
    else:
        if len(v_set) == 1:
            # bit mask
            v_first = 0
            v_label = v_label_stack[0]
            if v_label_stack[0] == 0:
                # starts with 0, this is implicit, remove first
                v_first = v_length_stack.pop(0)
                v_label = v_label_stack[1]

            if v_length_byte_size == 1:
                new_mask = compress_slice_rle([
                    MASK_TYPE_BITMASK1,
                    v_label,
                    (v_first >> 16) & 255,
                    (v_first >> 8) & 255,
                    v_first & 255,
                    *v_length_stack
                ])
            elif v_length_byte_size == 2:
                v_length2 = []
                for v_val in v_length_stack:
                    v_length2.append((v_val >> 8) & 255)
                    v_length2.append(v_val & 255)
                new_mask = compress_slice_rle([
                    MASK_TYPE_BITMASK2,
                    v_label,
                    (v_first >> 16) & 255,
                    (v_first >> 8) & 255,
                    v_first & 255,
                    *v_length2
                ])
            elif v_length_byte_size == 3:
                v_length3 = []
                for v_val in v_length_stack:
                    v_length3.append((v_val >> 16) & 255)
                    v_length3.append((v_val >> 8) & 255)
                    v_length3.append(v_val & 255)
                new_mask = compress_slice_rle([
                    MASK_TYPE_BITMASK3,
                    v_label,
                    (v_first >> 16) & 255,
                    (v_first >> 8) & 255,
                    v_first & 255,
                    *v_length3
                ])
        else:
            # normal
            v_data_array = [
                v_label_stack[0],
                (v_length_stack[0] >> 16) & 255,
                (v_length_stack[0] >> 8) & 255,
                v_length_stack[0] & 255
            ]

            if v_length_byte_size == 1:
                for i in range(1, len(v_label_stack)):
                    v_data_array.append(v_label_stack[i])
                    v_data_array.append(v_length_stack[i])
                new_mask = compress_slice_rle([MASK_TYPE_REGULAR1] + v_data_array)
            elif v_length_byte_size == 2:
                for i in range(1, len(v_label_stack)):
                    v_data_array.append(v_label_stack[i])
                    v_data_array.append((v_length_stack[i] >> 8) & 255)
                    v_data_array.append(v_length_stack[i] & 255)
                new_mask = compress_slice_rle([MASK_TYPE_REGULAR2] + v_data_array)
            elif v_length_byte_size == 3:
                for i in range(1, len(v_label_stack)):
                    v_data_array.append(v_label_stack[i])
                    v_data_array.append((v_length_stack[i] >> 16) & 255)
                    v_data_array.append((v_length_stack[i] >> 8) & 255)
                    v_data_array.append(v_length_stack[i] & 255)
                new_mask = compress_slice_rle([MASK_TYPE_REGULAR3] + v_data_array)

    return new_mask


