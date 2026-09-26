import hashlib
from random import Random, seed
from typing import List, Final

from mmr import MountainRange, LayerKey

BLOCK_LENGTH: Final[int] = 65_536

rnd = Random()

def gen_block(seed: int, length: int) -> bytes:
    # Yes, this is horribly inefficient.
    rnd.seed(seed)
    return rnd.randbytes(length)

def gen_blocks(n_blocks: int) -> List[bytes]:
    return [
        # I don't care so much about the seed, just want
        # different blocks.
        gen_block(i, BLOCK_LENGTH)
        for i in range(n_blocks)
    ]

# SHA256 hash.
def H(block: bytes) -> bytes:
    return hashlib.sha256(block).digest()

# Keyed SHA256 compression.
def C(b1: bytes, b2: bytes, key: LayerKey) -> bytes:
    return H(
        # Yes this will probably generate 3
        # allocations for a single compression but
        # hey we're doing Python cause we don't care.
        b1 + b2 + key.value.to_bytes()
    )

def test_should_create_single_node_range() -> None:
    mr = MountainRange(H, C)
    blocks = gen_blocks(1)
    mr.extend(blocks)

    assert len(mr) == 1
    assert mr.root() == C(
        int(1).to_bytes(),
        H(blocks[0]),
        LayerKey.OtherParents
    )

def test_should_create_simple_tree_range() -> None:
    mr = MountainRange(H, C)
    blocks = gen_blocks(2)
    mr.extend(blocks)

    assert len(mr) == 3
    assert mr.root() == C(
        int(len(mr)).to_bytes(),
        C(
            H(blocks[0]), H(blocks[1]),
            LayerKey.DirectParents
        ),
        LayerKey.OtherParents
    )

def test_should_create_complex_tree_range() -> None:
    mr = MountainRange(H, C)
    blocks = gen_blocks(15)
    mr.extend(blocks)
    assert len(mr) == 26
    assert mr.root() == C(
        int(26).to_bytes(),
        C(
            # Subtree with 8 leaves.
            C(
                C(
                    C(H(blocks[0]), H(blocks[1]), LayerKey.DirectParents),
                    C(H(blocks[2]), H(blocks[3]), LayerKey.DirectParents),
                    LayerKey.OtherParents
                ),
                C(
                    C(H(blocks[4]), H(blocks[5]), LayerKey.DirectParents),
                    C(H(blocks[6]), H(blocks[7]), LayerKey.DirectParents),
                    LayerKey.OtherParents
                ),
                LayerKey.OtherParents
            ),
            C(
                # Subtree with 4 leaves.
                C(
                    C(H(blocks[8]), H(blocks[9]), LayerKey.DirectParents),
                    C(H(blocks[10]), H(blocks[11]), LayerKey.DirectParents),
                    LayerKey.OtherParents
                ),
                C(
                    # Subtree with 2 leaves.
                    C(H(blocks[12]), H(blocks[13]), LayerKey.DirectParents),
                    # Subtree with 1 leave.
                    H(blocks[14]),
                    LayerKey.OtherParents
                ),
                LayerKey.OtherParents
            ),
            LayerKey.OtherParents
        ),
        LayerKey.OtherParents
    )
