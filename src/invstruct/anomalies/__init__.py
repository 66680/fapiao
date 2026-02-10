from invstruct.anomalies.models import Anomaly


def attach_anomalies(*args, **kwargs):  # type: ignore[no-untyped-def]
    from invstruct.anomalies.engine import attach_anomalies as _attach_anomalies

    return _attach_anomalies(*args, **kwargs)


__all__ = ["Anomaly", "attach_anomalies"]
