# cython: language_level=3
# cython: boundscheck=False
# cython: wraparound=False
# cython: initializedcheck=False
# cython: nonecheck=False

"""Optional Cython TY6 decompression backend."""

import numpy as np
cimport numpy as np

from libc.stdint cimport int32_t, int64_t, uint32_t, uint64_t, uint8_t

np.import_array()


cdef inline int32_t _read_signed_int16(const uint8_t[:] data, Py_ssize_t pos):
    cdef uint32_t val = <uint32_t>data[pos] | (<uint32_t>data[pos + 1] << 8)
    if val >= 32768:
        val -= 65536
    return <int32_t>val


cdef inline int32_t _read_signed_int32(const uint8_t[:] data, Py_ssize_t pos):
    cdef int64_t val = <int64_t>data[pos]
    val |= <int64_t>data[pos + 1] << 8
    val |= <int64_t>data[pos + 2] << 16
    val |= <int64_t>data[pos + 3] << 24
    if val >= 2147483648:
        val -= 4294967296
    return <int32_t>val


cpdef np.ndarray decode_ty6_oneline(np.ndarray linedata, int w):
    """
    Decode a single TY6-compressed line.
    """
    cdef const uint8_t[:] data = linedata
    cdef np.ndarray ret = np.zeros(w, dtype=np.int32)
    cdef int32_t[:] out = ret
    cdef Py_ssize_t ipos = 0
    cdef Py_ssize_t opos = 0
    cdef Py_ssize_t i, j, k, block_start
    cdef int blocksize = 8
    cdef int short_overflow = 254
    cdef int long_overflow = 255
    cdef int short_overflow_signed = short_overflow - 127
    cdef int long_overflow_signed = long_overflow - 127
    cdef int firstpx
    cdef int px
    cdef int bittype
    cdef int nbit1
    cdef int nbit2
    cdef int nbit
    cdef int mask
    cdef object v1
    cdef object v2
    cdef int zero_at
    cdef int offset

    cdef Py_ssize_t nblock = (w - 1) // (blocksize * 2)
    cdef Py_ssize_t nrest = (w - 1) % (blocksize * 2)

    firstpx = data[ipos]
    ipos += 1
    if firstpx < short_overflow:
        out[opos] = firstpx - 127
    elif firstpx == long_overflow:
        out[opos] = _read_signed_int32(data, ipos)
        ipos += 4
    else:
        out[opos] = _read_signed_int16(data, ipos)
        ipos += 2
    opos += 1

    for k in range(nblock):
        bittype = data[ipos]
        nbit1 = bittype & 15
        nbit2 = (bittype >> 4) & 15
        ipos += 1

        zero_at = 0
        if nbit1 > 1:
            zero_at = (1 << (nbit1 - 1)) - 1

        v1 = 0
        for j in range(nbit1):
            v1 |= int(data[ipos]) << (8 * j)
            ipos += 1

        mask = (1 << nbit1) - 1
        for j in range(blocksize):
            out[opos] = (<int>((v1 >> (nbit1 * j)) & mask)) - zero_at
            opos += 1

        zero_at = 0
        if nbit2 > 1:
            zero_at = (1 << (nbit2 - 1)) - 1

        v2 = 0
        for j in range(nbit2):
            v2 |= int(data[ipos]) << (8 * j)
            ipos += 1

        mask = (1 << nbit2) - 1
        for j in range(blocksize):
            out[opos] = (<int>((v2 >> (nbit2 * j)) & mask)) - zero_at
            opos += 1

        block_start = opos - blocksize * 2
        for i in range(block_start, opos):
            offset = out[i]
            if offset >= short_overflow_signed:
                if offset >= long_overflow_signed:
                    offset = _read_signed_int32(data, ipos)
                    ipos += 4
                else:
                    offset = _read_signed_int16(data, ipos)
                    ipos += 2
            out[i] = out[i - 1] + offset

    for i in range(nrest):
        px = data[ipos]
        ipos += 1
        if px < short_overflow:
            out[opos] = out[opos - 1] + px - 127
        elif px == long_overflow:
            out[opos] = out[opos - 1] + _read_signed_int32(data, ipos)
            ipos += 4
        else:
            out[opos] = out[opos - 1] + _read_signed_int16(data, ipos)
            ipos += 2
        opos += 1

    return ret


cpdef np.ndarray decode_ty6_image(np.ndarray linedata, np.ndarray offsets, int ny, int nx):
    """
    Decode a full TY6-compressed image.
    """
    cdef np.ndarray image = np.zeros((ny, nx), dtype=np.int32)
    cdef const uint32_t[:] line_offsets = offsets
    cdef Py_ssize_t iy, line_start, line_end

    for iy in range(ny):
        line_start = line_offsets[iy]
        if iy < ny - 1:
            line_end = line_offsets[iy + 1]
            image[iy, :] = decode_ty6_oneline(linedata[line_start:line_end], nx)
        else:
            image[iy, :] = decode_ty6_oneline(linedata[line_start:], nx)

    return image
