from __future__ import annotations

from typing import Any, Callable

from pydantic_graph.v2.id_types import ForkId, JoinId


class ReducerContext[StateT, DepsT, InputT]:
    """The main reason this is not a dataclass is that we need it to be covariant in its type parameters."""

    def __init__(self, state: StateT, deps: DepsT, inputs: InputT):
        self._state = state
        self._deps = deps
        self._inputs = inputs

    @property
    def state(self) -> StateT:
        return self._state

    @property
    def deps(self) -> DepsT:
        return self._deps

    @property
    def inputs(self) -> InputT:
        return self._inputs

    def cancel_other_requests(self) -> None:
        raise NotImplementedError

    def __repr__(self):
        return f'{self.__class__.__name__}(state={self.state}, deps={self.deps}, inputs={self.inputs})'


type ReduceFunction[StateT, DepsT, InputT] = Callable[[ReducerContext[StateT, DepsT, InputT]], None]
type FinalizeFunction[StateT, DepsT, OutputT] = Callable[[ReducerContext[StateT, DepsT, None]], OutputT]
# TODO: Need to rework joins so that they are dataclass instances and can be serialized/deserialized.
#  The Join then retains a reference to the reducer type for serialization/deserialization purposes.
type Reducer[StateT, DepsT, InputT, OutputT] = tuple[
    ReduceFunction[StateT, DepsT, InputT], FinalizeFunction[StateT, DepsT, OutputT]
]
type ReducerFactory[StateT, DepsT, InputT, OutputT] = Callable[
    [ReducerContext[StateT, DepsT, InputT]], Reducer[StateT, DepsT, InputT, OutputT]
]


def reduce_to_list[T](item_type: type[T]) -> ReducerFactory[object, object, T, list[T]]:
    def reducer_factory(
        ctx: ReducerContext[object, object, T],
    ) -> Reducer[object, object, T, list[T]]:
        state: list[T] = [ctx.inputs]

        def reduce(_ctx: ReducerContext[object, object, T]) -> None:
            state.append(_ctx.inputs)

        def finalize(_ctx: ReducerContext[object, object, None]) -> list[T]:
            return state

        return reduce, finalize

    return reducer_factory


def reduce_to_dict[T: dict[Any, Any]](dict_type: type[T]) -> ReducerFactory[object, object, T, T]:
    def reducer_factory(
        ctx: ReducerContext[object, object, T],
    ) -> Reducer[object, object, T, T]:
        state: T = dict_type()
        state.update(ctx.inputs)

        def reduce(_ctx: ReducerContext[object, object, T]) -> None:
            state.update(_ctx.inputs)

        def finalize(_ctx: ReducerContext[object, object, None]) -> T:
            return state

        return reduce, finalize

    return reducer_factory


def reduce_to_none(
    ctx: ReducerContext[object, object, Any],
) -> tuple[ReduceFunction[object, object, Any], FinalizeFunction[object, object, None]]:
    def reduce(_ctx: ReducerContext[object, object, Any]) -> None:
        pass

    def finalize(_ctx: ReducerContext[object, object, None]) -> None:
        pass

    return reduce, finalize


class Join[StateT, DepsT, InputT, OutputT]:
    def __init__(
        self, id: JoinId, reducer_factory: ReducerFactory[StateT, DepsT, InputT, OutputT], joins: ForkId | None = None
    ) -> None:
        self.id = id
        self._reducer_factory = reducer_factory
        self.joins = joins

    @property
    def reducer_factory(self) -> ReducerFactory[StateT, DepsT, InputT, OutputT]:
        # reducer_factory cannot be editable due to variance issues; needs to be ReadOnly if in a dataclass
        return self._reducer_factory
