import logging
import os


def export(state, elapsed):
    if not os.getenv("LANGFUSE_PUBLIC_KEY") or not os.getenv("LANGFUSE_SECRET_KEY"):
        return
    try:
        from langfuse import get_client

        tracer = get_client()
        with tracer.start_as_current_observation(
            name="trippy.plan",
            as_type="span",
            metadata={"trip_id": state.trip_id, "elapsed_ms": int(elapsed * 1000)},
        ):
            for event in state.events:
                kind = "generation" if event.tokens is not None else "span"
                options = (
                    {"usage_details": {"total": event.tokens}}
                    if event.tokens is not None
                    else {}
                )
                with tracer.start_as_current_observation(
                    name=event.component + " / " + event.action,
                    as_type=kind,
                    metadata=event.model_dump(exclude_none=True),
                    **options,
                ):
                    pass
        tracer.flush()
    except Exception as exc:
        logging.getLogger("trippy.trace").warning(
            "Trace export unavailable (%s)", type(exc).__name__
        )
