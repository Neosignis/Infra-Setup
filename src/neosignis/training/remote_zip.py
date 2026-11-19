"""Bounded, seekable HTTP ranges over immutable multipart publisher ZIPs.

No full-part download, archive extraction, credentials or remote code execution.
ZIP CRC and local SHA256 are recorded; partial reads do NOT verify whole-part SHA.
"""
from collections import OrderedDict
import io
import re
import urllib.request


class MultipartRangeReader(io.RawIOBase):
    def __init__(self, parts, *, budget_bytes=128 * 1024**2, block_bytes=128 * 1024,
                 max_cache_blocks=32, opener=urllib.request.urlopen):
        super().__init__()
        if not parts or any(type(n) is not int or n < 1 for n in
                            (budget_bytes, block_bytes, max_cache_blocks)):
            raise ValueError('Positive transfer/cache limits and parts required')
        self.parts, self.offsets, total = [], [], 0
        for part in parts:
            if (type(part['size']) is not int or part['size'] < 1 or
                    not re.fullmatch(r'https://huggingface.co/[\w.-]+/[\w.-]+/resolve/[0-9a-f]{40}/[\w.-]+', part['url'])):
                raise ValueError('Expected immutable HTTPS publisher part and known byte count')
            self.parts.append(dict(part)); self.offsets.append(total)
            total += part['size']
        self.length, self.position = total, 0
        self.budget, self.block_bytes, self.max_cache = budget_bytes, block_bytes, max_cache_blocks
        self.transferred, self.requests, self.cache, self.opener = 0, 0, OrderedDict(), opener

    def readable(self):
        return True

    def seekable(self):
        return True

    def tell(self):
        return self.position

    def seek(self, offset, whence=0):
        if type(offset) is not int or whence not in (0, 1, 2):
            raise ValueError('Invalid seek')
        target = offset + (0 if whence == 0 else self.position if whence == 1 else self.length)
        if target < 0:
            raise ValueError('Negative seek')
        self.position = target
        return target

    def _block(self, number, block):
        key = number, block
        if key in self.cache:
            self.cache.move_to_end(key)
            return self.cache[key]
        part = self.parts[number]
        start, end = block * self.block_bytes, min((block + 1) * self.block_bytes, part['size']) - 1
        size = end - start + 1
        if self.transferred + size > self.budget:
            raise ValueError('HTTP transfer budget exhausted; no full archive fallback')
        # Distinct cache keys prevent intermediary reuse of the wrong range.
        url = part['url'] + f'?neosignis_range={start}-{end}'
        request = urllib.request.Request(url, headers={'Range': f'bytes={start}-{end}', 'Accept-Encoding': 'identity'})
        with self.opener(request, timeout=45) as response:
            expected = f'bytes {start}-{end}/{part["size"]}'
            if response.status != 206 or response.headers.get('Content-Range') != expected:
                raise ValueError('Server did not honor exact bounded range')
            if response.headers.get('Content-Encoding', 'identity') != 'identity':
                raise ValueError('Unexpected encoded range')
            data = response.read(size + 1)
            if len(data) != size:
                raise ValueError('Incomplete or oversized HTTP range')
        self.transferred += size; self.requests += 1
        self.cache[key] = data
        if len(self.cache) > self.max_cache:
            self.cache.popitem(last=False)
        return data

    def read(self, size=-1):
        if self.closed:
            raise ValueError('Reader is closed')
        if size is None or size < 0:
            size = self.length - self.position
        size = min(size, max(0, self.length - self.position))
        if size > 16 * 1024**2:
            raise ValueError('Single read exceeds 16 MiB bound')
        pieces = []
        while size:
            number = next(i for i, offset in reversed(list(enumerate(self.offsets))) if offset <= self.position)
            local = self.position - self.offsets[number]
            block, within = divmod(local, self.block_bytes)
            data = self._block(number, block)
            take = min(size, len(data) - within)
            pieces.append(data[within:within + take]); self.position += take; size -= take
        return b''.join(pieces)
