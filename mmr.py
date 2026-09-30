from collections.abc import Callable, Iterable
from dataclasses import dataclass
from enum import Enum


class LayerKey(Enum):
    DirectParents = 0x00
    OtherParents = 0x01


# I started with the idea of doing a generic tree but nailing down the
# types would be too time-consuming, so we do a byte tree.
HashFunction = Callable[[bytes], bytes]
CompressionFunction = Callable[[bytes, bytes, LayerKey], bytes]


@dataclass
class Tree:
    root: int
    length: int


class MountainRange:

    def __init__(
            self,
            hash_function: HashFunction,
            compression_function: CompressionFunction
    ) -> None:
        self._nodes: list[bytes] = []
        self._subtrees: list[Tree] = []
        self._H = hash_function
        self._C = compression_function

    def extend(self, nodes: Iterable[bytes]) -> None:
        for node in nodes:
            self.append(node)

    def append(self, node: bytes) -> None:
        self._nodes.append(self._H(node))
        # Node always starts in isolated subtree.
        self._subtrees.append(Tree(
            root=self._subtrees[-1].root + 1
            if len(self._subtrees) > 0 else 0,
            length=1
        ))

        i = len(self._subtrees) - 1
        while i >= 1:
            last = self._subtrees[i]
            before_last = self._subtrees[i - 1]

            if last.length != before_last.length:
                break

            # If same length, merge.
            layer_key = LayerKey.DirectParents if last.length == 1 else LayerKey.OtherParents
            print(f"Merge {before_last.root} and {last.root} with {layer_key}")
            self._subtrees.pop()
            root = self._C(
                self._nodes[before_last.root],
                self._nodes[last.root],
                layer_key
            )
            # Twice the number of nodes + new root.
            before_last.length = 2 * before_last.length + 1
            before_last.root = last.root + 1
            self._nodes.append(root)
            # Merge next.
            i -= 1

    def root(self) -> bytes:
        # ruff: noqa: TRY002
        if len(self._nodes) == 0:
            raise Exception("An empty tree has no root")
        # In herodotus, roots are compressed right-to-left and then
        # Hashed with the size. We likely need positional keys for
        # the trees and perhaps a domain separation key for the root.
        root = self._nodes[self._subtrees[-1].root]
        for i in range(len(self._subtrees) - 1):
            subtree = self._subtrees[-(i + 2)]
            root = self._C(
                self._nodes[subtree.root],
                root,
                LayerKey.OtherParents
            )

        return self._C(
            len(self._nodes).to_bytes(),
            root,
            LayerKey.OtherParents
        )

    def subtrees(self) -> Iterable[Tree]:
        return self._subtrees

    def __len__(self) -> int:
        return len(self._nodes)
